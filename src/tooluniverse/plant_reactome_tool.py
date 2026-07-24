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
        elif self.action == "get_participants":
            return self._get_participants(arguments)
        elif self.action == "get_species_tree":
            return self._get_species_tree(arguments)
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

    def _get_participants(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List the gene/protein/molecule participants of a pathway or reaction."""
        pathway_id = arguments.get("pathway_id") or arguments.get("event_id") or ""
        pathway_id = pathway_id.strip() if isinstance(pathway_id, str) else ""
        if not pathway_id:
            return {"status": "error", "error": "pathway_id parameter is required"}

        url = f"{PLANT_REACTOME_BASE_URL}/data/participants/{pathway_id}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        if not isinstance(data, list):
            data = []

        participants = []
        for item in data:
            if not isinstance(item, dict):
                continue
            ref_entities = []
            for ref in item.get("refEntities") or []:
                if not isinstance(ref, dict):
                    continue
                ref_entities.append(
                    {
                        "identifier": ref.get("identifier"),
                        "display_name": ref.get("displayName"),
                        "gene_names": ref.get("geneName"),
                        "schema_class": ref.get("schemaClass"),
                        "url": ref.get("url"),
                    }
                )
            participants.append(
                {
                    "pe_db_id": item.get("peDbId"),
                    "display_name": item.get("displayName"),
                    "schema_class": item.get("schemaClass"),
                    "ref_entities": ref_entities,
                }
            )

        return {
            "status": "success",
            "data": participants,
            "metadata": {
                "source": "Plant Reactome (Gramene)",
                "pathway_id": pathway_id,
                "total_participants": len(participants),
            },
        }

    def _get_species_tree(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve the full hierarchical pathway/event tree for a species by NCBI taxId."""
        tax_id = arguments.get("tax_id")
        if tax_id is None or (isinstance(tax_id, str) and not tax_id.strip()):
            return {
                "status": "error",
                "error": "tax_id parameter is required (NCBI taxonomy id, e.g. 4530 for Oryza sativa)",
            }
        tax_id = str(tax_id).strip()

        url = f"{PLANT_REACTOME_BASE_URL}/data/eventsHierarchy/{tax_id}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        if not isinstance(data, list):
            data = []

        return {
            "status": "success",
            "data": data,
            "metadata": {
                "source": "Plant Reactome (Gramene)",
                "tax_id": tax_id,
                "total_top_level_pathways": len(data),
            },
        }
