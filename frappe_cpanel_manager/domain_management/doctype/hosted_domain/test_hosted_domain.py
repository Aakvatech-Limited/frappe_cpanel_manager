# Copyright (c) 2026,     Aakvatech-Limited and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from frappe_cpanel_manager.api.domain import (
	apply_dns_changes,
	provision_domain,
	remove_dns_record,
	suspend_domain,
	sync_dns_from_server,
	terminate_domain,
	unsuspend_domain,
)
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

	def test_cname_conflict_with_other_record_at_same_name_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_domain(
				domain_name="cnameconflict.example.com",
				dns_records=[
					{"record_type": "CNAME", "record_name": "www", "value": "target.example.com"},
					{"record_type": "A", "record_name": "www", "value": "192.0.2.1"},
				],
			)

	def test_sync_dns_from_server_replaces_local_records(self):
		doc = self.make_domain(domain_name="syncme.example.com")
		dumpzone_response = make_mock_response(
			True,
			200,
			{
				"data": {
					"zone": [
						{
							"record": [
								{"Line": "1", "type": "SOA", "name": "syncme.example.com."},
								{
									"Line": "5",
									"type": "NS",
									"name": "syncme.example.com.",
									"nsdname": "ns1.example.com.",
									"ttl": "86400",
								},
								{
									"Line": "6",
									"type": "A",
									"name": "www.syncme.example.com.",
									"address": "192.0.2.10",
									"ttl": "14400",
								},
								{
									"Line": "7",
									"type": "MX",
									"name": "syncme.example.com.",
									"exchange": "mail.syncme.example.com.",
									"preference": "10",
									"ttl": "14400",
								},
								{
									"Line": "8",
									"type": "CAA",
									"name": "syncme.example.com.",
									"flag": "0",
									"tag": "issue",
									"value": "letsencrypt.org",
									"ttl": "14400",
								},
							]
						}
					]
				}
			},
		)

		with patch(
			"frappe_cpanel_manager.integrations.cpanel.client.requests.get",
			return_value=dumpzone_response,
		):
			sync_dns_from_server(doc.name)

		doc.reload()
		records = {row.record_type: row for row in doc.dns_records}
		self.assertEqual(len(doc.dns_records), 4)
		self.assertEqual(records["NS"].record_name, "@")
		self.assertEqual(records["NS"].zone_line, "5")
		self.assertEqual(records["A"].record_name, "www")
		self.assertEqual(records["A"].value, "192.0.2.10")
		self.assertEqual(records["A"].zone_line, "6")
		self.assertEqual(records["MX"].priority, 10)
		self.assertEqual(records["CAA"].value, "letsencrypt.org")
		self.assertEqual(records["CAA"].caa_flag, 0)
		self.assertEqual(records["CAA"].caa_tag, "issue")
		self.assertEqual(records["CAA"].zone_line, "8")

	def test_apply_dns_changes_adds_and_edits_then_resyncs(self):
		doc = self.make_domain(domain_name="applyme.example.com")
		doc.append("dns_records", {"record_type": "A", "record_name": "new", "value": "192.0.2.20"})
		doc.save()

		add_response = make_mock_response(True, 200, {"metadata": {"result": 1, "reason": "OK"}})
		resync_response = make_mock_response(
			True,
			200,
			{
				"data": {
					"zone": [
						{
							"record": [
								{
									"Line": "9",
									"type": "A",
									"name": "new.applyme.example.com.",
									"address": "192.0.2.20",
									"ttl": "14400",
								}
							]
						}
					]
				}
			},
		)

		with patch(
			"frappe_cpanel_manager.integrations.cpanel.client.requests.get",
			side_effect=[add_response, resync_response],
		):
			apply_dns_changes(doc.name)

		doc.reload()
		self.assertEqual(len(doc.dns_records), 1)
		self.assertEqual(doc.dns_records[0].zone_line, "9")

		logs = frappe.get_all(
			"cPanel Integration Log",
			filters={
				"reference_doctype": "Hosted Domain",
				"reference_name": doc.name,
				"operation": "addzonerecord",
			},
		)
		self.assertEqual(len(logs), 1)

	def test_remove_dns_record_deletes_local_and_remote(self):
		doc = self.make_domain(
			domain_name="removeme.example.com",
			dns_records=[{"record_type": "A", "record_name": "old", "value": "192.0.2.30", "zone_line": "3"}],
		)
		row_name = doc.dns_records[0].name

		remove_response = make_mock_response(True, 200, {"metadata": {"result": 1, "reason": "OK"}})
		with patch(
			"frappe_cpanel_manager.integrations.cpanel.client.requests.get",
			return_value=remove_response,
		):
			remove_dns_record(doc.name, row_name)

		doc.reload()
		self.assertEqual(len(doc.dns_records), 0)

		logs = frappe.get_all(
			"cPanel Integration Log",
			filters={
				"reference_doctype": "Hosted Domain",
				"reference_name": doc.name,
				"operation": "removezonerecord",
			},
		)
		self.assertEqual(len(logs), 1)

	def test_suspend_and_unsuspend_account_toggle_status(self):
		doc = self.make_domain(domain_name="suspendme.example.com")
		doc.db_set("status", "Active", update_modified=False)
		success = make_mock_response(True, 200, {"metadata": {"result": 1, "reason": "OK"}})

		with patch(
			"frappe_cpanel_manager.integrations.cpanel.client.requests.get",
			return_value=success,
		):
			suspend_domain(doc.name, reason="non-payment")
		doc.reload()
		self.assertEqual(doc.status, "Suspended")

		with self.assertRaises(frappe.ValidationError):
			suspend_domain(doc.name)

		with patch(
			"frappe_cpanel_manager.integrations.cpanel.client.requests.get",
			return_value=success,
		):
			unsuspend_domain(doc.name)
		doc.reload()
		self.assertEqual(doc.status, "Active")

	def test_suspend_rejected_for_dns_only_domain(self):
		doc = self.make_domain(
			domain_name="dnsonlysuspend.example.com",
			provisioning_type="DNS Only",
			cpanel_username=None,
			contact_email=None,
			initial_cpanel_password=None,
		)
		doc.db_set("status", "Active", update_modified=False)
		with self.assertRaises(frappe.ValidationError):
			suspend_domain(doc.name)

	def test_suspend_failure_records_error_and_keeps_status(self):
		doc = self.make_domain(domain_name="suspendfail.example.com")
		doc.db_set("status", "Active", update_modified=False)
		failure = make_mock_response(
			False, 422, {"metadata": {"result": 0, "reason": "Account already suspended."}}
		)

		with patch(
			"frappe_cpanel_manager.integrations.cpanel.client.requests.get",
			return_value=failure,
		):
			with self.assertRaises(CPanelAPIError):
				suspend_domain(doc.name)

		doc.reload()
		self.assertEqual(doc.status, "Active")
		self.assertIn("already suspended", doc.error_message)

	def test_terminate_account_success_from_active(self):
		doc = self.make_domain(domain_name="terminateme.example.com")
		doc.db_set("status", "Active", update_modified=False)
		success = make_mock_response(True, 200, {"metadata": {"result": 1, "reason": "OK"}})

		with patch(
			"frappe_cpanel_manager.integrations.cpanel.client.requests.get",
			return_value=success,
		):
			terminate_domain(doc.name)

		doc.reload()
		self.assertEqual(doc.status, "Terminated")

		logs = frappe.get_all(
			"cPanel Integration Log",
			filters={
				"reference_doctype": "Hosted Domain",
				"reference_name": doc.name,
				"operation": "removeacct",
			},
		)
		self.assertEqual(len(logs), 1)

	def test_terminate_rejected_when_not_active_or_suspended(self):
		doc = self.make_domain(domain_name="terminatedraft.example.com")
		with self.assertRaises(frappe.ValidationError):
			terminate_domain(doc.name)

	def test_terminate_requires_delete_permission(self):
		doc = self.make_domain(domain_name="terminateperm.example.com")
		doc.db_set("status", "Active", update_modified=False)
		operator_user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"cpanelsec-terminate-{frappe.generate_hash(length=6)}@example.test",
				"first_name": "Terminate",
				"send_welcome_email": 0,
				"roles": [{"role": "cPanel Manager Operator"}],
			}
		).insert(ignore_permissions=True)
		try:
			frappe.set_user(operator_user.name)
			with self.assertRaises(frappe.PermissionError):
				terminate_domain(doc.name)
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("User", operator_user.name, force=True)

		doc.reload()
		self.assertEqual(doc.status, "Active")


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
