# ensembl_xrefs_tool.py
"""
Ensembl Cross-references tool for ToolUniverse.

The Ensembl Xrefs API returns external database cross-references for any
Ensembl stable identifier (gene, transcript, translation, etc.). This
enables mapping between Ensembl, HGNC, EntrezGene, UniProt, Reactome,
MIM, GeneCards, and many other databases.

API: https://rest.ensembl.org/xrefs/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

ENSEMBL_REST_BASE = "https://rest.ensembl.org"
ENSEMBL_HEADERS = {"User-Agent": "ToolUniverse/1.0", "Accept": "application/json"}


@register_tool("EnsemblXrefsTool")
class EnsemblXrefsTool(BaseTool):
    """
    Tool for querying Ensembl cross-references API.

    Supports:
    - Get all external database cross-references for an Ensembl ID
    - Filter by external database name

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 90)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "xrefs_by_id")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Ensembl Xrefs API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"Ensembl API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to Ensembl REST API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 404:
                return {
                    "error": "Ensembl ID not found. Provide a valid Ensembl stable ID."
                }
            return {"error": f"Ensembl REST API HTTP {status}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "xrefs_by_id":
            return self._get_xrefs(arguments)
        elif self.endpoint == "xrefs_by_symbol":
            return self._get_xrefs_by_symbol(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_xrefs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get external cross-references for an Ensembl ID."""
        ensembl_id = arguments.get("ensembl_id", "")
        external_db = arguments.get("external_db", None)

        if not ensembl_id:
            return {
                "error": "ensembl_id is required (e.g., 'ENSG00000141510', 'ENST00000269305')."
            }

        url = f"{ENSEMBL_REST_BASE}/xrefs/id/{ensembl_id}"
        params_parts = ["content-type=application/json"]
        if external_db:
            params_parts.append(f"external_db={external_db}")

        full_url = f"{url}?{';'.join(params_parts)}"
        response = requests.get(full_url, headers=ENSEMBL_HEADERS, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            return {"error": "Unexpected response format."}

        # Group by database
        by_db = {}
        xrefs = []
        for item in data:
            db = item.get("dbname", "unknown")
            by_db.setdefault(db, 0)
            by_db[db] += 1

            xrefs.append(
                {
                    "dbname": db,
                    "db_display_name": item.get("db_display_name"),
                    "primary_id": item.get("primary_id"),
                    "display_id": item.get("display_id"),
                    "description": item.get("description"),
                    "info_type": item.get("info_type"),
                    "synonyms": item.get("synonyms", []),
                }
            )

        return {
            "data": {
                "ensembl_id": ensembl_id,
                "xrefs": xrefs[:100],
                "database_summary": by_db,
            },
            "metadata": {
                "source": "Ensembl REST API (rest.ensembl.org)",
                "total_xrefs": len(data),
                "returned": min(len(xrefs), 100),
                "databases_found": len(by_db),
            },
        }

    def _get_xrefs_by_symbol(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Look up Ensembl IDs for a gene symbol via external databases."""
        symbol = arguments.get("symbol", "")
        species = arguments.get("species", "human")
        external_db = arguments.get("external_db", None)

        if not symbol:
            return {"error": "symbol is required (gene symbol, e.g., 'TP53', 'BRCA1')."}

        url = f"{ENSEMBL_REST_BASE}/xrefs/symbol/{species}/{symbol}"
        params_parts = ["content-type=application/json"]
        if external_db:
            params_parts.append(f"external_db={external_db}")

        full_url = f"{url}?{';'.join(params_parts)}"
        response = requests.get(full_url, headers=ENSEMBL_HEADERS, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            return {"error": "Unexpected response format."}

        results = []
        for item in data[:50]:
            results.append(
                {
                    "id": item.get("id"),
                    "type": item.get("type"),
                }
            )

        return {
            "data": {
                "symbol": symbol,
                "species": species,
                "ensembl_ids": results,
            },
            "metadata": {
                "source": "Ensembl REST API (rest.ensembl.org)",
                "total_results": len(data),
                "returned": len(results),
            },
        }
