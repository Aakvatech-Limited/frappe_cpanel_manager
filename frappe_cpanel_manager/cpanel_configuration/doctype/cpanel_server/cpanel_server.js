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
	},
});
