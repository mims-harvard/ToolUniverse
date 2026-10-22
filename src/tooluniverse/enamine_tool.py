"""
Enamine tool for ToolUniverse.

Enamine is a leading supplier of make-on-demand compounds, building
blocks, and screening libraries for drug discovery.

Website: https://enamine.net/
"""

import urllib.parse

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

# Enamine base URL
ENAMINE_BASE_URL = "https://enamine.net"
# Enamine Store API
ENAMINE_STORE_URL = "https://new.enaminestore.com/api"


@register_tool("EnamineTool")
class EnamineTool(BaseTool):
    """
    Tool for searching Enamine compound libraries.

    Enamine provides:
    - Make-on-demand compounds (REAL database)
    - Building blocks
    - Screening libraries
    - Fragment libraries

    Note: Full API access may require registration.
    Basic search functionality available without API key.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 30)
        self.parameter = tool_config.get("parameter", {})

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Enamine query based on operation type."""
        operation = arguments.get("operation", "")
        # Auto-fill operation from tool config const if not provided by user
        if not operation:
            operation = self.get_schema_const_operation()

        if operation == "search_catalog":
            return self._search_catalog(arguments)
        elif operation == "get_compound":
            return self._get_compound(arguments)
        elif operation == "search_smiles":
            return self._search_smiles(arguments)
        elif operation == "get_libraries":
            return self._get_libraries(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: search_catalog, get_compound, search_smiles, get_libraries",
            }

    @staticmethod
    def _pagination(arguments: Dict[str, Any]):
        limit = arguments.get("limit", 20)
        offset = arguments.get("offset", 0)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            return {"status": "error", "error": "limit must be an integer from 1 to 100"}
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {"status": "error", "error": "offset must be a non-negative integer"}
        return limit, offset

    def _search_catalog(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search Enamine catalog by keyword or compound name.

        Args:
            arguments: Dict containing:
                - query: Search query
                - catalog: Catalog type (REAL, BB, SCR) - default: all
        """
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "Missing required parameter: query"}

        catalog = arguments.get("catalog", "all")
        pagination = self._pagination(arguments)
        if isinstance(pagination, dict):
            return pagination
        limit, offset = pagination

        try:
            # Try Enamine Store API
            response = requests.get(
                f"{ENAMINE_STORE_URL}/catalog/search",
                params={"q": query, "catalog": catalog},
                timeout=self.timeout,
                headers={
                    "User-Agent": "ToolUniverse/Enamine",
                    "Accept": "application/json",
                },
            )

            if response.status_code == 200 and "json" in response.headers.get(
                "Content-Type", ""
            ):
                data = response.json()
                results = (
                    data
                    if isinstance(data, list)
                    else data.get("compounds", data.get("results", []))
                )
                if not isinstance(results, list):
                    return {
                        "status": "error",
                        "error": "Enamine API returned an unexpected search payload",
                    }
                page = results[offset : offset + limit]
                has_more = offset + len(page) < len(results)
                return {
                    "status": "success",
                    "data": {
                        "query": query,
                        "catalog": catalog,
                        "results": page,
                        "count": len(page),
                    },
                    "metadata": {
                        "source": "Enamine",
                        "upstream_payload_count": len(results),
                        "returned": len(page),
                        "limit": limit,
                        "offset": offset,
                        "has_more_within_payload": has_more,
                        "next_offset": offset + len(page) if has_more else None,
                        "upstream_result_set_complete": None,
                        "warning": "The Enamine endpoint does not document whether its JSON payload is the complete catalog match set.",
                    },
                }

            # A navigation URL is not retrieved catalog data. Report failure
            # explicitly instead of returning a successful empty result.
            api_status = response.status_code
            return {
                "status": "error",
                "error": f"Enamine catalog API unavailable (HTTP {api_status}); no catalog data was retrieved.",
                "search_url": f"{ENAMINE_BASE_URL}/compound-search/quick?q={urllib.parse.quote(query)}",
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get compound by Enamine ID.

        Args:
            arguments: Dict containing:
                - enamine_id: Enamine compound ID (e.g., Z1234567890)
        """
        enamine_id = arguments.get("enamine_id", "")
        if not enamine_id:
            return {
                "status": "error",
                "error": "Missing required parameter: enamine_id",
            }

        try:
            response = requests.get(
                f"{ENAMINE_STORE_URL}/catalog/compound/{enamine_id}",
                timeout=self.timeout,
                headers={
                    "User-Agent": "ToolUniverse/Enamine",
                    "Accept": "application/json",
                },
            )

            if response.status_code == 200 and "json" in response.headers.get(
                "Content-Type", ""
            ):
                data = response.json()
                return {
                    "status": "success",
                    "data": data,
                    "metadata": {
                        "source": "Enamine",
                        "enamine_id": enamine_id,
                    },
                }

            # Do not present a guessed web URL as retrieved compound details.
            return {
                "status": "error",
                "error": f"Enamine compound API unavailable (HTTP {response.status_code}); no compound details were retrieved.",
                "compound_url": f"{ENAMINE_BASE_URL}/compound/{urllib.parse.quote(enamine_id)}",
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _search_smiles(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search Enamine by SMILES structure.

        Args:
            arguments: Dict containing:
                - smiles: SMILES string
                - search_type: exact, substructure, similarity (default: similarity)
        """
        smiles = arguments.get("smiles", "")
        if not smiles:
            return {"status": "error", "error": "Missing required parameter: smiles"}

        search_type = arguments.get("search_type", "similarity")
        if search_type not in {"exact", "substructure", "similarity"}:
            return {
                "status": "error",
                "error": "search_type must be exact, substructure, or similarity",
            }
        pagination = self._pagination(arguments)
        if isinstance(pagination, dict):
            return pagination
        limit, offset = pagination

        try:
            response = requests.post(
                f"{ENAMINE_STORE_URL}/catalog/structure-search",
                json={"smiles": smiles, "type": search_type},
                timeout=self.timeout,
                headers={
                    "User-Agent": "ToolUniverse/Enamine",
                    "Accept": "application/json",
                },
            )

            if response.status_code == 200 and "json" in response.headers.get(
                "Content-Type", ""
            ):
                data = response.json()
                results = data if isinstance(data, list) else data.get("compounds", [])
                if not isinstance(results, list):
                    return {
                        "status": "error",
                        "error": "Enamine API returned an unexpected structure-search payload",
                    }
                page = results[offset : offset + limit]
                has_more = offset + len(page) < len(results)
                return {
                    "status": "success",
                    "data": {
                        "query_smiles": smiles,
                        "search_type": search_type,
                        "results": page,
                        "count": len(page),
                    },
                    "metadata": {
                        "source": "Enamine",
                        "upstream_payload_count": len(results),
                        "returned": len(page),
                        "limit": limit,
                        "offset": offset,
                        "has_more_within_payload": has_more,
                        "next_offset": offset + len(page) if has_more else None,
                        "upstream_result_set_complete": None,
                        "warning": "The Enamine endpoint does not document whether its JSON payload is the complete catalog match set.",
                    },
                }

            encoded_smiles = urllib.parse.quote(smiles)
            return {
                "status": "error",
                "error": f"Enamine structure-search API unavailable (HTTP {response.status_code}); no compounds were retrieved.",
                "search_url": f"{ENAMINE_BASE_URL}/compound-search/structure?smiles={encoded_smiles}",
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_libraries(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get available Enamine compound libraries.

        Returns information about Enamine's screening libraries.
        """
        try:
            response = requests.get(
                f"{ENAMINE_STORE_URL}/libraries",
                timeout=self.timeout,
                headers={
                    "User-Agent": "ToolUniverse/Enamine",
                    "Accept": "application/json",
                },
            )

            if response.status_code == 200 and "json" in response.headers.get(
                "Content-Type", ""
            ):
                data = response.json()
                return {
                    "status": "success",
                    "data": {"libraries": data},
                    "metadata": {"source": "Enamine"},
                }

            # Static marketing copy is not a live library retrieval result.
            return {
                "status": "error",
                "error": f"Enamine libraries API unavailable (HTTP {response.status_code}); no live library data was retrieved.",
                "main_url": f"{ENAMINE_BASE_URL}/compound-collections",
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
