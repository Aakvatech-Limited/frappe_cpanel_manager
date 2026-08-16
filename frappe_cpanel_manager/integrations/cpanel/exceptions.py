import frappe


class CPanelAPIError(frappe.ValidationError):
	pass


class CPanelAuthenticationError(CPanelAPIError):
	pass


class CPanelPermissionError(CPanelAPIError):
	pass


class CPanelValidationError(CPanelAPIError):
	pass


class CPanelDuplicateResourceError(CPanelAPIError):
	pass


class CPanelNetworkError(CPanelAPIError):
	pass


class CPanelSSLError(CPanelAPIError):
	pass


class CPanelTimeoutError(CPanelAPIError):
	pass


class CPanelUnknownResponseError(CPanelAPIError):
	pass


# The categories the README asks the integration log to report. Kept here next to
# the taxonomy so a new exception class can't be added without a category.
ERROR_CATEGORIES = {
	CPanelAuthenticationError: "Authentication Error",
	CPanelPermissionError: "Permission Error",
	CPanelValidationError: "Validation Error",
	CPanelDuplicateResourceError: "Duplicate Resource",
	CPanelNetworkError: "Network Error",
	CPanelSSLError: "SSL Error",
	CPanelTimeoutError: "Timeout",
	CPanelUnknownResponseError: "Unknown Remote Response",
	CPanelAPIError: "cPanel API Error",
}


def error_category(exception):
	"""Classify an exception for the integration log.

	Walks the MRO so a subclass added later still resolves to its closest known
	parent rather than silently logging nothing.
	"""
	if exception is None:
		return None
	for klass in type(exception).__mro__:
		if klass in ERROR_CATEGORIES:
			return ERROR_CATEGORIES[klass]
	return "Unknown Error"


# Raw cPanel/WHM text is written for server admins, not for the person clicking a
# button in Frappe. These patterns turn the common failures into the kind of
# message the README asks for -- naming the resource and the reason -- while the
# untouched original is still kept on the document and in the integration log.
_FRIENDLY_PATTERNS = (
	("already exists", "{target} already exists on the server."),
	("already registered", "{target} is already registered on the server."),
	("does not exist", "{target} does not exist on the server."),
	("no such user", "{target} does not exist on the server."),
	("quota", "The request was rejected because it exceeds a limit on the account ({reason})."),
	("permission denied", "The API token is not permitted to do this ({reason})."),
	("invalid login", "The server rejected the API credentials."),
)


def friendly_message(action, target, exception):
	"""Build an operator-readable message for a failed cPanel action.

	`action` is a short verb phrase ("create mailbox"), `target` names the thing
	being acted on. Falls back to the raw reason rather than inventing one when
	nothing matches, so no failure is ever silently reworded into something less
	accurate than the server said.
	"""
	reason = str(exception or "").strip()
	lowered = reason.lower()

	for needle, template in _FRIENDLY_PATTERNS:
		if needle in lowered:
			return "Unable to {action} {target}: {detail}".format(
				action=action,
				target=target,
				detail=template.format(target=target, reason=reason),
			)

	if not reason:
		return f"Unable to {action} {target}: the cPanel server did not explain why."
	return f"Unable to {action} {target}: {reason}"
