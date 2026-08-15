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
		{
			"label": _("Provisioning Type"),
			"fieldname": "provisioning_type",
			"fieldtype": "Data",
			"width": 160,
		},
		{"label": _("cPanel Username"), "fieldname": "cpanel_username", "fieldtype": "Data", "width": 150},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("Provisioned On"), "fieldname": "provisioned_on", "fieldtype": "Datetime", "width": 170},
	]

	conditions, values = [], {}
	if filters.get("status"):
		conditions.append("status = %(status)s")
		values["status"] = filters.get("status")
	if filters.get("server"):
		conditions.append("server = %(server)s")
		values["server"] = filters.get("server")

	where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
	data = frappe.db.sql(
		f"""
		SELECT
			domain_name AS domain,
			server,
			provisioning_type,
			cpanel_username,
			status,
			last_provisioned_on AS provisioned_on
		FROM `tabHosted Domain`
		{where_clause}
		ORDER BY domain_name ASC
		""",
		values,
		as_dict=True,
	)

	return columns, data
