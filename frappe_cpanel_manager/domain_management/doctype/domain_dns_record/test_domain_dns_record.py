# Copyright (c) 2026,     Aakvatech-Limited and Contributors
# See license.txt

import frappe
from frappe.tests import UnitTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


def make_row(**kwargs):
	values = {"doctype": "Domain DNS Record", "record_type": "A", "record_name": "www", "value": "192.0.2.1"}
	values.update(kwargs)
	return frappe.get_doc(values)


class UnitTestDomainDNSRecord(UnitTestCase):
	def test_valid_a_record_passes(self):
		row = make_row()
		row.validate()
		self.assertEqual(row.value, "192.0.2.1")
		self.assertEqual(row.ttl, 14400)

	def test_invalid_ipv4_is_rejected(self):
		row = make_row(value="not-an-ip")
		with self.assertRaises(frappe.ValidationError):
			row.validate()

	def test_invalid_ipv6_is_rejected(self):
		row = make_row(record_type="AAAA", value="192.0.2.1")
		with self.assertRaises(frappe.ValidationError):
			row.validate()

	def test_valid_ipv6_passes(self):
		row = make_row(record_type="AAAA", value="2001:db8::1")
		row.validate()
		self.assertEqual(row.value, "2001:db8::1")

	def test_cname_requires_domain_like_value(self):
		row = make_row(record_type="CNAME", value="not a domain")
		with self.assertRaises(frappe.ValidationError):
			row.validate()

	def test_valid_cname_passes(self):
		row = make_row(record_type="CNAME", value="target.example.com.")
		row.validate()
		self.assertEqual(row.value, "target.example.com")

	def test_mx_without_priority_is_rejected(self):
		row = make_row(record_type="MX", value="mail.example.com")
		with self.assertRaises(frappe.ValidationError):
			row.validate()

	def test_mx_with_priority_passes(self):
		row = make_row(record_type="MX", value="mail.example.com", priority=10)
		row.validate()

	def test_srv_requires_weight_and_port(self):
		row = make_row(record_type="SRV", value="sip.example.com", priority=10)
		with self.assertRaises(frappe.ValidationError):
			row.validate()

	def test_srv_with_all_fields_passes(self):
		row = make_row(record_type="SRV", value="sip.example.com", priority=10, weight=5, port=5060)
		row.validate()

	def test_txt_allows_arbitrary_text(self):
		row = make_row(record_type="TXT", record_name="@", value="v=spf1 include:example.com ~all")
		row.validate()

	def test_empty_value_is_rejected(self):
		row = make_row(value="")
		with self.assertRaises(frappe.ValidationError):
			row.validate()

	def test_record_name_normalized_to_apex(self):
		row = make_row(record_name="")
		row.validate()
		self.assertEqual(row.record_name, "@")

	def test_invalid_record_name_is_rejected(self):
		row = make_row(record_name="not a valid name!")
		with self.assertRaises(frappe.ValidationError):
			row.validate()
