# pdbe_search_tool.py
"""
PDBe Search (Solr) API tool for ToolUniverse.

PDBe Search provides a powerful Solr-based search interface for the
Protein Data Bank in Europe. It supports full-text and field-specific
queries across all PDB entries, with faceting and filtering capabilities.

API: https://www.ebi.ac.uk/pdbe/search/pdb/select
Also: https://www.ebi.ac.uk/pdbe/api/pdb/compound/summary/{ligand_id}
No authentication required. Free for all use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

PDBE_SEARCH_URL = "https://www.ebi.ac.uk/pdbe/search/pdb/select"
PDBE_API_URL = "https://www.ebi.ac.uk/pdbe/api/pdb"


def _integer_in_range(
    value: Any, *, name: str, minimum: int, maximum: int | None = None
) -> tuple[int | None, str | None]:
    if isinstance(value, bool):
        return None, f"{name} must be an integer"
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, f"{name} must be an integer"
    if isinstance(value, float) and not value.is_integer():
        return None, f"{name} must be an integer"
    if parsed < minimum or (maximum is not None and parsed > maximum):
        bounds = f"{minimum}-{maximum}" if maximum is not None else f">= {minimum}"
        return None, f"{name} must be in the range {bounds}"
    return parsed, None


@register_tool("PDBeSearchTool")
class PDBeSearchTool(BaseTool):
    """
    Tool for searching PDBe, the Protein Data Bank in Europe.

    Provides full-text and field-specific Solr queries across all PDB
    entries, plus compound/ligand lookup by identifier.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "search_structures"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the PDBe Search API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"PDBe Search API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to PDBe Search API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"PDBe Search API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying PDBe Search: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "search_structures":
            return self._search_structures(arguments)
        elif self.endpoint_type == "get_compound":
            return self._get_compound(arguments)
        elif self.endpoint_type == "search_by_organism":
            return self._search_by_organism(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type: {self.endpoint_type}",
            }

    def _search_structures(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search PDB structures by keyword or protein name."""
        query = arguments.get("query", "")
        if not query:
            return {
                "status": "error",
                "error": "query parameter is required (e.g., 'insulin', 'kinase', 'BRCA1')",
            }

        raw_limit = arguments.get("limit")
        limit, limit_error = _integer_in_range(
            10 if raw_limit is None else raw_limit,
            name="limit",
            minimum=1,
            maximum=1000,
        )
        if limit_error:
            return {"status": "error", "error": limit_error}
        raw_offset = arguments.get("offset")
        offset, offset_error = _integer_in_range(
            0 if raw_offset is None else raw_offset, name="offset", minimum=0
        )
        if offset_error:
            return {"status": "error", "error": offset_error}
        assert limit is not None and offset is not None

        raw_scan_budget = arguments.get("max_rows_scanned")
        default_scan_budget = min(max((offset + limit + 1) * 20, 500), 200_000)
        max_rows_scanned, scan_error = _integer_in_range(
            default_scan_budget if raw_scan_budget is None else raw_scan_budget,
            name="max_rows_scanned",
            minimum=1,
            maximum=200_000,
        )
        if scan_error:
            return {"status": "error", "error": scan_error}
        assert max_rows_scanned is not None

        # Ordering: relevance first (best text match), resolution as the tie-breaker.
        # Sorting purely by resolution put the best-resolved structure that merely
        # *mentions* the query first -- "insulin" returned human heart fatty-acid-binding
        # proteins, not insulin. sort_by="resolution" keeps the old behavior.
        # A final pdb_id tiebreaker keeps the order deterministic, so offset
        # pages neither repeat nor skip entries with equal score/resolution.
        if arguments.get("sort_by", "relevance") == "resolution":
            solr_sort = "resolution asc,pdb_id asc"
        else:
            solr_sort = "score desc,resolution asc,pdb_id asc"

        # PDBe's Solr index is entity-level, not deduplicated by PDB entry --
        # a single structure with multiple matching chains/entities can
        # appear as many docs sharing one pdb_id. For entity-dense queries
        # (e.g. "ribosome 70S", where one structure has dozens of matching
        # chains) a fixed over-fetch multiplier can exhaust its rows without
        # finding enough unique pdb_ids, especially when `sort` clusters all
        # of one entry's docs together. Page through Solr with `start`,
        # accumulating unique entries, until `limit` is reached or the
        # safety cap on rows scanned is hit.
        page_size = 1000
        target_unique_count = offset + limit + 1
        total = 0
        structures = []
        seen_pdb_ids = set()
        start = 0
        docs_exhausted = False
        while len(structures) < target_unique_count and start < max_rows_scanned:
            requested_rows = min(page_size, max_rows_scanned - start)
            params = {
                "q": query,
                "rows": requested_rows,
                "start": start,
                "fl": "pdb_id,title,resolution,experimental_method,deposition_date,number_of_entities,organism_scientific_name",
                "wt": "json",
                "sort": solr_sort,
            }
            response = requests.get(
                PDBE_SEARCH_URL, params=params, timeout=self.timeout
            )
            response.raise_for_status()
            raw = response.json()

            solr_response = raw.get("response", {})
            total = solr_response.get("numFound", 0)
            docs = solr_response.get("docs", [])

            for doc in docs:
                pdb_id = doc.get("pdb_id", "")
                if pdb_id and pdb_id in seen_pdb_ids:
                    continue
                seen_pdb_ids.add(pdb_id)
                entry = {
                    "pdb_id": pdb_id,
                    "title": doc.get("title", ""),
                    "resolution": doc.get("resolution"),
                    "experimental_method": doc.get("experimental_method", []),
                    "deposition_date": doc.get("deposition_date"),
                    "number_of_entities": doc.get("number_of_entities"),
                    "organism": doc.get("organism_scientific_name", []),
                }
                structures.append(entry)
                if len(structures) >= target_unique_count:
                    break

            start += len(docs)
            if len(docs) < requested_rows or start >= total:
                # Exhausted all matching docs before filling `limit`.
                docs_exhausted = True
                break

        page = structures[offset : offset + limit]
        has_more = bool(
            len(structures) > offset + limit or (not docs_exhausted and start < total)
        )
        page_complete = len(page) == limit or docs_exhausted
        scan_limit_reached = bool(not page_complete and start >= max_rows_scanned)
        warning = None
        if scan_limit_reached:
            warning = (
                "The entity-level scan budget was exhausted before the requested "
                "unique-PDB page was filled. Increase max_rows_scanned and rerun "
                "the same offset; the partial page is not complete."
            )

        return {
            "status": "success",
            "data": page,
            "metadata": {
                "source": "PDBe Search",
                "total_found": total,
                "total_found_note": (
                    "Entity-level Solr match count, not unique PDB entries -- "
                    "a single structure can contribute many matching chains/"
                    "entities, so this is typically far larger than `returned`."
                ),
                "returned": len(page),
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
                "truncated": has_more,
                "next_offset": offset + len(page)
                if has_more and len(page) > 0
                else None,
                "page_complete": page_complete,
                "rows_scanned": start,
                "unique_pdb_ids_scanned": len(structures),
                "max_rows_scanned": max_rows_scanned,
                "scan_limit_reached": scan_limit_reached,
                "warning": warning,
                "query": query,
                "endpoint": "search_structures",
            },
        }

    def _get_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get PDB ligand/compound information by compound ID."""
        compound_id = arguments.get("compound_id", "")
        if not compound_id:
            return {
                "status": "error",
                "error": "compound_id parameter is required (e.g., 'ATP', 'HEM', 'NAG')",
            }

        url = f"{PDBE_API_URL}/compound/summary/{compound_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        # Response keyed by compound ID
        compound_data = raw.get(compound_id, [])
        if not compound_data:
            compound_data = raw.get(compound_id.upper(), [])

        compounds = []
        for c in compound_data:
            if isinstance(c, dict):
                entry = {
                    "name": c.get("name", ""),
                    "formula": c.get("formula", ""),
                    "weight": c.get("weight"),
                    "compound_type": c.get("compound_type", ""),
                    "inchi": c.get("inchi", ""),
                    "inchi_key": c.get("inchi_key", ""),
                }
                # SMILES
                smiles_list = c.get("smiles", [])
                if isinstance(smiles_list, list) and smiles_list:
                    first = smiles_list[0]
                    if isinstance(first, dict):
                        entry["smiles"] = first.get("name", "")

                # Systematic names
                sys_names = c.get("systematic_names", [])
                if isinstance(sys_names, list) and sys_names:
                    for sn in sys_names[:2]:
                        if isinstance(sn, dict):
                            entry["systematic_name"] = sn.get("name", "")
                            break

                compounds.append(entry)

        result = compounds[0] if compounds else {}
        result["compound_id"] = compound_id

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "PDBe",
                "query": compound_id,
                "endpoint": "get_compound",
            },
        }

    def _search_by_organism(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search PDB structures filtered by organism."""
        organism = arguments.get("organism", "")
        query = arguments.get("query", "*:*")
        raw_limit = arguments.get("limit")
        limit, limit_error = _integer_in_range(
            10 if raw_limit is None else raw_limit,
            name="limit",
            minimum=1,
            maximum=10_000,
        )
        if limit_error:
            return {"status": "error", "error": limit_error}
        raw_start = arguments.get("start")
        start, start_error = _integer_in_range(
            0 if raw_start is None else raw_start, name="start", minimum=0
        )
        if start_error:
            return {"status": "error", "error": start_error}
        assert limit is not None and start is not None

        if not organism:
            return {
                "status": "error",
                "error": "organism parameter is required (e.g., 'Homo sapiens', 'Escherichia coli')",
            }

        # Build Solr query with organism filter
        full_query = f'{query} AND organism_scientific_name:"{organism}"'

        params = {
            "q": full_query,
            "rows": limit,
            "start": start,
            "fl": "pdb_id,title,resolution,experimental_method,deposition_date,organism_scientific_name",
            "wt": "json",
            "sort": "resolution asc",
        }

        response = requests.get(PDBE_SEARCH_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        solr_response = raw.get("response", {})
        total = solr_response.get("numFound", 0)

        structures = []
        for doc in solr_response.get("docs", []):
            entry = {
                "pdb_id": doc.get("pdb_id", ""),
                "title": doc.get("title", ""),
                "resolution": doc.get("resolution"),
                "experimental_method": doc.get("experimental_method", []),
                "deposition_date": doc.get("deposition_date"),
                "organism": doc.get("organism_scientific_name", []),
            }
            structures.append(entry)

        return {
            "status": "success",
            "data": structures,
            "metadata": {
                "source": "PDBe Search",
                "total_found": total,
                "returned": len(structures),
                "start": start,
                "has_more": start + len(structures) < total,
                "truncated": start + len(structures) < total,
                "next_start": (
                    start + len(structures) if start + len(structures) < total else None
                ),
                "query": query,
                "organism_filter": organism,
                "endpoint": "search_by_organism",
            },
        }
