# chebi_tool.py
"""
ChEBI 2.0 REST API tool for ToolUniverse.

ChEBI (Chemical Entities of Biological Interest) is a freely available
dictionary of molecular entities focused on 'small' chemical compounds,
maintained by EMBL-EBI. It provides an ontology-based classification
system, cross-references to other chemical databases, and detailed
structural information for 195,000+ compounds.

API: https://www.ebi.ac.uk/chebi/backend/api/
No authentication required. Free for all use.
"""

import re
import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

CHEBI_BASE_URL = "https://www.ebi.ac.uk/chebi/backend/api/public"


@register_tool("ChEBITool")
class ChEBITool(BaseTool):
    """
    Tool for querying ChEBI (Chemical Entities of Biological Interest).

    Provides compound lookup, text search, and ontology navigation
    for small molecules of biological relevance.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "get_compound"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the ChEBI API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"ChEBI API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to ChEBI API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"ChEBI API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying ChEBI: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "get_compound":
            return self._get_compound(arguments)
        elif self.endpoint_type == "search":
            return self._search(arguments)
        elif self.endpoint_type == "ontology_children":
            return self._ontology_children(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type: {self.endpoint_type}",
            }

    def _get_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed compound information by ChEBI ID."""
        chebi_id = arguments.get("chebi_id", None)
        if chebi_id is None:
            return {
                "status": "error",
                "error": "chebi_id parameter is required (e.g., 15365 for aspirin)",
            }

        url = f"{CHEBI_BASE_URL}/compound/{chebi_id}/"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        # Extract synonyms
        synonyms = []
        names_dict = raw.get("names", {})
        for name_type, name_list in names_dict.items():
            if isinstance(name_list, list):
                for entry in name_list[:10]:
                    if isinstance(entry, dict):
                        syn = entry.get("name", "")
                        if syn and syn not in synonyms:
                            synonyms.append(syn)

        # Chemical data is nested under 'chemical_data'
        chem_data = raw.get("chemical_data", {})
        if not isinstance(chem_data, dict):
            chem_data = {}

        # Structure data is under 'default_structure'
        struct_data = raw.get("default_structure", {})
        if not isinstance(struct_data, dict):
            struct_data = {}

        # Parse mass as float if string
        mass_val = chem_data.get("mass", None)
        if isinstance(mass_val, str):
            try:
                mass_val = float(mass_val)
            except ValueError:
                mass_val = None

        mono_mass = chem_data.get("monoisotopic_mass", None)
        if isinstance(mono_mass, str):
            try:
                mono_mass = float(mono_mass)
            except ValueError:
                mono_mass = None

        result = {
            "chebi_id": raw.get("id", chebi_id),
            "chebi_accession": raw.get("chebi_accession", f"CHEBI:{chebi_id}"),
            "name": raw.get("name", ""),
            "definition": raw.get("definition", None),
            "stars": raw.get("stars", 0),
            "formula": chem_data.get("formula", None),
            "mass": mass_val,
            "monoisotopic_mass": mono_mass,
            "charge": chem_data.get("charge", None),
            "smiles": struct_data.get("smiles", None),
            "inchikey": struct_data.get("standard_inchi_key", None),
            "synonyms": synonyms[:20],
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "ChEBI",
                "query": str(chebi_id),
                "endpoint": "compound",
            },
        }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search ChEBI by name, formula, or keyword using advanced search."""
        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)
        if not query:
            return {
                "status": "error",
                "error": "query parameter is required (e.g., 'glucose', 'caffeine')",
            }

        if limit is None:
            limit = 10
        limit = min(limit, 100)

        # Use advanced_search endpoint for better relevance
        url = f"{CHEBI_BASE_URL}/advanced_search/"
        payload = {
            "text_search_specification": {
                "or_specification": [{"text": query, "category": "all"}]
            },
            "stars": [2, 3],
        }
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        results = raw.get("results", [])
        compounds = []
        for hit in results[:limit]:
            source = hit.get("_source", {})
            # Strip HTML tags from name (ChEBI stores stereochemistry as HTML)
            raw_name = source.get("name", "")
            clean_name = re.sub(r"<[^>]+>", "", raw_name)
            compounds.append(
                {
                    "chebi_accession": source.get("chebi_accession", ""),
                    "name": clean_name,
                    "formula": source.get("formula", None),
                    "mass": source.get("mass", None),
                    "stars": source.get("stars", None),
                }
            )

        result = {
            "query": query,
            "result_count": len(compounds),
            "compounds": compounds,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "ChEBI",
                "query": query,
                "endpoint": "advanced_search",
            },
        }

    def _ontology_children(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get ontology children of a ChEBI compound."""
        chebi_id = arguments.get("chebi_id", None)
        if chebi_id is None:
            return {
                "status": "error",
                "error": "chebi_id parameter is required (e.g., 15365 for aspirin)",
            }

        url = f"{CHEBI_BASE_URL}/ontology/children/{chebi_id}/"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        # Extract relations
        relations = []
        ontology = raw.get("ontology_relations", {})
        incoming = ontology.get("incoming_relations", [])
        if isinstance(incoming, list):
            for rel in incoming:
                relations.append(
                    {
                        "child_id": rel.get("init_id", 0),
                        "child_name": rel.get("init_name", ""),
                        "relation_type": rel.get("relation_type", ""),
                        "parent_id": rel.get("final_id", 0),
                        "parent_name": rel.get("final_name", ""),
                    }
                )

        result = {
            "chebi_id": raw.get("id", chebi_id),
            "chebi_accession": raw.get("chebi_accession", f"CHEBI:{chebi_id}"),
            "relation_count": len(relations),
            "relations": relations,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "ChEBI",
                "query": str(chebi_id),
                "endpoint": "ontology/children",
            },
        }
