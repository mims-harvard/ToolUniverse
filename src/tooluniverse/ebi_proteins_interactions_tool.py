# ebi_proteins_interactions_tool.py
"""
EBI Proteins Interactions tool for ToolUniverse.

Provides protein-protein interaction data from the EBI Proteins API,
sourced from IntAct. Returns experimentally validated binary interactions
with partner details and experiment counts.

API: https://www.ebi.ac.uk/proteins/api/proteins/interaction/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

EBI_PROTEINS_BASE_URL = "https://www.ebi.ac.uk/proteins/api"


@register_tool("EBIProteinsInteractionsTool")
class EBIProteinsInteractionsTool(BaseTool):
    """
    Tool for querying EBI Proteins protein-protein interaction data.

    Supports:
    - Get interaction partners for a protein (from IntAct)
    - Get detailed protein info with interactions, diseases, locations

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "interactions")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the EBI Proteins Interactions API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"EBI Proteins API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to EBI Proteins API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 400:
                return {
                    "error": f"Invalid accession. Use a UniProt accession (e.g., P04637)."
                }
            return {"error": f"EBI Proteins API HTTP {status}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "interactions":
            return self._get_interactions(arguments)
        elif self.endpoint == "interaction_details":
            return self._get_interaction_details(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_interactions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get protein-protein interaction partners."""
        accession = arguments.get("accession", "")
        if not accession:
            return {"error": "accession is required (e.g., 'P04637')."}

        url = f"{EBI_PROTEINS_BASE_URL}/proteins/interaction/{accession}"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        # Data is a list of entries, each with interactions
        all_interactions = []
        if isinstance(data, list):
            for entry in data:
                for interaction in entry.get("interactions", []):
                    partner_acc = interaction.get(
                        "accession2", interaction.get("accession1")
                    )
                    # Skip self-interactions
                    if partner_acc == accession:
                        partner_acc = interaction.get("accession1")
                    all_interactions.append(
                        {
                            "partner_accession": partner_acc,
                            "gene_name": interaction.get("gene"),
                            "experiments": interaction.get("experiments", 0),
                            "organism_differ": interaction.get("organismDiffer", False),
                            "intact_id_a": interaction.get("interactor1"),
                            "intact_id_b": interaction.get("interactor2"),
                        }
                    )

        # Deduplicate by partner accession, keep highest experiment count
        seen = {}
        for interaction in all_interactions:
            partner = interaction["partner_accession"]
            if (
                partner not in seen
                or interaction["experiments"] > seen[partner]["experiments"]
            ):
                seen[partner] = interaction
        unique_interactions = sorted(
            seen.values(), key=lambda x: x["experiments"], reverse=True
        )

        return {
            "data": {
                "query_accession": accession,
                "interactions": unique_interactions,
            },
            "metadata": {
                "source": "EBI Proteins API / IntAct (ebi.ac.uk/proteins)",
                "total_interactions": len(unique_interactions),
            },
        }

    def _get_interaction_details(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get protein info with interactions, diseases, and locations."""
        accession = arguments.get("accession", "")
        if not accession:
            return {"error": "accession is required (e.g., 'P04637')."}

        url = f"{EBI_PROTEINS_BASE_URL}/proteins/interaction/{accession}"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list) or not data:
            return {"error": f"No interaction data found for {accession}"}

        # Extract protein metadata from first entry
        first_entry = data[0]
        protein_name = first_entry.get("accession", accession)
        protein_existence = first_entry.get("proteinExistence")
        organism = None
        taxonomy = first_entry.get("taxonomy")
        if taxonomy:
            organism = taxonomy if isinstance(taxonomy, str) else str(taxonomy)

        # Collect all interactions across entries
        all_interactions = []
        diseases = set()
        locations = set()

        for entry in data:
            for interaction in entry.get("interactions", []):
                partner_acc = interaction.get(
                    "accession2", interaction.get("accession1")
                )
                if partner_acc == accession:
                    partner_acc = interaction.get("accession1")
                all_interactions.append(
                    {
                        "partner_accession": partner_acc,
                        "gene_name": interaction.get("gene"),
                        "experiments": interaction.get("experiments", 0),
                        "organism_differ": interaction.get("organismDiffer", False),
                    }
                )

            # Extract diseases
            for disease in entry.get("diseases", []):
                disease_name = (
                    disease.get("diseaseId")
                    or disease.get("acronym")
                    or disease.get("type")
                )
                if disease_name:
                    diseases.add(str(disease_name))

            # Extract subcellular locations
            for loc in entry.get("subcellularLocations", []):
                for subloc in loc.get("locations", [loc]):
                    loc_name = (
                        subloc.get("value") if isinstance(subloc, dict) else str(subloc)
                    )
                    if loc_name:
                        locations.add(str(loc_name))

        # Deduplicate and sort
        seen = {}
        for interaction in all_interactions:
            partner = interaction["partner_accession"]
            if (
                partner not in seen
                or interaction["experiments"] > seen[partner]["experiments"]
            ):
                seen[partner] = interaction
        top_interactions = sorted(
            seen.values(), key=lambda x: x["experiments"], reverse=True
        )[:50]

        return {
            "data": {
                "query_accession": accession,
                "protein_name": protein_name,
                "protein_existence": protein_existence,
                "organism": organism,
                "total_interaction_entries": len(data),
                "top_interactions": top_interactions,
                "diseases": sorted(diseases),
                "subcellular_locations": sorted(locations),
            },
            "metadata": {
                "source": "EBI Proteins API / IntAct (ebi.ac.uk/proteins)",
                "total_interactions": len(seen),
            },
        }
