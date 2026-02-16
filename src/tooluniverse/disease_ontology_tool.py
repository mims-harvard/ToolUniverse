# disease_ontology_tool.py
"""
Disease Ontology (DO) REST API tool for ToolUniverse.

The Disease Ontology provides a standardized ontology for human disease terms.
It is widely used in bioinformatics for disease annotation and cross-referencing
with ICD-10, OMIM, MeSH, NCI Thesaurus, and SNOMED-CT.

API: https://www.disease-ontology.org/api/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

DO_BASE_URL = "https://www.disease-ontology.org/api/metadata"


@register_tool("DiseaseOntologyTool")
class DiseaseOntologyTool(BaseTool):
    """
    Tool for querying the Disease Ontology (DO) REST API.

    The Disease Ontology semantically integrates disease and medical
    vocabularies through cross-mapping of DO terms to MeSH, ICD,
    NCI Thesaurus, SNOMED CT, and OMIM.

    Supports: term lookup, parent hierarchy navigation.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_term")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Disease Ontology API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"Disease Ontology API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to Disease Ontology API"}
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {"error": f"DOID not found in Disease Ontology"}
            return {
                "error": f"Disease Ontology API HTTP error: {e.response.status_code}"
            }
        except Exception as e:
            return {"error": f"Unexpected error querying Disease Ontology: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate Disease Ontology endpoint."""
        if self.endpoint == "get_term":
            return self._get_term(arguments)
        elif self.endpoint == "get_parents":
            return self._get_parents(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _fetch_term(self, doid: str) -> Dict[str, Any]:
        """Fetch a single DO term by DOID."""
        # Extract numeric ID from DOID format
        if ":" in doid:
            numeric_id = doid.split(":")[1]
        else:
            numeric_id = doid

        url = f"{DO_BASE_URL}/DOID:{numeric_id}/"
        response = requests.get(url, timeout=self.timeout, allow_redirects=True)
        response.raise_for_status()
        return response.json()

    def _get_term(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a Disease Ontology term."""
        doid = arguments.get("doid", "")
        if not doid:
            return {"error": "doid parameter is required"}

        data = self._fetch_term(doid)

        # Parse parents
        parents = []
        for p in data.get("parents") or []:
            if isinstance(p, (list, tuple)) and len(p) >= 3:
                parents.append(
                    {
                        "relationship": p[0],
                        "name": p[1],
                        "id": p[2],
                    }
                )

        # Parse synonyms (format: "name TYPE []")
        synonyms = []
        for s in data.get("synonyms") or []:
            synonyms.append(s)

        return {
            "data": {
                "id": data.get("id"),
                "name": data.get("name"),
                "definition": data.get("definition"),
                "synonyms": synonyms,
                "parents": parents,
                "cross_references": data.get("xrefs", []),
                "subsets": data.get("subsets", []),
            },
            "metadata": {
                "source": "Disease Ontology (DO)",
            },
        }

    def _get_parents(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get parent terms for a Disease Ontology term with hierarchy navigation."""
        doid = arguments.get("doid", "")
        if not doid:
            return {"error": "doid parameter is required"}

        data = self._fetch_term(doid)

        parents_detail = []
        for p in data.get("parents") or []:
            if isinstance(p, (list, tuple)) and len(p) >= 3:
                parent_id = p[2]
                try:
                    parent_data = self._fetch_term(parent_id)
                    grandparents = []
                    for gp in parent_data.get("parents") or []:
                        if isinstance(gp, (list, tuple)) and len(gp) >= 3:
                            grandparents.append(
                                {
                                    "id": gp[2],
                                    "name": gp[1],
                                }
                            )

                    parents_detail.append(
                        {
                            "id": parent_id,
                            "name": parent_data.get("name"),
                            "definition": parent_data.get("definition"),
                            "grandparents": grandparents,
                        }
                    )
                except Exception:
                    parents_detail.append(
                        {
                            "id": parent_id,
                            "name": p[1],
                            "definition": None,
                            "grandparents": [],
                        }
                    )

        return {
            "data": {
                "id": data.get("id"),
                "name": data.get("name"),
                "parents": parents_detail,
            },
            "metadata": {
                "source": "Disease Ontology (DO)",
            },
        }
