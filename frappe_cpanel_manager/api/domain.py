import frappe


@frappe.whitelist()
def provision_domain(name):
	frappe.has_permission("Hosted Domain", "write", throw=True)
	doc = frappe.get_doc("Hosted Domain", name)
	doc.provision()
	return {"status": doc.status}
