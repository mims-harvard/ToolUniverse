# reactome_interactors_tool.py
"""
Reactome Interactors API tool for ToolUniverse.

This tool provides access to curated protein-protein interactions from
Reactome's IntAct-derived interaction data. It enables discovery of
molecular interactors for any protein and pathway context for entities.

API: https://reactome.org/ContentService/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

REACTOME_BASE_URL = "https://reactome.org/ContentService"


@register_tool("ReactomeInteractorsTool")
class ReactomeInteractorsTool(BaseTool):
    """
    Tool for querying protein interactors and entity pathways from Reactome.

    Reactome provides curated protein-protein interaction data derived from
    IntAct, with confidence scores and evidence counts. Also supports
    finding Reactome pathways associated with specific entities.

    Supports: get protein interactors, find pathways for entity,
    search Reactome entities.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "interactors")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Reactome API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Reactome API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to Reactome API"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"Reactome API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying Reactome: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate Reactome endpoint."""
        if self.endpoint == "interactors":
            return self._get_interactors(arguments)
        elif self.endpoint == "entity_pathways":
            return self._get_entity_pathways(arguments)
        elif self.endpoint == "search_entity":
            return self._search_entity(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _fetch_total_interactor_count(self, accession: str):
        """Return the true total interactor count, or None if unavailable.

        Fix-R18B-2/Feature-23C-2: the ``count`` field of the interactors
        ``/details`` response is the number of records on the page that was
        requested, NOT the size of the full result set -- live-verified for
        P04637, where page=1&pageSize=100 yields count=100 while
        page=1&pageSize=300 yields count=249. The dedicated ``/summary``
        endpoint is therefore the only cheap source of a real total
        (live-verified: P04637 -> 249, P42345 -> 22). Returns None on any
        failure so that a page count is never passed off as a total.
        """
        url = f"{REACTOME_BASE_URL}/interactors/static/molecule/{accession}/summary"
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            entities = response.json().get("entities", [])
        except (requests.exceptions.RequestException, ValueError, AttributeError):
            return None
        if not entities:
            return None
        count = entities[0].get("count")
        return count if isinstance(count, int) else None

    def _get_interactors(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get protein-protein interactors for a UniProt accession."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "status": "error",
                "error": "accession parameter is required (UniProt accession, e.g., P04637)",
            }

        page_size = arguments.get("page_size", 20)
        page = arguments.get("page", 1)
        if page_size is None:
            page_size = 20
        if isinstance(page_size, bool) or not isinstance(page_size, int) or page_size < 1:
            return {
                "status": "error",
                "error": "page_size must be a positive integer",
            }
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            return {"status": "error", "error": "page must be a positive integer"}

        url = f"{REACTOME_BASE_URL}/interactors/static/molecule/{accession}/details"
        # The requested page_size is passed through unclamped: Reactome honours
        # any pageSize on this endpoint (live-verified: pageSize=300 for P04637
        # returns all 249 interactors), so clamping here would silently truncate
        # results the caller explicitly asked for.
        params = {"page": page, "pageSize": page_size}

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        total = self._fetch_total_interactor_count(accession)

        entities = data.get("entities", [])
        if not entities:
            has_more = total is not None and page * page_size < total
            return {
                "status": "success",
                "data": {
                    "accession": accession,
                    "total_interactors": total if total is not None else 0,
                    "total_is_exact": total is not None,
                    "returned_interactors": 0,
                    "truncated": bool(total),
                    "page": page,
                    "has_more": has_more,
                    "next_page": page + 1 if has_more else None,
                    "interactors": [],
                },
                "metadata": {"source": "Reactome Interactors (IntAct)"},
            }

        entity = entities[0]
        interactors = []
        for i in entity.get("interactors", []):
            interactors.append(
                {
                    "accession": i.get("acc"),
                    "alias": i.get("alias"),
                    "score": i.get("score"),
                    "evidences": i.get("evidences"),
                }
            )

        # Sort by score descending
        interactors.sort(key=lambda x: x.get("score") or 0, reverse=True)

        returned = len(interactors)
        truncated = total is not None and returned < total
        has_more = total is not None and page * page_size < total
        result = {
            "accession": entity.get("acc"),
            "total_interactors": total if total is not None else returned,
            "total_is_exact": total is not None,
            "returned_interactors": returned,
            "truncated": truncated,
            "page": page,
            "has_more": has_more,
            "next_page": page + 1 if has_more else None,
            "interactors": interactors,
        }
        if truncated:
            result["note"] = (
                f"Showing {returned} of {total} interactors "
                f"on page {page} (page_size={page_size}). "
                + (
                    f"Continue with page={page + 1}, or re-run with "
                    f"page_size={total} to retrieve all of them."
                    if has_more
                    else "No later page is available."
                )
            )
        elif total is None:
            result["note"] = (
                "The total interactor count is unavailable (Reactome summary "
                "endpoint did not respond), so total_interactors reports the "
                f"{returned} interactor(s) returned on this page and may be "
                "incomplete."
            )

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "Reactome Interactors (IntAct)",
                "resource": data.get("resource"),
            },
        }

    def _get_entity_pathways(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get Reactome pathways associated with a specific entity."""
        entity_id = arguments.get("entity_id", "")
        if not entity_id:
            return {
                "status": "error",
                "error": "entity_id parameter is required (Reactome stable ID, e.g., R-HSA-199420)",
            }

        species = arguments.get("species") or 9606

        url = f"{REACTOME_BASE_URL}/data/pathways/low/entity/{entity_id}"
        params = {"species": species}

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        pathways = []
        if isinstance(data, list):
            for p in data:
                pathways.append(
                    {
                        "stable_id": p.get("stId"),
                        "name": p.get("displayName"),
                        "species": p.get("speciesName"),
                        "is_disease": p.get("isInDisease", False),
                        "has_diagram": p.get("hasDiagram", False),
                    }
                )

        return {
            "status": "success",
            "data": pathways,
            "metadata": {
                "source": "Reactome Content Service",
                "entity_id": entity_id,
                "species": species,
                "total_pathways": len(pathways),
            },
        }

    def _search_entity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search Reactome for entities (proteins, complexes, reactions)."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        species = arguments.get("species") or "Homo sapiens"
        types = arguments.get("types")
        limit = arguments.get("limit", 50)
        offset = arguments.get("offset", 0)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            return {
                "status": "error",
                "error": "limit must be an integer from 1 to 1000",
            }
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
            }

        url = f"{REACTOME_BASE_URL}/search/query"
        params = {
            "query": query,
            "species": species,
            "cluster": "true",
            "Start row": offset,
            "rows": limit,
        }
        if types:
            params["types"] = types

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = []
        result_groups = []
        for group in data.get("results", []):
            type_name = group.get("typeName", "")
            entries = group.get("entries", [])
            group_total = group.get("entriesCount")
            if not isinstance(group_total, int):
                group_total = len(entries)
            result_groups.append(
                {
                    "type": type_name,
                    "total": group_total,
                    "returned": len(entries),
                }
            )
            for entry in entries:
                # Strip HTML highlighting
                name = (
                    (entry.get("name") or "")
                    .replace('<span class="highlighting" >', "")
                    .replace("</span>", "")
                )
                results.append(
                    {
                        "stable_id": entry.get("stId"),
                        "name": name,
                        "type": type_name,
                        "species": entry.get("species"),
                        "exact_type": entry.get("exactType"),
                        "compartment_names": entry.get("compartmentNames"),
                    }
                )

        total = data.get("numberOfMatches")
        if not isinstance(total, int):
            total = len(results)
        has_more = any(
            offset + group["returned"] < group["total"] for group in result_groups
        )
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "Reactome Content Service",
                "query": query,
                "total_matches": total,
                "returned": len(results),
                # Reactome applies rows independently to every result type,
                # not as a global response limit. Keep ``limit`` as an input
                # compatibility alias, but disclose its real scope.
                "limit": limit,
                "limit_scope": "per_result_group",
                "rows_per_group": limit,
                "offset": offset,
                "has_more": has_more,
                "truncated": len(results) < total,
                "next_offset": offset + limit if has_more else None,
                "result_set_complete": offset == 0 and len(results) == total,
                "pagination_stalled": bool(has_more and not results),
                "groups": data.get("numberOfGroups", 0),
                "result_groups": result_groups,
            },
        }
