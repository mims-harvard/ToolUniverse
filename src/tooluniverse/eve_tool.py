# eve_tool.py
"""
EVE (Evolutionary model of Variant Effect) API tool for ToolUniverse.

EVE is an unsupervised deep learning model that predicts the clinical significance
of genetic variants using evolutionary data. It was developed by Harvard Medical
School (Marks Lab) and Oxford (OATML).

EVE scores range from 0 (benign) to 1 (pathogenic).
Classification threshold: score > 0.5 indicates likely pathogenic.

Data available at: https://evemodel.org/
EVE is also integrated into Ensembl VEP API.

Reference: Frazer et al., Nature 2021
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for EVE data (evemodel.org)
EVE_BASE_URL = "https://evemodel.org"

# Ensembl VEP API for EVE scores
ENSEMBL_VEP_URL = "https://rest.ensembl.org"


@register_tool("EVETool")
class EVETool(BaseTool):
    """
    Tool for querying EVE variant effect predictions.

    EVE provides:
    - Unsupervised pathogenicity predictions trained on evolutionary data
    - Scores from 0 (benign) to 1 (pathogenic)
    - Predictions for single amino acid variants

    EVE scores complement supervised methods like ClinVar annotations.
    Uses Ensembl VEP API with EVE plugin for variant scoring.
    """

    # Classification threshold from EVE paper
    PATHOGENIC_THRESHOLD = 0.5

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_variant_score"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the EVE API call."""
        operation = self.operation

        if operation == "get_variant_score":
            return self._get_variant_score(arguments)
        elif operation == "get_gene_info":
            return self._get_gene_info(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _classify_score(self, score: float) -> str:
        """Classify EVE score."""
        if score > self.PATHOGENIC_THRESHOLD:
            return "likely_pathogenic"
        else:
            return "likely_benign"

    def _get_variant_score(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get EVE score for a variant using Ensembl VEP.

        Supports both genomic coordinates and HGVS notation.
        """
        # Support multiple input formats
        variant = arguments.get("variant")  # HGVS format: ENST00000269305.4:c.100G>A
        chrom = arguments.get("chrom")
        pos = arguments.get("pos")
        ref = arguments.get("ref")
        alt = arguments.get("alt")
        species = arguments.get("species", "human")

        try:
            if variant:
                # Use HGVS notation via VEP
                url = f"{ENSEMBL_VEP_URL}/vep/{species}/hgvs/{variant}"
                params = {"EVE": 1, "content-type": "application/json"}
            elif chrom and pos and ref and alt:
                # Use genomic coordinates
                chrom = str(chrom).replace("chr", "")
                region = f"{chrom}:{pos}:{pos}"
                allele = f"{ref}/{alt}"
                url = f"{ENSEMBL_VEP_URL}/vep/{species}/region/{region}/{allele}"
                params = {"EVE": 1, "content-type": "application/json"}
            else:
                return {
                    "status": "error",
                    "error": "Provide either 'variant' (HGVS) or 'chrom', 'pos', 'ref', 'alt'",
                }

            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 400:
                return {
                    "status": "error",
                    "error": f"Invalid variant format: {response.json().get('error', 'Unknown error')}",
                }

            response.raise_for_status()
            data = response.json()

            # Parse VEP response for EVE scores
            results = []
            for item in data:
                transcript_consequences = item.get("transcript_consequences", [])
                for tc in transcript_consequences:
                    eve_score = tc.get("eve_score")
                    if eve_score is not None:
                        # Build protein_change from amino_acids + protein_start
                        # VEP returns amino_acids as "R/L" and protein_start as 248
                        amino_acids = tc.get("amino_acids")
                        protein_start = tc.get("protein_start")
                        if amino_acids and protein_start:
                            parts = amino_acids.split("/")
                            if len(parts) == 2:
                                protein_change = (
                                    f"p.{parts[0]}{protein_start}{parts[1]}"
                                )
                            else:
                                protein_change = amino_acids
                        else:
                            protein_change = None
                        results.append(
                            {
                                "transcript_id": tc.get("transcript_id"),
                                "gene_symbol": tc.get("gene_symbol"),
                                "protein_change": protein_change,
                                "eve_score": eve_score,
                                "eve_class": tc.get("eve_class"),
                                "classification": self._classify_score(eve_score),
                                "consequence": tc.get("consequence_terms", []),
                                "polyphen_prediction": tc.get("polyphen_prediction"),
                                "sift_prediction": tc.get("sift_prediction"),
                            }
                        )

            if results:
                return {
                    "status": "success",
                    "data": {
                        "variant": variant or f"{chrom}:{pos} {ref}>{alt}",
                        "eve_scores": results,
                        "threshold": {
                            "pathogenic": f"> {self.PATHOGENIC_THRESHOLD}",
                            "benign": f"<= {self.PATHOGENIC_THRESHOLD}",
                        },
                    },
                }
            else:
                # EVE may not be available for all variants
                return {
                    "status": "success",
                    "data": {
                        "variant": variant or f"{chrom}:{pos} {ref}>{alt}",
                        "eve_scores": [],
                        "message": "No EVE scores available for this variant. EVE covers ~3,000 disease-related genes.",
                        "vep_data": data,  # Return VEP data even without EVE
                    },
                }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Ensembl VEP API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Ensembl VEP API request failed: {str(e)}",
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_gene_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if EVE scores are available for a gene.

        EVE provides predictions for ~3,000 disease-related genes.
        """
        gene_symbol = arguments.get("gene_symbol")

        if not gene_symbol:
            return {"status": "error", "error": "gene_symbol parameter is required"}

        try:
            # Query Ensembl to get gene info and check if it's covered
            url = f"{ENSEMBL_VEP_URL}/lookup/symbol/homo_sapiens/{gene_symbol}"
            params = {"content-type": "application/json"}

            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 404:
                return {
                    "status": "success",
                    "data": None,
                    "message": f"Gene '{gene_symbol}' not found in Ensembl",
                }

            response.raise_for_status()
            gene_data = response.json()

            return {
                "status": "success",
                "data": {
                    "gene_symbol": gene_symbol,
                    "ensembl_id": gene_data.get("id"),
                    "description": gene_data.get("description"),
                    "biotype": gene_data.get("biotype"),
                    "eve_note": "To get EVE scores, query specific variants using get_variant_score. EVE covers ~3,000 disease-related genes.",
                    "eve_website": f"https://evemodel.org/proteins/{gene_symbol}",
                },
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Ensembl API request failed: {str(e)}"}
