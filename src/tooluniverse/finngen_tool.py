"""
FinnGen REST API tool for ToolUniverse.

FinnGen is a large-scale Finnish genomics initiative combining genome
data from Finnish biobanks with health registry data. It provides GWAS
summary statistics for >2,400 disease endpoints across ~500,000 Finns.

API: https://r12.finngen.fi/api/
No authentication required. Free for all use.
Release 12 (current): 486,367 participants.
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

FINNGEN_BASE_URL = "https://r12.finngen.fi/api"


@register_tool("FinnGenTool")
class FinnGenTool(BaseTool):
    """
    Tool for querying FinnGen, the Finnish population genomics study.

    Provides access to phenotype metadata, variant fine-mapping regions,
    and regional GWAS associations for 2,470 disease endpoints from
    the Finnish biobank.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "list_phenotypes"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the FinnGen API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"FinnGen API request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to FinnGen API",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"FinnGen API error: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        dispatch_map = {
            "list_phenotypes": self._list_phenotypes,
            "get_phenotype": self._get_phenotype,
            "get_variant_finemapping": self._get_variant_finemapping,
            "get_region_associations": self._get_region_associations,
        }
        handler = dispatch_map.get(self.endpoint_type)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type: {self.endpoint_type}",
            }
        return handler(arguments)

    def _list_phenotypes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List/search FinnGen phenotypes."""
        query = (arguments.get("query") or "").lower()
        category = (arguments.get("category") or "").lower()
        min_cases = arguments.get("min_cases")
        limit = arguments.get("limit", 50)

        url = f"{FINNGEN_BASE_URL}/phenos"
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        all_phenos = resp.json()

        results = []
        for p in all_phenos:
            if query:
                searchable = f"{p.get('phenocode', '')} {p.get('phenostring', '')} {p.get('category', '')}".lower()
                if query not in searchable:
                    continue
            if category:
                # Match against human-readable category name OR phenocode prefix
                # e.g. "C3_" matches phenocodes starting with "C3_"; "Neoplasms" matches category name
                phenocode = p.get("phenocode", "").lower()
                cat_name = p.get("category", "").lower()
                if category not in cat_name and not phenocode.startswith(category):
                    continue
            if min_cases and p.get("num_cases", 0) < min_cases:
                continue
            results.append(
                {
                    "phenocode": p.get("phenocode"),
                    "phenostring": p.get("phenostring"),
                    "category": p.get("category"),
                    "num_cases": p.get("num_cases"),
                    "num_controls": p.get("num_controls"),
                    "num_gw_significant": p.get("num_gw_significant"),
                }
            )

        results.sort(key=lambda x: x.get("num_cases", 0), reverse=True)
        total = len(results)
        results = results[:limit]

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "FinnGen r12",
                "total_matching": total,
                "returned": len(results),
                "total_phenotypes": len(all_phenos),
            },
        }

    def _get_phenotype(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get details for a specific FinnGen phenotype."""
        phenocode = arguments.get("phenocode", "")
        if not phenocode:
            return {"status": "error", "error": "phenocode is required"}

        url = f"{FINNGEN_BASE_URL}/pheno/{phenocode}"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"Phenotype '{phenocode}' not found in FinnGen",
            }
        resp.raise_for_status()
        data = resp.json()

        result = {
            "phenocode": data.get("phenocode"),
            "phenostring": data.get("phenostring"),
            "category": data.get("category"),
            "num_cases": data.get("num_cases"),
            "num_controls": data.get("num_controls"),
            "num_gw_significant": data.get("num_gw_significant"),
            "num_cases_prev": data.get("num_cases_prev"),
            "num_controls_prev": data.get("num_controls_prev"),
            "gc_lambda": data.get("gc_lambda"),
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "FinnGen r12",
                "release": "R12 (486,367 participants)",
            },
        }

    def _get_variant_finemapping(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get fine-mapping regions associated with a genomic variant."""
        variant = arguments.get("variant", "")
        if not variant:
            return {
                "status": "error",
                "error": "variant is required (format: chr:pos:ref:alt, e.g. 19:44908684:T:C)",
            }

        # Normalize separators: accept chr-pos-ref-alt or chr:pos:ref:alt
        variant = variant.replace("-", ":")

        url = f"{FINNGEN_BASE_URL}/variant/{variant}"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"Variant '{variant}' not found in FinnGen",
            }
        resp.raise_for_status()
        data = resp.json()

        parsed_regions: List[Dict[str, Any]] = [
            {
                "phenocode": r.get("phenocode"),
                "chromosome": r.get("chr"),
                "start": r.get("start"),
                "end": r.get("end"),
                "type": r.get("type"),
            }
            for r in data.get("regions", [])
        ]

        return {
            "status": "success",
            "data": parsed_regions,
            "metadata": {
                "source": "FinnGen r12",
                "variant": variant,
                "total_regions": len(parsed_regions),
            },
        }

    def _get_region_associations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get regional association data for a phenotype in a genomic region."""
        phenocode = arguments.get("phenocode", "")
        region = arguments.get("region", "")
        if not phenocode or not region:
            return {
                "status": "error",
                "error": "Both phenocode and region are required. region format: chr:start-end (e.g. 9:22000000-22200000)",
            }

        url = f"{FINNGEN_BASE_URL}/region/{phenocode}/{region}"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"No data for phenotype '{phenocode}' in region '{region}'",
            }
        resp.raise_for_status()
        data = resp.json()

        pheno_info = data.get("phenotype", {})
        region_info = data.get("region", {})
        summaries = data.get("region_summary", [])

        # Parse credible sets from the summaries
        credible_sets: List[Dict[str, Any]] = []
        for summary in summaries:
            region_id = summary.get("region_id")
            for cs in summary.get("credible_sets", []):
                lead_variants = cs.get("lead_variants", [])
                parsed_leads = []
                for lv in lead_variants:
                    parsed_leads.append(
                        {
                            "variant_id": lv.get("id"),
                            "rsid": lv.get("rsid"),
                            "chromosome": lv.get("chr"),
                            "position": lv.get("position"),
                            "ref": lv.get("ref"),
                            "alt": lv.get("alt"),
                            "maf": lv.get("maf"),
                            "posterior_probability": lv.get("prob"),
                            "credible_set": lv.get("cs"),
                        }
                    )
                credible_sets.append(
                    {
                        "region_id": region_id,
                        "chromosome": cs.get("chr"),
                        "start": cs.get("start"),
                        "end": cs.get("end"),
                        "lead_variants": parsed_leads,
                    }
                )

        result = {
            "phenotype": {
                "phenocode": pheno_info.get("phenocode"),
                "phenostring": pheno_info.get("phenostring"),
                "num_cases": pheno_info.get("num_cases"),
                "num_controls": pheno_info.get("num_controls"),
            },
            "region": {
                "chromosome": region_info.get("chromosome"),
                "start": region_info.get("start"),
                "end": region_info.get("stop"),
            },
            "credible_sets": credible_sets,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "FinnGen r12",
                "num_credible_sets": len(credible_sets),
            },
        }
