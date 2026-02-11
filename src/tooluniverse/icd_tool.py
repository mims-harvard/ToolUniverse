"""ICD (International Classification of Diseases) API Tools.

WHO ICD-11 API for disease classification and coding.

Official API: https://icd.who.int/icdapi
Requires ICD_CLIENT_ID / ICD_CLIENT_SECRET environment variables.
"""

import os
import time
from urllib.parse import quote as url_quote

import requests
from typing import Any, Dict, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

ICD_API_BASE = "https://id.who.int/icd"
ICD_API_AUTH = "https://icdaccessmanagement.who.int/connect/token"


@register_tool("ICDTool")
class ICDTool(BaseTool):
    """WHO ICD-11 API tool for disease classification and coding."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        fields = tool_config.get("fields", {})
        self.endpoint_template = fields.get("endpoint", "")
        self.linearization = fields.get("linearization", "mms")
        self.use_browser = fields.get("use_browser", False)
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0

    def _get_access_token(self) -> Optional[str]:
        """Get OAuth2 access token for ICD API (cached until near expiry)."""
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token

        client_id = os.getenv("ICD_CLIENT_ID")
        client_secret = os.getenv("ICD_CLIENT_SECRET")

        if not client_id or not client_secret:
            return None

        try:
            payload = {
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "icdapi_access",
                "grant_type": "client_credentials",
            }
            resp = requests.post(ICD_API_AUTH, data=payload, timeout=30)
            resp.raise_for_status()
            token_data = resp.json()

            self._access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)
            self._token_expiry = time.time() + (expires_in - 60)
            return self._access_token
        except Exception:
            return None

    _PLACEHOLDER_KEYS = {
        "{linearization}": "linearization",
        "{entity_id}": "entity_id",
        "{code}": "code",
    }

    def _build_url(self, arguments: Dict[str, Any]) -> str:
        """Build the full URL from endpoint template and arguments."""
        endpoint = self.endpoint_template

        for placeholder, arg_key in self._PLACEHOLDER_KEYS.items():
            if placeholder in endpoint:
                default = self.linearization if arg_key == "linearization" else ""
                endpoint = endpoint.replace(placeholder, arguments.get(arg_key, default))

        if "{search_term}" in endpoint:
            search_term = url_quote(arguments.get("query", ""))
            endpoint = endpoint.replace("{search_term}", search_term)

        if self.use_browser:
            return f"https://icd.who.int/browse/2024-01/mms{endpoint}"

        return f"{ICD_API_BASE}{endpoint}"

    _BOOL_PARAMS = ("flatResults", "useFlexisearch")

    def _make_request(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Make request to ICD API."""
        access_token = self._get_access_token()
        if not access_token:
            return {
                "error": (
                    "ICD API authentication required. "
                    "Set ICD_CLIENT_ID and ICD_CLIENT_SECRET environment variables. "
                    "Register at: https://icd.who.int/icdapi"
                )
            }

        url = self._build_url(arguments)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Accept-Language": arguments.get("language", "en"),
            "API-Version": "v2",
        }

        params = {}
        for key in self._BOOL_PARAMS:
            if key in arguments:
                params[key] = str(arguments[key]).lower()

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            return {
                "data": resp.json(),
                "metadata": {
                    "source": "WHO ICD-11 API",
                    "endpoint": url,
                    "linearization": arguments.get("linearization", self.linearization),
                    "language": arguments.get("language", "en"),
                },
            }
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {e}"}
        except ValueError as e:
            return {"error": f"Failed to parse JSON: {e}"}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        return self._make_request(arguments)


@register_tool("ICD10Tool")
class ICD10Tool(BaseTool):
    """Tool for ICD-10-CM codes using external API."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        fields = tool_config.get("fields", {})
        self.endpoint_template = fields.get("endpoint", "")
        self.base_url = fields.get("base_url", "https://clinicaltables.nlm.nih.gov/api")

    def _build_url(self, arguments: Dict[str, Any]) -> str:
        """Build the full URL from endpoint template and arguments."""
        endpoint = self.endpoint_template

        # Replace {code} placeholder
        if "{code}" in endpoint:
            code = arguments.get("code", "")
            endpoint = endpoint.replace("{code}", code)

        return f"{self.base_url}{endpoint}"

    def _make_request(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Make request to ICD-10 API (NLM Clinical Tables)."""
        url = self._build_url(arguments)

        # Build query parameters for search
        params = {}
        if "query" in arguments:
            params["sf"] = "code,name"  # Search fields
            params["terms"] = arguments["query"]
            params["maxList"] = arguments.get("limit", 20)

        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            # Parse the response format from NLM Clinical Tables
            # Format: [total_count, [codes], null, [[code, name], ...]]
            if isinstance(data, list) and len(data) >= 4:
                total = data[0]
                results = data[3] if len(data) > 3 else []

                formatted_results = []
                for item in results:
                    if len(item) >= 2:
                        formatted_results.append({
                            "code": item[0],
                            "name": item[1]
                        })

                return {
                    "data": {
                        "total": total,
                        "results": formatted_results
                    },
                    "metadata": {
                        "source": "NLM Clinical Tables - ICD-10-CM",
                        "endpoint": url,
                        "version": "2026 ICD-10-CM codes",
                        "note": "ICD-10-CM is the US clinical modification of ICD-10"
                    }
                }

            # Direct code lookup
            return {
                "data": data,
                "metadata": {
                    "source": "NLM Clinical Tables - ICD-10-CM",
                    "endpoint": url
                }
            }

        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except (ValueError, IndexError) as e:
            return {"error": f"Failed to parse response: {str(e)}"}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        return self._make_request(arguments)
