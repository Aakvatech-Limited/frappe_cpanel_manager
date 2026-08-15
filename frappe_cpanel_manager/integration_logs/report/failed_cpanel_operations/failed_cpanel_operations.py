# Copyright (c) 2026, Aakvatech-Limited and contributors
# See license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Datetime", "width": 170},
		{
			"label": _("Server"),
			"fieldname": "server",
			"fieldtype": "Link",
			"options": "cPanel Server",
			"width": 170,
		},
		{"label": _("Operation"), "fieldname": "operation", "fieldtype": "Data", "width": 150},
		{
			"label": _("Log"),
			"fieldname": "log",
			"fieldtype": "Link",
			"options": "cPanel Integration Log",
			"width": 140,
		},
		{"label": _("Reference Document"), "fieldname": "reference", "fieldtype": "Data", "width": 220},
		{"label": _("Error Message"), "fieldname": "error_message", "fieldtype": "Data", "width": 320},
	]

	query_filters = {"status": "Failed"}
	if filters.get("server"):
		query_filters["server"] = filters.get("server")
	if filters.get("from_date") and filters.get("to_date"):
		query_filters["request_time"] = ["between", [filters.get("from_date"), filters.get("to_date")]]
	elif filters.get("from_date"):
		query_filters["request_time"] = [">=", filters.get("from_date")]
	elif filters.get("to_date"):
		query_filters["request_time"] = ["<=", filters.get("to_date")]

	data = frappe.get_all(
		"cPanel Integration Log",
		filters=query_filters,
		fields=[
			"request_time as date",
			"server",
			"operation",
			"name as log",
			"reference_doctype",
			"reference_name",
			"error_message",
		],
		order_by="request_time desc",
	)

	for row in data:
		reference_doctype = row.pop("reference_doctype", None)
		reference_name = row.pop("reference_name", None)
		row["reference"] = " ".join(part for part in (reference_doctype, reference_name) if part)

	return columns, data
