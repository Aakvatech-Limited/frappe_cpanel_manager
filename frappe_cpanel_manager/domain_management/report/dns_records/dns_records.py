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

	record = frappe.qb.DocType("Domain DNS Record")
	domain = frappe.qb.DocType("Hosted Domain")

	query = (
		frappe.qb.from_(record)
		.inner_join(domain)
		.on(domain.name == record.parent)
		.select(
			domain.domain_name.as_("domain"),
			record.record_type,
			record.record_name,
			record.value,
			record.ttl,
			record.zone_line,
		)
		.orderby(domain.domain_name)
		.orderby(record.record_type)
		.orderby(record.record_name)
	)

	if filters.get("domain"):
		query = query.where(domain.name == filters.get("domain"))
	if filters.get("record_type"):
		query = query.where(record.record_type == filters.get("record_type"))

	data = query.run(as_dict=True)

	# `zone_line` is only set once a row has been pushed to (or pulled from) the
	# server, so an empty one means the record has not been applied yet.
	for row in data:
		row["synced"] = "Yes" if row.pop("zone_line", None) else "No"

	return columns, data
