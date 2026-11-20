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


def _phenotype_row(record: dict) -> dict:
    """One FinnGen phenotype, as both the list and the lookup should report it.

    `gc_lambda` is the genomic-control inflation factor at four quantiles,
    and it is on all 2,470 phenotypes of the /phenos list. It is how a caller
    tells a usable GWAS from one whose statistics are inflated or, for a rare
    phenotype, deflated -- AB1_TUBERCULOSIS_MILIARY reads 0.38 at the 0.5
    quantile. `assoc_files` is the summary-statistics file behind the
    phenotype.

    The single-phenotype lookup already returned gc_lambda and the list did
    not, from the same upstream record shape, so both now build this row and
    the fields present decide what it carries.
    """
    row = {
        "phenocode": record.get("phenocode"),
        "phenostring": record.get("phenostring"),
        "category": record.get("category"),
        "category_index": record.get("category_index"),
        "num_cases": record.get("num_cases"),
        "num_controls": record.get("num_controls"),
        "num_gw_significant": record.get("num_gw_significant"),
        # Keyed by quantile: {"0.001": .., "0.01": .., "0.1": .., "0.5": ..}
        "gc_lambda": record.get("gc_lambda"),
        "assoc_files": [f for f in (record.get("assoc_files") or []) if f],
    }
    # Only the per-phenotype endpoint carries the previous release's counts.
    for key in ("num_cases_prev", "num_controls_prev"):
        if key in record:
            row[key] = record.get(key)
    return row


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
        try:
            limit = max(1, int(arguments.get("limit") or 50))
            offset = max(0, int(arguments.get("offset", 0)))
        except (TypeError, ValueError):
            return {
                "status": "error",
                "error": "Parameters 'limit' and 'offset' must be integers.",
            }

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
            results.append(_phenotype_row(p))

        results.sort(key=lambda x: x.get("num_cases", 0), reverse=True)
        total = len(results)
        results = results[offset : offset + limit]
        has_more = offset + len(results) < total

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "FinnGen r12",
                "total_matching": total,
                "returned": len(results),
                "total_phenotypes": len(all_phenos),
                "offset": offset,
                "limit": limit,
                "has_more": has_more,
                "truncated": has_more,
                "next_offset": offset + len(results) if has_more else None,
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

        result = _phenotype_row(data)

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

        # FinnGen answers with THREE top-level keys and this returned one of
        # them. `regions` is 455 fine-mapping region definitions -- a
        # phenocode and an interval, and no statistic. `results` is 2470
        # association rows carrying beta, mlogp, maf, n_case, n_control and
        # `phenostring`, the readable phenotype name. The tool's description
        # promises "which disease associations a variant contributes to" and
        # it returned `M13_ARTHROPATHIES` with no effect size, no p-value and
        # no phenotype name, while all of it sat in the same response.
        by_pheno: Dict[str, Dict[str, Any]] = {}
        for row in data.get("results") or []:
            if isinstance(row, dict) and row.get("phenocode"):
                by_pheno.setdefault(str(row["phenocode"]), row)

        def association_of(phenocode):
            row = by_pheno.get(str(phenocode))
            if not row:
                return None
            return {
                "phenostring": row.get("phenostring"),
                "category": row.get("category"),
                "beta": row.get("beta"),
                "mlogp": row.get("mlogp"),
                "maf": row.get("maf"),
                "maf_case": row.get("maf_case"),
                "maf_control": row.get("maf_control"),
                "n_case": row.get("n_case"),
                "n_control": row.get("n_control"),
                "n_sample": row.get("n_sample"),
            }

        parsed_regions: List[Dict[str, Any]] = [
            {
                "phenocode": r.get("phenocode"),
                "chromosome": r.get("chr"),
                "start": r.get("start"),
                "end": r.get("end"),
                "type": r.get("type"),
                # The region's own results file, so the credible set behind
                # the interval can be fetched.
                "path": r.get("path"),
                # The association this region's phenotype actually shows for
                # the variant, joined on phenocode.
                "association": association_of(r.get("phenocode")),
            }
            for r in data.get("regions", [])
        ]
        matched = sum(1 for r in parsed_regions if r.get("association"))

        return {
            "status": "success",
            "data": parsed_regions,
            "metadata": {
                "source": "FinnGen r12",
                "variant": variant,
                "total_regions": len(parsed_regions),
                # The response's association rows, and how many regions one
                # could be joined to. A region with association null is one
                # FinnGen fine-mapped but did not report a phenome-wide row
                # for; saying so is the difference between "no association"
                # and "not looked up".
                "total_association_rows": len(data.get("results") or []),
                "regions_with_association": matched,
                "regions_without_association": len(parsed_regions) - matched,
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
