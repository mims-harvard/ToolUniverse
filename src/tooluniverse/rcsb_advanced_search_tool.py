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
            return {"error": f"RCSB Search API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to RCSB Search API"}
        except requests.exceptions.HTTPError as e:
            msg = ""
            try:
                msg = e.response.json().get("message", "")[:200]
            except Exception:
                msg = str(e.response.status_code)
            return {"error": f"RCSB Search API error: {msg}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "advanced_search":
            return self._advanced_search(arguments)
        elif self.endpoint == "motif_search":
            return self._motif_search(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _advanced_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search PDB by multiple attribute filters."""
        query_text = arguments.get("query")
        organism = arguments.get("organism")
        max_resolution = arguments.get("max_resolution")
        experimental_method = arguments.get("experimental_method")
        polymer_description = arguments.get("polymer_description")
        min_deposition_date = arguments.get("min_deposition_date")
        rows = min(arguments.get("rows") or 10, 50)
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
                "error": "At least one search parameter is required (query, organism, max_resolution, experimental_method, polymer_description, or min_deposition_date)"
            }

        if len(nodes) == 1:
            query = nodes[0]
        else:
            query = {"type": "group", "logical_operator": "and", "nodes": nodes}

        # Sort mapping
        sort_map = {
            "resolution": "rcsb_entry_info.resolution_combined",
            "date": "rcsb_accession_info.deposit_date",
            "weight": "rcsb_entry_info.molecular_weight",
        }
        sort_field = sort_map.get(sort_by, sort_map["resolution"])
        sort_direction = "desc" if sort_by == "date" else "asc"

        request_body = {
            "query": query,
            "return_type": "entry",
            "request_options": {
                "paginate": {"start": 0, "rows": rows},
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
                "data": [],
                "metadata": {
                    "source": "RCSB PDB Advanced Search",
                    "total_count": 0,
                    "returned": 0,
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
            "data": results,
            "metadata": {
                "source": "RCSB PDB Advanced Search",
                "total_count": data.get("total_count", 0),
                "returned": len(results),
            },
        }

    def _motif_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search PDB by sequence motif pattern."""
        pattern = arguments.get("pattern", "")
        if not pattern:
            return {"error": "pattern parameter is required"}

        pattern_type = arguments.get("pattern_type") or "prosite"
        sequence_type = arguments.get("sequence_type") or "protein"
        rows = min(arguments.get("rows") or 10, 50)

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
            "request_options": {"paginate": {"start": 0, "rows": rows}},
        }

        response = requests.post(
            RCSB_SEARCH_URL,
            json=request_body,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )

        if response.status_code == 204 or len(response.content) == 0:
            return {
                "data": [],
                "metadata": {
                    "source": "RCSB PDB Motif Search",
                    "total_count": 0,
                    "returned": 0,
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
            "data": results,
            "metadata": {
                "source": "RCSB PDB Motif Search",
                "total_count": data.get("total_count", 0),
                "returned": len(results),
                "pattern": pattern,
                "pattern_type": pattern_type,
            },
        }
