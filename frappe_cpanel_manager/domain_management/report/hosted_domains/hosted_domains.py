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

	query_filters = {}
	if filters.get("status"):
		query_filters["status"] = filters.get("status")
	if filters.get("server"):
		query_filters["server"] = filters.get("server")

	data = frappe.get_all(
		"Hosted Domain",
		filters=query_filters,
		fields=[
			"domain_name as domain",
			"server",
			"provisioning_type",
			"cpanel_username",
			"status",
			"last_provisioned_on as provisioned_on",
		],
		order_by="domain_name asc",
	)

	return columns, data
