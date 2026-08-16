// Copyright (c) 2026, Aakvatech-Limited and contributors
// For license information, please see license.txt

frappe.query_reports["Failed cPanel Operations"] = {
	filters: [
		{
			fieldname: "server",
			label: __("Server"),
			fieldtype: "Link",
			options: "cPanel Server",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
	],
};
