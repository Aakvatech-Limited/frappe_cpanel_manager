import frappe


@frappe.whitelist()
def provision_domain(name):
	frappe.has_permission("Hosted Domain", "write", throw=True)
	doc = frappe.get_doc("Hosted Domain", name)
	doc.provision()
	return {"status": doc.status}


@frappe.whitelist()
def enqueue_provision(name):
	frappe.has_permission("Hosted Domain", "write", throw=True)
	doc = frappe.get_doc("Hosted Domain", name)
	return doc.enqueue_provision()


@frappe.whitelist()
def sync_dns_from_server(name):
	frappe.has_permission("Hosted Domain", "write", throw=True)
	doc = frappe.get_doc("Hosted Domain", name)
	doc.sync_dns_from_server()
	return {"dns_records": len(doc.dns_records)}


@frappe.whitelist()
def apply_dns_changes(name):
	frappe.has_permission("Hosted Domain", "write", throw=True)
	doc = frappe.get_doc("Hosted Domain", name)
	doc.apply_dns_changes()
	return {"dns_records": len(doc.dns_records)}


@frappe.whitelist()
def remove_dns_record(name, row_name):
	frappe.has_permission("Hosted Domain", "write", throw=True)
	doc = frappe.get_doc("Hosted Domain", name)
	doc.remove_dns_record(row_name)
	return {"dns_records": len(doc.dns_records)}
