# three_d_beacons_tool.py
"""
3D Beacons API tool for ToolUniverse.

Provides access to the 3D Beacons Hub API, which aggregates 3D structure
models for proteins from multiple data providers including PDBe, AlphaFold DB,
SWISS-MODEL, PED (Protein Ensemble Database), AlphaFill, and isoform.io.

API: https://www.ebi.ac.uk/pdbe/pdbe-kb/3dbeacons/api/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from collections import Counter
from .base_tool import BaseTool


BEACONS_BASE_URL = "https://www.ebi.ac.uk/pdbe/pdbe-kb/3dbeacons/api"


class ThreeDBeaconsTool(BaseTool):
    """
    Tool for 3D Beacons Hub API providing aggregated 3D structure models
    from multiple providers for a given UniProt protein accession.

    Aggregates experimental structures (PDBe), predicted models (AlphaFold DB),
    homology models (SWISS-MODEL), conformational ensembles (PED), and more.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "summary")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the 3D Beacons API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"3D Beacons API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to 3D Beacons API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                return {
                    "error": f"No structures found for protein: {arguments.get('accession', '')}"
                }
            return {"error": f"3D Beacons API HTTP error: {code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying 3D Beacons API: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "summary":
            return self._get_structure_summary(arguments)
        elif self.endpoint == "structures":
            return self._get_structures(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_structure_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary of all 3D structures/models for a UniProt protein."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "error": "accession parameter is required (UniProt accession, e.g., 'P04637')"
            }

        url = f"{BEACONS_BASE_URL}/uniprot/summary/{accession}.json"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        structures = data.get("structures", [])
        uniprot_entry = data.get("uniprot_entry", {})

        # Compute provider and category statistics
        provider_counts = Counter(
            s.get("summary", {}).get("provider", "unknown") for s in structures
        )
        category_counts = Counter(
            s.get("summary", {}).get("model_category", "unknown") for s in structures
        )

        return {
            "data": {
                "accession": uniprot_entry.get("ac", accession),
                "sequence_length": uniprot_entry.get("sequence_length"),
                "total_structures": len(structures),
                "by_provider": dict(provider_counts),
                "by_category": dict(category_counts),
            },
            "metadata": {
                "source": "3D Beacons Hub API",
                "accession": accession,
            },
        }

    def _get_structures(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed structure list for a UniProt protein."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "error": "accession parameter is required (UniProt accession, e.g., 'P04637')"
            }

        category_filter = arguments.get("category", None)
        provider_filter = arguments.get("provider", None)
        max_results = arguments.get("max_results", 20)

        url = f"{BEACONS_BASE_URL}/uniprot/summary/{accession}.json"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        structures = data.get("structures", [])
        uniprot_entry = data.get("uniprot_entry", {})

        # Apply filters
        if category_filter:
            cat_upper = category_filter.upper()
            structures = [
                s
                for s in structures
                if cat_upper in s.get("summary", {}).get("model_category", "").upper()
            ]
        if provider_filter:
            prov_lower = provider_filter.lower()
            structures = [
                s
                for s in structures
                if prov_lower in s.get("summary", {}).get("provider", "").lower()
            ]

        total_matched = len(structures)
        structures = structures[:max_results]

        # Format results
        result_structures = []
        for s in structures:
            sm = s.get("summary", {})
            entry = {
                "model_identifier": sm.get("model_identifier"),
                "model_category": sm.get("model_category"),
                "provider": sm.get("provider"),
                "coverage": sm.get("coverage"),
                "model_url": sm.get("model_url"),
                "created": sm.get("created"),
            }
            # Add resolution for experimental structures
            if sm.get("resolution"):
                entry["resolution"] = sm.get("resolution")
            # Add confidence for predicted models
            if sm.get("confidence_avg_local_score"):
                entry["confidence_avg_local_score"] = sm.get(
                    "confidence_avg_local_score"
                )
            # Add sequence range
            if sm.get("uniprot_start"):
                entry["uniprot_start"] = sm.get("uniprot_start")
                entry["uniprot_end"] = sm.get("uniprot_end")
            # Add method for experimental
            if sm.get("experimental_method"):
                entry["experimental_method"] = sm.get("experimental_method")

            result_structures.append(entry)

        return {
            "data": {
                "accession": uniprot_entry.get("ac", accession),
                "sequence_length": uniprot_entry.get("sequence_length"),
                "total_matched": total_matched,
                "returned": len(result_structures),
                "structures": result_structures,
            },
            "metadata": {
                "source": "3D Beacons Hub API",
                "accession": accession,
                "category_filter": category_filter,
                "provider_filter": provider_filter,
            },
        }
