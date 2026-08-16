# Copyright (c) 2026, Aakvatech-Limited and Contributors
# See license.txt

import frappe
from frappe.tests import UnitTestCase

from frappe_cpanel_manager.password_utils import (
	DEFAULT_PASSWORD_LENGTH,
	MIN_PASSWORD_LENGTH,
	SPECIAL_CHARACTERS,
	check_password_strength,
	generate_password,
)


class UnitTestPasswordGeneration(UnitTestCase):
	def test_generated_password_satisfies_every_rule(self):
		# Generated repeatedly: the character classes are seeded deterministically
		# but the rest is random, so a single sample could pass by luck.
		for _ in range(50):
			password = generate_password(exclude_terms=["sales", "example.com"])
			self.assertEqual(check_password_strength(password, ["sales", "example.com"]), [])

	def test_generated_password_has_expected_length_and_classes(self):
		password = generate_password()
		self.assertEqual(len(password), DEFAULT_PASSWORD_LENGTH)
		self.assertTrue(any(c.islower() for c in password))
		self.assertTrue(any(c.isupper() for c in password))
		self.assertTrue(any(c.isdigit() for c in password))
		self.assertTrue(any(c in SPECIAL_CHARACTERS for c in password))

	def test_short_length_is_raised_to_the_minimum(self):
		self.assertEqual(len(generate_password(length=4)), MIN_PASSWORD_LENGTH)

	def test_generated_passwords_are_unique(self):
		passwords = {generate_password() for _ in range(200)}
		self.assertEqual(len(passwords), 200)

	def test_generated_password_excludes_quotes_and_spaces(self):
		# These travel through WHM query params and shell-adjacent tooling.
		for _ in range(50):
			password = generate_password()
			for forbidden in ("'", '"', "\\", " ", "`"):
				self.assertNotIn(forbidden, password)

	def test_generated_password_never_contains_its_own_account_terms(self):
		for _ in range(100):
			password = generate_password(exclude_terms=["postmaster", "shaule.space"])
			lowered = password.lower()
			for term in ("postmaster", "shaule.space", "shaule", "space"):
				self.assertNotIn(term, lowered)


class UnitTestPasswordStrength(UnitTestCase):
	def test_too_short_is_rejected(self):
		self.assertIn("Must be at least 14 characters long.", check_password_strength("Ab1!efgh"))

	def test_missing_character_classes_are_reported(self):
		problems = check_password_strength("abcdefghijklmnop")
		self.assertIn("Must contain an uppercase letter.", problems)
		self.assertIn("Must contain a number.", problems)
		self.assertIn("Must contain a special character.", problems)

	def test_password_containing_domain_is_rejected(self):
		problems = check_password_strength("Xy7!example.comQq", ["example.com"])
		self.assertIn("Must not contain the domain name or account name.", problems)

	def test_password_containing_mailbox_is_rejected(self):
		problems = check_password_strength("Xy7!salesQqrstuv", ["sales"])
		self.assertIn("Must not contain the domain name or account name.", problems)

	def test_common_word_is_rejected(self):
		problems = check_password_strength("MyPassword123!xy")
		self.assertIn("Must not contain a common or easily guessed word.", problems)

	def test_short_domain_parts_do_not_cause_false_rejections(self):
		# "co" from "foo.co" must not be treated as an excluded term, or almost
		# any random password would be rejected.
		self.assertEqual(check_password_strength("Xy7!QwrtuvbnmK", ["foo.co"]), [])

	def test_strong_password_passes(self):
		self.assertEqual(check_password_strength("Xy7!QwrtuvbnmK"), [])


class IntegrationTestGeneratePasswordEndpoints(frappe.tests.IntegrationTestCase):
	def setUp(self):
		self.server = frappe.get_doc(
			{
				"doctype": "cPanel Server",
				"server_name": f"pwtest-{frappe.generate_hash(length=8)}",
				"hostname": "whm.example.test",
				"whm_username": "root",
				"whm_api_token": "top-secret-token",
			}
		).insert()
		self.domain = frappe.get_doc(
			{
				"doctype": "Hosted Domain",
				"domain_name": "pwgen.example.com",
				"server": self.server.name,
				"provisioning_type": "New cPanel Account",
				"cpanel_username": "pwgenuser",
				"contact_email": "owner@example.com",
				"initial_cpanel_password": "placeholder-value",
			}
		).insert()

	def tearDown(self):
		frappe.db.delete("Domain Email Account", {"hosted_domain": self.domain.name})
		frappe.db.delete("Hosted Domain", {"server": self.server.name})
		frappe.delete_doc("cPanel Server", self.server.name, force=True)

	def test_domain_endpoint_returns_a_valid_password_without_storing_it(self):
		from frappe_cpanel_manager.api.domain import generate_cpanel_password

		before = self.domain.get_password("initial_cpanel_password", raise_exception=False)
		result = generate_cpanel_password(self.domain.name)
		password = result["password"]

		self.assertEqual(check_password_strength(password, ["pwgenuser", "pwgen.example.com"]), [])
		self.domain.reload()
		# Generating must not touch the stored value; the client sets it explicitly.
		self.assertEqual(self.domain.get_password("initial_cpanel_password", raise_exception=False), before)

	def test_mailbox_endpoint_excludes_mailbox_and_domain(self):
		from frappe_cpanel_manager.api.email import generate_mailbox_password

		self.domain.db_set("status", "Active", update_modified=False)
		account = frappe.get_doc(
			{
				"doctype": "Domain Email Account",
				"hosted_domain": self.domain.name,
				"mailbox": "billing",
				"quota_mb": 1024,
			}
		).insert()

		password = generate_mailbox_password(account.name)["password"]
		self.assertEqual(check_password_strength(password, ["billing", "pwgen.example.com"]), [])

	def test_generating_writes_no_integration_log(self):
		from frappe_cpanel_manager.api.domain import generate_cpanel_password

		generate_cpanel_password(self.domain.name)
		logs = frappe.get_all(
			"cPanel Integration Log",
			filters={"reference_doctype": "Hosted Domain", "reference_name": self.domain.name},
		)
		self.assertEqual(logs, [])
