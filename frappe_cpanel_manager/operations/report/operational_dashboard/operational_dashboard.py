# Copyright (c) 2026, Aakvatech-Limited and contributors
# See license.txt

import frappe
from frappe import _


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

	conditions, values = [], {}
	if filters.get("status"):
		conditions.append("hd.status = %(status)s")
		values["status"] = filters.get("status")
	if filters.get("server"):
		conditions.append("hd.server = %(server)s")
		values["server"] = filters.get("server")

	where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
	data = frappe.db.sql(
		f"""
		SELECT
			hd.domain_name AS domain,
			hd.server,
			hd.status,
			hd.last_provisioned_on AS last_activity,
			(
				SELECT COUNT(*)
				FROM `tabcPanel Integration Log` log
				WHERE log.reference_doctype = 'Hosted Domain' AND log.reference_name = hd.name
			) AS log_count
		FROM `tabHosted Domain` hd
		{where_clause}
		ORDER BY hd.last_provisioned_on DESC, hd.domain_name ASC
		""",
		values,
		as_dict=True,
	)

	return columns, data
