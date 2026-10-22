# interpro_entry_tool.py
"""
InterPro Entry API tool for ToolUniverse.

Provides access to InterPro REST API for retrieving domain/family
entries associated with a protein, and searching InterPro entries
by keyword.

API: https://www.ebi.ac.uk/interpro/api/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from urllib.parse import parse_qs, urlparse
from .base_tool import BaseTool


INTERPRO_BASE_URL = "https://www.ebi.ac.uk/interpro/api"


class InterProEntryTool(BaseTool):
    """
    Tool for InterPro entry API providing protein-to-domain mappings
    and domain/family search.

    Complements existing InterPro tools by offering reverse lookups
    (protein -> all domains) and keyword-based entry search.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "entries_for_protein")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the InterPro entry API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"InterPro API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to InterPro API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                return {
                    "status": "error",
                    "error": f"Not found: {arguments.get('accession', arguments.get('query', ''))}",
                }
            return {"status": "error", "error": f"InterPro API HTTP error: {code}"}
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying InterPro API: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "entries_for_protein":
            return self._get_entries_for_protein(arguments)
        elif self.endpoint == "search_entries":
            return self._search_entries(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    @staticmethod
    def _next_cursor(data: Dict[str, Any]):
        next_url = data.get("next")
        if not next_url:
            return None
        values = parse_qs(urlparse(next_url).query).get("cursor", [])
        return values[0] if values else None

    @staticmethod
    def _add_cursor(params: Dict[str, Any], arguments: Dict[str, Any]) -> None:
        cursor = arguments.get("cursor")
        if cursor:
            params["cursor"] = cursor

    @staticmethod
    def _page_controls(arguments: Dict[str, Any], default: int, maximum: int):
        page_size = arguments.get("page_size", default)
        if page_size is None:
            page_size = default
        if (
            isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or not 1 <= page_size <= maximum
        ):
            return {
                "status": "error",
                "error": f"page_size must be an integer from 1 to {maximum}",
            }
        cursor = arguments.get("cursor")
        if cursor is not None and (not isinstance(cursor, str) or not cursor.strip()):
            return {
                "status": "error",
                "error": "cursor must be a non-empty string when supplied",
            }
        return page_size, cursor

    def _get_entries_for_protein(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all InterPro domain/family entries annotated on a protein."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "status": "error",
                "error": "accession parameter is required (UniProt accession, e.g., 'P04637')",
            }

        url = f"{INTERPRO_BASE_URL}/entry/interpro/protein/uniprot/{accession}"
        controls = self._page_controls(arguments, 100, 200)
        if isinstance(controls, dict):
            return controls
        page_size, cursor = controls
        params = {"page_size": page_size}
        self._add_cursor(params, arguments)
        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        entries = []
        for r in results:
            meta = r.get("metadata", {})
            # The InterPro protein-entries endpoint returns metadata.name as a
            # plain string; keep the dict guard in case the API shape changes.
            name_obj = meta.get("name", "")
            name = (
                name_obj.get("name", "")
                if isinstance(name_obj, dict)
                else (str(name_obj) if name_obj else "")
            )

            entries.append(
                {
                    "accession": meta.get("accession"),
                    "name": name,
                    "type": meta.get("type"),
                    "source_database": meta.get("source_database"),
                }
            )

        next_cursor = self._next_cursor(data)
        total = data.get("count", len(entries))
        return {
            "status": "success",
            "data": {
                "protein_accession": accession,
                "total_entries": total,
                "returned": len(entries),
                "page_size": page_size,
                "has_more": next_cursor is not None,
                "next_cursor": next_cursor,
                "truncated": cursor is not None or next_cursor is not None,
                "result_set_complete": bool(
                    cursor is None and next_cursor is None and len(entries) == total
                ),
                "pagination_stalled": bool(next_cursor and not entries),
                "entries": entries,
            },
            "metadata": {
                "source": "InterPro API - Entries for Protein",
                "accession": accession,
            },
        }

    def _search_entries(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search InterPro entries by keyword."""
        query = arguments.get("query", "")
        if not query:
            return {
                "status": "error",
                "error": "query parameter is required (e.g., 'zinc finger', 'kinase', 'p53')",
            }

        entry_type = arguments.get("entry_type", None)
        valid_entry_types = {
            "domain",
            "family",
            "homologous_superfamily",
            "repeat",
            "conserved_site",
            "active_site",
            "binding_site",
            "ptm",
        }
        if entry_type is not None and entry_type not in valid_entry_types:
            return {
                "status": "error",
                "error": "entry_type must be one of: " + ", ".join(sorted(valid_entry_types)),
            }
        controls = self._page_controls(arguments, 20, 50)
        if isinstance(controls, dict):
            return controls
        page_size, cursor = controls

        url = f"{INTERPRO_BASE_URL}/entry/interpro"
        params = {
            "search": query,
            "page_size": page_size,
        }
        self._add_cursor(params, arguments)
        if entry_type:
            params["type"] = entry_type

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        entries = []
        for r in results:
            meta = r.get("metadata", {})
            # metadata.name is a plain string here; keep the dict guard for safety.
            name_obj = meta.get("name", "")
            name = (
                name_obj.get("name", "")
                if isinstance(name_obj, dict)
                else (str(name_obj) if name_obj else "")
            )

            counters = meta.get("counters", {})
            entries.append(
                {
                    "accession": meta.get("accession"),
                    "name": name,
                    "type": meta.get("type"),
                    "protein_count": counters.get("proteins"),
                    "structure_count": counters.get("structures"),
                    "taxa_count": counters.get("taxa"),
                }
            )

        next_cursor = self._next_cursor(data)
        total = data.get("count", len(entries))
        return {
            "status": "success",
            "data": {
                "query": query,
                "total_results": total,
                "returned": len(entries),
                "page_size": page_size,
                "has_more": next_cursor is not None,
                "next_cursor": next_cursor,
                "truncated": cursor is not None or next_cursor is not None,
                "result_set_complete": bool(
                    cursor is None and next_cursor is None and len(entries) == total
                ),
                "pagination_stalled": bool(next_cursor and not entries),
                "entries": entries,
            },
            "metadata": {
                "source": "InterPro API - Entry Search",
                "query": query,
            },
        }
