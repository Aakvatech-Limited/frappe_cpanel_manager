# Copyright (c) 2026, Aakvatech-Limited and contributors
# See license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Count


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = [
		{"label": _("Domain"), "fieldname": "domain", "fieldtype": "Data", "width": 220},
		{
			"label": _("Server"),
			"fieldname": "server",
			"fieldtype": "Link",
			"options": "cPanel Server",
			"width": 180,
		},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": _("Last Activity"), "fieldname": "last_activity", "fieldtype": "Datetime", "width": 180},
		{"label": _("Log Count"), "fieldname": "log_count", "fieldtype": "Int", "width": 90},
	]

	query_filters = {}
	if filters.get("status"):
		query_filters["status"] = filters.get("status")
	if filters.get("server"):
		query_filters["server"] = filters.get("server")

	data = frappe.get_all(
		"Hosted Domain",
		filters=query_filters,
		fields=[
			"name",
			"domain_name as domain",
			"server",
			"status",
			"last_provisioned_on as last_activity",
		],
		order_by="last_provisioned_on desc, domain_name asc",
	)

	# One grouped query for every domain's log count, rather than a correlated
	# subquery per row.
	log = frappe.qb.DocType("cPanel Integration Log")
	counts = (
		frappe.qb.from_(log)
		.select(log.reference_name, Count(log.name).as_("log_count"))
		.where(log.reference_doctype == "Hosted Domain")
		.groupby(log.reference_name)
	).run(as_dict=True)
	counts_by_domain = {row.reference_name: row.log_count for row in counts}

	for row in data:
		row["log_count"] = counts_by_domain.get(row.pop("name"), 0)

	return columns, data
