// Copyright (c) 2026, Aakvatech-Limited and contributors
// For license information, please see license.txt

frappe.query_reports["DNS Records"] = {
	filters: [
		{
			fieldname: "domain",
			label: __("Domain"),
			fieldtype: "Link",
			options: "Hosted Domain",
		},
		{
			fieldname: "record_type",
			label: __("Record Type"),
			fieldtype: "Select",
			options: ["", "A", "AAAA", "CAA", "CNAME", "MX", "NS", "SRV", "TXT"],
		},
	],
};
