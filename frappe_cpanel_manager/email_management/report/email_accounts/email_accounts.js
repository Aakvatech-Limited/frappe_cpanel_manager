// Copyright (c) 2026, Aakvatech-Limited and contributors
// For license information, please see license.txt

frappe.query_reports["Email Accounts"] = {
	filters: [
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: ["", "Draft", "Creating", "Active", "Suspended", "Failed", "Deleted"],
		},
		{
			fieldname: "hosted_domain",
			label: __("Domain"),
			fieldtype: "Link",
			options: "Hosted Domain",
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
	],
};
