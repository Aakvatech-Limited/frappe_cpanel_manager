// Copyright (c) 2026, Aakvatech-Limited and contributors
// For license information, please see license.txt

frappe.query_reports["Hosted Domains"] = {
	filters: [
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: [
				"",
				"Draft",
				"Queued",
				"Provisioning",
				"Active",
				"Suspended",
				"Terminated",
				"Failed",
			],
		},
		{
			fieldname: "server",
			label: __("Server"),
			fieldtype: "Link",
			options: "cPanel Server",
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
	],
};
