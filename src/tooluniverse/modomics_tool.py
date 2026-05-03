"""
MODOMICS API tool for ToolUniverse.

MODOMICS is a comprehensive database of RNA modifications providing
chemical structures, biosynthetic pathways, locations in RNA sequences,
and modifying enzymes.

API: https://iimcb.genesilico.pl/modomics/api/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

MODOMICS_BASE = "https://iimcb.genesilico.pl/modomics/api"


@register_tool("MODOMICSTool")
class MODOMICSTool(BaseTool):
    """
    Tool for querying the MODOMICS RNA modification database.

    Supports: list_modifications, get_modification, search_modifications.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "list_modifications"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the MODOMICS API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"MODOMICS API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to MODOMICS API.",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error querying MODOMICS: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to the appropriate endpoint."""
        dispatch = {
            "list_modifications": self._list_modifications,
            "get_modification": self._get_modification,
            "search_modifications": self._search_modifications,
        }
        handler = dispatch.get(self.endpoint_type)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown endpoint type: {self.endpoint_type}",
            }
        return handler(arguments)

    def _list_modifications(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all RNA modifications in MODOMICS."""
        limit = arguments.get("limit", 50)

        url = f"{MODOMICS_BASE}/modifications"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"API returned {resp.status_code}: {resp.text[:200]}",
            }

        data = resp.json()
        # MODOMICS returns a dict keyed by ID
        modifications = []
        for mod_id, mod_data in list(data.items())[:limit]:
            modifications.append(
                {
                    "id": mod_data.get("id"),
                    "name": mod_data.get("name"),
                    "short_name": mod_data.get("short_name"),
                    "formula": mod_data.get("formula"),
                    "mass_avg": mod_data.get("mass_avg"),
                    "mass_monoiso": mod_data.get("mass_monoiso"),
                    "reference_moiety": mod_data.get("reference_moiety"),
                    "smiles": mod_data.get("smile"),
                }
            )

        return {
            "status": "success",
            "data": {
                "modifications": modifications,
                "total": len(data),
                "returned": len(modifications),
            },
        }

    def _get_modification(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get details of a specific RNA modification by ID."""
        mod_id = arguments.get("modification_id")
        if not mod_id:
            return {
                "status": "error",
                "error": "modification_id parameter is required",
            }

        url = f"{MODOMICS_BASE}/modifications/{mod_id}"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"API returned {resp.status_code}: {resp.text[:200]}",
            }

        data = resp.json()
        # Response is a dict keyed by ID, even for single item
        if not data:
            return {
                "status": "error",
                "error": f"No modification found with ID {mod_id}",
            }

        mod_data = list(data.values())[0]
        return {
            "status": "success",
            "data": {
                "id": mod_data.get("id"),
                "name": mod_data.get("name"),
                "short_name": mod_data.get("short_name"),
                "new_abbrev": mod_data.get("new_abbrev"),
                "formula": mod_data.get("formula"),
                "mass_avg": mod_data.get("mass_avg"),
                "mass_monoiso": mod_data.get("mass_monoiso"),
                "mass_prot": mod_data.get("mass_prot"),
                "reference_moiety": mod_data.get("reference_moiety"),
                "smiles": mod_data.get("smile"),
                "product_ions": mod_data.get("product_ions"),
                "lc_elution_comment": mod_data.get("lc_elution_comment"),
                "lc_elution_time": mod_data.get("lc_elution_time"),
            },
        }

    def _search_modifications(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search RNA modifications by name or short name."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        limit = arguments.get("limit", 20)

        url = f"{MODOMICS_BASE}/modifications"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"API returned {resp.status_code}: {resp.text[:200]}",
            }

        data = resp.json()
        query_lower = query.lower()

        # Client-side search across name, short_name, formula
        matches = []
        for mod_data in data.values():
            name = (mod_data.get("name") or "").lower()
            short = (mod_data.get("short_name") or "").lower()
            formula = (mod_data.get("formula") or "").lower()
            if query_lower in name or query_lower in short or query_lower in formula:
                matches.append(
                    {
                        "id": mod_data.get("id"),
                        "name": mod_data.get("name"),
                        "short_name": mod_data.get("short_name"),
                        "formula": mod_data.get("formula"),
                        "mass_avg": mod_data.get("mass_avg"),
                        "reference_moiety": mod_data.get("reference_moiety"),
                        "smiles": mod_data.get("smile"),
                    }
                )

        return {
            "status": "success",
            "data": {
                "results": matches[:limit],
                "total_matches": len(matches),
                "returned": min(len(matches), limit),
            },
        }
