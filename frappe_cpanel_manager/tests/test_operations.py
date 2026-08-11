# Copyright (c) 2026, Aakvatech-Limited and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from frappe_cpanel_manager.integrations.cpanel.exceptions import CPanelTimeoutError
from frappe_cpanel_manager.integrations.cpanel.operations import run_with_retry


class UnitTestRetryFramework(UnitTestCase):
	def test_run_with_retry_retries_transient_exceptions(self):
		attempts = {"count": 0}

		def action():
			attempts["count"] += 1
			if attempts["count"] < 3:
				raise CPanelTimeoutError("temporary")
			return "ok"

		self.assertEqual(run_with_retry(action, retries=3, retryable_exceptions=(CPanelTimeoutError,)), "ok")
		self.assertEqual(attempts["count"], 3)

	def test_run_with_retry_raises_after_exhausting_retries(self):
		attempts = {"count": 0}

		def action():
			attempts["count"] += 1
			raise CPanelTimeoutError("still failing")

		with self.assertRaises(CPanelTimeoutError):
			run_with_retry(action, retries=2, retryable_exceptions=(CPanelTimeoutError,))

		self.assertEqual(attempts["count"], 3)


class IntegrationTestOperationalQueue(IntegrationTestCase):
	def setUp(self):
		self.server = frappe.get_doc(
			{
				"doctype": "cPanel Server",
				"server_name": f"queue-server-{frappe.generate_hash(length=8)}",
				"hostname": "whm.example.test",
				"whm_username": "root",
				"whm_api_token": "top-secret-token",
			}
		).insert()

	def tearDown(self):
		frappe.db.delete("Hosted Domain", {"server": self.server.name})
		frappe.delete_doc("cPanel Server", self.server.name, force=True)

	def make_domain(self, **kwargs):
		values = {
			"doctype": "Hosted Domain",
			"domain_name": "queue.example.com",
			"server": self.server.name,
			"provisioning_type": "DNS Only",
		}
		values.update(kwargs)
		return frappe.get_doc(values).insert()

	def test_enqueue_provision_marks_domain_queued_and_schedules_job(self):
		doc = self.make_domain(domain_name="queued.example.com")

		with patch("frappe_cpanel_manager.integrations.cpanel.operations.frappe.enqueue") as enqueue:
			doc.enqueue_provision()

		doc.reload()
		self.assertEqual(doc.status, "Queued")
		enqueue.assert_called_once()
		self.assertEqual(enqueue.call_args.kwargs["job_name"], f"Hosted Domain:{doc.name}:provision")
		self.assertEqual(enqueue.call_args.kwargs["queue"], "long")

		# "Queued" must be a real Select option: db_set() bypasses validation, but a
		# normal save (e.g. a user reopening the record in the desk) does not.
		doc.save()
