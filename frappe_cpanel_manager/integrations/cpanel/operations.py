# Copyright (c) 2026, Aakvatech-Limited and contributors
# See license.txt

import time

import frappe

from frappe_cpanel_manager.integrations.cpanel.exceptions import (
	CPanelNetworkError,
	CPanelSSLError,
	CPanelTimeoutError,
)


def run_with_retry(
	action,
	retries=2,
	retryable_exceptions=(CPanelTimeoutError, CPanelNetworkError, CPanelSSLError),
	delay_seconds=2,
	on_retry=None,
):
	"""Retry a transient cPanel/WHM operation a fixed number of times."""
	last_exc = None
	for attempt in range(retries + 1):
		try:
			return action()
		except retryable_exceptions as exc:
			last_exc = exc
			if attempt >= retries:
				raise
			if on_retry:
				on_retry(attempt + 1, exc)
			frappe.log_error(
				title="cPanel operation retry",
				message=f"Retrying operation after transient error: {exc}",
			)
			if delay_seconds:
				time.sleep(delay_seconds)

	if last_exc:
		raise last_exc
	raise RuntimeError("run_with_retry requires an action to execute.")


def process_hosted_domain_provision(docname):
	"""Background-job entry point for queued Hosted Domain provisioning."""
	doc = frappe.get_doc("Hosted Domain", docname)
	try:
		run_with_retry(
			lambda: doc.provision(),
			retries=2,
			retryable_exceptions=(CPanelTimeoutError, CPanelNetworkError, CPanelSSLError),
			delay_seconds=2,
		)
	except Exception as exc:
		if doc.status != "Failed":
			doc.db_set("status", "Failed", update_modified=False)
			doc.db_set("error_message", str(exc), update_modified=False)
		frappe.log_error(title="Queued Hosted Domain Provision Failed", message=str(exc))
		raise
