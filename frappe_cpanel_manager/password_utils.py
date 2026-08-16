"""Secure password generation and strength checking.

Implements the password rules the project README sets out: at least 14
characters, mixed case, a digit, a special character, and never containing the
domain name or mailbox/username it belongs to.

Generation is deliberately server-side only. Doing it in the browser would put
the plaintext into console/devtools history, which the README rules out, and
`secrets` gives a cryptographically secure source that JS `Math.random` does not.
"""

import re
import secrets
import string

import frappe
from frappe import _

MIN_PASSWORD_LENGTH = 14
DEFAULT_PASSWORD_LENGTH = 20

# Quotes, backslashes and spaces are excluded: these passwords travel through
# WHM/UAPI query params and shell-adjacent tooling, where they are the classic
# source of "works locally, breaks on the server" quoting bugs.
SPECIAL_CHARACTERS = "!@#$%^&*()-_=+.,?"
PASSWORD_ALPHABET = string.ascii_lowercase + string.ascii_uppercase + string.digits + SPECIAL_CHARACTERS

# Substrings that make a password guessable regardless of length.
COMMON_PASSWORD_FRAGMENTS = (
	"password",
	"passwd",
	"qwerty",
	"letmein",
	"welcome",
	"admin",
	"root",
	"cpanel",
	"webmail",
	"123456",
	"abc123",
	"iloveyou",
	"changeme",
	"secret",
)


def _split_terms(exclude_terms):
	"""Expand terms into the pieces worth checking.

	A mailbox of "sales" or a domain of "example.com" should also rule out
	"example", so domains are split on their separators as well as kept whole.
	"""
	terms = set()
	for term in exclude_terms or []:
		if not term:
			continue
		value = str(term).strip().lower()
		if not value:
			continue
		terms.add(value)
		for part in re.split(r"[.@_\-]+", value):
			# Two-character fragments ("co", "io") would reject almost any
			# random string, so only keep parts long enough to be meaningful.
			if len(part) >= 3:
				terms.add(part)
	return terms


def generate_password(exclude_terms=None, length=DEFAULT_PASSWORD_LENGTH):
	"""Return a random password satisfying every rule in `check_password_strength`.

	`exclude_terms` should carry the domain and mailbox/username the password is
	for, so the result can never embed its own account name.
	"""
	length = max(int(length or DEFAULT_PASSWORD_LENGTH), MIN_PASSWORD_LENGTH)
	terms = _split_terms(exclude_terms)
	rng = secrets.SystemRandom()

	# Bounded rather than `while True`: each attempt already satisfies the
	# character-class rules, so retries only guard the (very unlikely) case of a
	# random string happening to contain an excluded term.
	for _attempt in range(100):
		characters = [
			secrets.choice(string.ascii_lowercase),
			secrets.choice(string.ascii_uppercase),
			secrets.choice(string.digits),
			secrets.choice(SPECIAL_CHARACTERS),
		]
		characters += [secrets.choice(PASSWORD_ALPHABET) for _ in range(length - len(characters))]
		rng.shuffle(characters)
		password = "".join(characters)

		lowered = password.lower()
		if any(term in lowered for term in terms):
			continue
		if any(fragment in lowered for fragment in COMMON_PASSWORD_FRAGMENTS):
			continue
		return password

	frappe.throw(_("Could not generate a password that satisfies the required rules."))


def check_password_strength(password, exclude_terms=None):
	"""Return a list of human-readable rule violations; empty means the password passes."""
	problems = []
	value = password or ""

	if len(value) < MIN_PASSWORD_LENGTH:
		problems.append(_("Must be at least {0} characters long.").format(MIN_PASSWORD_LENGTH))
	if not any(character.islower() for character in value):
		problems.append(_("Must contain a lowercase letter."))
	if not any(character.isupper() for character in value):
		problems.append(_("Must contain an uppercase letter."))
	if not any(character.isdigit() for character in value):
		problems.append(_("Must contain a number."))
	if not any(character in SPECIAL_CHARACTERS for character in value):
		problems.append(_("Must contain a special character."))

	lowered = value.lower()
	if any(term in lowered for term in _split_terms(exclude_terms)):
		problems.append(_("Must not contain the domain name or account name."))
	if any(fragment in lowered for fragment in COMMON_PASSWORD_FRAGMENTS):
		problems.append(_("Must not contain a common or easily guessed word."))

	return problems
