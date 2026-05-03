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

    def _search_taxa(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for taxa by name."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        per_page = arguments.get("per_page") or 10
        url = f"{INAT_BASE_URL}/taxa"
        params = {"q": query, "per_page": min(per_page, 200)}
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
                "total_results": data.get("total_results", len(results)),
                "query": query,
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
        params = {}
        if arguments.get("taxon_id"):
            params["taxon_id"] = arguments["taxon_id"]
        if arguments.get("query"):
            params["taxon_name"] = arguments["query"]
        if arguments.get("place_id"):
            params["place_id"] = arguments["place_id"]
        params["quality_grade"] = arguments.get("quality_grade") or "research"
        params["per_page"] = min(arguments.get("per_page") or 10, 200)
        params["order_by"] = "created_at"

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

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "iNaturalist",
                "total_results": data.get("total_results", len(results)),
                "per_page": params["per_page"],
            },
        }

    def _get_species_counts(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get species counts for a taxon group or location."""
        params = {}
        if arguments.get("taxon_id"):
            params["taxon_id"] = arguments["taxon_id"]
        if arguments.get("place_id"):
            params["place_id"] = arguments["place_id"]
        params["quality_grade"] = arguments.get("quality_grade") or "research"
        params["per_page"] = min(arguments.get("per_page") or 20, 500)

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
            },
        }
