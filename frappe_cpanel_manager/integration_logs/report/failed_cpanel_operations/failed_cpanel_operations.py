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

	conditions, values = ["status = 'Failed'"], {}
	if filters.get("server"):
		conditions.append("server = %(server)s")
		values["server"] = filters.get("server")
	if filters.get("from_date"):
		conditions.append("request_time >= %(from_date)s")
		values["from_date"] = filters.get("from_date")
	if filters.get("to_date"):
		conditions.append("request_time <= %(to_date)s")
		values["to_date"] = filters.get("to_date")

	where_clause = "WHERE " + " AND ".join(conditions)
	data = frappe.db.sql(
		f"""
		SELECT
			request_time AS date,
			server,
			operation,
			name AS log,
			CONCAT_WS(' ', reference_doctype, reference_name) AS reference,
			error_message
		FROM `tabcPanel Integration Log`
		{where_clause}
		ORDER BY request_time DESC
		""",
		values,
		as_dict=True,
	)

	return columns, data
