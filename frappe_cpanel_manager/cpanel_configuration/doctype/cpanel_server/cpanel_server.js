// Copyright (c) 2026,     Aakvatech-Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("cPanel Server", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		frm.add_custom_button(__("Test Connection"), () => {
			frappe.call({
				method: "frappe_cpanel_manager.api.server.test_connection",
				args: { server: frm.doc.name },
				freeze: true,
				freeze_message: __("Testing connection..."),
				callback: () => frm.reload_doc(),
			});
		});

		frm.add_custom_button(__("Fetch Server Information"), () => {
			frappe.call({
				method: "frappe_cpanel_manager.api.server.fetch_server_information",
				args: { server: frm.doc.name },
				freeze: true,
				freeze_message: __("Reading server information..."),
				callback: (r) => {
					if (!r.message) {
						return;
					}
					const rows = [
						[__("WHM Version"), r.message.version],
						[__("Hostname"), r.message.hostname],
						[__("Load Average (1m)"), r.message.load_average],
					]
						.map(
							([label, value]) =>
								`<tr><td class="text-muted" style="padding-right: 16px;">${label}</td>` +
								`<td>${frappe.utils.escape_html(String(value))}</td></tr>`
						)
						.join("");
					frappe.msgprint({
						title: __("Server Information"),
						message: `<table>${rows}</table>`,
					});
				},
			});
		});

		frm.add_custom_button(__("View Integration Logs"), () => {
			frappe.set_route("List", "cPanel Integration Log", { server: frm.doc.name });
		});
	},
});
