# alphamissense_tool.py
"""
AlphaMissense API tool for ToolUniverse.

AlphaMissense is DeepMind's deep learning model for predicting the pathogenicity
of missense variants. It provides pathogenicity classifications for ~71 million
possible single amino acid substitutions in the human proteome.

Classifications:
- Pathogenic: score > 0.564
- Ambiguous: 0.34 <= score <= 0.564
- Benign: score < 0.34

API Documentation: https://alphamissense.hegelab.org/
Data Source: Cheng et al., Science 2023
"""

import requests
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for AlphaMissense API (hegelab.org)
ALPHAMISSENSE_BASE_URL = "https://alphamissense.hegelab.org"


@register_tool("AlphaMissenseTool")
class AlphaMissenseTool(BaseTool):
    """
    Tool for querying AlphaMissense pathogenicity predictions.

    AlphaMissense uses deep learning trained on evolutionary data to predict
    the pathogenicity of all possible single amino acid substitutions in human proteins.

    Classification thresholds:
    - Pathogenic: score > 0.564
    - Ambiguous: 0.34 <= score <= 0.564
    - Benign: score < 0.34

    No authentication required. Free for academic/research use.
    """

    # Classification thresholds from the AlphaMissense paper
    PATHOGENIC_THRESHOLD = 0.564
    BENIGN_THRESHOLD = 0.34

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_protein_scores"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the AlphaMissense API call."""
        operation = self.operation

        if operation == "get_protein_scores":
            return self._get_protein_scores(arguments)
        elif operation == "get_variant_score":
            return self._get_variant_score(arguments)
        elif operation == "get_residue_scores":
            return self._get_residue_scores(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _classify_score(self, score: float) -> str:
        """Classify pathogenicity based on AlphaMissense thresholds."""
        if score > self.PATHOGENIC_THRESHOLD:
            return "pathogenic"
        elif score < self.BENIGN_THRESHOLD:
            return "benign"
        else:
            return "ambiguous"

    def _get_protein_scores(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get AlphaMissense scores for a protein by UniProt ID.

        Note: The AlphaMissense API requires querying individual residue positions.
        This method demonstrates access to the data by sampling the first position.
        For complete protein-wide analysis, use get_residue_scores for each position.
        """
        uniprot_id = arguments.get("uniprot_id")

        if not uniprot_id:
            return {"status": "error", "error": "uniprot_id parameter is required"}

        try:
            # Sample query at position 1 to verify protein exists and get format
            url = f"{ALPHAMISSENSE_BASE_URL}/hotspotapi"
            params = {"uid": uniprot_id, "resi": 1}

            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 404:
                return {
                    "status": "success",
                    "data": None,
                    "message": f"No AlphaMissense data found for UniProt ID: {uniprot_id}",
                }

            # For 400 errors, try a few different positions as protein might not start at position 1
            if response.status_code == 400:
                # Try position 10 as some proteins don't have data at position 1
                for test_pos in [10, 50, 100]:
                    params = {"uid": uniprot_id, "resi": test_pos}
                    response = requests.get(url, params=params, timeout=self.timeout)
                    if response.status_code == 200:
                        break

                # If still failing after trying multiple positions
                if response.status_code != 200:
                    return {
                        "status": "error",
                        "error": f"AlphaMissense API returned 400 Bad Request. The UniProt ID '{uniprot_id}' may not be available in AlphaMissense database, or the protein sequence may have no annotated residues.",
                    }

            response.raise_for_status()
            data = response.json()

            # Get structure file info for comprehensive data access
            pdb_url = f"{ALPHAMISSENSE_BASE_URL}/pdb/AF-{uniprot_id}-F1-AM_v4.pdb"

            return {
                "status": "success",
                "data": {
                    "uniprot_id": uniprot_id,
                    "sample_residue": data.get("resi", params["resi"]),
                    "sample_data": data,
                    "access_info": {
                        "note": "AlphaMissense API requires per-residue queries. Use AlphaMissense_get_residue_scores for specific positions.",
                        "pdb_download": pdb_url,
                        "api_endpoint": f"{ALPHAMISSENSE_BASE_URL}/hotspotapi?uid={uniprot_id}&resi=POSITION",
                    },
                    "thresholds": {
                        "pathogenic": f"> {self.PATHOGENIC_THRESHOLD}",
                        "ambiguous": f"{self.BENIGN_THRESHOLD} - {self.PATHOGENIC_THRESHOLD}",
                        "benign": f"< {self.BENIGN_THRESHOLD}",
                    },
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"AlphaMissense API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"AlphaMissense API request failed: {str(e)}",
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_variant_score(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get AlphaMissense pathogenicity score for a specific variant.

        Variant format: p.X123Y where X is reference amino acid, 123 is position,
        and Y is the variant amino acid.
        """
        uniprot_id = arguments.get("uniprot_id")
        variant = arguments.get("variant")

        if not uniprot_id:
            return {"status": "error", "error": "uniprot_id parameter is required"}
        if not variant:
            return {
                "status": "error",
                "error": "variant parameter is required (e.g., 'p.R123H' or 'R123H')",
            }

        # Parse variant notation
        variant_clean = variant.replace("p.", "").strip()

        try:
            # Extract position from variant (e.g., "R123H" -> 123)
            import re

            match = re.match(r"([A-Z])(\d+)([A-Z])", variant_clean)
            if not match:
                return {
                    "status": "error",
                    "error": f"Invalid variant format: {variant}. Expected format: p.X123Y or X123Y (e.g., p.R123H)",
                }

            ref_aa = match.group(1)
            position = int(match.group(2))
            alt_aa = match.group(3)

            # Query the API
            url = f"{ALPHAMISSENSE_BASE_URL}/hotspotapi"
            params = {"uid": uniprot_id, "resi": position}

            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 404:
                return {
                    "status": "success",
                    "data": None,
                    "message": f"No AlphaMissense data found for {uniprot_id} position {position}",
                }

            response.raise_for_status()
            data = response.json()

            # Look for the specific variant in the response
            score = None
            if isinstance(data, dict):
                # API may return different formats
                scores = data.get("scores", data.get("data", {}))
                if isinstance(scores, dict):
                    score = scores.get(alt_aa)
                elif isinstance(scores, list):
                    for item in scores:
                        if item.get("aa") == alt_aa or item.get("variant") == alt_aa:
                            score = item.get("score", item.get("am_pathogenicity"))
                            break

            if score is not None:
                classification = self._classify_score(score)
                return {
                    "status": "success",
                    "data": {
                        "uniprot_id": uniprot_id,
                        "variant": f"p.{ref_aa}{position}{alt_aa}",
                        "position": position,
                        "reference_aa": ref_aa,
                        "variant_aa": alt_aa,
                        "pathogenicity_score": score,
                        "classification": classification,
                        "thresholds": {
                            "pathogenic": f"> {self.PATHOGENIC_THRESHOLD}",
                            "ambiguous": f"{self.BENIGN_THRESHOLD} - {self.PATHOGENIC_THRESHOLD}",
                            "benign": f"< {self.BENIGN_THRESHOLD}",
                        },
                    },
                }
            else:
                return {
                    "status": "success",
                    "data": {
                        "uniprot_id": uniprot_id,
                        "variant": f"p.{ref_aa}{position}{alt_aa}",
                        "raw_response": data,
                        "message": "Score extraction requires parsing API response format",
                    },
                }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"AlphaMissense API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"AlphaMissense API request failed: {str(e)}",
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_residue_scores(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get AlphaMissense scores for all possible substitutions at a specific residue.

        Returns scores for all 20 amino acid substitutions at the given position.
        """
        uniprot_id = arguments.get("uniprot_id")
        position = arguments.get("position")

        if not uniprot_id:
            return {"status": "error", "error": "uniprot_id parameter is required"}
        if not position:
            return {"status": "error", "error": "position parameter is required"}

        try:
            position = int(position)
        except (ValueError, TypeError):
            return {"status": "error", "error": "position must be an integer"}

        try:
            url = f"{ALPHAMISSENSE_BASE_URL}/hotspotapi"
            params = {"uid": uniprot_id, "resi": position}

            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 404:
                return {
                    "status": "success",
                    "data": None,
                    "message": f"No AlphaMissense data found for {uniprot_id} position {position}",
                }

            response.raise_for_status()
            data = response.json()

            return {
                "status": "success",
                "data": {
                    "uniprot_id": uniprot_id,
                    "position": position,
                    "scores": data,
                    "thresholds": {
                        "pathogenic": f"> {self.PATHOGENIC_THRESHOLD}",
                        "ambiguous": f"{self.BENIGN_THRESHOLD} - {self.PATHOGENIC_THRESHOLD}",
                        "benign": f"< {self.BENIGN_THRESHOLD}",
                    },
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"AlphaMissense API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"AlphaMissense API request failed: {str(e)}",
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
