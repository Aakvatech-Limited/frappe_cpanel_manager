import frappe
from frappe import _
from frappe.utils import now_datetime

from frappe_cpanel_manager.integrations.cpanel.client import CPanelClient
from frappe_cpanel_manager.integrations.cpanel.exceptions import CPanelAPIError


@frappe.whitelist()
def test_connection(server):
	frappe.has_permission("cPanel Server", "write", throw=True)
	doc = frappe.get_doc("cPanel Server", server)
	client = CPanelClient(doc)

	try:
		result = client.call_whm("version")
	except CPanelAPIError as e:
		doc.db_set("last_connection_status", "Failed", update_modified=False)
		doc.db_set("last_connection_test", now_datetime(), update_modified=False)
		frappe.throw(str(e), title=_("Connection Failed"))

	doc.db_set("last_connection_status", "Success", update_modified=False)
	doc.db_set("last_connection_test", now_datetime(), update_modified=False)
	return result
