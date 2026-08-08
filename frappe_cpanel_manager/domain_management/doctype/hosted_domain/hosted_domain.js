// Copyright (c) 2026,     Aakvatech-Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Hosted Domain", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		if (["Queued", "Provisioning"].includes(frm.doc.status)) {
			return;
		}

		if (frm.doc.status !== "Active") {
			frm.add_custom_button(__("Provision"), () => {
				frappe.call({
					method: "frappe_cpanel_manager.api.domain.provision_domain",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Provisioning domain..."),
					callback: () => frm.reload_doc(),
				});
			});

			frm.add_custom_button(__("Queue Provisioning"), () => {
				frappe.call({
					method: "frappe_cpanel_manager.api.domain.enqueue_provision",
					args: { name: frm.doc.name },
					callback: () => frm.reload_doc(),
				});
			});
			return;
		}

		frm.add_custom_button(
			__("Sync DNS from Server"),
			() => {
				frappe.call({
					method: "frappe_cpanel_manager.api.domain.sync_dns_from_server",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Fetching DNS records..."),
					callback: () => frm.reload_doc(),
				});
			},
			__("DNS")
		);

		frm.add_custom_button(
			__("Apply DNS Changes"),
			() => {
				frappe.call({
					method: "frappe_cpanel_manager.api.domain.apply_dns_changes",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Applying DNS changes..."),
					callback: () => frm.reload_doc(),
				});
			},
			__("DNS")
		);

		if (frm.doc.provisioning_type === "New cPanel Account") {
			frm.add_custom_button(__("Email Accounts"), () => {
				frappe.set_route("list", "Domain Email Account", { hosted_domain: frm.doc.name });
			});
		}
	},
});
