# Copyright (c) 2026,     Aakvatech-Limited and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from frappe_cpanel_manager.api.domain import provision_domain
from frappe_cpanel_manager.domain_management.utils import normalize_domain
from frappe_cpanel_manager.integrations.cpanel.exceptions import CPanelAPIError, CPanelDuplicateResourceError

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


def make_mock_response(ok, status_code, payload):
	resp = MagicMock()
	resp.ok = ok
	resp.status_code = status_code
	resp.json.return_value = payload
	resp.text = frappe.as_json(payload)
	return resp


NO_MATCH = make_mock_response(True, 200, {"metadata": {"result": 1}, "data": {"acct": []}})


class IntegrationTestHostedDomain(IntegrationTestCase):
	"""
	Integration tests for HostedDomain.
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

	def tearDown(self):
		frappe.db.delete("cPanel Integration Log", {"server": self.server.name})
		frappe.db.delete("Hosted Domain", {"server": self.server.name})
		frappe.delete_doc("cPanel Server", self.server.name, force=True)

	def make_domain(self, **kwargs):
		values = {
			"doctype": "Hosted Domain",
			"domain_name": "Example.COM",
			"server": self.server.name,
			"provisioning_type": "New cPanel Account",
			"cpanel_username": "exampleuser",
			"contact_email": "owner@example.com",
			"initial_cpanel_password": "correct-horse-battery",
		}
		values.update(kwargs)
		return frappe.get_doc(values).insert()

	def test_domain_name_is_normalized_on_save(self):
		doc = self.make_domain(domain_name="HTTPS://Example.ORG/some/path")
		self.assertEqual(doc.domain_name, "example.org")

	def test_duplicate_domain_on_same_server_is_rejected(self):
		self.make_domain(domain_name="dupe.example.com")
		with self.assertRaises(frappe.ValidationError):
			self.make_domain(domain_name="dupe.example.com")

	def test_provision_new_account_success_clears_password_and_logs(self):
		doc = self.make_domain(domain_name="newaccount.example.com")
		success = make_mock_response(
			True, 200, {"metadata": {"result": 1, "reason": "OK"}, "data": {"result": 1}}
		)

		with patch(
			"frappe_cpanel_manager.integrations.cpanel.client.requests.get",
			side_effect=[NO_MATCH, success],
		):
			provision_domain(doc.name)

		doc.reload()
		self.assertEqual(doc.status, "Active")
		self.assertIsNotNone(doc.last_provisioned_on)
		self.assertFalse(doc.get_password("initial_cpanel_password", raise_exception=False))

		logs = frappe.get_all(
			"cPanel Integration Log",
			filters={"reference_doctype": "Hosted Domain", "reference_name": doc.name},
			fields=["operation", "status", "sanitized_request"],
		)
		self.assertEqual(len(logs), 1)
		self.assertEqual(logs[0].operation, "createacct")
		self.assertNotIn("correct-horse-battery", logs[0].sanitized_request)

	def test_provision_dns_only_does_not_require_account_fields(self):
		doc = self.make_domain(
			domain_name="dnsonly.example.com",
			provisioning_type="DNS Only",
			cpanel_username=None,
			contact_email=None,
			initial_cpanel_password=None,
		)
		success = make_mock_response(True, 200, {"metadata": {"result": 1, "reason": "OK"}})

		with patch(
			"frappe_cpanel_manager.integrations.cpanel.client.requests.get",
			side_effect=[NO_MATCH, success],
		):
			provision_domain(doc.name)

		doc.reload()
		self.assertEqual(doc.status, "Active")

	def test_provision_fails_when_domain_already_exists_on_server(self):
		doc = self.make_domain(domain_name="existing.example.com")
		already_exists = make_mock_response(
			True, 200, {"metadata": {"result": 1}, "data": {"acct": [{"domain": "existing.example.com"}]}}
		)

		with patch(
			"frappe_cpanel_manager.integrations.cpanel.client.requests.get",
			return_value=already_exists,
		):
			with self.assertRaises(CPanelDuplicateResourceError):
				provision_domain(doc.name)

		doc.reload()
		self.assertEqual(doc.status, "Draft")

	def test_provision_failure_records_error_and_status(self):
		doc = self.make_domain(domain_name="willfail.example.com")
		failure = make_mock_response(
			False, 422, {"metadata": {"result": 0, "reason": "Sorry, that domain is already registered."}}
		)

		with patch(
			"frappe_cpanel_manager.integrations.cpanel.client.requests.get",
			side_effect=[NO_MATCH, failure],
		):
			with self.assertRaises(CPanelAPIError):
				provision_domain(doc.name)

		doc.reload()
		self.assertEqual(doc.status, "Failed")
		self.assertIn("already registered", doc.error_message)


class UnitTestNormalizeDomain(UnitTestCase):
	def test_strips_scheme_path_query_and_port(self):
		self.assertEqual(normalize_domain("HTTPS://Example.COM:8443/some/path?x=1#y"), "example.com")

	def test_strips_trailing_dot(self):
		self.assertEqual(normalize_domain("example.com."), "example.com")

	def test_rejects_missing_domain(self):
		with self.assertRaises(frappe.ValidationError):
			normalize_domain("")

	def test_rejects_bare_hostname_without_tld(self):
		with self.assertRaises(frappe.ValidationError):
			normalize_domain("localhost")
