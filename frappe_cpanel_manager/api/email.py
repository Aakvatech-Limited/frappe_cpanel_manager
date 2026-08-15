import frappe


@frappe.whitelist()
def create_mailbox(name):
	frappe.has_permission("Domain Email Account", "write", throw=True)
	doc = frappe.get_doc("Domain Email Account", name)
	doc.create_mailbox()
	return {"status": doc.status}


@frappe.whitelist()
def change_password(name, new_password):
	frappe.has_permission("Domain Email Account", "write", throw=True)
	doc = frappe.get_doc("Domain Email Account", name)
	doc.change_password(new_password)
	return {"status": doc.status}


@frappe.whitelist()
def edit_quota(name, quota_mb):
	frappe.has_permission("Domain Email Account", "write", throw=True)
	doc = frappe.get_doc("Domain Email Account", name)
	doc.edit_quota(frappe.utils.cint(quota_mb))
	return {"quota_mb": doc.quota_mb}


@frappe.whitelist()
def suspend_mailbox(name):
	frappe.has_permission("Domain Email Account", "write", throw=True)
	doc = frappe.get_doc("Domain Email Account", name)
	doc.suspend()
	return {"status": doc.status}


@frappe.whitelist()
def unsuspend_mailbox(name):
	frappe.has_permission("Domain Email Account", "write", throw=True)
	doc = frappe.get_doc("Domain Email Account", name)
	doc.unsuspend()
	return {"status": doc.status}


@frappe.whitelist()
def delete_mailbox(name):
	frappe.has_permission("Domain Email Account", "write", throw=True)
	doc = frappe.get_doc("Domain Email Account", name)
	doc.delete_mailbox()
	return {"status": doc.status}
