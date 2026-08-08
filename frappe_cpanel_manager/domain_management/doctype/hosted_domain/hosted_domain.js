// Copyright (c) 2026,     Aakvatech-Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Hosted Domain", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.status === "Active") {
			return;
		}
		frm.add_custom_button(__("Provision"), () => {
			frappe.call({
				method: "frappe_cpanel_manager.api.domain.provision_domain",
				args: { name: frm.doc.name },
				freeze: true,
				freeze_message: __("Provisioning domain..."),
				callback: () => frm.reload_doc(),
			});
		});
	},
});
