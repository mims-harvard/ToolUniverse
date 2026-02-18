# uniprot_locations_tool.py
"""
UniProt Subcellular Locations API tool for ToolUniverse.

The UniProt Subcellular Locations database provides controlled vocabulary
for protein subcellular localization. Each location includes definition,
GO mapping, keyword associations, hierarchical relationships, and protein
count statistics.

API: https://rest.uniprot.org/locations/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

UNIPROT_LOCATIONS_URL = "https://rest.uniprot.org/locations"


@register_tool("UniProtLocationsTool")
class UniProtLocationsTool(BaseTool):
    """
    Tool for querying the UniProt Subcellular Locations database.

    Supports:
    - Get location details by ID (SL-XXXX)
    - Search locations by name or keyword

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_location")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the UniProt Locations API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"UniProt Locations API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to UniProt Locations API"}
        except requests.exceptions.HTTPError as e:
            return {
                "error": f"UniProt Locations API HTTP error: {e.response.status_code}"
            }
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "get_location":
            return self._get_location(arguments)
        elif self.endpoint == "search_locations":
            return self._search_locations(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _parse_location(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a location entry into a clean structure."""
        # Gene Ontology mappings
        go_terms = []
        for go in data.get("geneOntologies", []):
            go_terms.append(
                {
                    "go_id": go.get("goId"),
                    "name": go.get("name"),
                }
            )

        # Keyword association
        keyword = data.get("keyword")
        keyword_info = None
        if keyword:
            keyword_info = {
                "id": keyword.get("id"),
                "name": keyword.get("name"),
            }

        # Statistics
        stats = data.get("statistics") or {}

        # Hierarchical relationships
        is_part_of = []
        for part in data.get("partOf", []):
            is_part_of.append(
                {
                    "id": part.get("id"),
                    "name": part.get("name"),
                }
            )

        contains = []
        for child in data.get("isA", []):
            contains.append(
                {
                    "id": child.get("id"),
                    "name": child.get("name"),
                }
            )

        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "definition": data.get("definition"),
            "content": data.get("content"),
            "category": data.get("category"),
            "note": data.get("note"),
            "synonyms": data.get("synonyms", []),
            "keyword": keyword_info,
            "gene_ontologies": go_terms,
            "reviewed_protein_count": stats.get("reviewedProteinCount"),
            "unreviewed_protein_count": stats.get("unreviewedProteinCount"),
            "part_of": is_part_of,
            "children": contains,
        }

    def _get_location(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get subcellular location details by ID."""
        location_id = arguments.get("location_id", "")
        if not location_id:
            return {
                "error": "location_id parameter is required (e.g., 'SL-0091' for cytosol)"
            }

        # Normalize ID
        location_id = location_id.strip()
        if not location_id.startswith("SL-"):
            location_id = f"SL-{location_id}"

        url = f"{UNIPROT_LOCATIONS_URL}/{location_id}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        return {
            "data": self._parse_location(data),
            "metadata": {
                "source": "UniProt Subcellular Locations",
            },
        }

    def _search_locations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search subcellular locations by name or keyword."""
        query = arguments.get("query", "")
        if not query:
            return {
                "error": "query parameter is required (e.g., 'nucleus', 'membrane', 'mitochondria')"
            }

        size = min(arguments.get("size") or 10, 50)

        url = f"{UNIPROT_LOCATIONS_URL}/search"
        params = {
            "query": query,
            "size": size,
        }

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        results_raw = data.get("results", [])
        results = [self._parse_location(loc) for loc in results_raw]

        return {
            "data": results,
            "metadata": {
                "source": "UniProt Subcellular Locations",
                "query": query,
                "returned": len(results),
            },
        }
