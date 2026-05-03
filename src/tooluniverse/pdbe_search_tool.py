# pdbe_search_tool.py
"""
PDBe Search (Solr) API tool for ToolUniverse.

PDBe Search provides a powerful Solr-based search interface for the
Protein Data Bank in Europe. It supports full-text and field-specific
queries across all PDB entries, with faceting and filtering capabilities.

API: https://www.ebi.ac.uk/pdbe/search/pdb/select
Also: https://www.ebi.ac.uk/pdbe/api/pdb/compound/summary/{ligand_id}
No authentication required. Free for all use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

PDBE_SEARCH_URL = "https://www.ebi.ac.uk/pdbe/search/pdb/select"
PDBE_API_URL = "https://www.ebi.ac.uk/pdbe/api/pdb"


@register_tool("PDBeSearchTool")
class PDBeSearchTool(BaseTool):
    """
    Tool for searching PDBe, the Protein Data Bank in Europe.

    Provides full-text and field-specific Solr queries across all PDB
    entries, plus compound/ligand lookup by identifier.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "search_structures"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the PDBe Search API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"PDBe Search API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to PDBe Search API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"PDBe Search API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying PDBe Search: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "search_structures":
            return self._search_structures(arguments)
        elif self.endpoint_type == "get_compound":
            return self._get_compound(arguments)
        elif self.endpoint_type == "search_by_organism":
            return self._search_by_organism(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type: {self.endpoint_type}",
            }

    def _search_structures(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search PDB structures by keyword or protein name."""
        query = arguments.get("query", "")
        if not query:
            return {
                "status": "error",
                "error": "query parameter is required (e.g., 'insulin', 'kinase', 'BRCA1')",
            }

        limit = min(arguments.get("limit", 10), 50)

        params = {
            "q": query,
            "rows": limit,
            "fl": "pdb_id,title,resolution,experimental_method,deposition_date,number_of_entities,organism_scientific_name",
            "wt": "json",
            "sort": "resolution asc",
        }

        response = requests.get(PDBE_SEARCH_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        solr_response = raw.get("response", {})
        total = solr_response.get("numFound", 0)

        structures = []
        for doc in solr_response.get("docs", []):
            entry = {
                "pdb_id": doc.get("pdb_id", ""),
                "title": doc.get("title", ""),
                "resolution": doc.get("resolution"),
                "experimental_method": doc.get("experimental_method", []),
                "deposition_date": doc.get("deposition_date"),
                "number_of_entities": doc.get("number_of_entities"),
                "organism": doc.get("organism_scientific_name", []),
            }
            structures.append(entry)

        return {
            "status": "success",
            "data": structures,
            "metadata": {
                "source": "PDBe Search",
                "total_found": total,
                "returned": len(structures),
                "query": query,
                "endpoint": "search_structures",
            },
        }

    def _get_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get PDB ligand/compound information by compound ID."""
        compound_id = arguments.get("compound_id", "")
        if not compound_id:
            return {
                "status": "error",
                "error": "compound_id parameter is required (e.g., 'ATP', 'HEM', 'NAG')",
            }

        url = f"{PDBE_API_URL}/compound/summary/{compound_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        # Response keyed by compound ID
        compound_data = raw.get(compound_id, [])
        if not compound_data:
            compound_data = raw.get(compound_id.upper(), [])

        compounds = []
        for c in compound_data:
            if isinstance(c, dict):
                entry = {
                    "name": c.get("name", ""),
                    "formula": c.get("formula", ""),
                    "weight": c.get("weight"),
                    "compound_type": c.get("compound_type", ""),
                    "inchi": c.get("inchi", ""),
                    "inchi_key": c.get("inchi_key", ""),
                }
                # SMILES
                smiles_list = c.get("smiles", [])
                if isinstance(smiles_list, list) and smiles_list:
                    first = smiles_list[0]
                    if isinstance(first, dict):
                        entry["smiles"] = first.get("name", "")

                # Systematic names
                sys_names = c.get("systematic_names", [])
                if isinstance(sys_names, list) and sys_names:
                    for sn in sys_names[:2]:
                        if isinstance(sn, dict):
                            entry["systematic_name"] = sn.get("name", "")
                            break

                compounds.append(entry)

        result = compounds[0] if compounds else {}
        result["compound_id"] = compound_id

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "PDBe",
                "query": compound_id,
                "endpoint": "get_compound",
            },
        }

    def _search_by_organism(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search PDB structures filtered by organism."""
        organism = arguments.get("organism", "")
        query = arguments.get("query", "*:*")
        limit = min(arguments.get("limit", 10), 50)

        if not organism:
            return {
                "status": "error",
                "error": "organism parameter is required (e.g., 'Homo sapiens', 'Escherichia coli')",
            }

        # Build Solr query with organism filter
        full_query = f'{query} AND organism_scientific_name:"{organism}"'

        params = {
            "q": full_query,
            "rows": limit,
            "fl": "pdb_id,title,resolution,experimental_method,deposition_date,organism_scientific_name",
            "wt": "json",
            "sort": "resolution asc",
        }

        response = requests.get(PDBE_SEARCH_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        solr_response = raw.get("response", {})
        total = solr_response.get("numFound", 0)

        structures = []
        for doc in solr_response.get("docs", []):
            entry = {
                "pdb_id": doc.get("pdb_id", ""),
                "title": doc.get("title", ""),
                "resolution": doc.get("resolution"),
                "experimental_method": doc.get("experimental_method", []),
                "deposition_date": doc.get("deposition_date"),
                "organism": doc.get("organism_scientific_name", []),
            }
            structures.append(entry)

        return {
            "status": "success",
            "data": structures,
            "metadata": {
                "source": "PDBe Search",
                "total_found": total,
                "returned": len(structures),
                "query": query,
                "organism_filter": organism,
                "endpoint": "search_by_organism",
            },
        }
