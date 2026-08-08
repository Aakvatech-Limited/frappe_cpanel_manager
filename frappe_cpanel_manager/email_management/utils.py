import re

import frappe
from frappe import _

MAILBOX_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._+-]{0,62}[a-z0-9])?$")


def normalize_mailbox(raw_mailbox):
	"""Lowercase and validate a mailbox local-part (the part before the "@").

	Accepts a bare local part ("sales") or a full address ("Sales@Example.com") and
	always returns just the local part, so a pasted full address doesn't fail validation
	against the wrong domain.
	"""
	if not raw_mailbox or not raw_mailbox.strip():
		frappe.throw(_("Mailbox is required."))

	value = raw_mailbox.strip().lower()
	value = value.split("@")[0]

	if not MAILBOX_RE.match(value):
		frappe.throw(_("{0} is not a valid mailbox name.").format(raw_mailbox))

	return value
