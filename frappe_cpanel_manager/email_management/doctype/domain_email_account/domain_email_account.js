// Copyright (c) 2026,     Aakvatech-Limited and contributors
// For license information, please see license.txt

// Shown once, on demand. The password is never written to the console or the
// document timeline, so this dialog is the operator's only chance to copy it.
function show_generated_password(password) {
	frappe.msgprint({
		title: __("Generated Password"),
		indicator: "green",
		message:
			__("Copy this password now -- it is not stored anywhere and cannot be shown again.") +
			`<pre class="mt-3" style="user-select: all; padding: 8px;">${frappe.utils.escape_html(
				password
			)}</pre>`,
	});
}

frappe.ui.form.on("Domain Email Account", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		if (frm.doc.status === "Draft") {
			frm.add_custom_button(__("Generate Password"), () => {
				frappe.call({
					method: "frappe_cpanel_manager.api.email.generate_mailbox_password",
					args: { name: frm.doc.name },
					callback: (r) => {
						if (!r.message) {
							return;
						}
						frm.set_value("initial_password", r.message.password);
						show_generated_password(r.message.password);
					},
				});
			});

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
				const dialog = new frappe.ui.Dialog({
					title: __("Change Mailbox Password"),
					fields: [
						{
							fieldname: "new_password",
							fieldtype: "Password",
							label: __("New Password"),
							reqd: 1,
						},
						{
							fieldname: "generate",
							fieldtype: "Button",
							label: __("Generate Secure Password"),
							click: () => {
								frappe.call({
									method: "frappe_cpanel_manager.api.email.generate_mailbox_password",
									args: { name: frm.doc.name },
									callback: (r) => {
										if (r.message) {
											dialog.set_value("new_password", r.message.password);
											show_generated_password(r.message.password);
										}
									},
								});
							},
						},
					],
					primary_action_label: __("Change Password"),
					primary_action: (values) => {
						dialog.hide();
						frappe.call({
							method: "frappe_cpanel_manager.api.email.change_password",
							args: { name: frm.doc.name, new_password: values.new_password },
							freeze: true,
							freeze_message: __("Changing password..."),
							callback: () => frm.reload_doc(),
						});
					},
				});
				dialog.show();
			});

			frm.add_custom_button(__("Edit Quota"), () => {
				frappe.prompt(
					[
						{
							fieldname: "unlimited",
							fieldtype: "Check",
							label: __("Unlimited Quota"),
							default: frm.doc.unlimited_quota,
						},
						{
							fieldname: "quota_mb",
							fieldtype: "Int",
							label: __("Quota (MB)"),
							default: frm.doc.quota_mb,
							depends_on: "eval:!doc.unlimited",
						},
					],
					(values) => {
						frappe.call({
							method: "frappe_cpanel_manager.api.email.edit_quota",
							args: {
								name: frm.doc.name,
								quota_mb: values.quota_mb,
								unlimited: values.unlimited ? 1 : 0,
							},
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
