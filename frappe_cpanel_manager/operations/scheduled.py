# Copyright (c) 2026, Aakvatech-Limited and contributors
# See license.txt

import frappe


def sync_pending_hosted_domains():
	"""Schedule a lightweight housekeeping pass for Hosted Domains that are still queued."""
	for doc in frappe.get_all(
		"Hosted Domain",
		filters={"status": "Queued"},
		fields=["name"],
		limit_page_length=50,
	):
		frappe.enqueue(
			"frappe_cpanel_manager.integrations.cpanel.operations.process_hosted_domain_provision",
			queue="long",
			docname=doc.name,
			job_name=f"Hosted Domain:{doc.name}:provision",
			enqueue_after_commit=True,
		)
