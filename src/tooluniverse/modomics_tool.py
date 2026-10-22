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

    def _fetch_catalog(self):
        """Fetch and validate the complete catalog returned by the public API."""
        url = f"{MODOMICS_BASE}/modifications"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"API returned {resp.status_code}: {resp.text[:200]}",
            }
        try:
            data = resp.json()
        except ValueError:
            return {"status": "error", "error": "MODOMICS returned invalid JSON"}
        if not isinstance(data, dict):
            return {
                "status": "error",
                "error": "MODOMICS catalog response was not an object keyed by ID",
            }
        catalog = []
        for key, record in data.items():
            if (
                not isinstance(key, str)
                or not key.isdigit()
                or not isinstance(record, dict)
            ):
                return {
                    "status": "error",
                    "error": "MODOMICS catalog contained a malformed keyed record",
                }
            key_id = int(key)
            if record.get("id") != key_id:
                return {
                    "status": "error",
                    "error": "MODOMICS catalog key conflicts with embedded modification ID",
                    "catalog_key": key,
                    "embedded_id": record.get("id"),
                }
            catalog.append((key_id, record))
        catalog.sort(key=lambda item: item[0])
        return catalog

    @staticmethod
    def _controls(arguments: Dict[str, Any], default_limit: int):
        limit = arguments.get("limit", default_limit)
        offset = arguments.get("offset", 0)
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 500
        ):
            return {
                "status": "error",
                "error": "limit must be an integer from 1 to 500",
            }
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
            }
        return limit, offset

    @staticmethod
    def _record(record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": record.get("id"),
            "name": record.get("name"),
            "short_name": record.get("short_name"),
            "new_abbrev": record.get("new_abbrev"),
            "formula": record.get("formula"),
            "mass_avg": record.get("mass_avg"),
            "mass_monoiso": record.get("mass_monoiso"),
            "mass_prot": record.get("mass_prot"),
            "reference_moiety": record.get("reference_moiety"),
            "smiles": record.get("smile"),
            "product_ions": record.get("product_ions"),
            "lc_elution_comment": record.get("lc_elution_comment"),
            "lc_elution_time": record.get("lc_elution_time"),
        }

    def _list_modifications(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all RNA modifications in MODOMICS."""
        controls = self._controls(arguments, 50)
        if isinstance(controls, dict):
            return controls
        limit, offset = controls
        catalog = self._fetch_catalog()
        if isinstance(catalog, dict):
            return catalog
        modifications = [
            self._record(record) for _, record in catalog[offset : offset + limit]
        ]

        next_offset = offset + len(modifications)
        has_more = next_offset < len(catalog)
        return {
            "status": "success",
            "data": {
                "modifications": modifications,
                "total": len(catalog),
                "returned": len(modifications),
                "offset": offset,
                "has_more": has_more,
                "next_offset": next_offset if has_more else None,
                "result_set_complete": not has_more,
            },
            "metadata": {"source": "MODOMICS complete modifications catalog"},
        }

    def _get_modification(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get details of a specific RNA modification by ID."""
        mod_id = arguments.get("modification_id")
        if isinstance(mod_id, bool) or not isinstance(mod_id, int) or mod_id < 1:
            return {
                "status": "error",
                "error": "modification_id must be a positive integer",
            }
        catalog = self._fetch_catalog()
        if isinstance(catalog, dict):
            return catalog
        matches = [record for key, record in catalog if key == mod_id]
        if not matches:
            return {
                "status": "error",
                "error": f"No modification found with ID {mod_id}",
                "requested_modification_id": mod_id,
                "catalog_total": len(catalog),
            }
        return {
            "status": "success",
            "data": self._record(matches[0]),
            "metadata": {
                "source": "MODOMICS complete modifications catalog",
                "lookup_strategy": "exact_catalog_key",
                "requested_modification_id": mod_id,
                "returned_modification_id": matches[0]["id"],
                "catalog_total": len(catalog),
                "requested_scope_complete": True,
            },
        }

    def _search_modifications(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search RNA modifications by name or short name."""
        query = arguments.get("query", "")
        if not isinstance(query, str) or not query.strip():
            return {"status": "error", "error": "query must be a non-empty string"}
        controls = self._controls(arguments, 20)
        if isinstance(controls, dict):
            return controls
        limit, offset = controls
        catalog = self._fetch_catalog()
        if isinstance(catalog, dict):
            return catalog
        query_lower = query.strip().casefold()

        # Client-side search across name, short_name, formula
        matches = []
        for _, mod_data in catalog:
            name = (mod_data.get("name") or "").casefold()
            short = (mod_data.get("short_name") or "").casefold()
            formula = (mod_data.get("formula") or "").casefold()
            if query_lower in name or query_lower in short or query_lower in formula:
                matches.append(self._record(mod_data))

        page = matches[offset : offset + limit]
        next_offset = offset + len(page)
        has_more = next_offset < len(matches)
        return {
            "status": "success",
            "data": {
                "results": page,
                "total_matches": len(matches),
                "returned": len(page),
                "offset": offset,
                "has_more": has_more,
                "next_offset": next_offset if has_more else None,
                "result_set_complete": not has_more,
            },
            "metadata": {
                "source": "MODOMICS complete modifications catalog",
                "catalog_total": len(catalog),
                "search_fields": ["name", "short_name", "formula"],
            },
        }
