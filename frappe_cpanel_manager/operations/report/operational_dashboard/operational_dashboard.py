# Copyright (c) 2026, Aakvatech-Limited and contributors
# See license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = [
		{"label": _("Domain"), "fieldname": "domain", "fieldtype": "Data", "width": 220},
		{"label": _("Server"), "fieldname": "server", "fieldtype": "Data", "width": 180},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": _("Last Activity"), "fieldname": "last_activity", "fieldtype": "Datetime", "width": 180},
		{"label": _("Log Count"), "fieldname": "log_count", "fieldtype": "Int", "width": 90},
	]

	conditions = []
	if filters and filters.get("status"):
		conditions.append(f"status = {frappe.db.escape(filters['status'])}")
	if filters and filters.get("server"):
		conditions.append(f"server = {frappe.db.escape(filters['server'])}")

	where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
	query = f"""
		SELECT
			name AS domain,
			server,
			status,
			COALESCE(last_provisioned_on, last_action_on) AS last_activity,
			(SELECT COUNT(*) FROM `tabcPanel Integration Log` WHERE reference_doctype = 'Hosted Domain' AND reference_name = hd.name) AS log_count
		FROM `tabHosted Domain` hd
		{where_clause}
		ORDER BY COALESCE(last_provisioned_on, last_action_on) DESC, name ASC
	"""
	data = frappe.db.sql(query, as_dict=True)
	return columns, data
