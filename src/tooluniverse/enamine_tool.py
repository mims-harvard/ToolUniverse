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
                return {
                    "status": "success",
                    "data": {
                        "query": query,
                        "catalog": catalog,
                        "results": results[:20],
                        "count": len(results),
                    },
                    "metadata": {"source": "Enamine"},
                }

            # API unavailable — return search URL with explicit note
            api_status = response.status_code
            return {
                "status": "success",
                "data": {
                    "query": query,
                    "catalog": catalog,
                    "results": [],
                    "api_available": False,
                    "search_url": f"{ENAMINE_BASE_URL}/compound-search/quick?q={query}",
                    "note": f"Enamine API returned HTTP {api_status}. Visit search_url to search manually. REAL database contains 37B+ make-on-demand compounds.",
                },
                "metadata": {"source": "Enamine"},
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

            # Return compound URL
            return {
                "status": "success",
                "data": {
                    "enamine_id": enamine_id,
                    "url": f"{ENAMINE_BASE_URL}/compound/{enamine_id}",
                    "note": "Visit url to view compound details and ordering information",
                },
                "metadata": {"source": "Enamine", "enamine_id": enamine_id},
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
                return {
                    "status": "success",
                    "data": {
                        "query_smiles": smiles,
                        "search_type": search_type,
                        "results": results[:20],
                        "count": len(results),
                    },
                    "metadata": {"source": "Enamine"},
                }

            # Return search guidance
            encoded_smiles = urllib.parse.quote(smiles)
            return {
                "status": "success",
                "data": {
                    "query_smiles": smiles,
                    "search_type": search_type,
                    "results": [],
                    "search_url": f"{ENAMINE_BASE_URL}/compound-search/structure?smiles={encoded_smiles}",
                    "note": "Visit search_url to perform structure search on Enamine catalog",
                },
                "metadata": {"source": "Enamine"},
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

            # Return known libraries info
            return {
                "status": "success",
                "data": {
                    "libraries": [
                        {
                            "name": "REAL Database",
                            "description": "37+ billion make-on-demand compounds",
                            "url": f"{ENAMINE_BASE_URL}/compound-collections/real-compounds",
                        },
                        {
                            "name": "Building Blocks",
                            "description": "300,000+ in-stock building blocks for synthesis",
                            "url": f"{ENAMINE_BASE_URL}/building-blocks",
                        },
                        {
                            "name": "Screening Compounds",
                            "description": "3M+ ready-to-ship screening compounds",
                            "url": f"{ENAMINE_BASE_URL}/compound-collections/screening-compounds",
                        },
                        {
                            "name": "Fragment Library",
                            "description": "Diverse fragment collection for FBDD",
                            "url": f"{ENAMINE_BASE_URL}/compound-collections/fragments",
                        },
                        {
                            "name": "Covalent Library",
                            "description": "Compounds with reactive warheads",
                            "url": f"{ENAMINE_BASE_URL}/compound-collections/covalent-screening",
                        },
                    ],
                    "main_url": f"{ENAMINE_BASE_URL}/compound-collections",
                },
                "metadata": {"source": "Enamine"},
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
