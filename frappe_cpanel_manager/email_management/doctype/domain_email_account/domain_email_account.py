# Copyright (c) 2026,     Aakvatech-Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime
from frappe.utils.password import remove_encrypted_password

from frappe_cpanel_manager.email_management.utils import normalize_mailbox
from frappe_cpanel_manager.integrations.cpanel.client import CPanelClient, sanitize_params
from frappe_cpanel_manager.integrations.cpanel.exceptions import CPanelAPIError


class DomainEmailAccount(Document):
	def validate(self):
		self.mailbox = normalize_mailbox(self.mailbox)
		domain = self._get_hosted_domain()

		if domain.provisioning_type != "New cPanel Account" or not domain.cpanel_username:
			frappe.throw(
				_("{0} is DNS Only and has no cPanel account to hold mailboxes.").format(domain.domain_name)
			)
		if domain.status != "Active":
			frappe.throw(
				_("{0} must be provisioned (Active) before adding email accounts.").format(domain.domain_name)
			)

		self.email_address = f"{self.mailbox}@{domain.domain_name}"
		self._check_duplicate_on_domain()

	def _check_duplicate_on_domain(self):
		duplicate = frappe.db.exists(
			"Domain Email Account",
			{
				"hosted_domain": self.hosted_domain,
				"mailbox": self.mailbox,
				"name": ["!=", self.name or ""],
			},
		)
		if duplicate:
			frappe.throw(_("Mailbox {0} already exists on {1}.").format(self.mailbox, self.hosted_domain))

	def _get_hosted_domain(self):
		"""Always re-read the parent Hosted Domain rather than caching/fetching its
		fields onto this doc -- cpanel_username/status can change after this record
		is created, and stale copies would silently target the wrong account."""
		return frappe.get_doc("Hosted Domain", self.hosted_domain)

	def _call_email_uapi(self, function_name, params, domain=None):
		domain = domain or self._get_hosted_domain()
		client = CPanelClient(domain.server)
		return client.call_uapi_via_whm(
			domain.cpanel_username,
			"Email",
			function_name,
			params,
			reference_doctype=self.doctype,
			reference_name=self.name,
		)

	def create_mailbox(self):
		if self.status != "Draft":
			frappe.throw(_("This mailbox has already been created."))

		domain = self._get_hosted_domain()
		password = self.get_password("initial_password", raise_exception=False)
		if not password:
			frappe.throw(_("Initial Password is required to create the mailbox."))

		self.db_set("status", "Creating", update_modified=False)
		try:
			result = self._call_email_uapi(
				"add_pop",
				{
					"email": self.mailbox,
					"domain": domain.domain_name,
					"password": password,
					"quota": self.quota_mb or 0,
				},
				domain=domain,
			)
		except CPanelAPIError as e:
			self.db_set("status", "Failed", update_modified=False)
			self.db_set("error_message", str(e), update_modified=False)
			frappe.throw(str(e), exc=type(e), title=_("Mailbox Creation Failed"))

		self.db_set("status", "Active", update_modified=False)
		self.db_set("last_action_on", now_datetime(), update_modified=False)
		self.db_set(
			"last_api_response", frappe.as_json(sanitize_params(result), indent=2), update_modified=False
		)
		self.db_set("error_message", "", update_modified=False)
		if self.get_password("initial_password", raise_exception=False):
			remove_encrypted_password(self.doctype, self.name, "initial_password")
			self.db_set("initial_password", "", update_modified=False)

	def change_password(self, new_password):
		if self.status not in ("Active", "Suspended"):
			frappe.throw(_("The mailbox must exist on the server before its password can be changed."))
		if not new_password:
			frappe.throw(_("A new password is required."))

		domain = self._get_hosted_domain()
		try:
			result = self._call_email_uapi(
				"passwd_pop",
				{"email": self.mailbox, "domain": domain.domain_name, "password": new_password},
				domain=domain,
			)
		except CPanelAPIError as e:
			self.db_set("error_message", str(e), update_modified=False)
			frappe.throw(str(e), exc=type(e), title=_("Password Change Failed"))

		self.db_set("last_action_on", now_datetime(), update_modified=False)
		self.db_set(
			"last_api_response", frappe.as_json(sanitize_params(result), indent=2), update_modified=False
		)
		self.db_set("error_message", "", update_modified=False)

	def edit_quota(self, quota_mb):
		if self.status not in ("Active", "Suspended"):
			frappe.throw(_("The mailbox must exist on the server before its quota can be changed."))

		domain = self._get_hosted_domain()
		try:
			result = self._call_email_uapi(
				"edit_pop_quota",
				{"email": self.mailbox, "domain": domain.domain_name, "quota": quota_mb or 0},
				domain=domain,
			)
		except CPanelAPIError as e:
			self.db_set("error_message", str(e), update_modified=False)
			frappe.throw(str(e), exc=type(e), title=_("Quota Change Failed"))

		self.db_set("quota_mb", quota_mb or 0, update_modified=False)
		self.db_set("last_action_on", now_datetime(), update_modified=False)
		self.db_set(
			"last_api_response", frappe.as_json(sanitize_params(result), indent=2), update_modified=False
		)
		self.db_set("error_message", "", update_modified=False)

	def suspend(self):
		if self.status != "Active":
			frappe.throw(_("Only an active mailbox can be suspended."))
		self._set_suspension("suspend_login", "Suspended")

	def unsuspend(self):
		if self.status != "Suspended":
			frappe.throw(_("Only a suspended mailbox can be unsuspended."))
		self._set_suspension("unsuspend_login", "Active")

	def delete_mailbox(self):
		if self.status not in ("Active", "Suspended"):
			frappe.throw(_("Only an existing mailbox (Active or Suspended) can be deleted."))

		domain = self._get_hosted_domain()
		try:
			result = self._call_email_uapi(
				"delete_pop", {"email": self.mailbox, "domain": domain.domain_name}, domain=domain
			)
		except CPanelAPIError as e:
			self.db_set("error_message", str(e), update_modified=False)
			frappe.throw(str(e), exc=type(e), title=_("Mailbox Deletion Failed"))

		self.db_set("status", "Deleted", update_modified=False)
		self.db_set("last_action_on", now_datetime(), update_modified=False)
		self.db_set(
			"last_api_response", frappe.as_json(sanitize_params(result), indent=2), update_modified=False
		)
		self.db_set("error_message", "", update_modified=False)

	def _set_suspension(self, function_name, new_status):
		domain = self._get_hosted_domain()
		try:
			result = self._call_email_uapi(
				function_name, {"email": self.mailbox, "domain": domain.domain_name}, domain=domain
			)
		except CPanelAPIError as e:
			self.db_set("error_message", str(e), update_modified=False)
			frappe.throw(str(e), exc=type(e), title=_("Mailbox Update Failed"))

		self.db_set("status", new_status, update_modified=False)
		self.db_set("last_action_on", now_datetime(), update_modified=False)
		self.db_set(
			"last_api_response", frappe.as_json(sanitize_params(result), indent=2), update_modified=False
		)
		self.db_set("error_message", "", update_modified=False)
