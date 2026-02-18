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
            return {"error": f"InterPro API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to InterPro API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                return {
                    "error": f"Not found: {arguments.get('accession', arguments.get('query', ''))}"
                }
            return {"error": f"InterPro API HTTP error: {code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying InterPro API: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "entries_for_protein":
            return self._get_entries_for_protein(arguments)
        elif self.endpoint == "search_entries":
            return self._search_entries(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_entries_for_protein(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all InterPro domain/family entries annotated on a protein."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "error": "accession parameter is required (UniProt accession, e.g., 'P04637')"
            }

        url = f"{INTERPRO_BASE_URL}/entry/interpro/protein/uniprot/{accession}"
        params = {"page_size": 200}
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
            name_obj = meta.get("name", {})
            if isinstance(name_obj, dict):
                name = name_obj.get("name", "")
                short_name = name_obj.get("short", "")
            else:
                name = str(name_obj) if name_obj else ""
                short_name = ""

            entries.append(
                {
                    "accession": meta.get("accession"),
                    "name": name,
                    "short_name": short_name,
                    "type": meta.get("type"),
                    "source_database": meta.get("source_database"),
                }
            )

        return {
            "data": {
                "protein_accession": accession,
                "total_entries": data.get("count", len(entries)),
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
                "error": "query parameter is required (e.g., 'zinc finger', 'kinase', 'p53')"
            }

        entry_type = arguments.get("entry_type", None)
        page_size = arguments.get("page_size", 20)

        url = f"{INTERPRO_BASE_URL}/entry/interpro"
        params = {
            "search": query,
            "page_size": min(page_size, 50),
        }
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
            name_obj = meta.get("name", {})
            if isinstance(name_obj, dict):
                name = name_obj.get("name", "")
                short_name = name_obj.get("short", "")
            else:
                name = str(name_obj) if name_obj else ""
                short_name = ""

            counters = meta.get("counters", {})
            entries.append(
                {
                    "accession": meta.get("accession"),
                    "name": name,
                    "short_name": short_name,
                    "type": meta.get("type"),
                    "protein_count": counters.get("proteins"),
                    "structure_count": counters.get("structures"),
                    "taxa_count": counters.get("taxa"),
                }
            )

        return {
            "data": {
                "query": query,
                "total_results": data.get("count", len(entries)),
                "returned": len(entries),
                "entries": entries,
            },
            "metadata": {
                "source": "InterPro API - Entry Search",
                "query": query,
            },
        }
