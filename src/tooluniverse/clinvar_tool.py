"""
ClinVar REST API Tool

This tool provides access to the ClinVar database for clinical variant information,
disease associations, and clinical significance data.
"""

import re
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
            # NCBI returns HTTP 200 with an empty uids list and an inline
            # "Invalid uid ..." message when the id is not a numeric ClinVar
            # Variation ID (e.g. a dbSNP rsID was passed). Surface this as a
            # real error instead of forwarding the raw success envelope.
            ncbi_err = data.get("error") or data.get("result", {}).get("error")
            msg = f"No ClinVar record found for variant_id '{variant_id}'."
            if isinstance(variant_id, str) and variant_id.lower().startswith("rs"):
                msg += (
                    " Pass a numeric ClinVar Variation ID (e.g. 12345), not a"
                    " dbSNP rsID."
                )
            if ncbi_err:
                msg += f" NCBI: {ncbi_err}"
            return {
                "error_result": {
                    "status": "error",
                    "error": msg,
                    "url": result.get("url"),
                }
            }

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

        gene_hyphen_variant = None
        if "gene" in arguments:
            # Fix-R10D-1: ClinVar's [gene] index only matches a bare HGNC
            # symbol, but a natural clinical phrasing like "NF2 gene" (used
            # verbatim in real research questions -- e.g. "look up the NF2
            # gene") silently returns 0 results, since the literal trailing
            # word "gene" becomes part of the queried string (confirmed
            # live and via raw NCBI E-utils curl: "Nf2 gene[gene]" -> 0
            # hits, "NF2[gene]" -> 2612 hits). Strip a trailing/leading
            # "gene"/"protein" qualifier word before querying.
            gene = re.sub(
                r"^\s*(?:gene|protein)\s+|\s+(?:gene|protein)\s*$",
                "",
                arguments["gene"],
                flags=re.IGNORECASE,
            ).strip()

            # Fix-R8B-1 (revised, Fix-R49A-1): some genes are informally
            # hyphenated even though their current HGNC symbol has none (e.g.
            # "BRCA-2" for "BRCA2", "HER-2" for "HER2" -- confirmed live via
            # raw NCBI E-utils: "BRCA-2[gene]" -> 0 hits, "BRCA2[gene]" ->
            # 21879 hits). R8B-1 originally handled this by unconditionally
            # stripping every hyphen, but that silently broke every gene
            # whose CURRENT official HGNC symbol genuinely contains one --
            # confirmed live for the entire HLA family (HLA-B[gene] -> 130
            # hits, HLAB[gene] -> 0), the NKX homeobox family (NKX2-5[gene]
            # -> real hits, NKX25[gene] -> 0), and MT- mitochondrial genes
            # (MT-ND1[gene] -> 194 hits, MTND1[gene] -> 0) -- all clinically
            # significant gene families (HLA pharmacogenomics/transplant,
            # NKX cardiac/pancreatic development, MT- mitochondrial disease).
            # Query with the hyphen preserved first; only fall back to the
            # stripped form if that returns zero results, so both the old
            # informally-hyphenated-name case and genuinely-hyphenated
            # official symbols work.
            if "-" in gene:
                gene_hyphen_variant = gene.replace("-", "")
            query_parts.append(f"{gene}[gene]")

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
            #
            # Fix-R6C-1: that [Filter] form only indexes single-word clinsig
            # values -- confirmed live that "clinsig risk factor"[Filter] and
            # "clinsig likely pathogenic"[Filter] both silently return 0
            # results even though matching variants exist (e.g. HFE C282Y,
            # whose own classification literally contains "risk factor").
            # ClinVar separately indexes compound values via clinsig_<value
            # with underscores>[prop] (confirmed live for risk_factor and
            # likely_pathogenic). OR both forms so single-word values keep
            # using the already-verified [Filter] path while compound values
            # fall through to the [prop] path -- this can only add matches
            # the old query missed, never drop ones it already found.
            clnsig = arguments["clinical_significance"].lower().replace("_", " ")
            clnsig_prop = clnsig.replace(" ", "_")
            query_parts.append(
                f'("clinsig {clnsig}"[Filter] OR clinsig_{clnsig_prop}[prop])'
            )

        # Fix-R5D-1/R8C-1: a caller-supplied param that doesn't match any
        # recognized name/alias (e.g. "gene_name" instead of "gene", or
        # "variant_name" -- there is no such parameter, only "variant_id")
        # was silently dropped. When it's the ONLY param supplied, this
        # produced a generic "at least one search parameter is required"
        # error with no hint the parameter itself was misnamed. When OTHER
        # valid params are also supplied, the query still runs but silently
        # ignores the unrecognized one -- confirmed live that
        # {"gene": "GJB2", "variant_name": "35delG"} returns all 739 GJB2
        # variants with no indication the variant_name filter had zero
        # effect. Name unrecognized parameter(s) in both cases.
        recognized = {
            "gene",
            "gene_symbol",
            "condition",
            "query",
            "variant_id",
            "clinical_significance",
            "significance",
            "max_results",
            "limit",
        }
        unrecognized = sorted(set(arguments) - recognized)

        if not query_parts:
            if unrecognized:
                return {
                    "status": "error",
                    "error": (
                        f"Unrecognized parameter(s): {', '.join(unrecognized)}. "
                        "Valid search parameters: gene (or gene_symbol), "
                        "condition (or query), variant_id, "
                        "clinical_significance (or significance)."
                    ),
                }
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

        # Fix-R49A-1: the hyphen-preserved gene query above found nothing --
        # retry once with the hyphen stripped, for the informally-hyphenated
        # BRCA-2/HER-2-style names ClinVar's index doesn't recognize.
        if gene_hyphen_variant and int(data["esearchresult"].get("count", 0)) == 0:
            # "gene" is always the first query part appended when present.
            fallback_query_parts = [f"{gene_hyphen_variant}[gene]"] + query_parts[1:]
            fallback_params = dict(params, term=" AND ".join(fallback_query_parts))
            fallback_result = self._make_request(self.endpoint, fallback_params)
            if (
                fallback_result.get("status") == "success"
                and "esearchresult" in fallback_result.get("data", {})
                and int(fallback_result["data"]["esearchresult"].get("count", 0)) > 0
            ):
                result = fallback_result
                data = result["data"]

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
        response_data = {
            "total_count": count,
            "variant_ids": ids,
            "variants": variants,
            "query_translation": esearch.get("querytranslation", ""),
            "search_params": search_params,
        }
        if unrecognized:
            response_data["ignored_parameters"] = unrecognized
        return {"status": "success", "data": response_data}


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
        # Fix-R8E-1/R6C-2: `result["data"]` (the full, unprocessed esummary
        # envelope from _make_request) duplicates the same content already
        # exposed at formatted_data["raw_data"] -- keeping both roughly
        # tripled payload size for no informational gain and made this
        # tool's output nearly indistinguishable from
        # ClinVarGetClinicalSignificance's, which has the identical
        # duplication. Drop the redundant top-level copy; raw access is
        # still available via formatted_data.raw_data.
        result.pop("data", None)

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
        # Fix-R8E-1/R6C-2: see the matching fix in ClinVarGetVariantDetails
        # -- result["data"] duplicates formatted_data["raw_data"].
        result.pop("data", None)

        return result
