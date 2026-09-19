"""
protocols.io API Tool

Provides programmatic access to protocols.io, the widely-used public
repository of peer-reviewed and community-submitted scientific lab
protocols (https://www.protocols.io/).

Supports:
- Searching public protocols by keyword
- Retrieving a specific protocol's full detail (description, materials,
  authors, DOI)
- Listing a specific protocol's ordered steps

API docs: https://apidoc.protocols.io/
Authentication: OAuth Bearer token via the PROTOCOLS_IO_API_KEY
environment variable. Obtain a token by registering an application at
https://www.protocols.io/api-clients and completing the OAuth flow (or
using a static developer token issued for your account).
"""

import os
import requests
from typing import Any, Dict, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

_API_KEY_FROM_ENV = object()

# Search lives on the v3 API; per-protocol detail/steps moved to v4.
SEARCH_BASE_URL = "https://www.protocols.io/api/v3"
DETAIL_BASE_URL = "https://www.protocols.io/api/v4"


@register_tool("ProtocolsIOTool")
class ProtocolsIOTool(BaseTool):
    """
    Tool for querying protocols.io's public protocol repository.

    Requires an OAuth Bearer token via the PROTOCOLS_IO_API_KEY
    environment variable. Register an API client at
    https://www.protocols.io/api-clients to obtain one.
    """

    def __init__(
        self,
        tool_config: Dict[str, Any],
        api_key: Optional[str] = _API_KEY_FROM_ENV,
        timeout: int = 30,
    ):
        super().__init__(tool_config)
        self.timeout = timeout
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        if api_key is _API_KEY_FROM_ENV:
            # Resolve at construction time so a long-lived process or test
            # can rotate credentials without re-importing this module.
            api_key = os.environ.get("PROTOCOLS_IO_API_KEY")
        self.api_key = api_key

    def _headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": "Bearer " + self.api_key,
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation")
        if not operation:
            return {
                "status": "error",
                "error": "Missing required parameter: operation",
            }

        if not self.api_key:
            return {
                "status": "error",
                "error": (
                    "protocols.io API key required. Set PROTOCOLS_IO_API_KEY "
                    "to a valid OAuth Bearer token. Register an API client "
                    "at https://www.protocols.io/api-clients to obtain one."
                ),
            }

        handlers = {
            "search_protocols": self._search_protocols,
            "get_protocol": self._get_protocol,
            "get_protocol_steps": self._get_protocol_steps,
        }

        handler = handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}. Available: {}".format(
                    operation, ", ".join(handlers.keys())
                ),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "protocols.io API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to protocols.io API"}
        except Exception as e:  # noqa: BLE001 - surfaced to the caller, not raised
            return {"status": "error", "error": "Operation failed: {}".format(str(e))}

    @staticmethod
    def _auth_error(response) -> Optional[Dict[str, Any]]:
        if response.status_code in (401, 403):
            return {
                "status": "error",
                "error": (
                    "Authentication failed (HTTP {}). Check that "
                    "PROTOCOLS_IO_API_KEY holds a current OAuth Bearer "
                    "token; tokens expire roughly once a year and must be "
                    "refreshed."
                ).format(response.status_code),
            }
        if response.status_code == 400:
            # Live-verified: protocols.io returns 400 (not 401/403) for a
            # malformed or invalid Bearer token, in addition to genuinely
            # malformed requests -- so this hint stays a possibility, not a
            # certainty.
            return {
                "status": "error",
                "error": (
                    "protocols.io returned HTTP 400. This can mean a "
                    "malformed request, but for this API it also commonly "
                    "means PROTOCOLS_IO_API_KEY is invalid or expired -- "
                    "verify the token before assuming the request itself "
                    "is wrong."
                ),
            }
        if response.status_code == 404:
            return {"status": "error", "error": "Protocol not found on protocols.io"}
        return None

    def _search_protocols(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search public protocols.io protocols by keyword."""
        query = arguments.get("query")
        if not query:
            return {"status": "error", "error": "Missing required parameter: query"}

        limit = min(int(arguments.get("limit", 10) or 10), 50)
        order_field = arguments.get("order_field") or "relevance"

        params = {
            "filter": "public",
            "key": query,
            "order_field": order_field,
            "order_dir": "desc",
            "page_size": limit,
        }

        response = requests.get(
            SEARCH_BASE_URL + "/protocols",
            params=params,
            headers=self._headers(),
            timeout=self.timeout,
        )

        auth_err = self._auth_error(response)
        if auth_err:
            return auth_err

        response.raise_for_status()
        data = response.json()
        items = data.get("items", data.get("protocols", []))

        return {
            "status": "success",
            "data": {
                "protocols": items,
                "total_count": data.get("pagination", {}).get(
                    "total_results", len(items)
                ),
            },
            "metadata": {
                "source": "protocols.io",
                "query": query,
                "order_field": order_field,
            },
        }

    def _get_protocol(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get full detail for a specific protocol by ID, URI, or DOI."""
        protocol_id = arguments.get("protocol_id")
        if not protocol_id:
            return {
                "status": "error",
                "error": "Missing required parameter: protocol_id",
            }

        params = {"content_format": arguments.get("content_format") or "json"}

        response = requests.get(
            "{}/protocols/{}".format(DETAIL_BASE_URL, str(protocol_id).strip()),
            params=params,
            headers=self._headers(),
            timeout=self.timeout,
        )

        auth_err = self._auth_error(response)
        if auth_err:
            return auth_err

        response.raise_for_status()
        protocol = response.json()

        return {
            "status": "success",
            "data": protocol,
            "metadata": {"source": "protocols.io", "protocol_id": str(protocol_id)},
        }

    def _get_protocol_steps(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List the ordered steps for a specific protocol by ID, URI, or DOI."""
        protocol_id = arguments.get("protocol_id")
        if not protocol_id:
            return {
                "status": "error",
                "error": "Missing required parameter: protocol_id",
            }

        params = {"content_format": arguments.get("content_format") or "json"}

        response = requests.get(
            "{}/protocols/{}/steps".format(DETAIL_BASE_URL, str(protocol_id).strip()),
            params=params,
            headers=self._headers(),
            timeout=self.timeout,
        )

        auth_err = self._auth_error(response)
        if auth_err:
            return auth_err

        response.raise_for_status()
        data = response.json()
        steps = data if isinstance(data, list) else data.get("steps", [])

        return {
            "status": "success",
            "data": {"steps": steps, "step_count": len(steps)},
            "metadata": {"source": "protocols.io", "protocol_id": str(protocol_id)},
        }
