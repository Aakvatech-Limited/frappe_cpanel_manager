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
