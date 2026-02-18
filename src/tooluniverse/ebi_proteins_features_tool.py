# ebi_proteins_features_tool.py
"""
EBI Proteins API Feature Categories tool for ToolUniverse.

Provides access to specific feature categories from the EBI Proteins API:
- DOMAINS_AND_SITES: binding sites, DNA binding regions, motifs, regions
- MOLECULE_PROCESSING: signal peptides, transit peptides, chains, propeptides
- STRUCTURAL: secondary structure assignments (helix, strand, turn)

API: https://www.ebi.ac.uk/proteins/api/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool


PROTEINS_API_BASE_URL = "https://www.ebi.ac.uk/proteins/api"


class EBIProteinsFeaturesTool(BaseTool):
    """
    Tool for retrieving category-specific protein features from EBI Proteins API.

    Different from EBIProteinsExtTool (mutagenesis, PTM) - this covers
    domain/site annotations, molecule processing info, and secondary structure.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.category = fields.get("category", "DOMAINS_AND_SITES")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the EBI Proteins API features call."""
        try:
            return self._get_features(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"EBI Proteins API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to EBI Proteins API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                return {"error": f"Protein not found: {arguments.get('accession', '')}"}
            return {"error": f"EBI Proteins API HTTP error: {code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying EBI Proteins API: {str(e)}"}

    def _get_features(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get features for a specific category."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "error": "accession parameter is required (UniProt accession, e.g., P04637)"
            }

        url = f"{PROTEINS_API_BASE_URL}/features/{accession}"
        params = {"categories": self.category}
        headers = {"Accept": "application/json"}
        response = requests.get(
            url, params=params, headers=headers, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        features = []
        for f in data.get("features", []):
            feature = {
                "type": f.get("type"),
                "position_start": f.get("begin"),
                "position_end": f.get("end"),
                "description": f.get("description"),
            }

            # Include evidences (compact)
            evidences = []
            for ev in f.get("evidences", [])[:3]:
                src = ev.get("source", {})
                evidences.append(
                    {
                        "code": ev.get("code"),
                        "source": src.get("name"),
                        "id": src.get("id"),
                    }
                )
            if evidences:
                feature["evidences"] = evidences

            features.append(feature)

        # Get feature type distribution
        type_counts = {}
        for f in data.get("features", []):
            ft = f.get("type", "UNKNOWN")
            type_counts[ft] = type_counts.get(ft, 0) + 1

        # Determine source label
        category_labels = {
            "DOMAINS_AND_SITES": "Domain/Site Features",
            "MOLECULE_PROCESSING": "Molecule Processing",
            "STRUCTURAL": "Secondary Structure",
        }

        return {
            "data": {
                "accession": data.get("accession"),
                "entry_name": data.get("entryName"),
                "sequence_length": len(data.get("sequence", "")),
                "features": features[:100],
                "total_features": len(data.get("features", [])),
                "feature_type_counts": type_counts,
            },
            "metadata": {
                "source": f"EBI Proteins API - {category_labels.get(self.category, self.category)}",
                "accession": accession,
                "category": self.category,
            },
        }
