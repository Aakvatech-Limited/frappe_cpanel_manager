import requests

import frappe
from frappe.utils import now_datetime

from frappe_cpanel_manager.integrations.cpanel.exceptions import (
	CPanelAPIError,
	CPanelAuthenticationError,
	CPanelNetworkError,
	CPanelPermissionError,
	CPanelSSLError,
	CPanelTimeoutError,
	CPanelUnknownResponseError,
)

SANITIZE_KEYS = {"password", "pass", "token", "whm_api_token", "new_password", "cpanel_token"}


def sanitize_params(params):
	if not params:
		return params
	return {key: ("***REDACTED***" if key.lower() in SANITIZE_KEYS else value) for key, value in params.items()}


class CPanelClient:
	def __init__(self, server):
		if isinstance(server, str):
			server = frappe.get_doc("cPanel Server", server)
		self.server = server
		self.hostname = server.hostname.strip().rstrip("/")
		self.verify_ssl = bool(server.verify_ssl)
		self.whm_username = server.whm_username
		self.whm_token = server.get_password("whm_api_token")

	def _check_response(self, response):
		try:
			payload = response.json()
		except ValueError:
			frappe.log_error(title="Invalid cPanel API Response", message=response.text)
			raise CPanelUnknownResponseError("The cPanel server returned an invalid response.")

		if response.status_code == 401:
			raise CPanelAuthenticationError(self._extract_error(payload) or "Authentication with the cPanel server failed.")
		if response.status_code == 403:
			raise CPanelPermissionError(self._extract_error(payload) or "The API token does not have permission for this operation.")

		if not response.ok:
			raise CPanelAPIError(self._extract_error(payload) or "The cPanel API request failed.")

		error = self._extract_error(payload)
		if error:
			raise CPanelAPIError(error)

		return payload

	def _extract_error(self, payload):
		if not isinstance(payload, dict):
			return None

		metadata = payload.get("metadata") or {}
		if metadata.get("result") in (0, False):
			return metadata.get("reason")

		result = payload.get("result")
		if isinstance(result, dict):
			errors = result.get("errors")
			if isinstance(errors, list):
				return "\n".join(str(error) for error in errors if error)
			if errors:
				return str(errors)

		return None

	def _request(self, url, headers, params, method):
		try:
			if method.upper() == "POST":
				return requests.post(url, headers=headers, data=params or {}, timeout=60, verify=self.verify_ssl)
			return requests.get(url, headers=headers, params=params or {}, timeout=60, verify=self.verify_ssl)
		except requests.exceptions.SSLError as e:
			raise CPanelSSLError(f"SSL certificate verification failed for {self.hostname}.") from e
		except requests.exceptions.Timeout as e:
			raise CPanelTimeoutError(f"The request to {self.hostname} timed out.") from e
		except requests.exceptions.ConnectionError as e:
			raise CPanelNetworkError(f"Unable to reach {self.hostname}.") from e

	def _log(self, api_layer, operation, params, response=None, error=None, reference_doctype=None, reference_name=None):
		sanitized_response = None
		if response is not None:
			try:
				sanitized_response = frappe.as_json(response.json(), indent=2)
			except ValueError:
				sanitized_response = response.text

		try:
			frappe.get_doc(
				{
					"doctype": "cPanel Integration Log",
					"server": self.server.name,
					"operation": operation,
					"api_layer": api_layer,
					"status": "Failed" if error else "Success",
					"http_status": getattr(response, "status_code", None),
					"request_time": now_datetime(),
					"completion_time": now_datetime(),
					"sanitized_request": frappe.as_json(sanitize_params(params), indent=2),
					"sanitized_response": sanitized_response,
					"error_message": str(error) if error else None,
					"reference_doctype": reference_doctype,
					"reference_name": reference_name,
				}
			).insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(title="Failed to write cPanel Integration Log", message=frappe.get_traceback())

	def call_whm(self, function_name, params=None, reference_doctype=None, reference_name=None):
		if not self.whm_token:
			raise CPanelAPIError("WHM API token is not configured.")

		url = f"https://{self.hostname}:{self.server.whm_port or 2087}/json-api/{function_name}"
		headers = {"Authorization": f"whm {self.whm_username}:{self.whm_token}"}
		query = {"api.version": 1}
		query.update(params or {})

		response = None
		try:
			response = self._request(url, headers, query, "GET")
			result = self._check_response(response)
		except CPanelAPIError as e:
			self._log(
				"WHM API 1",
				function_name,
				query,
				response=response,
				error=e,
				reference_doctype=reference_doctype,
				reference_name=reference_name,
			)
			raise

		self._log(
			"WHM API 1",
			function_name,
			query,
			response=response,
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)
		return result

	def call_uapi(
		self,
		cpanel_username,
		cpanel_token,
		module,
		function_name,
		params=None,
		method="GET",
		reference_doctype=None,
		reference_name=None,
	):
		url = f"https://{self.hostname}:{self.server.cpanel_port or 2083}/execute/{module}/{function_name}"
		headers = {"Authorization": f"cpanel {cpanel_username}:{cpanel_token}"}

		response = None
		try:
			response = self._request(url, headers, params, method)
			result = self._check_response(response)
		except CPanelAPIError as e:
			self._log(
				"cPanel UAPI",
				f"{module}/{function_name}",
				params,
				response=response,
				error=e,
				reference_doctype=reference_doctype,
				reference_name=reference_name,
			)
			raise

		self._log(
			"cPanel UAPI",
			f"{module}/{function_name}",
			params,
			response=response,
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)
		return result

	def call_uapi_via_whm(
		self, cpanel_username, module, function_name, params=None, reference_doctype=None, reference_name=None
	):
		"""Execute a UAPI function through the WHM 'cpanel' proxy, using only the
		WHM token (no per-account cPanel token needed).

		NOTE: the exact request/response shape used here is inferred from cPanel's
		published documentation and has not been verified against a live server.
		Confirm during the sandbox spike and adjust as needed:
		https://api.docs.cpanel.net/whm/introduction/calling-uapi-and-api-1-functions-with-whm-api-1/
		"""
		whm_params = {
			"cpanel_jsonapi_user": cpanel_username,
			"cpanel_jsonapi_apiversion": 3,
			"cpanel_jsonapi_module": module,
			"cpanel_jsonapi_func": function_name,
		}
		whm_params.update(params or {})
		return self.call_whm(
			"cpanel", params=whm_params, reference_doctype=reference_doctype, reference_name=reference_name
		)
