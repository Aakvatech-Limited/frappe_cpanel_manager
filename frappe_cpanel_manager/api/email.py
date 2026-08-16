import frappe

from frappe_cpanel_manager.password_utils import generate_password


@frappe.whitelist()
def generate_mailbox_password(name: str):
	"""Generate a password for this mailbox without storing or applying it.

	Returned to the caller so the operator can copy it once; nothing is written
	to the document and no cPanel call (and therefore no integration log entry)
	happens here.
	"""
	frappe.has_permission("Domain Email Account", "write", throw=True)
	doc = frappe.get_doc("Domain Email Account", name)
	domain_name = frappe.db.get_value("Hosted Domain", doc.hosted_domain, "domain_name")
	return {"password": generate_password(exclude_terms=[doc.mailbox, domain_name])}


@frappe.whitelist()
def create_mailbox(name: str):
	frappe.has_permission("Domain Email Account", "write", throw=True)
	doc = frappe.get_doc("Domain Email Account", name)
	doc.create_mailbox()
	return {"status": doc.status}


@frappe.whitelist()
def change_password(name: str, new_password: str):
	frappe.has_permission("Domain Email Account", "write", throw=True)
	doc = frappe.get_doc("Domain Email Account", name)
	doc.change_password(new_password)
	return {"status": doc.status}


@frappe.whitelist()
def edit_quota(name: str, quota_mb: int):
	frappe.has_permission("Domain Email Account", "write", throw=True)
	doc = frappe.get_doc("Domain Email Account", name)
	doc.edit_quota(frappe.utils.cint(quota_mb))
	return {"quota_mb": doc.quota_mb}


@frappe.whitelist()
def suspend_mailbox(name: str):
	frappe.has_permission("Domain Email Account", "write", throw=True)
	doc = frappe.get_doc("Domain Email Account", name)
	doc.suspend()
	return {"status": doc.status}


@frappe.whitelist()
def unsuspend_mailbox(name: str):
	frappe.has_permission("Domain Email Account", "write", throw=True)
	doc = frappe.get_doc("Domain Email Account", name)
	doc.unsuspend()
	return {"status": doc.status}


@frappe.whitelist()
def delete_mailbox(name: str):
	frappe.has_permission("Domain Email Account", "write", throw=True)
	doc = frappe.get_doc("Domain Email Account", name)
	doc.delete_mailbox()
	return {"status": doc.status}
