import frappe


@frappe.whitelist()
def provision_domain(name: str):
	frappe.has_permission("Hosted Domain", "write", throw=True)
	doc = frappe.get_doc("Hosted Domain", name)
	doc.provision()
	return {"status": doc.status}


@frappe.whitelist()
def enqueue_provision(name: str):
	frappe.has_permission("Hosted Domain", "write", throw=True)
	doc = frappe.get_doc("Hosted Domain", name)
	return doc.enqueue_provision()


@frappe.whitelist()
def sync_dns_from_server(name: str):
	frappe.has_permission("Hosted Domain", "write", throw=True)
	doc = frappe.get_doc("Hosted Domain", name)
	doc.sync_dns_from_server()
	return {"dns_records": len(doc.dns_records)}


@frappe.whitelist()
def apply_dns_changes(name: str):
	frappe.has_permission("Hosted Domain", "write", throw=True)
	doc = frappe.get_doc("Hosted Domain", name)
	doc.apply_dns_changes()
	return {"dns_records": len(doc.dns_records)}


@frappe.whitelist()
def remove_dns_record(name: str, row_name: str):
	frappe.has_permission("Hosted Domain", "write", throw=True)
	doc = frappe.get_doc("Hosted Domain", name)
	doc.remove_dns_record(row_name)
	return {"dns_records": len(doc.dns_records)}


@frappe.whitelist()
def suspend_domain(name: str, reason: str | None = None):
	frappe.has_permission("Hosted Domain", "write", throw=True)
	doc = frappe.get_doc("Hosted Domain", name)
	doc.suspend(reason)
	return {"status": doc.status}


@frappe.whitelist()
def unsuspend_domain(name: str):
	frappe.has_permission("Hosted Domain", "write", throw=True)
	doc = frappe.get_doc("Hosted Domain", name)
	doc.unsuspend()
	return {"status": doc.status}


@frappe.whitelist()
def terminate_domain(name: str):
	# Irreversible -- destroys the account's domains, mail, files and databases on the
	# server, so it requires delete-tier permission, not just write (Operators can
	# provision/suspend day-to-day, but termination is Administrator-only by design).
	frappe.has_permission("Hosted Domain", "delete", throw=True)
	doc = frappe.get_doc("Hosted Domain", name)
	doc.terminate()
	return {"status": doc.status}
