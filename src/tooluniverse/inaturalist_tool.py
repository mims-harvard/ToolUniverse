# inaturalist_tool.py
"""
iNaturalist API tool for ToolUniverse.

iNaturalist is a citizen science platform for biodiversity observations,
connecting millions of people worldwide to document and identify species.
The API provides access to taxa, observations, and species counts.

API: https://api.inaturalist.org/v1/
No authentication required. Free public access.
Rate limit: Be respectful (no more than ~1 req/sec).
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

INAT_BASE_URL = "https://api.inaturalist.org/v1"


@register_tool("INaturalistTool")
class INaturalistTool(BaseTool):
    """
    Tool for querying iNaturalist biodiversity data.

    iNaturalist aggregates citizen science observations from around the world.
    Research-grade observations are community-verified and used in scientific
    research. Covers all kingdoms of life with over 150 million observations.

    Supports: taxa search, taxon details, observation search, species counts.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "search_taxa")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the iNaturalist API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"iNaturalist API request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to iNaturalist API"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"iNaturalist API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying iNaturalist: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate iNaturalist endpoint."""
        if self.endpoint == "search_taxa":
            return self._search_taxa(arguments)
        elif self.endpoint == "get_taxon":
            return self._get_taxon(arguments)
        elif self.endpoint == "search_observations":
            return self._search_observations(arguments)
        elif self.endpoint == "species_counts":
            return self._get_species_counts(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    @staticmethod
    def _page_metadata(
        total: int, page: int, per_page: int, returned: int
    ) -> Dict[str, Any]:
        accessible_pages = 10000 // per_page
        accessible_total = min(total, accessible_pages * per_page)
        has_more = bool(returned and page < accessible_pages and page * per_page < total)
        return {
            "returned": returned,
            "total_results": total,
            "total_results_is_exact": True,
            "page": page,
            "per_page": per_page,
            "has_more": has_more,
            "next_page": page + 1 if has_more else None,
            "accessible_results": accessible_total,
            "accessible_pages": min(
                accessible_pages, (total + per_page - 1) // per_page
            ),
            "upstream_truncated": total > accessible_total,
            "truncated": page > 1 or has_more or total > accessible_total,
            "result_set_complete": page == 1 and returned == total,
            "api_result_window_limit": 10000,
            "pagination_scope": "inaturalist_page_10000_result_window",
            "warning": (
                "iNaturalist matched more records than this endpoint's page-based "
                "10,000-result window exposes. Refine the query."
                if total > accessible_total
                else None
            ),
        }

    @staticmethod
    def _validate_page(
        arguments: Dict[str, Any], default_per_page: int, maximum: int
    ) -> tuple[int, int] | Dict[str, Any]:
        per_page = arguments.get("per_page", default_per_page)
        page = arguments.get("page", 1)
        if per_page is None:
            per_page = default_per_page
        if page is None:
            page = 1
        if (
            isinstance(per_page, bool)
            or not isinstance(per_page, int)
            or not 1 <= per_page <= maximum
        ):
            return {
                "status": "error",
                "error": f"per_page must be an integer between 1 and {maximum}",
                "parameter": "per_page",
            }
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            return {
                "status": "error",
                "error": "page must be an integer greater than or equal to 1",
                "parameter": "page",
            }
        if page * per_page > 10000:
            return {
                "status": "error",
                "error": "iNaturalist requires page * per_page <= 10000",
                "parameter": "page",
            }
        return page, per_page

    def _search_taxa(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for taxa by name."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        pagination = self._validate_page(arguments, 10, 200)
        if isinstance(pagination, dict):
            return pagination
        page, per_page = pagination
        url = f"{INAT_BASE_URL}/taxa"
        params = {"q": query, "per_page": per_page, "page": page}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        results = []
        for r in data.get("results", []):
            cs = r.get("conservation_status")
            results.append(
                {
                    "id": r.get("id"),
                    "name": r.get("name", ""),
                    "common_name": r.get("preferred_common_name"),
                    "rank": r.get("rank"),
                    "observations_count": r.get("observations_count", 0),
                    "is_active": r.get("is_active", True),
                    "conservation_status": cs.get("status") if cs else None,
                    "wikipedia_url": r.get("wikipedia_url"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "iNaturalist",
                "query": query,
                **self._page_metadata(
                    data.get("total_results", len(results)), page, params["per_page"], len(results)
                ),
            },
        }

    def _get_taxon(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed taxon information by ID."""
        taxon_id = arguments.get("taxon_id")
        if taxon_id is None:
            return {"status": "error", "error": "taxon_id parameter is required"}

        url = f"{INAT_BASE_URL}/taxa/{taxon_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])
        if not results:
            return {"status": "error", "error": f"Taxon ID {taxon_id} not found"}

        r = results[0]
        cs = r.get("conservation_status")

        # Build ancestry
        ancestors = r.get("ancestors", [])
        ancestry = []
        for a in ancestors:
            ancestry.append(
                {
                    "name": a.get("name", ""),
                    "rank": a.get("rank"),
                    "id": a.get("id"),
                }
            )

        return {
            "data": {
                "id": r.get("id"),
                "name": r.get("name", ""),
                "common_name": r.get("preferred_common_name"),
                "rank": r.get("rank"),
                "observations_count": r.get("observations_count", 0),
                "is_active": r.get("is_active", True),
                "conservation_status": cs.get("status") if cs else None,
                "wikipedia_url": r.get("wikipedia_url"),
                "ancestry": ancestry,
            },
            "metadata": {
                "source": "iNaturalist",
            },
        }

    def _search_observations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for species observations."""
        pagination = self._validate_page(arguments, 10, 200)
        if isinstance(pagination, dict):
            return pagination
        page, per_page = pagination
        params = {}
        if arguments.get("taxon_id"):
            params["taxon_id"] = arguments["taxon_id"]
        if arguments.get("query"):
            params["taxon_name"] = arguments["query"]
        if arguments.get("place_id"):
            params["place_id"] = arguments["place_id"]
        quality_grade = arguments.get("quality_grade") or "research"
        if quality_grade not in {"research", "needs_id", "casual"}:
            return {
                "status": "error",
                "error": "quality_grade must be one of: research, needs_id, casual",
                "parameter": "quality_grade",
            }
        id_below = arguments.get("id_below")
        if id_below is not None and (
            isinstance(id_below, bool) or not isinstance(id_below, int) or id_below < 1
        ):
            return {
                "status": "error",
                "error": "id_below must be a positive integer",
                "parameter": "id_below",
            }
        if id_below is not None and page != 1:
            return {
                "status": "error",
                "error": "page must be 1 when id_below cursor pagination is used",
                "parameter": "page",
            }
        params["quality_grade"] = quality_grade
        params["per_page"] = per_page
        params["page"] = page
        params["order_by"] = "id"
        params["order"] = "desc"
        if id_below is not None:
            params["id_below"] = id_below

        if not params.get("taxon_id") and not params.get("taxon_name"):
            return {"status": "error", "error": "Either taxon_id or query is required"}

        url = f"{INAT_BASE_URL}/observations"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        results = []
        for obs in data.get("results", []):
            taxon = obs.get("taxon") or {}
            geojson = obs.get("geojson") or {}
            coords = geojson.get("coordinates", [None, None])
            photos = obs.get("photos", [])

            results.append(
                {
                    "id": obs.get("id"),
                    "species_name": taxon.get("name"),
                    "common_name": taxon.get("preferred_common_name"),
                    "observed_on": obs.get("observed_on"),
                    "place_guess": obs.get("place_guess"),
                    "latitude": coords[1] if len(coords) > 1 else None,
                    "longitude": coords[0] if coords else None,
                    "quality_grade": obs.get("quality_grade"),
                    "user": obs.get("user", {}).get("login"),
                    "photo_url": photos[0].get("url") if photos else None,
                }
            )

        total = data.get("total_results", len(results))
        total_is_exact = isinstance(total, int) and not isinstance(total, bool)
        returned = len(results)
        page_has_more = bool(
            total_is_exact
            and returned
            and page * per_page < total
            and (page + 1) * per_page <= 10000
        )
        cursor_has_more = bool(total_is_exact and returned and page * per_page < total)
        next_id_below = results[-1]["id"] if cursor_has_more else None
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "iNaturalist",
                "returned": returned,
                "total_results": total if total_is_exact else None,
                "total_results_is_exact": total_is_exact,
                "total_results_scope": (
                    "records_below_id_below" if id_below is not None else "all_matches"
                ),
                "page": page,
                "per_page": per_page,
                "page_has_more": page_has_more,
                "next_page": page + 1 if page_has_more else None,
                "has_more": cursor_has_more,
                "id_below": id_below,
                "next_id_below": next_id_below,
                "truncated": page > 1 or cursor_has_more or id_below is not None,
                "result_set_complete": bool(
                    total_is_exact and id_below is None and page == 1 and returned == total
                ),
                "api_result_window_limit": 10000,
                "pagination_scope": "inaturalist_id_below_sliding_window",
                "warning": (
                    "Page-number pagination is limited to 10,000 results. Continue "
                    "with page=1 and metadata.next_id_below to traverse beyond it."
                    if total_is_exact and total > 10000
                    else None
                ),
            },
        }

    def _get_species_counts(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get species counts for a taxon group or location."""
        pagination = self._validate_page(arguments, 20, 500)
        if isinstance(pagination, dict):
            return pagination
        page, per_page = pagination
        params = {}
        if arguments.get("taxon_id"):
            params["taxon_id"] = arguments["taxon_id"]
        if arguments.get("place_id"):
            params["place_id"] = arguments["place_id"]
        quality_grade = arguments.get("quality_grade") or "research"
        if quality_grade not in {"research", "needs_id", "casual"}:
            return {
                "status": "error",
                "error": "quality_grade must be one of: research, needs_id, casual",
                "parameter": "quality_grade",
            }
        params["quality_grade"] = quality_grade
        params["per_page"] = per_page
        params["page"] = page

        if not params.get("taxon_id") and not params.get("place_id"):
            return {
                "status": "error",
                "error": "Either taxon_id or place_id is required",
            }

        url = f"{INAT_BASE_URL}/observations/species_counts"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        results = []
        for r in data.get("results", []):
            taxon = r.get("taxon", {})
            results.append(
                {
                    "taxon_id": taxon.get("id"),
                    "name": taxon.get("name", ""),
                    "common_name": taxon.get("preferred_common_name"),
                    "rank": taxon.get("rank"),
                    "count": r.get("count", 0),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "iNaturalist",
                "total_species": data.get("total_results", len(results)),
                **self._page_metadata(
                    data.get("total_results", len(results)),
                    params["page"],
                    params["per_page"],
                    len(results),
                ),
            },
        }
