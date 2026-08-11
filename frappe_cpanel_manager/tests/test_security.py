# Copyright (c) 2026,     Aakvatech-Limited and Contributors
# See license.txt
#
# Phase 5 security test suite: the role/permission matrix, field-level
# restriction of token/password fields, and the response-sanitization
# guarantee (a secret must never survive into a stored log or response,
# even if a provider response happens to echo one back).

from unittest.mock import MagicMock, patch

import frappe
from frappe.model import get_permitted_fields
from frappe.tests import IntegrationTestCase, UnitTestCase

from frappe_cpanel_manager.api.domain import provision_domain
from frappe_cpanel_manager.api.email import create_mailbox
from frappe_cpanel_manager.integrations.cpanel.client import sanitize_params

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []

ROLES = [
	"cPanel Manager Administrator",
	"cPanel Manager Operator",
	"cPanel Manager Email Administrator",
	"cPanel Manager Support",
	"cPanel Manager Auditor",
]


def get_permlevel_roles(doctype, permlevel):
	rows = frappe.get_all(
		"DocPerm", filters={"parent": doctype, "permlevel": permlevel, "read": 1}, fields=["role"]
	)
	return {row.role for row in rows}


def get_base_perm(doctype, role):
	rows = frappe.get_all(
		"DocPerm",
		filters={"parent": doctype, "permlevel": 0, "role": role},
		fields=["create", "write", "delete", "read"],
	)
	return rows[0] if rows else None


def make_mock_response(ok, status_code, payload):
	resp = MagicMock()
	resp.ok = ok
	resp.status_code = status_code
	resp.json.return_value = payload
	resp.text = frappe.as_json(payload)
	return resp


class UnitTestSanitizeParams(UnitTestCase):
	def test_redacts_nested_dict_values(self):
		redacted = sanitize_params({"data": {"acct": [{"password": "leak-me", "domain": "example.com"}]}})
		self.assertEqual(redacted["data"]["acct"][0]["password"], "***REDACTED***")
		self.assertEqual(redacted["data"]["acct"][0]["domain"], "example.com")

	def test_redacts_secret_keys_inside_lists(self):
		redacted = sanitize_params({"items": [{"token": "abc"}, {"note": "fine"}]})
		self.assertEqual(redacted["items"][0]["token"], "***REDACTED***")
		self.assertEqual(redacted["items"][1]["note"], "fine")

	def test_non_dict_non_list_values_pass_through(self):
		self.assertEqual(sanitize_params("just a string"), "just a string")
		self.assertEqual(sanitize_params(None), None)
		self.assertEqual(sanitize_params(42), 42)


class UnitTestPermissionMatrix(UnitTestCase):
	"""Declarative checks that the shipped DocPerm rows match the intended matrix.
	These don't touch the database beyond reading DocPerm, so they run as unit tests."""

	def test_all_five_roles_are_defined(self):
		for role in ROLES:
			self.assertTrue(frappe.db.exists("Role", role), f"{role} is missing")

	def test_cpanel_server_token_restricted_to_administrators_only(self):
		self.assertEqual(
			get_permlevel_roles("cPanel Server", 1),
			{"System Manager", "cPanel Manager Administrator"},
		)

	def test_hosted_domain_password_open_to_operator_too(self):
		self.assertEqual(
			get_permlevel_roles("Hosted Domain", 1),
			{"System Manager", "cPanel Manager Administrator", "cPanel Manager Operator"},
		)

	def test_domain_email_account_password_open_to_email_administrator_too(self):
		self.assertEqual(
			get_permlevel_roles("Domain Email Account", 1),
			{"System Manager", "cPanel Manager Administrator", "cPanel Manager Email Administrator"},
		)

	def test_support_and_auditor_are_read_only_on_every_provisioning_doctype(self):
		for doctype in ("cPanel Server", "Hosted Domain", "Domain Email Account"):
			for role in ("cPanel Manager Support", "cPanel Manager Auditor"):
				perm = get_base_perm(doctype, role)
				self.assertIsNotNone(perm, f"{role} has no permission row on {doctype}")
				self.assertEqual(perm.write, 0, f"{role} should not have write on {doctype}")
				self.assertEqual(perm.create, 0, f"{role} should not have create on {doctype}")
				self.assertEqual(perm.delete, 0, f"{role} should not have delete on {doctype}")
				self.assertEqual(perm.read, 1, f"{role} should have read on {doctype}")

	def test_operator_has_no_access_to_domain_email_account(self):
		self.assertIsNone(get_base_perm("Domain Email Account", "cPanel Manager Operator"))

	def test_email_administrator_cannot_write_hosted_domain(self):
		perm = get_base_perm("Hosted Domain", "cPanel Manager Email Administrator")
		self.assertIsNotNone(perm)
		self.assertEqual(perm.read, 1)
		self.assertEqual(perm.write, 0)
		self.assertEqual(perm.create, 0)

	def test_auditor_can_read_integration_log_but_not_write(self):
		perm = get_base_perm("cPanel Integration Log", "cPanel Manager Auditor")
		self.assertIsNotNone(perm)
		self.assertEqual(perm.read, 1)
		self.assertEqual(perm.write, 0)

	def test_no_role_besides_admins_gets_delete_on_cpanel_server(self):
		for role in ("cPanel Manager Operator", "cPanel Manager Support", "cPanel Manager Auditor"):
			perm = get_base_perm("cPanel Server", role)
			self.assertIsNotNone(perm)
			self.assertEqual(perm.delete, 0, f"{role} should not be able to delete cPanel Server records")


class IntegrationTestPermissionEnforcement(IntegrationTestCase):
	"""Behavioral checks: an actual user with a narrow role is blocked by the
	framework, not just declared as blocked in DocPerm rows."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.server = frappe.get_doc(
			{
				"doctype": "cPanel Server",
				"server_name": f"sectest-server-{frappe.generate_hash(length=8)}",
				"hostname": "whm.example.test",
				"whm_username": "root",
				"whm_api_token": "top-secret-token",
			}
		).insert(ignore_permissions=True)
		cls.domain = frappe.get_doc(
			{
				"doctype": "Hosted Domain",
				"domain_name": f"sectest-{frappe.generate_hash(length=6)}.example.com",
				"server": cls.server.name,
				"provisioning_type": "New cPanel Account",
				"cpanel_username": "sectestuser",
				"contact_email": "owner@example.com",
				"initial_cpanel_password": "correct-horse-battery",
			}
		).insert(ignore_permissions=True)
		cls.domain.db_set("status", "Active", update_modified=False)

		cls.support_user = cls._make_user("cpanelsec-support@example.test", ["cPanel Manager Support"])
		cls.operator_user = cls._make_user("cpanelsec-operator@example.test", ["cPanel Manager Operator"])
		cls.auditor_user = cls._make_user("cpanelsec-auditor@example.test", ["cPanel Manager Auditor"])
		cls.admin_role_user = cls._make_user(
			"cpanelsec-admin@example.test", ["cPanel Manager Administrator"]
		)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		frappe.db.delete("cPanel Integration Log", {"server": cls.server.name})
		frappe.delete_doc("Hosted Domain", cls.domain.name, force=True, ignore_permissions=True)
		frappe.delete_doc("cPanel Server", cls.server.name, force=True, ignore_permissions=True)
		for email in (cls.support_user, cls.operator_user, cls.auditor_user, cls.admin_role_user):
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)
		super().tearDownClass()

	@staticmethod
	def _make_user(email, roles):
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
				"roles": [{"role": role} for role in roles],
			}
		).insert(ignore_permissions=True)
		return user.name

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_support_user_cannot_create_hosted_domain(self):
		frappe.set_user(self.support_user)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{
					"doctype": "Hosted Domain",
					"domain_name": "shouldfail.example.com",
					"server": self.server.name,
					"provisioning_type": "DNS Only",
				}
			).insert()

	def test_support_user_cannot_call_provision_domain(self):
		frappe.set_user(self.support_user)
		with self.assertRaises(frappe.PermissionError):
			provision_domain(self.domain.name)

	def test_support_user_cannot_call_create_mailbox(self):
		account = frappe.get_doc(
			{
				"doctype": "Domain Email Account",
				"hosted_domain": self.domain.name,
				"mailbox": "sectest",
				"initial_password": "correct-horse-battery",
			}
		).insert(ignore_permissions=True)
		try:
			frappe.set_user(self.support_user)
			with self.assertRaises(frappe.PermissionError):
				create_mailbox(account.name)
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("Domain Email Account", account.name, force=True, ignore_permissions=True)

	def test_operator_cannot_see_whm_api_token_field(self):
		fields = get_permitted_fields("cPanel Server", user=self.operator_user, permission_type="read")
		self.assertNotIn("whm_api_token", fields)
		self.assertIn("hostname", fields)

	def test_administrator_role_can_see_whm_api_token_field(self):
		fields = get_permitted_fields("cPanel Server", user=self.admin_role_user, permission_type="read")
		self.assertIn("whm_api_token", fields)

	def test_support_user_cannot_see_hosted_domain_password_field(self):
		fields = get_permitted_fields("Hosted Domain", user=self.support_user, permission_type="read")
		self.assertNotIn("initial_cpanel_password", fields)
		self.assertIn("domain_name", fields)

	def test_operator_can_see_hosted_domain_password_field(self):
		fields = get_permitted_fields("Hosted Domain", user=self.operator_user, permission_type="read")
		self.assertIn("initial_cpanel_password", fields)

	def test_auditor_cannot_edit_existing_integration_log(self):
		log = frappe.get_doc(
			{
				"doctype": "cPanel Integration Log",
				"server": self.server.name,
				"operation": "version",
				"api_layer": "WHM API 1",
				"status": "Success",
			}
		).insert(ignore_permissions=True)
		try:
			frappe.set_user(self.auditor_user)
			log_as_auditor = frappe.get_doc("cPanel Integration Log", log.name)
			log_as_auditor.error_message = "tampered"
			with self.assertRaises(frappe.PermissionError):
				log_as_auditor.save()
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("cPanel Integration Log", log.name, force=True, ignore_permissions=True)


class IntegrationTestResponseSanitization(IntegrationTestCase):
	"""Regression coverage for the Phase 5 fix: API responses are redacted the
	same way request params always were, so a provider that echoes back a
	submitted secret can't leak it into a stored log or document field."""

	def setUp(self):
		self.server = frappe.get_doc(
			{
				"doctype": "cPanel Server",
				"server_name": f"sanitize-server-{frappe.generate_hash(length=8)}",
				"hostname": "whm.example.test",
				"whm_username": "root",
				"whm_api_token": "top-secret-token",
			}
		).insert()
		self.domain = frappe.get_doc(
			{
				"doctype": "Hosted Domain",
				"domain_name": f"sanitize-{frappe.generate_hash(length=6)}.example.com",
				"server": self.server.name,
				"provisioning_type": "New cPanel Account",
				"cpanel_username": "sanitizeuser",
				"contact_email": "owner@example.com",
				"initial_cpanel_password": "correct-horse-battery",
			}
		).insert()

	def tearDown(self):
		frappe.db.delete("cPanel Integration Log", {"server": self.server.name})
		frappe.delete_doc("Hosted Domain", self.domain.name, force=True)
		frappe.delete_doc("cPanel Server", self.server.name, force=True)

	def test_response_that_echoes_a_password_is_redacted_in_the_log_and_on_the_document(self):
		echoing_response = make_mock_response(
			True,
			200,
			{
				"metadata": {"result": 1, "reason": "OK"},
				"data": {"result": 1, "password": "correct-horse-battery"},
			},
		)

		with patch(
			"frappe_cpanel_manager.integrations.cpanel.client.requests.get",
			return_value=echoing_response,
		):
			provision_domain(self.domain.name)

		self.domain.reload()
		self.assertNotIn("correct-horse-battery", self.domain.last_api_response)
		self.assertIn("REDACTED", self.domain.last_api_response)

		log = frappe.get_last_doc(
			"cPanel Integration Log",
			filters={"reference_doctype": "Hosted Domain", "reference_name": self.domain.name},
		)
		self.assertNotIn("correct-horse-battery", log.sanitized_response)
		self.assertIn("REDACTED", log.sanitized_response)
