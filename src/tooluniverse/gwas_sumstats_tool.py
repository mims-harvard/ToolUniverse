"""
EBI GWAS Summary Statistics REST API tool for ToolUniverse.

Provides access to full GWAS summary statistics deposited with the
GWAS Catalog. Unlike the main GWAS Catalog (which stores curated top hits),
this API gives access to variant-level summary statistics across the
entire genome for deposited studies.

API: https://www.ebi.ac.uk/gwas/summary-statistics/api/
No authentication required.
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

GWAS_SS_BASE_URL = "https://www.ebi.ac.uk/gwas/summary-statistics/api"


@register_tool("GWASSumStatsTool")
class GWASSumStatsTool(BaseTool):
    """
    Tool for querying EBI GWAS Summary Statistics API.

    Provides full variant-level summary statistics from deposited GWAS
    studies, including effect sizes, p-values, and allele frequencies
    for specific genomic regions.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "list_studies"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the GWAS Summary Statistics API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"GWAS Summary Statistics API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to GWAS Summary Statistics API",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"GWAS Summary Statistics API error: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        dispatch_map = {
            "list_studies": self._list_studies,
            "get_trait_studies": self._get_trait_studies,
            "get_region_associations": self._get_region_associations,
        }
        handler = dispatch_map.get(self.endpoint_type)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type: {self.endpoint_type}",
            }
        return handler(arguments)

    def _list_studies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List GWAS studies with deposited summary statistics."""
        size = arguments.get("size") or arguments.get("limit") or 20

        url = f"{GWAS_SS_BASE_URL}/studies"
        params = {"size": min(size, 100)}
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        studies_raw = data.get("_embedded", {}).get("studies", [])
        studies: List[Dict[str, Any]] = []
        for entry in studies_raw:
            # Each entry may be a list with one dict, or a dict
            if isinstance(entry, list):
                for s in entry:
                    studies.append({"study_accession": s.get("study_accession")})
            elif isinstance(entry, dict):
                studies.append({"study_accession": entry.get("study_accession")})

        return {
            "status": "success",
            "data": studies,
            "metadata": {
                "source": "EBI GWAS Summary Statistics",
                "returned": len(studies),
            },
        }

    def _get_trait_studies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get studies with summary statistics for a given EFO trait."""
        trait_id = arguments.get("trait_id", "")
        if not trait_id:
            return {
                "status": "error",
                "error": "trait_id is required (e.g., 'EFO_0000249' for Alzheimer's)",
            }

        url = f"{GWAS_SS_BASE_URL}/traits/{trait_id}/studies"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"No summary statistics found for trait '{trait_id}'",
            }
        resp.raise_for_status()
        data = resp.json()

        studies_raw = data.get("_embedded", {}).get("studies", [])
        studies: List[Dict[str, Any]] = []
        for s in studies_raw:
            if isinstance(s, dict):
                studies.append({"study_accession": s.get("study_accession")})
            elif isinstance(s, list):
                for item in s:
                    studies.append({"study_accession": item.get("study_accession")})

        return {
            "status": "success",
            "data": studies,
            "metadata": {
                "source": "EBI GWAS Summary Statistics",
                "trait_id": trait_id,
                "num_studies": len(studies),
            },
        }

    def _get_region_associations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary statistics for variants in a chromosomal region."""
        chromosome = arguments.get("chromosome")
        bp_lower = arguments.get("bp_lower")
        bp_upper = arguments.get("bp_upper")
        p_upper = arguments.get("p_upper", 5e-8)
        study_accession = arguments.get("study_accession")
        size = arguments.get("size", 50)

        if not chromosome:
            return {
                "status": "error",
                "error": "chromosome is required (e.g., 19)",
            }
        if bp_lower is None or bp_upper is None:
            return {
                "status": "error",
                "error": "bp_lower and bp_upper are required",
            }

        url = f"{GWAS_SS_BASE_URL}/chromosomes/{chromosome}/associations"
        params = {
            "bp_lower": bp_lower,
            "bp_upper": bp_upper,
            "size": min(size, 1000),
        }
        if p_upper is not None:
            params["p_upper"] = p_upper
        if study_accession:
            params["study_accession"] = study_accession

        resp = requests.get(url, params=params, timeout=self.timeout)
        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"No associations found for chr{chromosome}:{bp_lower}-{bp_upper}",
            }
        resp.raise_for_status()
        data = resp.json()

        assocs_raw = data.get("_embedded", {}).get("associations", {})
        associations: List[Dict[str, Any]] = []
        for _key, v in assocs_raw.items():
            associations.append(
                {
                    "variant_id": v.get("variant_id"),
                    "chromosome": v.get("chromosome"),
                    "position": v.get("base_pair_location"),
                    "p_value": v.get("p_value"),
                    "beta": v.get("beta"),
                    "odds_ratio": v.get("odds_ratio"),
                    "effect_allele": v.get("effect_allele"),
                    "other_allele": v.get("other_allele"),
                    "effect_allele_frequency": v.get("effect_allele_frequency"),
                    "study_accession": v.get("study_accession"),
                    "trait": v.get("trait"),
                    "ci_lower": v.get("ci_lower"),
                    "ci_upper": v.get("ci_upper"),
                }
            )

        associations.sort(key=lambda x: x.get("p_value") or 1.0)

        return {
            "status": "success",
            "data": associations,
            "metadata": {
                "source": "EBI GWAS Summary Statistics",
                "region": f"chr{chromosome}:{bp_lower}-{bp_upper}",
                "p_upper_filter": p_upper,
                "num_associations": len(associations),
            },
        }
