# complex_portal_tool.py
"""
EBI Complex Portal API tool for ToolUniverse.

The Complex Portal is a manually curated, encyclopaedic resource of
macromolecular complexes from a number of key model organisms.
It includes CORUM mammalian protein complex data.

Data includes:
- Curated protein complex compositions
- Subunit stoichiometry
- Complex function and disease relevance
- Cross-references to PDB structures, Reactome pathways, GO annotations

API Documentation: https://www.ebi.ac.uk/complexportal/documentation
Base URL: https://www.ebi.ac.uk/complexportal/ws/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for Complex Portal API (IntAct complex-ws)
COMPLEX_PORTAL_BASE = "https://www.ebi.ac.uk/intact/complex-ws"


@register_tool("ComplexPortalTool")
class ComplexPortalTool(BaseTool):
    """
    Tool for querying the EBI Complex Portal for curated protein complexes.

    Provides access to:
    - Protein complex search by gene/protein name
    - Detailed complex compositions and stoichiometry
    - Complex function, disease associations, and cross-references
    - Data from CORUM and other curated complex databases

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_complexes"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Complex Portal API call."""
        operation = self.operation

        if operation == "search_complexes":
            return self._search_complexes(arguments)
        elif operation == "get_complex":
            return self._get_complex(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _search_complexes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for protein complexes containing a given gene/protein.

        Queries the Complex Portal search endpoint.
        """
        query = arguments.get("query", "")
        species = arguments.get("species", "9606")  # Default: human
        first = arguments.get("first", 0)
        number = arguments.get("number", 25)

        if not query:
            return {"status": "error", "error": "query parameter is required"}

        try:
            url = f"{COMPLEX_PORTAL_BASE}/search/{query}"
            params = {
                "format": "json",
                "facets": "species_f",
                "filters": f"species_f:({species})" if species else None,
                "first": first,
                "number": min(number, 100),
            }
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}

            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            complexes = []
            elements = data.get("elements", [])
            for elem in elements:
                complex_info = {
                    "complex_id": elem.get("complexAC"),
                    "name": elem.get("complexName"),
                    "species": elem.get("organismName"),
                    "description": (
                        elem.get("description", "")[:500]
                        if elem.get("description")
                        else None
                    ),
                    "predicted": elem.get("predictedComplex", False),
                    "subunits": [],
                }

                # Parse interactors (subunits)
                for interactor in elem.get("interactors", elem.get("participants", [])):
                    subunit = {
                        "identifier": interactor.get("identifier"),
                        "name": interactor.get("name"),
                        "description": interactor.get("description"),
                        "stoichiometry": interactor.get("stochiometry"),
                        "interactor_type": interactor.get("interactorType"),
                    }
                    complex_info["subunits"].append(subunit)

                complexes.append(complex_info)

            total_found = data.get(
                "totalNumberOfResults", data.get("size", len(complexes))
            )

            return {
                "status": "success",
                "data": {
                    "query": query,
                    "species_filter": species,
                    "complexes": complexes,
                    "count": len(complexes),
                    "total_found": total_found,
                },
                "source": "EBI Complex Portal (includes CORUM data)",
            }

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Complex Portal API timeout after {self.timeout}s",
            }
        except requests.exceptions.HTTPError as e:
            status_code = (
                e.response.status_code if e.response is not None else "unknown"
            )
            if status_code == 404:
                return {
                    "status": "success",
                    "data": {
                        "query": query,
                        "complexes": [],
                        "count": 0,
                        "total_found": 0,
                    },
                    "message": f"No complexes found for '{query}'",
                }
            return {
                "status": "error",
                "error": f"Complex Portal API HTTP error: {status_code}",
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Complex Portal API request failed: {str(e)}",
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_complex(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed information for a specific protein complex by its Complex Portal ID.

        Returns full complex data including subunit composition, function, and cross-references.
        """
        complex_id = arguments.get("complex_id", "")

        if not complex_id:
            return {"status": "error", "error": "complex_id parameter is required"}

        try:
            url = f"{COMPLEX_PORTAL_BASE}/complex/{complex_id}"
            params = {"format": "json"}

            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # Parse complex details
            complex_data = {
                "complex_id": data.get("complexAC"),
                "name": data.get("complexName"),
                "systematic_name": data.get("systematicName"),
                "species": data.get("organismName"),
                "taxonomy_id": data.get("organismTaxId"),
                "description": data.get("description"),
                "properties": data.get("properties"),
                "complex_type": data.get("complexType"),
                "evidence_type": data.get("evidenceType"),
                "subunits": [],
                "cross_references": [],
                "diseases": [],
                "go_annotations": [],
            }

            # Parse interactors (subunits)
            for interactor in data.get("interactors", data.get("participants", [])):
                subunit = {
                    "identifier": interactor.get("identifier"),
                    "name": interactor.get("name"),
                    "description": interactor.get("description"),
                    "stoichiometry": interactor.get("stochiometry"),
                    "interactor_type": interactor.get("interactorType"),
                }
                complex_data["subunits"].append(subunit)

            # Parse cross-references
            for xref in data.get("crossReferences", []):
                db = xref.get("database", "")
                xref_entry = {
                    "database": db,
                    "identifier": xref.get("identifier"),
                    "description": xref.get("description"),
                }
                if db.lower() in ("efo", "orphanet", "mondo"):
                    complex_data["diseases"].append(xref_entry)
                elif db.lower() == "go":
                    complex_data["go_annotations"].append(xref_entry)
                else:
                    complex_data["cross_references"].append(xref_entry)

            return {
                "status": "success",
                "data": complex_data,
                "source": "EBI Complex Portal",
            }

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Complex Portal API timeout after {self.timeout}s",
            }
        except requests.exceptions.HTTPError as e:
            status_code = (
                e.response.status_code if e.response is not None else "unknown"
            )
            if status_code == 404:
                return {
                    "status": "success",
                    "data": None,
                    "message": f"Complex not found: {complex_id}",
                }
            return {
                "status": "error",
                "error": f"Complex Portal API HTTP error: {status_code}",
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Complex Portal API request failed: {str(e)}",
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
