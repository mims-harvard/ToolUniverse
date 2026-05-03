# plant_reactome_tool.py
"""
Plant Reactome (Gramene) REST API tool for ToolUniverse.

Plant Reactome is a free, open-source, curated database of plant metabolic and
regulatory pathways. It is hosted by Gramene and provides pathway data for 140+
plant species including model organisms (Arabidopsis thaliana, Oryza sativa) and
major crop species.

API: https://plantreactome.gramene.org/ContentService/
No authentication required. Free for all use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

PLANT_REACTOME_BASE_URL = "https://plantreactome.gramene.org/ContentService"


@register_tool("PlantReactomeTool")
class PlantReactomeTool(BaseTool):
    """
    Tool for querying the Plant Reactome pathway database.

    Plant Reactome provides curated plant metabolic and regulatory pathways.
    Supports searching pathways, getting pathway details, and listing available
    species. Covers photosynthesis, carbon fixation, nitrogen metabolism,
    hormone signaling, secondary metabolites, and more.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.action = fields.get("action", "search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Plant Reactome API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Plant Reactome API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Plant Reactome API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"Plant Reactome API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying Plant Reactome: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate query method."""
        if self.action == "search":
            return self._search(arguments)
        elif self.action == "get_pathway":
            return self._get_pathway(arguments)
        elif self.action == "list_species":
            return self._list_species(arguments)
        else:
            return {"status": "error", "error": f"Unknown action: {self.action}"}

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for plant pathways."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        species = arguments.get("species")

        params = {
            "query": query,
            "cluster": "true",
        }
        if species:
            params["species"] = species

        url = f"{PLANT_REACTOME_BASE_URL}/search/query"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()

        # Flatten the grouped results into a list
        results = []
        groups = data.get("results", [])
        for group in groups:
            for entry in group.get("entries", []):
                results.append(
                    {
                        "stId": entry.get("stId", ""),
                        "name": entry.get("name", ""),
                        "species": entry.get("species", [None]),
                        "exact_type": entry.get("exactType"),
                        "compartment_names": entry.get("compartmentNames"),
                    }
                )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "Plant Reactome (Gramene)",
                "total_results": data.get("numberOfMatches", len(results)),
                "total_groups": data.get("numberOfGroups", len(groups)),
                "query": query,
            },
        }

    def _get_pathway(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed pathway information."""
        pathway_id = arguments.get("pathway_id", "")
        if not pathway_id:
            return {"status": "error", "error": "pathway_id parameter is required"}

        url = f"{PLANT_REACTOME_BASE_URL}/data/query/{pathway_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()

        return {
            "status": "success",
            "data": data,
            "metadata": {
                "source": "Plant Reactome (Gramene)",
                "pathway_id": pathway_id,
            },
        }

    def _list_species(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all available plant species."""
        url = f"{PLANT_REACTOME_BASE_URL}/data/species/all"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()

        species_list = []
        for sp in data:
            species_list.append(
                {
                    "dbId": sp.get("dbId"),
                    "displayName": sp.get("displayName", ""),
                    "taxId": sp.get("taxId"),
                    "abbreviation": sp.get("abbreviation"),
                }
            )

        return {
            "status": "success",
            "data": species_list,
            "metadata": {
                "source": "Plant Reactome (Gramene)",
                "total_species": len(species_list),
            },
        }
