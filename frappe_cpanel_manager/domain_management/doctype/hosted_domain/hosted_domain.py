# Copyright (c) 2026,     Aakvatech-Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime
from frappe.utils.password import remove_encrypted_password

from frappe_cpanel_manager.domain_management.utils import (
	DNS_RECORD_TYPES,
	dns_name_from_fqdn,
	dns_name_to_fqdn,
	domain_exists_on_server,
	normalize_domain,
)
from frappe_cpanel_manager.integrations.cpanel.client import CPanelClient, sanitize_params
from frappe_cpanel_manager.integrations.cpanel.exceptions import CPanelAPIError, CPanelDuplicateResourceError


class HostedDomain(Document):
	def validate(self):
		self.domain_name = normalize_domain(self.domain_name)
		self._check_duplicate_on_server()
		self._validate_dns_records()

	def _check_duplicate_on_server(self):
		duplicate = frappe.db.exists(
			"Hosted Domain",
			{
				"domain_name": self.domain_name,
				"server": self.server,
				"name": ["!=", self.name or ""],
			},
		)
		if duplicate:
			frappe.throw(
				_("Domain {0} is already hosted on server {1}.").format(self.domain_name, self.server)
			)

	def _validate_dns_records(self):
		types_by_name = {}
		for row in self.dns_records or []:
			types_by_name.setdefault(row.record_name, []).append(row.record_type)

		for record_name, types in types_by_name.items():
			if "CNAME" in types and len(types) > 1:
				frappe.throw(
					_(
						"{0} has a CNAME record and cannot have any other record type at the same name."
					).format(record_name)
				)

	def enqueue_provision(self):
		"""Queue a provisioning run so long-running or transient failures can be retried safely."""
		self.db_set("status", "Queued", update_modified=False)
		frappe.enqueue(
			"frappe_cpanel_manager.integrations.cpanel.operations.process_hosted_domain_provision",
			queue="long",
			docname=self.name,
			job_name=f"Hosted Domain:{self.name}:provision",
			enqueue_after_commit=True,
		)
		return {"status": self.status}

	def provision(self):
		client = CPanelClient(self.server)

		if domain_exists_on_server(client, self.domain_name):
			frappe.throw(
				_("Domain {0} already exists on the target server.").format(self.domain_name),
				exc=CPanelDuplicateResourceError,
			)

		self.db_set("status", "Provisioning", update_modified=False)
		function_name, params = self._build_provision_request()

		try:
			result = client.call_whm(
				function_name, params, reference_doctype=self.doctype, reference_name=self.name
			)
		except CPanelAPIError as e:
			self.db_set("status", "Failed", update_modified=False)
			self.db_set("error_message", str(e), update_modified=False)
			frappe.throw(str(e), exc=type(e), title=_("Provisioning Failed"))

		self.db_set("status", "Active", update_modified=False)
		self.db_set("last_provisioned_on", now_datetime(), update_modified=False)
		self.db_set(
			"last_api_response", frappe.as_json(sanitize_params(result), indent=2), update_modified=False
		)
		self.db_set("error_message", "", update_modified=False)
		if self.get_password("initial_cpanel_password", raise_exception=False):
			remove_encrypted_password(self.doctype, self.name, "initial_cpanel_password")
			self.db_set("initial_cpanel_password", "", update_modified=False)

	def _build_provision_request(self):
		if self.provisioning_type == "DNS Only":
			params = {"domain": self.domain_name}
			if self.ip_address:
				params["ip"] = self.ip_address
			return "adddns", params

		if not self.cpanel_username:
			frappe.throw(_("cPanel Username is required for a New cPanel Account."))
		password = self.get_password("initial_cpanel_password", raise_exception=False)
		if not password:
			frappe.throw(_("Initial cPanel Password is required for a New cPanel Account."))

		params = {
			"username": self.cpanel_username,
			"domain": self.domain_name,
			"password": password,
			"contactemail": self.contact_email,
		}
		if self.hosting_package:
			params["plan"] = self.hosting_package
		if self.ip_address:
			params["ip"] = self.ip_address
		return "createacct", params

	def sync_dns_from_server(self):
		"""Overwrite the local `dns_records` table with the zone currently on the server."""
		client = CPanelClient(self.server)
		result = client.call_whm(
			"dumpzone", {"domain": self.domain_name}, reference_doctype=self.doctype, reference_name=self.name
		)
		self.set("dns_records", self._parse_zone_records(result))
		self.save()

	def _parse_zone_records(self, result):
		"""Map WHM API 1 `dumpzone` output onto Domain DNS Record rows.

		Confirmed against a live WHM server: the payload is
		`{"data": {"zone": [{"record": [...]}]}, "metadata": {...}}`. A
		`{"dnszone": [...]}` fallback is kept for older/alternate shapes.
		Only the record types this app manages (frappe_cpanel_manager.domain_management.utils.DNS_RECORD_TYPES)
		are kept; SOA/apex control entries are skipped so a sync never touches them.
		"""
		entries = None
		zone_list = (result.get("data") or {}).get("zone")
		if isinstance(zone_list, list) and zone_list:
			entries = zone_list[0].get("record")
		if entries is None:
			entries = result.get("dnszone")
		entries = entries or []

		rows = []
		for entry in entries:
			record_type = (entry.get("type") or "").upper()
			if record_type not in DNS_RECORD_TYPES:
				continue

			value = (
				entry.get("address")
				or entry.get("cname")
				or entry.get("exchange")
				or entry.get("nsdname")
				or entry.get("target")
				or entry.get("txtdata")
				or (entry.get("value") if record_type == "CAA" else None)
				or ""
			)
			rows.append(
				{
					"record_type": record_type,
					"record_name": dns_name_from_fqdn(entry.get("name"), self.domain_name),
					"value": value.rstrip(".") if value else value,
					"ttl": cint(entry.get("ttl")) or 14400,
					"priority": cint(entry.get("preference") or entry.get("priority") or 0) or None,
					"weight": cint(entry.get("weight")) if record_type == "SRV" else None,
					"port": cint(entry.get("port")) if record_type == "SRV" else None,
					"caa_flag": cint(entry.get("flag")) if record_type == "CAA" else None,
					"caa_tag": entry.get("tag") if record_type == "CAA" else None,
					"zone_line": entry.get("Line") or entry.get("line"),
				}
			)
		return rows

	def apply_dns_changes(self):
		"""Push every local DNS record row to the server: rows with a `zone_line` are
		updated in place, rows without one are treated as new. Re-syncs from the
		server afterwards so `zone_line` reflects the server's canonical state
		(the add/edit calls don't reliably return the new line number)."""
		client = CPanelClient(self.server)
		for row in self.dns_records or []:
			params = self._build_dns_record_params(row)
			if row.zone_line:
				params["line"] = row.zone_line
				client.call_whm(
					"editzonerecord", params, reference_doctype=self.doctype, reference_name=self.name
				)
			else:
				client.call_whm(
					"addzonerecord", params, reference_doctype=self.doctype, reference_name=self.name
				)
		self.sync_dns_from_server()

	def _build_dns_record_params(self, row):
		params = {
			"domain": self.domain_name,
			"name": dns_name_to_fqdn(row.record_name, self.domain_name),
			"type": row.record_type,
			"ttl": row.ttl or 14400,
			"class": "IN",
		}
		if row.record_type in ("A", "AAAA"):
			params["address"] = row.value
		elif row.record_type == "CNAME":
			params["cname"] = row.value
		elif row.record_type == "MX":
			params["exchange"] = row.value
			params["preference"] = row.priority
		elif row.record_type == "NS":
			params["nsdname"] = row.value
		elif row.record_type == "SRV":
			params["target"] = row.value
			params["priority"] = row.priority
			params["weight"] = row.weight
			params["port"] = row.port
		elif row.record_type == "CAA":
			params["flag"] = row.caa_flag or 0
			params["tag"] = row.caa_tag
			params["value"] = row.value
		elif row.record_type == "TXT":
			params["txtdata"] = row.value
		return params

	def remove_dns_record(self, row_name):
		"""Delete a single DNS record: remove it on the server (if it has ever been
		synced) then drop the local row. Deliberately explicit and per-row rather
		than inferred from a table diff, since a DNS deletion is hard to reverse."""
		row = next((r for r in (self.dns_records or []) if r.name == row_name), None)
		if not row:
			frappe.throw(_("DNS record row {0} not found.").format(row_name))

		if row.zone_line:
			client = CPanelClient(self.server)
			client.call_whm(
				"removezonerecord",
				{"domain": self.domain_name, "line": row.zone_line},
				reference_doctype=self.doctype,
				reference_name=self.name,
			)

		self.dns_records = [r for r in self.dns_records if r.name != row_name]
		self.save()
