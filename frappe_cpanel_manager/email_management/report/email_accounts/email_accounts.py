# Copyright (c) 2026, Aakvatech-Limited and contributors
# See license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = [
		{"label": _("Email Address"), "fieldname": "email_address", "fieldtype": "Data", "width": 220},
		{"label": _("Domain"), "fieldname": "domain", "fieldtype": "Data", "width": 200},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 180,
		},
		{"label": _("Quota (MB)"), "fieldname": "quota_mb", "fieldtype": "Int", "width": 110},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("Last Action On"), "fieldname": "last_action_on", "fieldtype": "Datetime", "width": 170},
	]

	account = frappe.qb.DocType("Domain Email Account")
	domain = frappe.qb.DocType("Hosted Domain")

	query = (
		frappe.qb.from_(account)
		.inner_join(domain)
		.on(domain.name == account.hosted_domain)
		.select(
			account.email_address,
			domain.domain_name.as_("domain"),
			domain.customer,
			account.quota_mb,
			account.status,
			account.last_action_on,
		)
		.orderby(account.email_address)
	)

	if filters.get("status"):
		query = query.where(account.status == filters.get("status"))
	if filters.get("hosted_domain"):
		query = query.where(account.hosted_domain == filters.get("hosted_domain"))
	if filters.get("customer"):
		query = query.where(domain.customer == filters.get("customer"))

	return columns, query.run(as_dict=True)
