# Copyright (c) 2026,     Aakvatech-Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime
from frappe.utils.password import remove_encrypted_password

from frappe_cpanel_manager.domain_management.utils import domain_exists_on_server, normalize_domain
from frappe_cpanel_manager.integrations.cpanel.client import CPanelClient
from frappe_cpanel_manager.integrations.cpanel.exceptions import CPanelAPIError, CPanelDuplicateResourceError


class HostedDomain(Document):
	def validate(self):
		self.domain_name = normalize_domain(self.domain_name)
		self._check_duplicate_on_server()

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
		self.db_set("last_api_response", frappe.as_json(result, indent=2), update_modified=False)
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
