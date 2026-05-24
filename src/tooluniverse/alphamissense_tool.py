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

from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for AlphaMissense API (hegelab.org)
ALPHAMISSENSE_BASE_URL = "https://alphamissense.hegelab.org"
UNIPROT_FASTA_URL = "https://rest.uniprot.org/uniprotkb/{accession}.fasta"


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

    def _fetch_protein_length(self, uniprot_id: str) -> Optional[int]:
        """Get protein length from UniProt FASTA."""
        try:
            r = requests.get(UNIPROT_FASTA_URL.format(accession=uniprot_id), timeout=15)
            if r.status_code != 200:
                return None
            lines = r.text.strip().splitlines()
            return len("".join(lines[1:]))
        except requests.exceptions.RequestException:
            return None

    def _fetch_single_residue(
        self, uniprot_id: str, position: int
    ) -> Optional[Dict[str, Any]]:
        """Fetch one residue's AlphaMissense scores; returns None on error."""
        try:
            r = requests.get(
                f"{ALPHAMISSENSE_BASE_URL}/hotspotapi",
                params={"uid": uniprot_id, "resi": position},
                timeout=self.timeout,
            )
            if r.status_code != 200:
                return None
            return r.json()
        except requests.exceptions.RequestException:
            return None

    def _get_protein_scores(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get AlphaMissense scores for every residue of a protein.

        The hegelab AlphaMissense API only supports per-residue queries — there
        is no whole-protein dump endpoint. This method abstracts that by:
          1. Looking up the protein length from UniProt FASTA
          2. Fetching all residues concurrently via a thread pool
          3. Returning the aggregated per-position records

        Set max_residues to cap the loop if you only want a partial protein
        (e.g. for fast diagnostic calls). max_residues=0 (the default) means
        no cap — fetch every residue.
        """
        uniprot_id = arguments.get("uniprot_id")
        if not uniprot_id:
            return {"status": "error", "error": "uniprot_id parameter is required"}

        max_residues = arguments.get("max_residues", 0)
        try:
            max_residues = int(max_residues) if max_residues else 0
        except (TypeError, ValueError):
            max_residues = 0

        # 1. Protein length from UniProt
        protein_length = self._fetch_protein_length(uniprot_id)
        if protein_length is None:
            return {
                "status": "error",
                "error": (
                    f"Could not fetch UniProt sequence length for '{uniprot_id}'. "
                    f"Verify the accession is correct."
                ),
            }

        positions = list(range(1, protein_length + 1))
        if max_residues and max_residues < len(positions):
            positions = positions[:max_residues]

        # 2. Concurrent per-residue fetch
        scores: List[Optional[Dict[str, Any]]] = [None] * len(positions)
        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_idx = {
                executor.submit(self._fetch_single_residue, uniprot_id, p): i
                for i, p in enumerate(positions)
            }
            for fut in as_completed(future_to_idx):
                idx = future_to_idx[fut]
                try:
                    scores[idx] = fut.result()
                except Exception:
                    scores[idx] = None

        n_fetched = sum(1 for s in scores if s is not None)
        if n_fetched == 0:
            pdb_url = f"{ALPHAMISSENSE_BASE_URL}/pdb/AF-{uniprot_id}-F1-AM_v4.pdb"
            return {
                "status": "error",
                "error": (
                    f"No AlphaMissense data found for '{uniprot_id}' "
                    f"(tried {len(positions)} positions, all returned non-200). "
                    f"The protein may not be in the AlphaMissense database."
                ),
                "pdb_download": pdb_url,
            }

        # 3. Aggregate into per-position list (drop Nones from failed positions)
        per_position = [
            {"position": p, **(s or {})}
            for p, s in zip(positions, scores)
            if s is not None
        ]

        return {
            "status": "success",
            "data": {
                "uniprot_id": uniprot_id,
                "protein_length": protein_length,
                "scores": per_position,
                "n_positions_returned": n_fetched,
                "n_positions_attempted": len(positions),
                "max_residues_cap": max_residues if max_residues else None,
                "thresholds": {
                    "pathogenic": f"> {self.PATHOGENIC_THRESHOLD}",
                    "ambiguous": f"{self.BENIGN_THRESHOLD} - {self.PATHOGENIC_THRESHOLD}",
                    "benign": f"< {self.BENIGN_THRESHOLD}",
                },
                "pdb_download": f"{ALPHAMISSENSE_BASE_URL}/pdb/AF-{uniprot_id}-F1-AM_v4.pdb",
            },
        }

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
