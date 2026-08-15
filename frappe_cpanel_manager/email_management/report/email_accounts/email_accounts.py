# Copyright (c) 2026, Aakvatech-Limited and contributors
# See license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = [
		{"label": _("Email Address"), "fieldname": "email_address", "fieldtype": "Data", "width": 220},
		{"label": _("Domain"), "fieldname": "domain", "fieldtype": "Data", "width": 200},
		{"label": _("Quota (MB)"), "fieldname": "quota_mb", "fieldtype": "Int", "width": 110},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("Last Action On"), "fieldname": "last_action_on", "fieldtype": "Datetime", "width": 170},
	]

	conditions, values = [], {}
	if filters.get("status"):
		conditions.append("dea.status = %(status)s")
		values["status"] = filters.get("status")
	if filters.get("hosted_domain"):
		conditions.append("dea.hosted_domain = %(hosted_domain)s")
		values["hosted_domain"] = filters.get("hosted_domain")

	where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
	data = frappe.db.sql(
		f"""
		SELECT
			dea.email_address,
			hd.domain_name AS domain,
			dea.quota_mb,
			dea.status,
			dea.last_action_on
		FROM `tabDomain Email Account` dea
		INNER JOIN `tabHosted Domain` hd ON hd.name = dea.hosted_domain
		{where_clause}
		ORDER BY dea.email_address ASC
		""",
		values,
		as_dict=True,
	)

	return columns, data
