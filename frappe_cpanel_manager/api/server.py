import frappe
from frappe import _
from frappe.utils import now_datetime

from frappe_cpanel_manager.integrations.cpanel.client import CPanelClient
from frappe_cpanel_manager.integrations.cpanel.exceptions import CPanelAPIError


@frappe.whitelist()
def test_connection(server: str):
	frappe.has_permission("cPanel Server", "write", throw=True)
	doc = frappe.get_doc("cPanel Server", server)
	client = CPanelClient(doc)

	try:
		result = client.call_whm("version")
	except CPanelAPIError as e:
		doc.db_set("last_connection_status", "Failed", update_modified=False)
		doc.db_set("last_connection_test", now_datetime(), update_modified=False)
		frappe.throw(str(e), exc=type(e), title=_("Connection Failed"))

	doc.db_set("last_connection_status", "Success", update_modified=False)
	doc.db_set("last_connection_test", now_datetime(), update_modified=False)
	return result


@frappe.whitelist()
def fetch_server_information(server: str):
	"""Read-only snapshot of the server, for the Fetch Server Information button.

	Deliberately limited to calls that only read: this button must never change
	anything on a live hosting server. Each lookup is optional -- a token scoped
	without a given privilege should degrade to "unavailable" rather than fail
	the whole panel.
	"""
	frappe.has_permission("cPanel Server", "read", throw=True)
	client = CPanelClient(server)

	info = {}
	for label, function_name, extract in (
		("version", "version", lambda r: (r.get("data") or {}).get("version")),
		("hostname", "gethostname", lambda r: (r.get("data") or {}).get("hostname")),
		("load_average", "systemloadavg", lambda r: (r.get("data") or {}).get("one")),
	):
		try:
			info[label] = extract(client.call_whm(function_name)) or _("Unavailable")
		except CPanelAPIError as e:
			info[label] = _("Unavailable ({0})").format(str(e)[:80])

	return info
