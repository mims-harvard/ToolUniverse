"""
ClinVar REST API Tool

This tool provides access to the ClinVar database for clinical variant information,
disease associations, and clinical significance data.
"""

import requests
import time
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool


class ClinVarRESTTool(BaseTool):
    """Base class for ClinVar REST API tools."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "ToolUniverse/1.0"}
        )
        self.timeout = 30

    def _make_request(
        self, endpoint: str, params: Optional[Dict] = None, max_retries: int = 3
    ) -> Dict[str, Any]:
        """Make a request to the ClinVar API with automatic retry for rate limiting."""
        url = f"{self.base_url}{endpoint}"

        for attempt in range(max_retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)

                # Handle rate limiting (429 error)
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        wait_time = int(retry_after)
                    else:
                        # Default exponential backoff: 1, 2, 4 seconds
                        wait_time = 2**attempt

                    if attempt < max_retries:
                        print(
                            f"Rate limited (429). Waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}..."
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        return {
                            "status": "error",
                            "error": f"Rate limited after {max_retries} retries. Please wait before making more requests.",
                            "url": url,
                            "retry_after": retry_after,
                        }

                response.raise_for_status()

                # ClinVar API returns XML by default, but we can request JSON
                if params and params.get("retmode") == "json":
                    data = response.json()
                else:
                    # Parse XML response
                    data = response.text

                return {
                    "status": "success",
                    "data": data,
                    "url": url,
                    "content_type": response.headers.get(
                        "content-type", "application/xml"
                    ),
                    "rate_limit_info": {
                        "limit": response.headers.get("X-RateLimit-Limit"),
                        "remaining": response.headers.get("X-RateLimit-Remaining"),
                    },
                }

            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    wait_time = 2**attempt
                    print(
                        f"Request failed: {str(e)}. Retrying in {wait_time} seconds..."
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    return {
                        "status": "error",
                        "error": f"ClinVar API request failed after {max_retries} retries: {str(e)}",
                        "url": url,
                    }

        return {"status": "error", "error": "Maximum retries exceeded", "url": url}

    def _parse_variant_summary(self, vdata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract common fields from a single esummary variant record."""
        gc = vdata.get("germline_classification", {})
        return {
            "title": vdata.get("title", ""),
            "genes": [g.get("symbol", "") for g in vdata.get("genes", [])],
            "clinical_significance": gc.get("description", ""),
            "review_status": gc.get("review_status", ""),
        }

    def _fetch_variant(self, variant_id: str) -> Dict[str, Any]:
        """Fetch a single variant by ID via esummary. Returns (variant_data, error_result) tuple-style dict.

        On success: {"variant_data": {...}, "result": {...}}
        On error: {"error_result": {...}}
        """
        params = {"db": "clinvar", "id": variant_id, "retmode": "json"}
        result = self._make_request("/esummary.fcgi", params)

        if result.get("status") != "success":
            return {"error_result": result}

        data = result.get("data", {})
        variant_data = data.get("result", {}).get(variant_id)

        if not variant_data:
            return {"error_result": result}

        # Check for NCBI inline error (HTTP 200 but variant not found)
        if variant_data.get("error"):
            return {
                "error_result": {
                    "status": "error",
                    "error": f"Variant {variant_id} not found in ClinVar: {variant_data['error']}",
                    "url": result.get("url"),
                }
            }

        return {"variant_data": variant_data, "result": result}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        return self._make_request(self.endpoint, arguments)


@register_tool("ClinVarSearchVariants")
class ClinVarSearchVariants(ClinVarRESTTool):
    """Search for variants in ClinVar by gene or condition."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/esearch.fcgi"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search variants by gene or condition."""
        # Normalize aliases before dispatch
        if not arguments.get("gene") and arguments.get("gene_symbol"):
            arguments = dict(arguments, gene=arguments["gene_symbol"])
        if not arguments.get("clinical_significance") and arguments.get("significance"):
            arguments = dict(arguments, clinical_significance=arguments["significance"])
        if not arguments.get("condition") and arguments.get("query"):
            arguments = dict(arguments, condition=arguments["query"])

        params = {
            "db": "clinvar",
            "retmode": "json",
            "retmax": arguments.get("max_results") or arguments.get("limit", 20),
        }

        # Build search query
        query_parts = []

        if "gene" in arguments:
            query_parts.append(f"{arguments['gene']}[gene]")

        if "condition" in arguments:
            # Feature-70B-005: [disease/phenotype] is not a valid ClinVar eSearch field.
            # Use [dis] (disease/phenotype) field tag for condition searches.
            # Quote multi-word conditions so ClinVar treats them as a phrase.
            condition = arguments["condition"].strip()
            if " " in condition and not condition.startswith('"'):
                condition = f'"{condition}"'
            query_parts.append(f"{condition}[dis]")

        if "variant_id" in arguments:
            # Feature-70B-004: [variant_id] is not recognized by ClinVar eSearch.
            # Use [uid] to look up by numeric variation ID.
            query_parts.append(f"{arguments['variant_id']}[uid]")

        if "clinical_significance" in arguments:
            # Feature-82A-002: NCBI silently translates [clnsig] to [All Fields],
            # returning unrelated variants. The correct syntax is the [Filter] field:
            # "clinsig pathogenic"[Filter] which properly restricts to the clinsig index.
            clnsig = arguments["clinical_significance"].lower().replace("_", " ")
            query_parts.append(f'"clinsig {clnsig}"[Filter]')

        if not query_parts:
            return {
                "status": "error",
                "error": "At least one search parameter is required",
            }

        params["term"] = " AND ".join(query_parts)

        result = self._make_request(self.endpoint, params)

        if result.get("status") != "success":
            return result

        data = result.get("data", {})
        if "esearchresult" not in data:
            return result

        esearch = data["esearchresult"]
        ids = esearch.get("idlist", [])
        count = int(esearch.get("count", 0))

        variants = []
        if ids:
            summary_result = self._make_request(
                "/esummary.fcgi",
                {"db": "clinvar", "id": ",".join(ids[:200]), "retmode": "json"},
            )
            if summary_result.get("status") == "success":
                result_map = summary_result.get("data", {}).get("result", {})
                for vid in ids:
                    vdata = result_map.get(vid)
                    if vdata and not vdata.get("error"):
                        variants.append(
                            {"variant_id": vid, **self._parse_variant_summary(vdata)}
                        )

        search_params = {
            k: v
            for k, v in {
                "gene": arguments.get("gene"),
                "condition": arguments.get("condition"),
                "variant_id": arguments.get("variant_id"),
                "clinical_significance": arguments.get("clinical_significance"),
            }.items()
            if v is not None
        }
        return {
            "status": "success",
            "data": {
                "total_count": count,
                "variant_ids": ids,
                "variants": variants,
                "query_translation": esearch.get("querytranslation", ""),
                "search_params": search_params,
            },
        }


@register_tool("ClinVarGetVariantDetails")
class ClinVarGetVariantDetails(ClinVarRESTTool):
    """Get detailed variant information by ClinVar ID."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/esummary.fcgi"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get variant details by ClinVar ID."""
        variant_id = arguments.get("variant_id", "")
        if not variant_id:
            return {"status": "error", "error": "variant_id is required"}

        fetch = self._fetch_variant(variant_id)
        if "error_result" in fetch:
            return fetch["error_result"]

        variant_data = fetch["variant_data"]
        result = fetch["result"]
        result["variant_id"] = variant_id
        result["formatted_data"] = {
            "variant_id": variant_id,
            "accession": variant_data.get("accession", ""),
            "obj_type": variant_data.get("obj_type", ""),
            "chromosome": variant_data.get("chr_sort", ""),
            "location": variant_data.get("variation_set", [{}])[0]
            .get("variation_loc", [{}])[0]
            .get("band", ""),
            "variation_name": variant_data.get("variation_set", [{}])[0].get(
                "variation_name", ""
            ),
            **self._parse_variant_summary(variant_data),
            "raw_data": variant_data,
        }

        return result


@register_tool("ClinVarGetClinicalSignificance")
class ClinVarGetClinicalSignificance(ClinVarRESTTool):
    """Get clinical significance information for variants."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/esummary.fcgi"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get clinical significance by variant ID."""
        variant_id = arguments.get("variant_id", "")
        if not variant_id:
            return {"status": "error", "error": "variant_id is required"}

        fetch = self._fetch_variant(variant_id)
        if "error_result" in fetch:
            return fetch["error_result"]

        variant_data = fetch["variant_data"]
        result = fetch["result"]
        result["variant_id"] = variant_id

        # Extract clinical significance information
        germline_class = variant_data.get("germline_classification", {})
        clinical_impact = variant_data.get("clinical_impact_classification", {})
        oncogenicity = variant_data.get("oncogenicity_classification", {})

        result["formatted_data"] = {
            "variant_id": variant_id,
            "germline_classification": {
                "description": germline_class.get("description", ""),
                "review_status": germline_class.get("review_status", ""),
                "last_evaluated": germline_class.get("last_evaluated", ""),
                "fda_recognized": germline_class.get("fda_recognized_database", ""),
                "traits": [
                    trait.get("trait_name", "")
                    for trait in germline_class.get("trait_set", [])
                ],
            },
            "clinical_impact": {
                "description": clinical_impact.get("description", ""),
                "review_status": clinical_impact.get("review_status", ""),
                "last_evaluated": clinical_impact.get("last_evaluated", ""),
            },
            "oncogenicity": {
                "description": oncogenicity.get("description", ""),
                "review_status": oncogenicity.get("review_status", ""),
                "last_evaluated": oncogenicity.get("last_evaluated", ""),
            },
            "raw_data": variant_data,
        }

        return result
