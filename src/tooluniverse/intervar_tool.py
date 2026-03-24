"""
InterVar Tool

InterVar implements the ACMG/AMP 2015 standards and guidelines for germline variant
interpretation. Given a genomic variant (chromosome, position, ref, alt), it returns
an ACMG/AMP classification (Pathogenic, Likely Pathogenic, Uncertain Significance,
Likely Benign, Benign) together with the evidence criteria that contributed to the
classification (PVS1, PS1-PS4, PM1-PM6, PP1-PP5, BA1, BP1-BP7, BS1-BS4).

API: http://wintervar.wglab.org/api_new.php
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

INTERVAR_BASE_URL = "http://wintervar.wglab.org/api_new.php"

# ACMG criteria descriptions for user-friendly output
CRITERIA_DESCRIPTIONS = {
    "PVS1": "Null variant in gene where LOF is disease mechanism",
    "PS1": "Same amino acid change as established pathogenic variant",
    "PS2": "De novo variant (confirmed parentage)",
    "PS3": "Well-established functional studies support damaging effect",
    "PS4": "Variant prevalence significantly increased in cases vs controls",
    "PM1": "Located in mutational hot spot / critical domain without benign variation",
    "PM2": "Absent or at extremely low frequency in population databases",
    "PM3": "Detected in trans with pathogenic variant for recessive disorder",
    "PM4": "Protein length changes due to in-frame indels or stop-loss",
    "PM5": "Novel missense at position where different pathogenic missense known",
    "PM6": "Assumed de novo without confirmation of parentage",
    "PP1": "Co-segregation with disease in multiple affected family members",
    "PP2": "Missense in gene with low rate of benign missense and pathogenic missense common",
    "PP3": "Multiple computational evidence supporting deleterious effect",
    "PP4": "Patient phenotype or family history highly specific for gene",
    "PP5": "Reputable source recently reports variant as pathogenic",
    "BA1": "Allele frequency > 5% in population databases",
    "BP1": "Missense variant in gene where only truncating variants cause disease",
    "BP2": "Observed in trans with pathogenic variant for dominant OR in cis with pathogenic",
    "BP3": "In-frame indels in repetitive region without known function",
    "BP4": "Multiple computational evidence suggest no impact on gene/gene product",
    "BP5": "Variant found in case with alternate molecular basis for disease",
    "BP6": "Reputable source recently reports variant as benign",
    "BP7": "Synonymous variant with no predicted splice impact",
    "BS1": "Allele frequency greater than expected for disorder",
    "BS2": "Observed in healthy adult with full penetrance expected at early age",
    "BS3": "Well-established functional studies show no damaging effect",
    "BS4": "Lack of co-segregation in affected members of family",
}


@register_tool("InterVarTool")
class InterVarTool(BaseTool):
    """
    InterVar: ACMG/AMP 2015 germline variant interpretation tool.

    Classifies germline variants as:
      Pathogenic | Likely Pathogenic | Uncertain Significance |
      Likely Benign | Benign

    according to the ACMG/AMP 2015 standards and guidelines.
    Returns individual evidence criteria (PVS1, PS1-PS4, PM1-PM6, PP1-PP5,
    BA1, BP1-BP7, BS1-BS4) with their activation status.

    Input: genomic coordinates (chr, pos, ref, alt) in hg19 or hg38.
    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get("operation", "classify")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        op = self.operation
        if op == "classify":
            return self._classify_variant(arguments)
        return {"status": "error", "error": f"Unknown operation: {op}"}

    @staticmethod
    def _parse_variant_args(arguments: Dict[str, Any]):
        """Parse and validate genomic variant arguments. Returns (params, error_dict_or_None)."""
        chrom = str(arguments.get("chrom", "")).replace("chr", "").strip()
        pos = arguments.get("pos")
        ref = str(arguments.get("ref", "")).strip().upper()
        alt = str(arguments.get("alt", "")).strip().upper()
        build = arguments.get("build", "hg19")

        if not chrom:
            return None, {"status": "error", "error": "chrom parameter is required"}
        if pos is None:
            return None, {"status": "error", "error": "pos parameter is required"}
        if not ref:
            return None, {"status": "error", "error": "ref parameter is required"}
        if not alt:
            return None, {"status": "error", "error": "alt parameter is required"}
        if build not in ("hg19", "hg38"):
            return None, {
                "status": "error",
                "error": f"Invalid build '{build}'. Must be 'hg19' or 'hg38'.",
            }

        params = {
            "queryType": "position",
            "build": build,
            "chr": chrom,
            "pos": int(pos),
            "ref": ref,
            "alt": alt,
        }
        return params, None

    def _classify_variant(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        params, err = self._parse_variant_args(arguments)
        if err:
            return err

        try:
            resp = requests.get(INTERVAR_BASE_URL, params=params, timeout=self.timeout)
            resp.raise_for_status()
            raw = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"InterVar API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"InterVar API request failed: {e}"}
        except Exception as e:
            return {"status": "error", "error": f"Failed to parse response: {e}"}

        if not isinstance(raw, dict) or "Intervar" not in raw:
            return {
                "status": "error",
                "error": "Unexpected response format from InterVar API",
                "raw": raw,
            }

        classification = raw["Intervar"]
        activated = {k: bool(v) for k, v in raw.items() if k in CRITERIA_DESCRIPTIONS}
        active_criteria = [k for k, v in activated.items() if v]

        return {
            "status": "success",
            "data": {
                "classification": classification,
                "variant": {
                    "chromosome": raw.get("Chromosome"),
                    "position": raw.get("Position"),
                    "ref_allele": raw.get("Ref_allele"),
                    "alt_allele": raw.get("Alt_allele"),
                    "gene": raw.get("Gene"),
                    "build": raw.get("Build"),
                },
                "active_criteria": active_criteria,
                "criteria_detail": {
                    k: {
                        "active": activated[k],
                        "description": CRITERIA_DESCRIPTIONS[k],
                    }
                    for k in activated
                },
            },
            "metadata": {
                "source": "InterVar (wintervar.wglab.org)",
                "guideline": "ACMG/AMP 2015 Standards and Guidelines",
                "classification_categories": [
                    "Pathogenic",
                    "Likely pathogenic",
                    "Uncertain significance",
                    "Likely benign",
                    "Benign",
                ],
            },
        }
