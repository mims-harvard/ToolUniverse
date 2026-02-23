"""
Identifiers.org API tool for ToolUniverse.

Identifiers.org is an ELIXIR service providing persistent, resolvable identifiers
for life science data. It supports 800+ registered namespaces (databases).

API: https://resolver.api.identifiers.org and https://registry.api.identifiers.org
No authentication required. Public access.
"""

import requests
from typing import Any

from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool

RESOLVER_BASE = "https://resolver.api.identifiers.org"
REGISTRY_BASE = "https://registry.api.identifiers.org"


@register_tool("IdentifiersOrgTool")
class IdentifiersOrgTool(BaseRESTTool):
    """
    Tool for Identifiers.org - biological identifier resolution service.

    Resolves compact identifiers (e.g., 'uniprot:P04637') to resource URLs
    and searches the namespace registry.

    No authentication required.
    """

    def __init__(self, tool_config: dict):
        super().__init__(tool_config)
        self.timeout = 20
        self.operation = tool_config.get("fields", {}).get("operation", "resolve")

    def run(self, arguments: dict) -> dict:
        """Execute the Identifiers.org API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"Identifiers.org request timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to Identifiers.org."}
        except requests.exceptions.HTTPError as e:
            return {"error": f"Identifiers.org HTTP error: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: dict) -> dict:
        op = self.operation
        if op == "resolve":
            return self._resolve(arguments)
        elif op == "get_namespace":
            return self._get_namespace(arguments)
        elif op == "search_namespaces":
            return self._search_namespaces(arguments)
        elif op == "list_namespaces":
            return self._list_namespaces(arguments)
        else:
            return {"error": f"Unknown operation: {op}"}

    def _resolve(self, arguments: dict) -> dict:
        """Resolve a compact identifier to resource URLs."""
        compact_id = arguments.get("compact_id", "").strip()
        if not compact_id:
            return {
                "error": "compact_id parameter is required (e.g., 'uniprot:P04637')"
            }

        # Use the compact_id directly in the URL path (no URL encoding of colon)
        url = f"{RESOLVER_BASE}/{compact_id}"
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        payload = data.get("payload", {})
        parsed = payload.get("parsedCompactIdentifier", {})
        resources = payload.get("resolvedResources", [])

        resolved = []
        for r in resources:
            resolved.append(
                {
                    "provider_code": r.get("providerCode"),
                    "resolved_url": r.get("compactIdentifierResolvedUrl"),
                    "description": r.get("description"),
                    "official": r.get("official"),
                    "home_url": r.get("resourceHomeUrl"),
                    "institution": r.get("institution", {}).get("name"),
                }
            )

        return {
            "data": {
                "compact_id": compact_id,
                "namespace": parsed.get("namespace"),
                "local_id": parsed.get("localId"),
                "resolved_resources": resolved,
                "resource_count": len(resolved),
            },
            "metadata": {
                "source": "Identifiers.org",
                "error_message": data.get("errorMessage"),
            },
        }

    def _get_namespace(self, arguments: dict) -> dict:
        """Get namespace details by prefix."""
        prefix = arguments.get("prefix", "").strip()
        if not prefix:
            return {"error": "prefix parameter is required (e.g., 'uniprot', 'pdb')"}

        url = f"{REGISTRY_BASE}/restApi/namespaces/search/findByPrefix"
        resp = requests.get(url, params={"prefix": prefix}, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        return {
            "data": data,
            "metadata": {
                "prefix": prefix,
                "source": "Identifiers.org Registry",
            },
        }

    def _search_namespaces(self, arguments: dict) -> dict:
        """Search namespaces by keyword."""
        content = arguments.get("content", "").strip()
        if not content:
            return {"error": "content parameter is required"}

        params: dict[str, Any] = {
            "content": content,
            "page": arguments.get("page", 0),
            "size": min(int(arguments.get("size", 10)), 50),
        }

        url = f"{REGISTRY_BASE}/restApi/namespaces/search/findByPrefixContaining"
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        embedded = data.get("_embedded", {})
        namespaces = embedded.get("namespaces", [])
        page_info = data.get("page", {})

        ns_list = []
        for ns in namespaces:
            ns_list.append(
                {
                    "prefix": ns.get("prefix"),
                    "name": ns.get("name"),
                    "pattern": ns.get("pattern"),
                    "description": ns.get("description"),
                    "sample_id": ns.get("sampleId"),
                    "deprecated": ns.get("deprecated"),
                }
            )

        return {
            "data": {
                "namespaces": ns_list,
                "total_elements": page_info.get("totalElements"),
                "total_pages": page_info.get("totalPages"),
            },
            "metadata": {
                "search_term": content,
                "source": "Identifiers.org Registry",
            },
        }

    def _list_namespaces(self, arguments: dict) -> dict:
        """List all registered namespaces with pagination."""
        params: dict[str, Any] = {
            "page": arguments.get("page", 0),
            "size": min(int(arguments.get("size", 20)), 100),
        }

        url = f"{REGISTRY_BASE}/restApi/namespaces"
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        embedded = data.get("_embedded", {})
        namespaces = embedded.get("namespaces", [])
        page_info = data.get("page", {})

        ns_list = [
            {
                "prefix": ns.get("prefix"),
                "name": ns.get("name"),
                "pattern": ns.get("pattern"),
                "sample_id": ns.get("sampleId"),
            }
            for ns in namespaces
        ]

        return {
            "data": {
                "namespaces": ns_list,
                "total_elements": page_info.get("totalElements"),
                "total_pages": page_info.get("totalPages"),
                "current_page": page_info.get("number"),
            },
            "metadata": {
                "source": "Identifiers.org Registry",
            },
        }
