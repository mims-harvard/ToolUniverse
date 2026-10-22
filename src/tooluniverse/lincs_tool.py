"""
LINCS SigCom (Signature Commons) API tool for ToolUniverse.

LINCS (Library of Integrated Network-Based Cellular Signatures) provides
drug perturbation gene expression signatures from the L1000 assay and other
high-throughput profiling technologies. SigCom LINCS aggregates 1.5M+
signatures across 431+ libraries.

Metadata API: https://maayanlab.cloud/sigcom-lincs/metadata-api/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

LINCS_BASE = "https://maayanlab.cloud/sigcom-lincs/metadata-api"


@register_tool("LINCSSignatureTool")
class LINCSSignatureTool(BaseTool):
    """
    Tool for querying LINCS SigCom drug perturbation signatures.

    Supports: search_signatures (find signatures by drug/perturbagen),
    list_libraries (browse available signature libraries).

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "search_signatures"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the LINCS API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"LINCS API request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to LINCS SigCom API.",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying LINCS: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to the appropriate LINCS endpoint."""
        if self.endpoint_type == "search_signatures":
            return self._search_signatures(arguments)
        elif self.endpoint_type == "list_libraries":
            return self._list_libraries(arguments)
        return {
            "status": "error",
            "error": f"Unknown endpoint type: {self.endpoint_type}",
        }

    def _search_signatures(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search LINCS signatures by drug/perturbagen name."""
        drug_name = arguments.get("drug_name", "")
        if not drug_name:
            return {"status": "error", "error": "drug_name parameter is required"}

        limit = arguments.get("limit", 20)
        offset = arguments.get("offset", 0)
        if limit is None:
            limit = 20
        if offset is None:
            offset = 0
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 1000
        ):
            return {
                "status": "error",
                "error": "limit must be an integer between 1 and 1000",
            }
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
            }
        cell_line = arguments.get("cell_line")

        # Build filter
        where = {"meta.pert_name": drug_name}
        if cell_line:
            where["meta.cell_line"] = cell_line

        # SigCom has no count endpoint. Fetch one lookahead record so has_more
        # is reliable without pretending that the current page length is total.
        payload = {"filter": {"where": where, "limit": limit + 1, "skip": offset}}

        resp = requests.post(
            f"{LINCS_BASE}/signatures/find",
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        signatures = resp.json()
        has_more = len(signatures) > limit
        signatures = signatures[:limit]

        results = []
        for sig in signatures:
            meta = sig.get("meta", {})
            results.append(
                {
                    "signature_id": sig.get("id"),
                    "drug_name": meta.get("pert_name"),
                    "cell_line": meta.get("cell_line"),
                    "dose": meta.get("pert_dose"),
                    "time_point": meta.get("pert_time"),
                    "perturbation_type": meta.get("pert_type"),
                    "tissue": meta.get("tissue"),
                    "disease": meta.get("disease"),
                    "anatomy": meta.get("anatomy"),
                    "pubchem_id": meta.get("pubchem_id"),
                    "library_id": sig.get("library"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_results": (
                    offset + len(results)
                    if not has_more and (offset == 0 or bool(results))
                    else None
                ),
                "total_is_exact": not has_more and (offset == 0 or bool(results)),
                "matches_lower_bound": offset + len(results) + (1 if has_more else 0),
                "returned": len(results),
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
                "truncated": has_more,
                "next_offset": offset + len(results) if has_more else None,
                "query_drug": drug_name,
                "query_cell_line": cell_line,
                "source": "LINCS SigCom",
            },
        }

    def _list_libraries(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List available LINCS signature libraries."""
        resp = requests.get(
            f"{LINCS_BASE}/libraries",
            timeout=self.timeout,
        )
        resp.raise_for_status()
        libraries = resp.json()

        keyword = arguments.get("keyword", "").lower()
        limit = arguments.get("limit", 50)
        offset = arguments.get("offset", 0)
        if limit is None:
            limit = 50
        if offset is None:
            offset = 0
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 1000
        ):
            return {
                "status": "error",
                "error": "limit must be an integer between 1 and 1000",
            }
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
            }

        matching_libraries = []
        for lib in libraries:
            meta = lib.get("meta", {})
            entry = {
                "library_id": lib.get("id"),
                "dataset": lib.get("dataset"),
                "dataset_type": lib.get("dataset_type"),
                "assay": meta.get("assay"),
                "organism": meta.get("organism"),
                "description": meta.get("description") or meta.get("summary"),
            }
            if keyword:
                searchable = " ".join(str(v) for v in entry.values() if v).lower()
                if keyword not in searchable:
                    continue
            matching_libraries.append(entry)

        results = matching_libraries[offset : offset + limit]
        has_more = offset + len(results) < len(matching_libraries)

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_libraries": len(libraries),
                "total_matches": len(matching_libraries),
                "returned": len(results),
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
                "truncated": has_more,
                "next_offset": offset + len(results) if has_more else None,
                "keyword_filter": keyword or None,
                "source": "LINCS SigCom",
            },
        }
