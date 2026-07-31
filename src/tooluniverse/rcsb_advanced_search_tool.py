# rcsb_advanced_search_tool.py
"""
RCSB PDB Advanced Search Tool for ToolUniverse.

Provides attribute-based filtering of PDB structures using the RCSB Search API v2.
Supports filtering by organism, resolution, experimental method, molecular weight,
polymer description, and deposition date. Goes beyond simple text/sequence search
to enable complex multi-criterion structure discovery.

API: https://search.rcsb.org/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

RCSB_SEARCH_URL = "https://search.rcsb.org/rcsbsearch/v2/query"

# Fix-R4B-2: `rows` was clamped to 50 and the paginate window start was
# hard-coded to 0, so results 51+ were structurally unreachable -- a search
# matching 81,865 entries could only ever expose its first 50, and a caller
# asking for rows=200 silently got 50 back with nothing in the response
# saying the request had been reduced. `start` makes the rest of the result
# set reachable; _paginate() reports the clamp instead of hiding it.
MAX_ROWS_PER_PAGE = 50


@register_tool("RCSBAdvancedSearchTool")
class RCSBAdvancedSearchTool(BaseTool):
    """
    Advanced attribute-based search of the RCSB Protein Data Bank.

    Enables complex queries combining organism, resolution, experimental method,
    molecular weight, and more. Returns PDB IDs matching all criteria.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "advanced_search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the RCSB advanced search."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"RCSB Search API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to RCSB Search API"}
        except requests.exceptions.HTTPError as e:
            msg = ""
            try:
                msg = e.response.json().get("message", "")[:200]
            except Exception:
                msg = str(e.response.status_code)
            return {"status": "error", "error": f"RCSB Search API error: {msg}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    @staticmethod
    def _paginate(arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve the paginate window, reporting any clamp applied to `rows`.

        Returns the RCSB `paginate` block plus the bookkeeping needed to tell
        the caller how much of the result set they actually received.
        """
        requested_rows = (
            arguments.get("rows")
            or arguments.get("limit")
            or arguments.get("max_results")
            or 10
        )
        requested_rows = max(1, int(requested_rows))
        rows = min(requested_rows, MAX_ROWS_PER_PAGE)
        start = max(0, int(arguments.get("start") or arguments.get("offset") or 0))

        clamped = None
        if requested_rows > rows:
            clamped = (
                f"Requested rows={requested_rows} exceeds the per-page maximum of "
                f"{MAX_ROWS_PER_PAGE}; returned {rows}. Use 'start' to page through "
                "the remaining results."
            )
        return {"start": start, "rows": rows, "clamp_note": clamped}

    @staticmethod
    def _pagination_metadata(window: Dict[str, Any], total: int, returned: int) -> Dict:
        """Build the metadata block describing this page of the result set."""
        meta: Dict[str, Any] = {
            "total_count": total,
            "returned": returned,
            "start": window["start"],
            "rows": window["rows"],
            "max_rows_per_page": MAX_ROWS_PER_PAGE,
        }

        notes = [n for n in (window["clamp_note"],) if n]
        next_start = window["start"] + returned
        if returned and next_start < total:
            notes.append(
                f"Showing results {window['start'] + 1}-{next_start} of {total}. "
                f"Re-run with start={next_start} for the next page."
            )
        if notes:
            meta["note"] = " ".join(notes)
        return meta

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "advanced_search":
            return self._advanced_search(arguments)
        elif self.endpoint == "motif_search":
            return self._motif_search(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _advanced_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search PDB by multiple attribute filters."""
        query_text = arguments.get("query")
        organism = arguments.get("organism")
        max_resolution = arguments.get("max_resolution")
        experimental_method = arguments.get("experimental_method")
        polymer_description = arguments.get("polymer_description")
        min_deposition_date = arguments.get("min_deposition_date")
        window = self._paginate(arguments)
        sort_by = arguments.get("sort_by") or "resolution"

        nodes = []

        if query_text:
            nodes.append(
                {
                    "type": "terminal",
                    "service": "full_text",
                    "parameters": {"value": query_text},
                }
            )

        if organism:
            nodes.append(
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "rcsb_entity_source_organism.scientific_name",
                        "operator": "exact_match",
                        "value": organism,
                    },
                }
            )

        if max_resolution is not None:
            nodes.append(
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "rcsb_entry_info.resolution_combined",
                        "operator": "less",
                        "value": float(max_resolution),
                    },
                }
            )

        if experimental_method:
            nodes.append(
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "exptl.method",
                        "operator": "exact_match",
                        "value": experimental_method,
                    },
                }
            )

        if polymer_description:
            nodes.append(
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "rcsb_polymer_entity.pdbx_description",
                        "operator": "contains_words",
                        "value": polymer_description,
                    },
                }
            )

        if min_deposition_date:
            nodes.append(
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "rcsb_accession_info.deposit_date",
                        "operator": "greater",
                        "value": min_deposition_date,
                    },
                }
            )

        if not nodes:
            return {
                "status": "error",
                "error": "At least one search parameter is required (query, organism, max_resolution, experimental_method, polymer_description, or min_deposition_date)",
            }

        if len(nodes) == 1:
            query = nodes[0]
        else:
            query = {"type": "group", "logical_operator": "and", "nodes": nodes}

        # Sort mapping
        # Fix-R11A-1: "score" (RCSB's own full-text relevance score) was
        # missing from this map entirely, so there was no way to request
        # relevance-sorted results even though every hit already carries a
        # `score` field in the response -- confirmed live and via raw RCSB
        # Search API curl that "score" is a valid sort_by value and sorts
        # correctly descending. Without it, results default to
        # resolution-sorted order, so the highest-relevance hit for a
        # text query could be buried well past the first page.
        sort_map = {
            "resolution": "rcsb_entry_info.resolution_combined",
            "date": "rcsb_accession_info.deposit_date",
            "weight": "rcsb_entry_info.molecular_weight",
            "score": "score",
        }
        sort_field = sort_map.get(sort_by, sort_map["resolution"])
        sort_direction = "desc" if sort_by in ("date", "score") else "asc"

        request_body = {
            "query": query,
            "return_type": "entry",
            "request_options": {
                "paginate": {"start": window["start"], "rows": window["rows"]},
                "sort": [{"sort_by": sort_field, "direction": sort_direction}],
            },
        }

        response = requests.post(
            RCSB_SEARCH_URL,
            json=request_body,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )

        if response.status_code == 204 or len(response.content) == 0:
            return {
                "status": "success",
                "data": [],
                "metadata": {
                    "source": "RCSB PDB Advanced Search",
                    **self._pagination_metadata(window, 0, 0),
                },
            }

        response.raise_for_status()
        data = response.json()

        results = []
        for hit in data.get("result_set", []):
            results.append(
                {
                    "pdb_id": hit.get("identifier"),
                    "score": hit.get("score"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "RCSB PDB Advanced Search",
                **self._pagination_metadata(
                    window, data.get("total_count", 0), len(results)
                ),
            },
        }

    def _motif_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search PDB by sequence motif pattern."""
        pattern = arguments.get("pattern", "")
        if not pattern:
            return {"status": "error", "error": "pattern parameter is required"}

        pattern_type = arguments.get("pattern_type") or "prosite"
        sequence_type = arguments.get("sequence_type") or "protein"
        window = self._paginate(arguments)

        request_body = {
            "query": {
                "type": "terminal",
                "service": "seqmotif",
                "parameters": {
                    "value": pattern,
                    "pattern_type": pattern_type,
                    "sequence_type": sequence_type,
                },
            },
            "return_type": "polymer_entity",
            "request_options": {
                "paginate": {"start": window["start"], "rows": window["rows"]}
            },
        }

        response = requests.post(
            RCSB_SEARCH_URL,
            json=request_body,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )

        if response.status_code == 204 or len(response.content) == 0:
            return {
                "status": "success",
                "data": [],
                "metadata": {
                    "source": "RCSB PDB Motif Search",
                    **self._pagination_metadata(window, 0, 0),
                    "pattern": pattern,
                    "pattern_type": pattern_type,
                },
            }

        response.raise_for_status()
        data = response.json()

        results = []
        for hit in data.get("result_set", []):
            identifier = hit.get("identifier", "")
            parts = identifier.split("_")
            pdb_id = parts[0] if parts else identifier
            entity_id = parts[1] if len(parts) > 1 else None
            results.append(
                {
                    "pdb_id": pdb_id,
                    "entity_id": entity_id,
                    "identifier": identifier,
                    "score": hit.get("score"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "RCSB PDB Motif Search",
                **self._pagination_metadata(
                    window, data.get("total_count", 0), len(results)
                ),
                "pattern": pattern,
                "pattern_type": pattern_type,
            },
        }
