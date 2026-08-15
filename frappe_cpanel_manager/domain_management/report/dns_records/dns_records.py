# Copyright (c) 2026, Aakvatech-Limited and contributors
# See license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = [
		{"label": _("Domain"), "fieldname": "domain", "fieldtype": "Data", "width": 200},
		{"label": _("Record Type"), "fieldname": "record_type", "fieldtype": "Data", "width": 110},
		{"label": _("Name"), "fieldname": "record_name", "fieldtype": "Data", "width": 160},
		{"label": _("Value"), "fieldname": "value", "fieldtype": "Data", "width": 280},
		{"label": _("TTL"), "fieldname": "ttl", "fieldtype": "Int", "width": 80},
		{"label": _("Synced"), "fieldname": "synced", "fieldtype": "Data", "width": 80},
	]

	conditions, values = [], {}
	if filters.get("domain"):
		conditions.append("hd.name = %(domain)s")
		values["domain"] = filters.get("domain")
	if filters.get("record_type"):
		conditions.append("ddr.record_type = %(record_type)s")
		values["record_type"] = filters.get("record_type")

	where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
	data = frappe.db.sql(
		f"""
		SELECT
			hd.domain_name AS domain,
			ddr.record_type,
			ddr.record_name,
			ddr.value,
			ddr.ttl,
			IF(ddr.zone_line IS NULL OR ddr.zone_line = '', 'No', 'Yes') AS synced
		FROM `tabDomain DNS Record` ddr
		INNER JOIN `tabHosted Domain` hd ON hd.name = ddr.parent
		{where_clause}
		ORDER BY hd.domain_name ASC, ddr.record_type ASC, ddr.record_name ASC
		""",
		values,
		as_dict=True,
	)

	return columns, data
