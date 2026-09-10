# Copyright (c) 2026,     Aakvatech-Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from frappe_cpanel_manager.domain_management.utils import (
	validate_caa_tag,
	validate_caa_value,
	validate_dns_record_name,
	validate_dns_record_value,
)


class DomainDNSRecord(Document):
	def validate(self):
		self.record_name = validate_dns_record_name(self.record_name)
		self.value = validate_dns_record_value(self.record_type, self.value)
		self.ttl = cint(self.ttl) or 14400

		if self.record_type in ("MX", "SRV") and self.priority in (None, ""):
			frappe.throw(_("Priority is required for {0} records.").format(self.record_type))

		if self.record_type == "SRV":
			if self.weight is None or self.weight == "":
				frappe.throw(_("Weight is required for SRV records."))
			if not self.port:
				frappe.throw(_("Port is required for SRV records."))

		if self.record_type == "CAA":
			if self.caa_flag in (None, ""):
				frappe.throw(_("CAA Flag is required for CAA records."))
			self.caa_tag = validate_caa_tag(self.caa_tag)
			validate_caa_value(self.caa_tag, self.value)
