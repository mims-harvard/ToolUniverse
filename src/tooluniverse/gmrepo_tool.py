"""
GMrepo Tool - Curated Human Gut Microbiome Repository

Provides access to the GMrepo database for querying gut microbiome species
and their associations with health phenotypes/diseases. GMrepo aggregates
curated 16S/metagenomic data from published human gut microbiome studies.

API base: https://gmrepo.humangut.info/api
No authentication required.

Note: The GMrepo API is a Django application. Some endpoints require POST with
JSON body and trailing slashes. Species detail endpoints are currently limited
to the bulk listing endpoints (get_all_gut_microbes, get_all_phenotypes).

Reference: Wu et al., Nucl. Acids Res. 2020
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool


GMREPO_BASE = "https://gmrepo.humangut.info/api"


@register_tool("GmrepoTool")
class GmrepoTool(BaseTool):
    """
    Tool for querying the GMrepo gut microbiome database.

    Supported operations:
    - search_species: Search gut microbiome species by name, filtering the
      full species catalog. Can also filter by phenotype association count.
    - get_phenotypes: List all phenotypes/conditions with microbiome data,
      optionally filtered by keyword.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = 60  # bulk endpoints can be slow
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "search_species"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the GMrepo API call."""
        try:
            if self.endpoint_type == "search_species":
                return self._search_species(arguments)
            elif self.endpoint_type == "get_phenotypes":
                return self._get_phenotypes(arguments)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown endpoint type: {self.endpoint_type}",
                }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "GMrepo API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to GMrepo API"}
        except Exception as e:
            return {"status": "error", "error": f"GMrepo API error: {str(e)}"}

    def _search_species(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for gut microbiome species by name."""
        query = arguments.get("query") or arguments.get("species_name", "")
        if not query:
            return {"status": "error", "error": "Missing required parameter: query"}

        limit = arguments.get("limit", 20)

        url = f"{GMREPO_BASE}/get_all_gut_microbes/"
        resp = requests.post(
            url,
            json={},
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != "200":
            return {
                "status": "error",
                "error": f"GMrepo returned error code: {data.get('code')}",
            }

        all_species = data.get("all_species", [])
        query_lower = query.lower()
        matches = [s for s in all_species if query_lower in s.get("name", "").lower()]

        # Sort by number of presented samples (most abundant first)
        matches.sort(key=lambda x: int(x.get("presented_samples", "0")), reverse=True)
        matches = matches[:limit]

        results = []
        for sp in matches:
            results.append(
                {
                    "ncbi_taxon_id": sp.get("ncbi_taxon_id"),
                    "name": sp.get("name"),
                    "presented_samples": sp.get("presented_samples"),
                    "nr_phenotypes": sp.get("nr_phenotypes"),
                    "pct_of_all_samples": sp.get("pct_of_all_samples"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "query": query,
                "total_matches": len(
                    [s for s in all_species if query_lower in s.get("name", "").lower()]
                ),
                "returned": len(results),
                "total_species_in_db": len(all_species),
            },
        }

    def _get_phenotypes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List phenotypes/conditions with gut microbiome data."""
        query = arguments.get("query", "")
        limit = arguments.get("limit", 20)

        url = f"{GMREPO_BASE}/get_all_phenotypes/"
        resp = requests.post(
            url,
            json={},
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != "200":
            return {
                "status": "error",
                "error": f"GMrepo returned error code: {data.get('code')}",
            }

        phenotypes = data.get("phenotypes", [])

        if query:
            query_lower = query.lower()
            phenotypes = [
                p for p in phenotypes if query_lower in p.get("term", "").lower()
            ]

        # Sort by number of valid runs (most data first)
        phenotypes.sort(key=lambda x: x.get("valid_runs", 0), reverse=True)
        phenotypes = phenotypes[:limit]

        results = []
        for p in phenotypes:
            results.append(
                {
                    "phenotype_id": p.get("id"),
                    "mesh_id": p.get("disease"),
                    "term": p.get("term"),
                    "all_samples": p.get("all_samples"),
                    "valid_runs": p.get("valid_runs"),
                    "nr_species": p.get("nr_species"),
                    "nr_genus": p.get("nr_genus"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "query": query or "(all phenotypes)",
                "returned": len(results),
                "total_phenotypes_in_db": len(data.get("phenotypes", [])),
            },
        }
