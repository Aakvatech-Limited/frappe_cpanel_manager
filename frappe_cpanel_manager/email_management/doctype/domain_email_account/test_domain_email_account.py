# Copyright (c) 2026,     Aakvatech-Limited and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from frappe_cpanel_manager.api.email import (
	change_password,
	create_mailbox,
	delete_mailbox,
	edit_quota,
	suspend_mailbox,
	unsuspend_mailbox,
)
from frappe_cpanel_manager.email_management.utils import normalize_mailbox
from frappe_cpanel_manager.integrations.cpanel.exceptions import CPanelAPIError

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


def make_mock_response(ok, status_code, payload):
	resp = MagicMock()
	resp.ok = ok
	resp.status_code = status_code
	resp.json.return_value = payload
	resp.text = frappe.as_json(payload)
	return resp


SUCCESS = make_mock_response(True, 200, {"metadata": {"result": 1, "reason": "OK"}})
FAILURE = make_mock_response(False, 422, {"metadata": {"result": 0, "reason": "Mailbox already exists."}})


class IntegrationTestDomainEmailAccount(IntegrationTestCase):
	"""
	Integration tests for DomainEmailAccount.
	Use this class for testing interactions between multiple components.
	"""

	def setUp(self):
		self.server = frappe.get_doc(
			{
				"doctype": "cPanel Server",
				"server_name": f"test-server-{frappe.generate_hash(length=8)}",
				"hostname": "whm.example.test",
				"whm_username": "root",
				"whm_api_token": "top-secret-token",
			}
		).insert()
		self.domain = frappe.get_doc(
			{
				"doctype": "Hosted Domain",
				"domain_name": f"mail-{frappe.generate_hash(length=6)}.example.com",
				"server": self.server.name,
				"provisioning_type": "New cPanel Account",
				"cpanel_username": "mailuser",
				"contact_email": "owner@example.com",
				"initial_cpanel_password": "correct-horse-battery",
			}
		).insert()
		self.domain.db_set("status", "Active", update_modified=False)

	def tearDown(self):
		frappe.db.delete("cPanel Integration Log", {"server": self.server.name})
		frappe.db.delete("Domain Email Account", {"hosted_domain": self.domain.name})
		frappe.delete_doc("Hosted Domain", self.domain.name, force=True)
		frappe.delete_doc("cPanel Server", self.server.name, force=True)

	def make_account(self, **kwargs):
		values = {
			"doctype": "Domain Email Account",
			"hosted_domain": self.domain.name,
			"mailbox": "sales",
			"initial_password": "correct-horse-battery",
		}
		values.update(kwargs)
		return frappe.get_doc(values).insert()

	def test_email_address_is_computed_on_save(self):
		doc = self.make_account(mailbox="Sales@ignored.example")
		self.assertEqual(doc.mailbox, "sales")
		self.assertEqual(doc.email_address, f"sales@{self.domain.domain_name}")

	def test_duplicate_mailbox_on_same_domain_is_rejected(self):
		self.make_account(mailbox="dupe")
		with self.assertRaises(frappe.ValidationError):
			self.make_account(mailbox="dupe")

	def test_account_rejected_when_domain_not_active(self):
		self.domain.db_set("status", "Draft", update_modified=False)
		with self.assertRaises(frappe.ValidationError):
			self.make_account(mailbox="toosoon")

	def test_account_rejected_for_dns_only_domain(self):
		dns_only = frappe.get_doc(
			{
				"doctype": "Hosted Domain",
				"domain_name": f"dnsonly-{frappe.generate_hash(length=6)}.example.com",
				"server": self.server.name,
				"provisioning_type": "DNS Only",
			}
		).insert()
		dns_only.db_set("status", "Active", update_modified=False)
		try:
			with self.assertRaises(frappe.ValidationError):
				self.make_account(hosted_domain=dns_only.name, mailbox="nope")
		finally:
			frappe.delete_doc("Hosted Domain", dns_only.name, force=True)

	def test_create_mailbox_success_clears_password_and_logs(self):
		doc = self.make_account(mailbox="success")

		with patch("frappe_cpanel_manager.integrations.cpanel.client.requests.get", return_value=SUCCESS):
			create_mailbox(doc.name)

		doc.reload()
		self.assertEqual(doc.status, "Active")
		self.assertIsNotNone(doc.last_action_on)
		self.assertFalse(doc.get_password("initial_password", raise_exception=False))

		logs = frappe.get_all(
			"cPanel Integration Log",
			filters={"reference_doctype": "Domain Email Account", "reference_name": doc.name},
			fields=["sanitized_request"],
		)
		self.assertEqual(len(logs), 1)
		self.assertNotIn("correct-horse-battery", logs[0].sanitized_request)

	def test_create_mailbox_requires_password(self):
		doc = self.make_account(mailbox="nopassword", initial_password=None)
		with self.assertRaises(frappe.ValidationError):
			create_mailbox(doc.name)

	def test_create_mailbox_failure_records_error_and_status(self):
		doc = self.make_account(mailbox="willfail")

		with patch("frappe_cpanel_manager.integrations.cpanel.client.requests.get", return_value=FAILURE):
			with self.assertRaises(CPanelAPIError):
				create_mailbox(doc.name)

		doc.reload()
		self.assertEqual(doc.status, "Failed")
		self.assertIn("already exists", doc.error_message)

	def test_change_password_requires_existing_mailbox(self):
		doc = self.make_account(mailbox="notyetcreated")
		with self.assertRaises(frappe.ValidationError):
			change_password(doc.name, "new-password-123")

	def test_change_password_success_never_logs_new_password(self):
		doc = self.make_account(mailbox="passwordchange")
		with patch("frappe_cpanel_manager.integrations.cpanel.client.requests.get", return_value=SUCCESS):
			create_mailbox(doc.name)

		with patch("frappe_cpanel_manager.integrations.cpanel.client.requests.get", return_value=SUCCESS):
			change_password(doc.name, "brand-new-secret")

		doc.reload()
		self.assertEqual(doc.status, "Active")

		logs = frappe.get_all(
			"cPanel Integration Log",
			filters={"reference_doctype": "Domain Email Account", "reference_name": doc.name},
			fields=["sanitized_request"],
		)
		for log in logs:
			self.assertNotIn("brand-new-secret", log.sanitized_request)

	def test_edit_quota_updates_local_value(self):
		doc = self.make_account(mailbox="quotachange")
		with patch("frappe_cpanel_manager.integrations.cpanel.client.requests.get", return_value=SUCCESS):
			create_mailbox(doc.name)

		with patch("frappe_cpanel_manager.integrations.cpanel.client.requests.get", return_value=SUCCESS):
			edit_quota(doc.name, 500)

		doc.reload()
		self.assertEqual(doc.quota_mb, 500)

	def test_suspend_and_unsuspend_toggle_status(self):
		doc = self.make_account(mailbox="suspendme")
		with patch("frappe_cpanel_manager.integrations.cpanel.client.requests.get", return_value=SUCCESS):
			create_mailbox(doc.name)

		with patch("frappe_cpanel_manager.integrations.cpanel.client.requests.get", return_value=SUCCESS):
			suspend_mailbox(doc.name)
		doc.reload()
		self.assertEqual(doc.status, "Suspended")

		with self.assertRaises(frappe.ValidationError):
			suspend_mailbox(doc.name)

		with patch("frappe_cpanel_manager.integrations.cpanel.client.requests.get", return_value=SUCCESS):
			unsuspend_mailbox(doc.name)
		doc.reload()
		self.assertEqual(doc.status, "Active")

	def test_delete_mailbox_requires_existing_mailbox(self):
		doc = self.make_account(mailbox="notyetcreateddelete")
		with self.assertRaises(frappe.ValidationError):
			delete_mailbox(doc.name)

	def test_delete_mailbox_success_sets_status_and_logs(self):
		doc = self.make_account(mailbox="deleteme")
		with patch("frappe_cpanel_manager.integrations.cpanel.client.requests.get", return_value=SUCCESS):
			create_mailbox(doc.name)

		with patch("frappe_cpanel_manager.integrations.cpanel.client.requests.get", return_value=SUCCESS):
			delete_mailbox(doc.name)

		doc.reload()
		self.assertEqual(doc.status, "Deleted")
		self.assertIsNotNone(doc.last_action_on)

		logs = frappe.get_all(
			"cPanel Integration Log",
			filters={"reference_doctype": "Domain Email Account", "reference_name": doc.name},
		)
		self.assertEqual(len(logs), 2)

		with self.assertRaises(frappe.ValidationError):
			delete_mailbox(doc.name)

	def test_delete_mailbox_failure_records_error(self):
		doc = self.make_account(mailbox="deletewillfail")
		with patch("frappe_cpanel_manager.integrations.cpanel.client.requests.get", return_value=SUCCESS):
			create_mailbox(doc.name)

		with patch("frappe_cpanel_manager.integrations.cpanel.client.requests.get", return_value=FAILURE):
			with self.assertRaises(CPanelAPIError):
				delete_mailbox(doc.name)

		doc.reload()
		self.assertEqual(doc.status, "Active")
		self.assertIn("already exists", doc.error_message)


class UnitTestNormalizeMailbox(UnitTestCase):
	def test_lowercases_and_accepts_plain_local_part(self):
		self.assertEqual(normalize_mailbox("Sales"), "sales")

	def test_strips_domain_from_full_address(self):
		self.assertEqual(normalize_mailbox("Sales@Example.COM"), "sales")

	def test_rejects_missing_value(self):
		with self.assertRaises(frappe.ValidationError):
			normalize_mailbox("")

	def test_rejects_invalid_characters(self):
		with self.assertRaises(frappe.ValidationError):
			normalize_mailbox("not a valid mailbox!")
