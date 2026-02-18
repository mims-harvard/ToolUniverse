# ensembl_vep_tool.py
"""
Ensembl VEP (Variant Effect Predictor) and Variant Recoder API tools for ToolUniverse.

Ensembl VEP predicts functional consequences of genetic variants including
impact on genes, transcripts, and proteins, with SIFT/PolyPhen scores.
The Variant Recoder converts between variant identifier formats.

API: https://rest.ensembl.org/
No authentication required. Rate limited to 15 requests/second.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

ENSEMBL_BASE_URL = "https://rest.ensembl.org"
ENSEMBL_HEADERS = {"User-Agent": "ToolUniverse/1.0", "Accept": "application/json"}


@register_tool("EnsemblVEPTool")
class EnsemblVEPTool(BaseTool):
    """
    Tool for Ensembl VEP variant annotation and Variant Recoder ID conversion.

    Supports three modes:
    - vep_hgvs: Annotate variants using HGVS notation (e.g., BRAF:p.Val600Glu)
    - vep_id: Annotate variants using dbSNP rsID (e.g., rs7903146)
    - variant_recoder: Convert variant IDs between formats (rsID -> HGVS, SPDI)

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.mode = fields.get("mode", "vep_hgvs")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Ensembl VEP or Variant Recoder API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "error": f"Ensembl API request timed out after {self.timeout} seconds"
            }
        except requests.exceptions.ConnectionError:
            return {
                "error": "Failed to connect to Ensembl REST API. Check network connectivity."
            }
        except requests.exceptions.HTTPError as e:
            return {
                "error": f"Ensembl API HTTP error: {e.response.status_code} - {e.response.text[:200]}"
            }
        except Exception as e:
            return {"error": f"Unexpected error querying Ensembl: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate Ensembl endpoint based on mode."""
        if self.mode == "vep_hgvs":
            return self._vep_hgvs(arguments)
        elif self.mode == "vep_id":
            return self._vep_id(arguments)
        elif self.mode == "variant_recoder":
            return self._variant_recoder(arguments)
        else:
            return {"error": f"Unknown mode: {self.mode}"}

    def _vep_hgvs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Annotate a variant using HGVS notation."""
        hgvs = arguments.get("hgvs_notation", "")
        if not hgvs:
            return {"error": "hgvs_notation parameter is required"}

        species = arguments.get("species", "human")
        url = f"{ENSEMBL_BASE_URL}/vep/{species}/hgvs/{hgvs}"
        params = {"content-type": "application/json"}

        response = requests.get(
            url, params=params, headers=ENSEMBL_HEADERS, timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        if isinstance(data, list) and data:
            result = data[0]
            return {
                "data": self._format_vep_result(result),
                "metadata": {
                    "source": "Ensembl VEP",
                    "species": species,
                    "input": hgvs,
                    "api_version": "REST",
                },
            }
        return {
            "data": {},
            "metadata": {
                "source": "Ensembl VEP",
                "species": species,
                "input": hgvs,
                "num_results": 0,
            },
        }

    def _vep_id(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Annotate a variant using dbSNP rsID."""
        variant_id = arguments.get("variant_id", "")
        if not variant_id:
            return {"error": "variant_id parameter is required"}

        species = arguments.get("species", "human")
        url = f"{ENSEMBL_BASE_URL}/vep/{species}/id/{variant_id}"
        params = {"content-type": "application/json"}

        response = requests.get(
            url, params=params, headers=ENSEMBL_HEADERS, timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        if isinstance(data, list) and data:
            result = data[0]
            return {
                "data": self._format_vep_result(result),
                "metadata": {
                    "source": "Ensembl VEP",
                    "species": species,
                    "input": variant_id,
                    "api_version": "REST",
                },
            }
        return {
            "data": {},
            "metadata": {
                "source": "Ensembl VEP",
                "species": species,
                "input": variant_id,
                "num_results": 0,
            },
        }

    def _variant_recoder(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Convert variant identifiers between formats."""
        variant_id = arguments.get("variant_id", "")
        if not variant_id:
            return {"error": "variant_id parameter is required"}

        species = arguments.get("species", "human")
        url = f"{ENSEMBL_BASE_URL}/variant_recoder/{species}/{variant_id}"
        params = {"content-type": "application/json"}

        response = requests.get(
            url, params=params, headers=ENSEMBL_HEADERS, timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()

        # Variant recoder returns list of dicts, each with allele keys
        alleles = []
        if isinstance(data, list):
            for entry in data:
                for allele_key, allele_info in entry.items():
                    if allele_key == "warnings":
                        continue
                    if isinstance(allele_info, dict):
                        alleles.append(
                            {
                                "allele": allele_key,
                                "input": allele_info.get("input", variant_id),
                                "id": allele_info.get("id", []),
                                "hgvsg": allele_info.get("hgvsg", []),
                                "hgvsc": allele_info.get("hgvsc", []),
                                "hgvsp": allele_info.get("hgvsp", []),
                                "spdi": allele_info.get("spdi", []),
                            }
                        )

        return {
            "data": alleles,
            "metadata": {
                "source": "Ensembl Variant Recoder",
                "species": species,
                "input": variant_id,
                "num_alleles": len(alleles),
            },
        }

    def _format_vep_result(self, result: Dict) -> Dict[str, Any]:
        """Format a VEP result to extract key information."""
        # Extract most informative transcript consequences
        transcript_consequences = []
        for tc in result.get("transcript_consequences", []):
            formatted = {
                "gene_symbol": tc.get("gene_symbol"),
                "gene_id": tc.get("gene_id"),
                "transcript_id": tc.get("transcript_id"),
                "biotype": tc.get("biotype"),
                "consequence_terms": tc.get("consequence_terms", []),
                "impact": tc.get("impact"),
                "amino_acids": tc.get("amino_acids"),
                "codons": tc.get("codons"),
                "protein_start": tc.get("protein_start"),
                "protein_end": tc.get("protein_end"),
                "sift_prediction": tc.get("sift_prediction"),
                "sift_score": tc.get("sift_score"),
                "polyphen_prediction": tc.get("polyphen_prediction"),
                "polyphen_score": tc.get("polyphen_score"),
                "strand": tc.get("strand"),
            }
            # Remove None values for cleaner output
            formatted = {k: v for k, v in formatted.items() if v is not None}
            transcript_consequences.append(formatted)

        # Extract colocated variants (known variants at this position)
        colocated = []
        for cv in result.get("colocated_variants", []):
            colocated.append(
                {
                    "id": cv.get("id"),
                    "allele_string": cv.get("allele_string"),
                    "frequencies": cv.get("frequencies"),
                }
            )

        return {
            "input": result.get("input") or result.get("id"),
            "assembly_name": result.get("assembly_name"),
            "seq_region_name": result.get("seq_region_name"),
            "start": result.get("start"),
            "end": result.get("end"),
            "strand": result.get("strand"),
            "allele_string": result.get("allele_string"),
            "most_severe_consequence": result.get("most_severe_consequence"),
            "transcript_consequences": transcript_consequences,
            "colocated_variants": colocated[:10],  # Limit to avoid huge responses
        }
