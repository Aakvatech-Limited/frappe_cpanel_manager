import re

import frappe
from frappe import _

DOMAIN_RE = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$")


def normalize_domain(raw_domain):
	"""Lowercase a domain and strip any scheme, path, query, port, or trailing dot."""
	if not raw_domain or not raw_domain.strip():
		frappe.throw(_("Domain Name is required."))

	value = raw_domain.strip().lower()
	value = re.sub(r"^[a-z][a-z0-9+.-]*://", "", value)
	value = value.split("/")[0].split("?")[0].split("#")[0].split(":")[0]
	value = value.rstrip(".")

	if not DOMAIN_RE.match(value):
		frappe.throw(_("{0} is not a valid domain name.").format(raw_domain))

	return value


def domain_exists_on_server(client, domain):
	"""Best-effort pre-create check using WHM API 1 listaccts.

	NOTE: listaccts only reports domains that own a cPanel account; on some
	cPanel versions it may not surface DNS-only zones added via `adddns`.
	Treat this as a safety net rather than the sole guard -- createacct and
	adddns both reject duplicate domains themselves, and that error is still
	surfaced to the caller. Verify this against a live server during the
	Phase 0 sandbox spike.
	"""
	result = client.call_whm("listaccts", {"search": domain, "searchtype": "domain"})
	accounts = (result.get("data") or {}).get("acct") or []
	return any((acct.get("domain") or "").lower() == domain for acct in accounts)
