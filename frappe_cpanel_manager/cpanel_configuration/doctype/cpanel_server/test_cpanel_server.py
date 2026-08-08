# Copyright (c) 2026,     Aakvatech-Limited and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from frappe_cpanel_manager.api.server import test_connection
from frappe_cpanel_manager.integrations.cpanel.client import CPanelClient, sanitize_params
from frappe_cpanel_manager.integrations.cpanel.exceptions import CPanelAuthenticationError

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


def make_mock_response(ok, status_code, payload):
	resp = MagicMock()
	resp.ok = ok
	resp.status_code = status_code
	resp.json.return_value = payload
	resp.text = frappe.as_json(payload)
	return resp


class IntegrationTestcPanelServer(IntegrationTestCase):
	"""
	Integration tests for cPanelServer.
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
		frappe.delete_doc("cPanel Server", self.server.name, force=True)

	def test_password_field_round_trips(self):
		client = CPanelClient(self.server)
		self.assertEqual(client.whm_token, "top-secret-token")

	def test_successful_call_updates_status_and_writes_sanitized_log(self):
		success = make_mock_response(True, 200, {"metadata": {"result": 1, "reason": "OK"}, "data": {"version": "11.128"}})

		with patch("frappe_cpanel_manager.integrations.cpanel.client.requests.get", return_value=success):
			result = test_connection(self.server.name)

		self.assertEqual(result["data"]["version"], "11.128")

		self.server.reload()
		self.assertEqual(self.server.last_connection_status, "Success")
		self.assertIsNotNone(self.server.last_connection_test)

		logs = frappe.get_all(
			"cPanel Integration Log",
			filters={"server": self.server.name},
			fields=["status", "sanitized_request"],
		)
		self.assertEqual(len(logs), 1)
		self.assertEqual(logs[0].status, "Success")
		self.assertNotIn("top-secret-token", logs[0].sanitized_request)

	def test_failed_call_raises_and_logs_failure_without_leaking_token(self):
		failure = make_mock_response(False, 401, {"metadata": {"result": 0, "reason": "Invalid Login Attempt"}})

		with patch("frappe_cpanel_manager.integrations.cpanel.client.requests.get", return_value=failure):
			with self.assertRaises(CPanelAuthenticationError):
				test_connection(self.server.name)

		self.server.reload()
		self.assertEqual(self.server.last_connection_status, "Failed")

		log = frappe.get_last_doc("cPanel Integration Log", filters={"server": self.server.name})
		self.assertEqual(log.status, "Failed")
		self.assertIn("Invalid Login Attempt", log.error_message)
		self.assertNotIn("top-secret-token", log.sanitized_request)


class UnitTestCPanelClientHelpers(UnitTestCase):
	"""Pure unit tests for helpers that don't need a doctype or database."""

	def test_sanitize_params_redacts_known_secret_keys(self):
		redacted = sanitize_params(
			{
				"whm_api_token": "secret1",
				"cpanel_token": "secret2",
				"new_password": "secret3",
				"username": "bob",
			}
		)
		self.assertEqual(redacted["whm_api_token"], "***REDACTED***")
		self.assertEqual(redacted["cpanel_token"], "***REDACTED***")
		self.assertEqual(redacted["new_password"], "***REDACTED***")
		self.assertEqual(redacted["username"], "bob")

	def test_sanitize_params_handles_empty_input(self):
		self.assertEqual(sanitize_params(None), None)
		self.assertEqual(sanitize_params({}), {})

	def test_extract_error_reads_whm_metadata_failure(self):
		client = CPanelClient.__new__(CPanelClient)
		error = client._extract_error({"metadata": {"result": 0, "reason": "Access Denied"}})
		self.assertEqual(error, "Access Denied")

	def test_extract_error_reads_uapi_errors_list(self):
		client = CPanelClient.__new__(CPanelClient)
		error = client._extract_error({"result": {"errors": ["Domain not found"]}})
		self.assertEqual(error, "Domain not found")

	def test_extract_error_returns_none_on_success_payload(self):
		client = CPanelClient.__new__(CPanelClient)
		error = client._extract_error({"metadata": {"result": 1}, "data": {}})
		self.assertIsNone(error)
