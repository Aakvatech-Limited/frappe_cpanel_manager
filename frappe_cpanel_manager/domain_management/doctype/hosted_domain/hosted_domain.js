// Copyright (c) 2026,     Aakvatech-Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Hosted Domain", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		if (["Queued", "Provisioning", "Terminated"].includes(frm.doc.status)) {
			return;
		}

		if (["Draft", "Failed"].includes(frm.doc.status)) {
			if (frm.doc.provisioning_type === "New cPanel Account") {
				frm.add_custom_button(__("Generate Password"), () => {
					frappe.call({
						method: "frappe_cpanel_manager.api.domain.generate_cpanel_password",
						args: { name: frm.doc.name },
						callback: (r) => {
							if (!r.message) {
								return;
							}
							frm.set_value("initial_cpanel_password", r.message.password);
							frappe.msgprint({
								title: __("Generated Password"),
								indicator: "green",
								message:
									__(
										"Copy this password now -- it is cleared from the document once provisioning succeeds."
									) +
									`<pre class="mt-3" style="user-select: all; padding: 8px;">${frappe.utils.escape_html(
										r.message.password
									)}</pre>`,
							});
						},
					});
				});
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

			frm.add_custom_button(__("Queue Provisioning"), () => {
				frappe.call({
					method: "frappe_cpanel_manager.api.domain.enqueue_provision",
					args: { name: frm.doc.name },
					callback: () => frm.reload_doc(),
				});
			});
			return;
		}

		const isNewAccount = frm.doc.provisioning_type === "New cPanel Account";

		if (isNewAccount && frm.doc.status === "Active") {
			frm.add_custom_button(
				__("Suspend Account"),
				() => {
					frappe.prompt(
						{ fieldname: "reason", fieldtype: "Data", label: __("Reason (optional)") },
						(values) => {
							frappe.call({
								method: "frappe_cpanel_manager.api.domain.suspend_domain",
								args: { name: frm.doc.name, reason: values.reason },
								freeze: true,
								freeze_message: __("Suspending account..."),
								callback: () => frm.reload_doc(),
							});
						},
						__("Suspend cPanel Account")
					);
				},
				__("Account")
			);
		}

		if (isNewAccount && frm.doc.status === "Suspended") {
			frm.add_custom_button(
				__("Unsuspend Account"),
				() => {
					frappe.call({
						method: "frappe_cpanel_manager.api.domain.unsuspend_domain",
						args: { name: frm.doc.name },
						freeze: true,
						freeze_message: __("Unsuspending account..."),
						callback: () => frm.reload_doc(),
					});
				},
				__("Account")
			);
		}

		if (isNewAccount && ["Active", "Suspended"].includes(frm.doc.status)) {
			frm.add_custom_button(
				__("Terminate Account"),
				() => {
					frappe.prompt(
						{
							fieldname: "confirm_domain",
							fieldtype: "Data",
							label: __("Type {0} to confirm", [frm.doc.domain_name]),
							reqd: 1,
						},
						(values) => {
							if (values.confirm_domain !== frm.doc.domain_name) {
								frappe.msgprint(
									__("Domain name did not match. Termination cancelled.")
								);
								return;
							}
							frappe.call({
								method: "frappe_cpanel_manager.api.domain.terminate_domain",
								args: { name: frm.doc.name },
								freeze: true,
								freeze_message: __("Terminating account..."),
								callback: () => frm.reload_doc(),
							});
						},
						__(
							"Terminate cPanel Account -- this permanently deletes the account, domains, mail and files"
						)
					);
				},
				__("Account")
			);
		}

		if (frm.doc.status !== "Active") {
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

		frm.fields_dict.dns_records.grid.add_custom_button(__("Delete on Server"), () => {
			const selected = frm.fields_dict.dns_records.grid.get_selected_children();
			if (!selected.length) {
				frappe.msgprint(__("Select one or more DNS records to delete."));
				return;
			}
			frappe.confirm(
				__(
					"Permanently delete {0} DNS record(s) from the live server? This cannot be undone.",
					[selected.length]
				),
				() => {
					frappe.dom.freeze(__("Deleting DNS record(s)..."));
					selected
						.reduce(
							(chain, row) =>
								chain.then(() =>
									frappe.call({
										method: "frappe_cpanel_manager.api.domain.remove_dns_record",
										args: { name: frm.doc.name, row_name: row.name },
									})
								),
							Promise.resolve()
						)
						.finally(() => {
							frappe.dom.unfreeze();
							frm.reload_doc();
						});
				}
			);
		});

		if (frm.doc.provisioning_type === "New cPanel Account") {
			frm.add_custom_button(__("Email Accounts"), () => {
				frappe.set_route("list", "Domain Email Account", { hosted_domain: frm.doc.name });
			});
		}
	},
});
