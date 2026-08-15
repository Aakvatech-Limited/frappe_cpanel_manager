// Copyright (c) 2026,     Aakvatech-Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Domain Email Account", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		if (frm.doc.status === "Draft") {
			frm.add_custom_button(__("Create Mailbox"), () => {
				frappe.call({
					method: "frappe_cpanel_manager.api.email.create_mailbox",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Creating mailbox..."),
					callback: () => frm.reload_doc(),
				});
			});
			return;
		}

		if (frm.doc.status === "Active") {
			frm.add_custom_button(__("Suspend"), () => {
				frappe.call({
					method: "frappe_cpanel_manager.api.email.suspend_mailbox",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Suspending mailbox..."),
					callback: () => frm.reload_doc(),
				});
			});
		}

		if (frm.doc.status === "Suspended") {
			frm.add_custom_button(__("Unsuspend"), () => {
				frappe.call({
					method: "frappe_cpanel_manager.api.email.unsuspend_mailbox",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Unsuspending mailbox..."),
					callback: () => frm.reload_doc(),
				});
			});
		}

		if (["Active", "Suspended"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Change Password"), () => {
				frappe.prompt(
					{
						fieldname: "new_password",
						fieldtype: "Password",
						label: __("New Password"),
						reqd: 1,
					},
					(values) => {
						frappe.call({
							method: "frappe_cpanel_manager.api.email.change_password",
							args: { name: frm.doc.name, new_password: values.new_password },
							freeze: true,
							freeze_message: __("Changing password..."),
							callback: () => frm.reload_doc(),
						});
					},
					__("Change Mailbox Password")
				);
			});

			frm.add_custom_button(__("Edit Quota"), () => {
				frappe.prompt(
					{
						fieldname: "quota_mb",
						fieldtype: "Int",
						label: __("Quota (MB, 0 = unlimited)"),
						default: frm.doc.quota_mb,
						reqd: 1,
					},
					(values) => {
						frappe.call({
							method: "frappe_cpanel_manager.api.email.edit_quota",
							args: { name: frm.doc.name, quota_mb: values.quota_mb },
							freeze: true,
							freeze_message: __("Updating quota..."),
							callback: () => frm.reload_doc(),
						});
					},
					__("Edit Mailbox Quota")
				);
			});

			frm.add_custom_button(__("Delete Mailbox"), () => {
				frappe.confirm(
					__(
						"Permanently delete mailbox {0} from the live server? This cannot be undone.",
						[frm.doc.email_address]
					),
					() => {
						frappe.call({
							method: "frappe_cpanel_manager.api.email.delete_mailbox",
							args: { name: frm.doc.name },
							freeze: true,
							freeze_message: __("Deleting mailbox..."),
							callback: () => frm.reload_doc(),
						});
					}
				);
			});
		}
	},
});
