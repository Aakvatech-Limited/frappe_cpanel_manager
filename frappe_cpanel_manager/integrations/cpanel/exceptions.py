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
