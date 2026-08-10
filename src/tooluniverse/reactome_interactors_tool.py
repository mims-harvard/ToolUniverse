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

        page_size = arguments.get("page_size") or 20

        url = f"{REACTOME_BASE_URL}/interactors/static/molecule/{accession}/details"
        # The requested page_size is passed through unclamped: Reactome honours
        # any pageSize on this endpoint (live-verified: pageSize=300 for P04637
        # returns all 249 interactors), so clamping here would silently truncate
        # results the caller explicitly asked for.
        params = {"page": 1, "pageSize": page_size}

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        total = self._fetch_total_interactor_count(accession)

        entities = data.get("entities", [])
        if not entities:
            return {
                "status": "success",
                "data": {
                    "accession": accession,
                    "total_interactors": total if total is not None else 0,
                    "total_is_exact": total is not None,
                    "returned_interactors": 0,
                    "truncated": bool(total),
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
        result = {
            "accession": entity.get("acc"),
            "total_interactors": total if total is not None else returned,
            "total_is_exact": total is not None,
            "returned_interactors": returned,
            "truncated": truncated,
            "interactors": interactors,
        }
        if truncated:
            result["note"] = (
                f"Showing {returned} of {total} interactors "
                f"(page_size={page_size}). Re-run with page_size={total} "
                "to retrieve all of them."
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

        url = f"{REACTOME_BASE_URL}/search/query"
        params = {
            "query": query,
            "species": species,
            "cluster": "true",
        }
        if types:
            params["types"] = types

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = []
        for group in data.get("results", []):
            type_name = group.get("typeName", "")
            for entry in group.get("entries", []):
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

        return {
            "status": "success",
            "data": results[:50],
            "metadata": {
                "source": "Reactome Content Service",
                "query": query,
                "total_matches": data.get("numberOfMatches", len(results)),
                "groups": data.get("numberOfGroups", 0),
            },
        }
