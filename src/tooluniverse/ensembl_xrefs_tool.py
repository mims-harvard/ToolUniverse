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
from urllib.parse import quote
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
            return {
                "status": "error",
                "error": f"Ensembl API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to Ensembl REST API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 404:
                return {
                    "status": "error",
                    "error": "Ensembl ID not found. Provide a valid Ensembl stable ID.",
                }
            # Fix-18B-1: swallowing the response body dropped Ensembl's own
            # actionable message -- e.g. a bad `species` value (common for
            # xrefs_by_symbol, which takes species as free text like "canine"
            # instead of the required internal name "canis_lupus_familiaris")
            # returns HTTP 400 with body {"error": "Can not find internal
            # name for species 'canine'"}, but callers only ever saw the bare
            # "Ensembl REST API HTTP 400". The sibling ensembl_tool.py already
            # includes response text for this reason; do the same here.
            detail = ""
            if e.response is not None:
                detail = (e.response.text or "").strip()[:200]
            return {
                "status": "error",
                "error": f"Ensembl REST API HTTP {status}"
                + (f": {detail}" if detail else ""),
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "xrefs_by_id":
            return self._get_xrefs(arguments)
        elif self.endpoint == "xrefs_by_symbol":
            return self._get_xrefs_by_symbol(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_xrefs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get external cross-references for an Ensembl ID."""
        ensembl_id = arguments.get("ensembl_id")
        external_db = arguments.get("external_db", None)

        if not isinstance(ensembl_id, str) or not ensembl_id.strip():
            return {
                "status": "error",
                "error": "ensembl_id must be a non-empty string",
                "parameter": "ensembl_id",
            }
        if external_db is not None and (
            not isinstance(external_db, str) or not external_db.strip()
        ):
            return {
                "status": "error",
                "error": "external_db must be a non-empty string when provided",
                "parameter": "external_db",
            }
        pagination = self._pagination_controls(arguments, default_limit=500)
        if isinstance(pagination, dict):
            return pagination
        limit, offset = pagination
        ensembl_id = ensembl_id.strip()
        external_db = external_db.strip() if external_db is not None else None

        url = f"{ENSEMBL_REST_BASE}/xrefs/id/{quote(ensembl_id, safe='')}"
        params_parts = ["content-type=application/json"]
        if external_db:
            params_parts.append(f"external_db={quote(external_db, safe='')}")

        full_url = f"{url}?{';'.join(params_parts)}"
        response = requests.get(full_url, headers=ENSEMBL_HEADERS, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            return {"status": "error", "error": "Unexpected response format."}

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

        page = xrefs[offset : offset + limit]
        page_by_db = {}
        for item in page:
            db = item["dbname"]
            page_by_db[db] = page_by_db.get(db, 0) + 1
        next_offset = offset + len(page)
        has_more = next_offset < len(xrefs)
        truncated = offset > 0 or has_more
        return {
            "status": "success",
            "data": {
                "ensembl_id": ensembl_id,
                "xrefs": page,
                "database_summary": by_db,
                "page_database_summary": page_by_db,
                "truncated": truncated,
            },
            "metadata": {
                "source": "Ensembl REST API (rest.ensembl.org)",
                "total_xrefs": len(data),
                "returned": len(page),
                "offset": offset,
                "limit": limit,
                "has_more": has_more,
                "next_offset": next_offset if has_more else None,
                "result_set_complete": not truncated,
                "databases_found": len(by_db),
            },
        }

    def _get_xrefs_by_symbol(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Look up Ensembl IDs for a gene symbol via external databases."""
        symbol = arguments.get("symbol")
        species = arguments.get("species", "human")
        external_db = arguments.get("external_db", None)

        if not isinstance(symbol, str) or not symbol.strip():
            return {
                "status": "error",
                "error": "symbol must be a non-empty string",
                "parameter": "symbol",
            }
        if not isinstance(species, str) or not species.strip():
            return {
                "status": "error",
                "error": "species must be a non-empty Ensembl species name",
                "parameter": "species",
            }
        if external_db is not None and (
            not isinstance(external_db, str) or not external_db.strip()
        ):
            return {
                "status": "error",
                "error": "external_db must be a non-empty string when provided",
                "parameter": "external_db",
            }
        pagination = self._pagination_controls(arguments, default_limit=50)
        if isinstance(pagination, dict):
            return pagination
        limit, offset = pagination
        symbol = symbol.strip()
        species = species.strip()
        external_db = external_db.strip() if external_db is not None else None

        url = (
            f"{ENSEMBL_REST_BASE}/xrefs/symbol/"
            f"{quote(species, safe='')}/{quote(symbol, safe='')}"
        )
        params_parts = ["content-type=application/json"]
        if external_db:
            params_parts.append(f"external_db={quote(external_db, safe='')}")

        full_url = f"{url}?{';'.join(params_parts)}"
        response = requests.get(full_url, headers=ENSEMBL_HEADERS, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            return {"status": "error", "error": "Unexpected response format."}

        results = []
        for item in data[offset : offset + limit]:
            results.append(
                {
                    "id": item.get("id"),
                    "type": item.get("type"),
                }
            )

        next_offset = offset + len(results)
        has_more = next_offset < len(data)
        truncated = offset > 0 or has_more
        return {
            "status": "success",
            "data": {
                "symbol": symbol,
                "species": species,
                "ensembl_ids": results,
            },
            "metadata": {
                "source": "Ensembl REST API (rest.ensembl.org)",
                "total_results": len(data),
                "returned": len(results),
                "offset": offset,
                "limit": limit,
                "has_more": has_more,
                "next_offset": next_offset if has_more else None,
                "truncated": truncated,
                "result_set_complete": not truncated,
            },
        }

    @staticmethod
    def _pagination_controls(arguments: Dict[str, Any], default_limit: int):
        limit = arguments.get("limit", default_limit)
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 5000
        ):
            return {
                "status": "error",
                "error": "limit must be an integer between 1 and 5000",
                "parameter": "limit",
            }
        offset = arguments.get("offset", 0)
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
                "parameter": "offset",
            }
        return limit, offset
