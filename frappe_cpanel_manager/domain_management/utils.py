import ipaddress
import re

import frappe
from frappe import _

DOMAIN_RE = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$")
DNS_NAME_RE = re.compile(
	r"^(\*|[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)(\.(\*|[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?))*$"
)
DNS_RECORD_TYPES = ("A", "AAAA", "CAA", "CNAME", "MX", "NS", "SRV", "TXT")
CAA_TAGS = ("issue", "issuewild", "iodef")


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


def validate_dns_record_name(record_name):
	"""Normalize a record name to lowercase, relative to its zone. "@" means the zone apex."""
	value = (record_name or "@").strip().lower().rstrip(".")
	if value in ("", "@"):
		return "@"
	if not DNS_NAME_RE.match(value):
		frappe.throw(_("{0} is not a valid DNS record name.").format(record_name))
	return value


def validate_dns_record_value(record_type, value):
	"""Type-specific validation for a DNS record's value, per RFC-shaped constraints for the
	record types this app manages (A, AAAA, CAA, CNAME, MX, NS, SRV, TXT)."""
	if not value or not value.strip():
		frappe.throw(_("Value is required for a {0} record.").format(record_type))
	value = value.strip().rstrip(".")

	if record_type == "A":
		try:
			ipaddress.IPv4Address(value)
		except ValueError:
			frappe.throw(_("{0} is not a valid IPv4 address for an A record.").format(value))
	elif record_type == "AAAA":
		try:
			ipaddress.IPv6Address(value)
		except ValueError:
			frappe.throw(_("{0} is not a valid IPv6 address for an AAAA record.").format(value))
	elif record_type in ("CNAME", "MX", "NS", "SRV"):
		if not DOMAIN_RE.match(value.lower()):
			frappe.throw(_("{0} is not a valid target domain for a {1} record.").format(value, record_type))
	return value


def validate_caa_tag(tag):
	if tag not in CAA_TAGS:
		frappe.throw(_("{0} is not a valid CAA tag. Use one of: {1}").format(tag, ", ".join(CAA_TAGS)))
	return tag


def validate_caa_value(tag, value):
	"""CAA's value shape depends on its tag: issue/issuewild take a CA domain (or "; " to
	deny all CAs); iodef takes a reporting URI (mailto: or http(s):), not a domain."""
	if tag in ("issue", "issuewild"):
		if value != ";" and not DOMAIN_RE.match(value.lower()):
			frappe.throw(
				_(
					"{0} is not a valid CAA value for tag '{1}' -- expected a CA domain (e.g. letsencrypt.org) or ';'."
				).format(value, tag)
			)
	elif tag == "iodef":
		if not re.match(r"^(mailto:|https?://)", value.lower()):
			frappe.throw(
				_(
					"{0} is not a valid CAA value for tag 'iodef' -- expected a mailto: or http(s):// URI."
				).format(value)
			)


def dns_name_to_fqdn(record_name, domain):
	"""Convert a name relative to `domain` ("@", "www") to a fully-qualified, trailing-dot name."""
	value = (record_name or "@").strip().lower().rstrip(".")
	if value in ("", "@"):
		return f"{domain}."
	if value == domain or value.endswith(f".{domain}"):
		return f"{value}."
	return f"{value}.{domain}."


def dns_name_from_fqdn(remote_name, domain):
	"""Convert a zone's fully-qualified record name back to a name relative to `domain`."""
	value = (remote_name or "").strip().lower().rstrip(".")
	domain = (domain or "").lower()
	if value == domain:
		return "@"
	suffix = f".{domain}"
	if value.endswith(suffix):
		return value[: -len(suffix)]
	return value or "@"
