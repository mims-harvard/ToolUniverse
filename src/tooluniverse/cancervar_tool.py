"""
CancerVar Tool

CancerVar implements the AMP/ASCO/CAP 2017 guidelines for clinical interpretation of
somatic variants in cancer. Given a genomic variant (chromosome, position, ref, alt),
it returns a tier classification (Tier I–IV) together with all AMP/ASCO/CAP Biomarker
Prioritization (CBP) criteria scores and an oncogenicity index (OPAI).

Tiers:
  Tier I   – Variants of Strong Clinical Significance
  Tier II  – Variants of Potential Clinical Significance
  Tier III – Variants of Unknown Clinical Significance
  Tier IV  – Benign or Likely Benign Variants

API: http://cancervar.wglab.org/api_new.php
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool
from .intervar_tool import InterVarTool

CANCERVAR_BASE_URL = "http://cancervar.wglab.org/api_new.php"

# AMP/ASCO/CAP CBP criteria descriptions
CBP_DESCRIPTIONS = {
    "CBP_1": "FDA-approved or well-established therapeutic association (same cancer type)",
    "CBP_2": "FDA-approved or well-established therapeutic association (different cancer type)",
    "CBP_3": "Evidence from well-powered studies with consensus (investigational biomarker)",
    "CBP_4": "Evidence from multiple small studies (investigational biomarker, same cancer type)",
    "CBP_5": "Preclinical studies only",
    "CBP_6": "No evidence for oncogenic function",
    "CBP_7": "Listed in cancer mutation hotspot databases",
    "CBP_8": "Observed in functional domain with established cancer mechanism",
    "CBP_9": "Population allele frequency (0=common, 1=rare, 2=absent/very rare)",
    "CBP_10": "Predicted damaging by computational tools",
    "CBP_11": "Listed as somatic mutation in cancer databases (COSMIC, cBioPortal)",
    "CBP_12": "Literature-reported as somatic mutation in cancer",
}

TIER_DESCRIPTIONS = {
    "Tier_I_strong": "Tier I – Variants of Strong Clinical Significance (FDA-approved or well-established)",
    "Tier_II_potential": "Tier II – Variants of Potential Clinical Significance (investigational/preclinical evidence)",
    "Tier_III_unknown": "Tier III – Variants of Unknown Clinical Significance",
    "Tier_IV_benign": "Tier IV – Benign or Likely Benign Variants",
}


@register_tool("CancerVarTool")
class CancerVarTool(BaseTool):
    """
    CancerVar: AMP/ASCO/CAP 2017 somatic variant interpretation tool.

    Classifies somatic cancer variants into four tiers per the AMP/ASCO/CAP 2017
    guidelines: Tier I (strong clinical significance), Tier II (potential clinical
    significance), Tier III (unknown significance), Tier IV (benign/likely benign).

    Returns all 12 CBP criteria scores, the tier assignment, and the Oncogenicity
    Pathogenicity Index (OPAI, 0–1).

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

    def _classify_variant(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        params, err = InterVarTool._parse_variant_args(arguments)
        if err:
            return err

        try:
            resp = requests.get(CANCERVAR_BASE_URL, params=params, timeout=self.timeout)
            resp.raise_for_status()
            raw = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"CancerVar API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"CancerVar API request failed: {e}"}
        except Exception as e:
            return {"status": "error", "error": f"Failed to parse response: {e}"}

        if not isinstance(raw, dict) or "Cancervar" not in raw:
            return {
                "status": "error",
                "error": "Unexpected response format from CancerVar API",
                "raw": raw,
            }

        cancervar_str = raw["Cancervar"]
        tier_label = cancervar_str
        tier_score = None
        if "#" in cancervar_str:
            parts = cancervar_str.split("#", 1)
            try:
                tier_score = int(parts[0])
            except ValueError:
                pass
            tier_label = parts[1] if len(parts) > 1 else cancervar_str

        tier_description = TIER_DESCRIPTIONS.get(tier_label, tier_label)

        cbp_criteria = {
            k: {"value": raw.get(k), "description": CBP_DESCRIPTIONS.get(k, k)}
            for k in CBP_DESCRIPTIONS
            if k in raw
        }

        opai = raw.get("OPAI")

        return {
            "status": "success",
            "data": {
                "tier": tier_label,
                "tier_score": tier_score,
                "tier_description": tier_description,
                "opai": opai,
                "variant": {
                    "chromosome": raw.get("Chromosome"),
                    "position": raw.get("Position"),
                    "ref_allele": raw.get("Ref_allele"),
                    "alt_allele": raw.get("Alt_allele"),
                    "gene": raw.get("Gene"),
                    "build": raw.get("Build"),
                },
                "cbp_criteria": cbp_criteria,
            },
            "metadata": {
                "source": "CancerVar (cancervar.wglab.org)",
                "guideline": "AMP/ASCO/CAP 2017 Standards and Guidelines",
                "tier_categories": list(TIER_DESCRIPTIONS.values()),
                "opai_range": "0.0–1.0 (higher = more likely oncogenic/pathogenic)",
            },
        }
