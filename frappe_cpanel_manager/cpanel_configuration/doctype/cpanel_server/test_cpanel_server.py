# Copyright (c) 2026,     Aakvatech-Limited and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from frappe_cpanel_manager.api.server import test_connection
from frappe_cpanel_manager.integrations.cpanel.client import CPanelClient, sanitize_params
from frappe_cpanel_manager.integrations.cpanel.exceptions import (
	CPanelAPIError,
	CPanelAuthenticationError,
	CPanelTimeoutError,
	error_category,
	friendly_message,
)

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
		success = make_mock_response(
			True, 200, {"metadata": {"result": 1, "reason": "OK"}, "data": {"version": "11.128"}}
		)

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
		failure = make_mock_response(
			False, 401, {"metadata": {"result": 0, "reason": "Invalid Login Attempt"}}
		)

		with patch("frappe_cpanel_manager.integrations.cpanel.client.requests.get", return_value=failure):
			with self.assertRaises(CPanelAuthenticationError):
				test_connection(self.server.name)

		self.server.reload()
		self.assertEqual(self.server.last_connection_status, "Failed")

		log = frappe.get_last_doc("cPanel Integration Log", filters={"server": self.server.name})
		self.assertEqual(log.status, "Failed")
		self.assertIn("Invalid Login Attempt", log.error_message)
		self.assertNotIn("top-secret-token", log.sanitized_request)

	def test_fetch_server_information_reads_only(self):
		from frappe_cpanel_manager.api.server import fetch_server_information

		success = make_mock_response(
			True,
			200,
			{"metadata": {"result": 1}, "data": {"version": "11.128", "hostname": "h", "one": "0.4"}},
		)
		with patch("frappe_cpanel_manager.integrations.cpanel.client.requests.get", return_value=success):
			info = fetch_server_information(self.server.name)

		self.assertEqual(info["version"], "11.128")
		self.assertEqual(info["hostname"], "h")
		self.assertEqual(info["load_average"], "0.4")

	def test_fetch_server_information_degrades_per_lookup(self):
		"""A token missing one privilege must not blank out the whole panel."""
		from frappe_cpanel_manager.api.server import fetch_server_information

		ok = make_mock_response(True, 200, {"metadata": {"result": 1}, "data": {"version": "11.128"}})
		denied = make_mock_response(False, 403, {"metadata": {"result": 0, "reason": "Access denied"}})
		with patch(
			"frappe_cpanel_manager.integrations.cpanel.client.requests.get",
			side_effect=[ok, denied, denied],
		):
			info = fetch_server_information(self.server.name)

		self.assertEqual(info["version"], "11.128")
		self.assertIn("Unavailable", info["hostname"])


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

	# The API 2 payloads below are copied verbatim from a live server (shaule.space),
	# not invented -- an API 2 failure used to be reported as success.
	def test_extract_error_reads_api2_error_key(self):
		client = CPanelClient.__new__(CPanelClient)
		error = client._extract_error(
			{
				"cpanelresult": {
					"apiversion": 2,
					"data": {
						"reason": "Could not find function 'nope' in module 'Park'",
						"result": 0,
					},
					"error": "Could not find function 'nope' in module 'Park'",
					"func": "nope",
					"module": "Park",
				}
			}
		)
		self.assertEqual(error, "Could not find function 'nope' in module 'Park'")

	def test_extract_error_reads_api2_data_result_without_error_key(self):
		client = CPanelClient.__new__(CPanelClient)
		error = client._extract_error(
			{"cpanelresult": {"apiversion": 2, "data": {"result": 0, "reason": "Quota exceeded"}}}
		)
		self.assertEqual(error, "Quota exceeded")

	def test_extract_error_reads_api2_event_failure(self):
		client = CPanelClient.__new__(CPanelClient)
		error = client._extract_error(
			{"cpanelresult": {"apiversion": 2, "data": [], "event": {"result": 0, "reason": "Denied"}}}
		)
		self.assertEqual(error, "Denied")

	def test_extract_error_returns_none_on_successful_api2_payload(self):
		client = CPanelClient.__new__(CPanelClient)
		error = client._extract_error(
			{
				"cpanelresult": {
					"apiversion": 2,
					"data": [],
					"event": {"result": 1},
					"func": "listaddondomains",
					"module": "Park",
					"postevent": {"result": 1},
					"preevent": {"result": 1},
				}
			}
		)
		self.assertIsNone(error)

	def test_extract_error_returns_none_on_successful_uapi_payload(self):
		client = CPanelClient.__new__(CPanelClient)
		error = client._extract_error(
			{
				"apiversion": 3,
				"func": "list_domains",
				"module": "DomainInfo",
				"result": {"data": {"main_domain": "shaule.space"}, "errors": None, "status": 1},
			}
		)
		self.assertIsNone(error)

	def test_describe_call_uses_whm_function_name_directly(self):
		client = CPanelClient.__new__(CPanelClient)
		self.assertEqual(client._describe_call("createacct", {"user": "bob"}), ("createacct", "WHM API 1"))

	def test_describe_call_unwraps_proxied_uapi_function(self):
		"""Proxied calls used to all log as a featureless "cpanel"."""
		client = CPanelClient.__new__(CPanelClient)
		operation, layer = client._describe_call(
			"cpanel",
			{
				"cpanel_jsonapi_apiversion": 3,
				"cpanel_jsonapi_module": "Email",
				"cpanel_jsonapi_func": "passwd_pop",
			},
		)
		self.assertEqual(operation, "Email::passwd_pop")
		self.assertEqual(layer, "cPanel UAPI")

	def test_describe_call_flags_api2_layer(self):
		client = CPanelClient.__new__(CPanelClient)
		operation, layer = client._describe_call(
			"cpanel",
			{
				"cpanel_jsonapi_apiversion": 2,
				"cpanel_jsonapi_module": "Park",
				"cpanel_jsonapi_func": "addaddondomain",
			},
		)
		self.assertEqual(operation, "Park::addaddondomain")
		self.assertEqual(layer, "cPanel API 2")

	def test_describe_call_falls_back_when_proxy_params_missing(self):
		client = CPanelClient.__new__(CPanelClient)
		self.assertEqual(client._describe_call("cpanel", {}), ("cpanel", "cPanel UAPI"))

	def test_error_category_classifies_known_exceptions(self):
		self.assertEqual(error_category(CPanelTimeoutError("t")), "Timeout")
		self.assertEqual(error_category(CPanelAuthenticationError("a")), "Authentication Error")
		self.assertEqual(error_category(CPanelAPIError("x")), "cPanel API Error")
		self.assertIsNone(error_category(None))

	def test_error_category_walks_mro_for_unknown_subclass(self):
		class NewTransientError(CPanelTimeoutError):
			pass

		self.assertEqual(error_category(NewTransientError("t")), "Timeout")

	def test_api2_failure_raises_instead_of_returning_silently(self):
		"""The regression this fix exists for: a failed API 2 call must raise."""
		client = CPanelClient.__new__(CPanelClient)
		response = make_mock_response(
			True,
			200,
			{"cpanelresult": {"apiversion": 2, "data": {"result": 0}, "error": "Quota exceeded"}},
		)
		with self.assertRaises(CPanelAPIError):
			client._check_response(response)


class UnitTestFriendlyMessages(UnitTestCase):
	def test_existing_resource_error_is_rephrased(self):
		msg = friendly_message(
			"create mailbox", "sales@example.com", CPanelAPIError("Mailbox already exists")
		)
		self.assertIn("sales@example.com already exists on the server", msg)
		self.assertTrue(msg.startswith("Unable to create mailbox sales@example.com"))

	def test_credentials_error_is_rephrased(self):
		msg = friendly_message("provision", "example.com", CPanelAPIError("Invalid login attempt"))
		self.assertIn("rejected the API credentials", msg)

	def test_unmatched_reason_is_preserved_verbatim(self):
		# Never reword a failure into something less accurate than the server said.
		msg = friendly_message("provision", "example.com", CPanelAPIError("Weird backend explosion 42"))
		self.assertIn("Weird backend explosion 42", msg)

	def test_empty_reason_still_names_the_target(self):
		msg = friendly_message("provision", "example.com", CPanelAPIError(""))
		self.assertIn("example.com", msg)
		self.assertIn("did not explain why", msg)
