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

# Human-readable clinical-significance classes whose NCBI clinsig [prop] token is
# NOT the naive underscore form. Confirmed live: "Uncertain significance" ->
# clinsig_vus[prop] (BRCA2: 4345), while clinsig_uncertain_significance[prop]
# returns 0 -- so filtering for VUS, the single LARGEST ClinVar category,
# silently returned an empty success. Keyed by the normalized (lowercased,
# spaces) class name.
_CLINSIG_PROP_ALIASES = {
    "uncertain significance": "vus",
}


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
        # An rsID (e.g. rs4244285) passed as `query` was aliased to `condition`
        # and searched as a DISEASE term ('rs4244285[dis]'), silently returning
        # 0 -- but ClinVar's free-text index DOES match a bare rsID (confirmed
        # live: term=rs4244285 -> 37 records). Route an rsID to a bare-term
        # search so the standard PGx chain rsID -> ClinVar works instead of a
        # false 'not found'.
        _rsid_src = arguments.get("rsid") or arguments.get("query")
        if (
            not arguments.get("rsid")
            and isinstance(_rsid_src, str)
            and re.fullmatch(r"rs\d+", _rsid_src.strip(), re.IGNORECASE)
        ):
            arguments = dict(arguments, rsid=_rsid_src.strip())
            arguments.pop("query", None)
        if not arguments.get("condition") and arguments.get("query"):
            arguments = dict(arguments, condition=arguments["query"])
        # `variant` is the intuitive name for the variant filter (the schema
        # calls it `variant_name`). Passing `variant` used to be silently
        # dropped whenever a valid param like `gene` was also present, so
        # {"gene":"KRAS","variant":"G12C"} returned ALL 599 KRAS variants
        # instead of the 2 G12C ones -- a dangerous silent full-gene dump.
        # Alias it, mirroring the gene_symbol/significance/query aliases above.
        if not arguments.get("variant_name") and arguments.get("variant"):
            arguments = dict(arguments, variant_name=arguments["variant"])

        params = {
            "db": "clinvar",
            "retmode": "json",
            "retmax": arguments.get("max_results") or arguments.get("limit", 20),
        }

        # Build search query
        query_parts = []
        compound_clnsig = False

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

        if arguments.get("rsid"):
            # Search a dbSNP rsID as a bare free-text term -- ClinVar matches it
            # across the record (not via [dis]/[gene]/[Variant name]).
            query_parts.append(str(arguments["rsid"]).strip())

        if "variant_id" in arguments:
            # Feature-70B-004: [variant_id] is not recognized by ClinVar eSearch.
            # Use [uid] to look up by numeric variation ID.
            query_parts.append(f"{arguments['variant_id']}[uid]")

        if arguments.get("variant_name"):
            # Fix-R78B-1: the Fix-R5D-1/R8C-1 comment above assumed there was
            # "no such parameter" -- but ClinVar eSearch DOES support a real
            # [Variant name] field tag (confirmed live: "HBB[gene] AND
            # Glu7Val[Variant name]" -> 9 hits including VCV 15333, the
            # canonical sickle-cell NM_000518.5(HBB):c.20A>T (p.Glu7Val)
            # Pathogenic record). Without this, an exact-match lookup for a
            # specific protein change/HGVS notation could only be done by
            # fetching gene-level rows (capped at 100) and filtering
            # client-side -- which silently misses old/low-ID records in any
            # variant-dense gene, since ClinVar's default gene-level order
            # isn't clinical-significance- or fame-ranked (confirmed live:
            # HBB's own sickle-cell record, one of the best-known variants in
            # human genetics, isn't within the first 100 or even the first
            # 425-Pathogenic-filtered gene-level rows). Accepts either a
            # single name or a list (a multi-allelic site yields one protein
            # change per allele; only the queried allele's name will hit, so
            # every candidate must be tried) -- combined with OR so one
            # request covers all candidates.
            names = arguments["variant_name"]
            names = names if isinstance(names, list) else [names]
            names = [str(n).strip() for n in names if str(n).strip()]
            # NCBI's [Variant name] index mangles the '.' in an HGVS reference
            # prefix ('p.Glu342Lys' -> 'p0x2eGlu342Lys') and matches nothing, so a
            # clinician typing standard HGVS got a silent false-empty. Strip the
            # leading reference-type prefix so 'p.Glu342Lys' -> 'Glu342Lys' (which
            # matches). Verified live: SERPINA1 p.Glu342Lys 0 -> 2 hits (Z-allele).
            names = [re.sub(r"(?i)^[pcgmnor]\.", "", n) for n in names]
            # An rsID passed as variant_name (e.g. rs776746) belongs in a bare
            # free-text search, not the [Variant name] field, which returns 0 for
            # it -- route it like the rsid param instead of a false-empty.
            rsid_names = [n for n in names if re.fullmatch(r"rs\d+", n, re.IGNORECASE)]
            names = [n for n in names if n not in rsid_names]
            for _rs in rsid_names:
                query_parts.append(_rs)
            if names:
                terms = " OR ".join(f"{n}[Variant name]" for n in names)
                query_parts.append(f"({terms})" if len(names) > 1 else terms)

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
            # A COMPOUND aggregate class like "Pathogenic/Likely pathogenic" has
            # no single NCBI clinsig token -- the slash breaks BOTH the [Filter]
            # phrase and the [prop] token, so the old query silently returned 0
            # even though the tool's OWN get_clinical_significance emits that exact
            # value. Treat "/" as OR and expand to the individual clinsig classes
            # (the clinically-actionable union), each via the proven
            # [Filter]-OR-[prop] path.
            _raw_clnsig = str(arguments["clinical_significance"])
            _components = [c.strip() for c in _raw_clnsig.split("/") if c.strip()]
            compound_clnsig = len(_components) > 1
            _clauses = []
            for _comp in _components:
                _c = _comp.lower().replace("_", " ")
                _c_prop = _c.replace(" ", "_")
                _forms = f'"clinsig {_c}"[Filter] OR clinsig_{_c_prop}[prop]'
                # Some classes index under a different NCBI token (e.g. VUS);
                # OR it in so a valid class is never a silent false-empty.
                _alias = _CLINSIG_PROP_ALIASES.get(_c)
                if _alias:
                    _forms += f" OR clinsig_{_alias}[prop]"
                _clauses.append(f"({_forms})")
            if _clauses:
                query_parts.append(
                    "(" + " OR ".join(_clauses) + ")"
                    if len(_clauses) > 1
                    else _clauses[0]
                )

        # Fix-R5D-1/R8C-1: a caller-supplied param that doesn't match any
        # recognized name/alias (e.g. "gene_name" instead of "gene") was
        # silently dropped. (Fix-R78B-1: "variant_name" -- originally called
        # out here as "no such parameter" -- is now a real, supported param;
        # see above.) When it's the ONLY param supplied, this
        # produced a generic "at least one search parameter is required"
        # error with no hint the parameter itself was misnamed. When OTHER
        # valid params are also supplied, the query still runs but silently
        # ignores the unrecognized one -- confirmed live that
        # {"gene": "GJB2", "made_up_param": "35delG"} returns all 739 GJB2
        # variants with no indication the made_up_param filter had zero
        # effect. Name unrecognized parameter(s) in both cases.
        recognized = {
            "gene",
            "gene_symbol",
            "condition",
            "query",
            "variant_id",
            "variant_name",
            "variant",
            "rsid",
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
                        "condition (or query), variant_id, variant_name, "
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

        # Fix-R62A-1: some gene symbols are HGNC-deprecated/renamed entirely,
        # not just informally hyphenated -- e.g. "GBA" (glucocerebrosidase,
        # Gaucher disease) was renamed to "GBA1" in 2023 to disambiguate from
        # the GBA2/GBA3 gene family, and ClinVar's own [gene] index has fully
        # absorbed the rename with no backward-compat alias (confirmed live
        # and via raw NCBI E-utils: "GBA[gene]" -> 0 hits, not even recognized
        # as a search phrase; "GBA1[gene]" -> 786 hits). Unlike the hyphen
        # case above, no string transform recovers the current symbol --
        # resolve it via NCBI's own gene database (which tracks "GBA" as an
        # alias of gene ID 2629, current official symbol "GBA1") instead of
        # hardcoding a growing alias list.
        if "gene" in arguments and int(data["esearchresult"].get("count", 0)) == 0:
            resolved_gene = self._resolve_deprecated_gene_symbol(gene)
            if resolved_gene and resolved_gene.upper() != gene.upper():
                resolved_query_parts = [f"{resolved_gene}[gene]"] + query_parts[1:]
                resolved_params = dict(params, term=" AND ".join(resolved_query_parts))
                resolved_result = self._make_request(self.endpoint, resolved_params)
                if (
                    resolved_result.get("status") == "success"
                    and "esearchresult" in resolved_result.get("data", {})
                    and int(resolved_result["data"]["esearchresult"].get("count", 0))
                    > 0
                ):
                    result = resolved_result
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
        if compound_clnsig:
            response_data["clinical_significance_note"] = (
                "The '/' in the requested clinical_significance was treated as OR: "
                "results are the union of the individual classes (e.g. Pathogenic "
                "AND Likely pathogenic), which is broader than only the aggregate "
                "'Pathogenic/Likely pathogenic' review class."
            )
        return {"status": "success", "data": response_data}

    def _resolve_deprecated_gene_symbol(self, gene: str) -> Optional[str]:
        """Look up `gene` in NCBI's own gene database (which tracks
        deprecated/previous symbols as aliases, e.g. "GBA" -> current
        official symbol "GBA1") and return its current official symbol.
        Best-effort: returns None on any failure or if no gene is found,
        never raises -- this is a fallback, not a hard requirement."""
        try:
            search_result = self._make_request(
                "/esearch.fcgi",
                {
                    "db": "gene",
                    "term": f"{gene}[sym] AND human[orgn]",
                    "retmode": "json",
                },
            )
            if search_result.get("status") != "success":
                return None
            ids = (
                search_result.get("data", {}).get("esearchresult", {}).get("idlist", [])
            )
            if not ids:
                return None
            summary_result = self._make_request(
                "/esummary.fcgi", {"db": "gene", "id": ids[0], "retmode": "json"}
            )
            if summary_result.get("status") != "success":
                return None
            gene_data = summary_result.get("data", {}).get("result", {}).get(ids[0], {})
            return gene_data.get("name") or None
        except Exception:
            return None


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
        # Fix-R8E-1/R6C-2: assign the formatted payload *over* `result["data"]`
        # (the full, unprocessed esummary envelope from _make_request) instead
        # of publishing it alongside under a second key. Keeping both roughly
        # tripled payload size for no informational gain and made this tool's
        # output nearly indistinguishable from ClinVarGetClinicalSignificance's,
        # which had the identical duplication. Overwriting preserves that
        # de-duplication -- raw access remains at data["raw_data"] -- while
        # delivering the payload under the `data` key the return_schema
        # declares and every other tool in the registry uses.
        result["data"] = {
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

        # Fix-R8E-1/R6C-2: see the matching fix in ClinVarGetVariantDetails --
        # assigning over `result["data"]` (the raw esummary envelope) both
        # de-duplicates the payload and honours the `data` key declared in the
        # return_schema. Raw access remains at data["raw_data"].
        result["data"] = {
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
