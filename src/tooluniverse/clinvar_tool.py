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

# The clinical-significance classes ClinVar's Entrez index ACTUALLY accepts.
# Enumerated by live-probing every documented germline/oncogenicity class
# through the exact clause this module builds
# (`"clinsig <v>"[Filter] OR clinsig_<v>[prop]`, plus the alias above) against
# db=clinvar with no other term, 2026-08. Only these returned a non-zero,
# non-parenthesised (i.e. index-recognised) translation:
#   pathogenic 256608 | likely pathogenic 165559 | uncertain significance
#   2367938 | vus 2368057 | likely benign 1165994 | benign 281217 |
#   established risk allele 6 | likely risk allele 119 | uncertain risk allele
#   180 | drug response 2612 | not provided 7616 | other 2209 |
#   risk factor 520
# Documented-but-unindexed spellings ("Affects", "association", "protective",
# "confers sensitivity", "Conflicting classifications of pathogenicity",
# "Oncogenic", "Likely oncogenic", "Pathogenic, low penetrance", ...) all came
# back 0 with Entrez wrapping the term in parentheses -- its signal for "this
# term is not in the index". Accepting them would paste an unmatchable token
# into the query and return a silent, filtered-to-nothing success, which is
# exactly the failure this list exists to prevent.
_CLINSIG_ACCEPTED = (
    "Pathogenic",
    "Likely pathogenic",
    "Uncertain significance",
    "VUS",
    "Likely benign",
    "Benign",
    "Established risk allele",
    "Likely risk allele",
    "Uncertain risk allele",
    "drug response",
    "risk factor",
    "not provided",
    "other",
)
_CLINSIG_ACCEPTED_NORMALIZED = {v.lower() for v in _CLINSIG_ACCEPTED}


def _normalize_clinsig(value: Any) -> list:
    """Split a clinical-significance value on '/' and normalize each component
    exactly the way the query builder does (lowercase, underscores/hyphens ->
    spaces), so validation can never accept a spelling the builder would then
    mangle. No accepted class contains a hyphen, and sibling variant tools emit
    hyphenated spellings (dbSNP reports "risk-factor"), so folding them keeps a
    chained call working instead of silently filtering to nothing."""
    return [
        re.sub(r"\s+", " ", re.sub(r"[_-]", " ", comp.strip().lower()))
        for comp in str(value).split("/")
        if comp.strip()
    ]


def _clinsig_query_clause(components: list) -> str:
    """Build the Entrez clause for already-normalized clinsig components.

    Single-word values are indexed under `"clinsig <v>"[Filter]`, compound ones
    under `clinsig_<v_with_underscores>[prop]`, and a few classes under a
    different NCBI token entirely (VUS); OR all applicable forms so a valid
    class is never a silent false-empty. Multiple components (from a '/'
    aggregate class) are OR'd into their union.
    """
    clauses = []
    for comp in components:
        forms = f'"clinsig {comp}"[Filter] OR clinsig_{comp.replace(" ", "_")}[prop]'
        alias = _CLINSIG_PROP_ALIASES.get(comp)
        if alias:
            forms += f" OR clinsig_{alias}[prop]"
        clauses.append(f"({forms})")
    if not clauses:
        return ""
    return "(" + " OR ".join(clauses) + ")" if len(clauses) > 1 else clauses[0]


def _invalid_clinsig_error(param_name: str, raw_value: Any, invalid: list) -> dict:
    """Reject an unrecognised clinical-significance value at the input, naming
    the offending PARAMETER.

    Previously such a value was pasted straight into the Entrez term, matched
    nothing, and the zero-result response then blamed the *gene* symbol -- so
    `{"gene": "TP53", "clinical_significance": "Banana"}` told the caller to
    go re-verify TP53, the one input that was never wrong.
    """
    return {
        "status": "error",
        "error": (
            f"Unrecognized {param_name} value(s): "
            + ", ".join(repr(i) for i in invalid)
            + f" (from {str(raw_value)!r}). No filter was applied and no search "
            "was run -- an unrecognized class matches nothing in ClinVar's "
            "index, which would look like 'this gene has no such variants'. "
            "ClinVar's clinical-significance index accepts only: "
            + ", ".join(_CLINSIG_ACCEPTED)
            + ". Case-insensitive; underscores are treated as spaces "
            "(e.g. 'likely_pathogenic'). Combine two classes with '/' to search "
            "their union (e.g. 'Pathogenic/Likely pathogenic')."
        ),
        "parameter": param_name,
        "invalid_values": invalid,
        "valid_values": list(_CLINSIG_ACCEPTED),
    }


# One term of an Entrez query translation together with the field tag Entrez
# actually applied to it: either a quoted phrase or a bare token, followed by
# "[<field>]". Entrez echoes its translation verbatim in `querytranslation`
# (confirmed live: 'RB1[gene] AND retinoblastoma[dis]' comes back unchanged),
# which is how a term's real search field can be read off a response that has
# already been fetched, with no extra request.
_TRANSLATED_TERM_RE = re.compile(r'("[^"]*"|[^\s()\[\]]+)\s*\[([^\]]+)\]')


def _normalize_translated_term(text: Any) -> str:
    """Fold a query term to a comparable form (unquoted, lowercase, single
    spaces) so a term this module emitted can be located in Entrez's echo of
    it regardless of quoting or case."""
    return re.sub(r"\s+", " ", str(text).replace('"', "").strip().lower())


def _field_tags_for_term(query_translation: str, term: str) -> list:
    """The field tag(s) Entrez actually attached to `term` in the translation
    it returned. Empty when the term is absent or carries no tag at all."""
    wanted = _normalize_translated_term(term)
    if not wanted or not query_translation:
        return []
    return [
        tag.strip()
        for raw, tag in _TRANSLATED_TERM_RE.findall(query_translation)
        if _normalize_translated_term(raw) == wanted
    ]


# ClinVar's [dis] index carries MedGen's concept names, not free clinical
# phrasing, and it has no fuzzy matching: confirmed live via raw E-utils that
# '"Leber congenital amaurosis"[dis]' returns 996 RPE65 records while the
# one-letter-different '"Lebers congenital amaurosis"[dis]' and the locus name
# 'RP20[dis]' each return 0. Any disclosure about a condition term points the
# caller at the index that decides the answer.
_CONDITION_INDEX_GUIDANCE = (
    "ClinVar's disease index carries MedGen's own condition names, matched "
    "exactly -- a synonym, a locus name or a one-letter misspelling matches "
    "nothing there. Look the condition up (e.g. via MedGen_search_conditions) "
    "and re-run with the indexed name to get a disease-filtered answer."
)


def _condition_filter_disclosure(
    condition: Any,
    condition_term: str,
    query_translation: str,
    freetext_retry: bool,
) -> Dict[str, Any]:
    """State, at the top level of the response, whether the caller's
    `condition` actually acted as a DISEASE filter on the count being returned.

    A disease-filtered count and a free-text count are indistinguishable in the
    payload but mean entirely different things -- "996 RPE65 records classified
    for Leber congenital amaurosis" versus "1 RPE65 record that happens to
    contain this text somewhere". Either the tool's own untagged retry below or
    an Entrez rewrite of the field tag can turn one into the other, and both
    are visible in the `querytranslation` Entrez already returned, so the
    distinction is disclosed without a second request.
    """
    fields = _field_tags_for_term(query_translation, condition_term)
    if any(f.lower() == "dis" for f in fields):
        return {"condition_filter_applied": True}
    if freetext_retry:
        field = fields[0] if fields else "All Fields"
        return {
            "condition_filter_applied": False,
            "condition_search_field": field,
            "condition_filter_warning": (
                f"total_count is NOT disease-filtered. The disease-restricted "
                f"search for condition '{condition}' returned no records, so the "
                f"term was automatically retried unrestricted (Entrez searched it "
                f"as [{field}]) and that free-text count is what is reported here: "
                "it counts records merely mentioning this text anywhere -- variant "
                "names, submitter comments, other linked conditions -- rather than "
                "records classified for this condition. " + _CONDITION_INDEX_GUIDANCE
            ),
        }
    if fields:
        field = fields[0]
        return {
            "condition_filter_applied": False,
            "condition_search_field": field,
            "condition_filter_warning": (
                f"total_count is NOT disease-filtered. Entrez did not keep the "
                f"[dis] field tag for condition '{condition}' -- it searched the "
                f"term as [{field}] instead (see query_translation), which matches "
                "the text anywhere in a record rather than restricting to records "
                "classified for this condition. " + _CONDITION_INDEX_GUIDANCE
            ),
        }
    # No translation echoed back (or the term is unrecognisable in it): there
    # is no evidence either way, and inventing a warning would be as misleading
    # as omitting a real one.
    return {}


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
        _clnsig_param = "clinical_significance"
        if not arguments.get("clinical_significance") and arguments.get("significance"):
            arguments = dict(arguments, clinical_significance=arguments["significance"])
            _clnsig_param = "significance"
        # Validate the clinical-significance filter BEFORE anything is queried:
        # an unrecognized class used to be pasted into the Entrez term, match
        # nothing, and come back as a `status: success` with 0 results whose
        # hint blamed the (perfectly valid) gene symbol instead.
        clnsig_components = []
        if str(arguments.get("clinical_significance") or "").strip():
            clnsig_components = _normalize_clinsig(arguments["clinical_significance"])
            invalid_clnsig = [
                c for c in clnsig_components if c not in _CLINSIG_ACCEPTED_NORMALIZED
            ]
            if invalid_clnsig:
                return _invalid_clinsig_error(
                    _clnsig_param,
                    arguments["clinical_significance"],
                    invalid_clnsig,
                )
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
        # A `query` carrying Entrez field tags ("7[chr] AND 1000:2000[chrpos37]")
        # is a search expression, not a disease name. Aliasing it to `condition`
        # wrapped the whole string in [dis] and returned 0 with no hint why.
        _q = arguments.get("query")
        if isinstance(_q, str) and re.search(r"\[[a-z0-9]+\]", _q, re.IGNORECASE):
            arguments = dict(arguments, raw_term=_q)
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

        # An expression the caller wrote themselves goes to Entrez untouched.
        if arguments.get("raw_term"):
            query_parts.append(str(arguments["raw_term"]))

        gene = None
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

        condition_dis_index = None
        condition_query_term = None
        condition_freetext_retry = False
        if "condition" in arguments:
            # Feature-70B-005: [disease/phenotype] is not a valid ClinVar eSearch field.
            # Use [dis] (disease/phenotype) field tag for condition searches.
            # Quote multi-word conditions so ClinVar treats them as a phrase.
            condition = arguments["condition"].strip()
            if " " in condition and not condition.startswith('"'):
                condition = f'"{condition}"'
            condition_query_term = condition
            condition_dis_index = len(query_parts)
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
            # An rsID passed as variant_name (e.g. rs776746) belongs in a bare
            # free-text search, not the [Variant name] field, which returns 0 for
            # it -- route it like the rsid param instead of a false-empty.
            rsid_names = [n for n in names if re.fullmatch(r"rs\d+", n, re.IGNORECASE)]
            names = [n for n in names if n not in rsid_names]
            for _rs in rsid_names:
                query_parts.append(_rs)
            # NCBI's [Variant name] index mangles the '.' in an unquoted HGVS
            # reference prefix ('p.Glu342Lys' -> 'p0x2eGlu342Lys') and matches
            # nothing, so a clinician typing standard HGVS got a silent
            # false-empty. Stripping the prefix fixed the protein case, but
            # Fix-R3-07: it silently BROKE the coding case, because c. notation
            # also carries '+'/'>' that Entrez only treats literally inside
            # quotes. Confirmed live -- there is no single spelling that works
            # for both:
            #     DPYD "c.1905+1G>A"[Variant name] -> 1 ; "1905+1G>A" -> 0
            #     SERPINA1 "p.Glu342Lys"    -> 0 ; "Glu342Lys"  -> 2
            # so `tu run ClinVar_search_variants '{"gene":"DPYD",
            # "variant_name":"c.1905+1G>A"}'` reported total_count 0 for
            # VCV000000432, one of the best-known pharmacogenomic variants.
            # Emit BOTH spellings, quoted, OR'd together: an OR can only add
            # matches the old query missed, never drop ones it already found.
            # Verified live: DPYD c.1905+1G>A 0->1, CYP2C19 c.681G>A 0->36,
            # SERPINA1 p.Glu342Lys still 2, HBB p.Glu7Val still 9.
            spellings = []
            for name in names:
                stripped = re.sub(r"(?i)^[pcgmnor]\.", "", name)
                for form in (name, stripped):
                    # Strip embedded quotes so they cannot break out of the
                    # quoted Entrez term.
                    form = form.replace('"', "").strip()
                    if form and form not in spellings:
                        spellings.append(form)
            if spellings:
                terms = " OR ".join(f'"{s}"[Variant name]' for s in spellings)
                query_parts.append(f"({terms})" if len(spellings) > 1 else terms)

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
            # Values were normalized and validated against the live-verified
            # accepted set up front (see _CLINSIG_ACCEPTED), so every component
            # reaching here is known to exist in ClinVar's index.
            compound_clnsig = len(clnsig_components) > 1
            _clause = _clinsig_query_clause(clnsig_components)
            if _clause:
                query_parts.append(_clause)

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

        # Fix-R9B-1: the [dis] field only matches ClinVar's own indexed
        # disease/phenotype name for a record, which frequently differs from
        # the name clinicians actually use -- confirmed live that
        # "MECP2 duplication syndrome"[dis] (arguably the most natural way to
        # refer to this exact condition) returns 0 even though ClinVar has
        # 101+ MECP2 records that reference that phrase in free text (under
        # its indexed name "Xq28 duplication syndrome" instead). Retry once
        # with the condition term unrestricted to any field ([All Fields])
        # when the [dis]-restricted search comes back empty -- this can only
        # add matches the strict query missed, never drop ones it found.
        #
        # ...but the count it produces is a free-text count, not a
        # disease-filtered one, and the two used to be reported identically:
        # `{"gene":"RPE65","condition":"Lebers congenital amaurosis"}` (one
        # letter off the indexed name) came back a plain success with
        # total_count 1 next to the 996 of the correctly-spelled query, with
        # nothing saying the second number was a substring match. Record that
        # this retry happened so the response can say so.
        if (
            condition_dis_index is not None
            and int(data["esearchresult"].get("count", 0)) == 0
        ):
            freetext_query_parts = list(query_parts)
            # The stored term is "<condition>[dis]" -- drop the field tag to
            # search it unrestricted instead.
            freetext_query_parts[condition_dis_index] = query_parts[
                condition_dis_index
            ][: -len("[dis]")]
            freetext_params = dict(params, term=" AND ".join(freetext_query_parts))
            freetext_result = self._make_request(self.endpoint, freetext_params)
            if (
                freetext_result.get("status") == "success"
                and "esearchresult" in freetext_result.get("data", {})
                and int(freetext_result["data"]["esearchresult"].get("count", 0)) > 0
            ):
                result = freetext_result
                data = result["data"]
                condition_freetext_retry = True

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
        query_translation = esearch.get("querytranslation", "")
        response_data = {
            "total_count": count,
            "variant_ids": ids,
            "variants": variants,
            "query_translation": query_translation,
            "search_params": search_params,
        }
        # Whether `condition` acted as a disease filter on the count above is
        # part of what the count MEANS, so it belongs beside it at the top
        # level rather than inside a note the caller has to read to notice.
        condition_applied = None
        if condition_query_term is not None:
            disclosure = _condition_filter_disclosure(
                arguments.get("condition"),
                condition_query_term,
                query_translation,
                condition_freetext_retry,
            )
            response_data.update(disclosure)
            condition_applied = disclosure.get("condition_filter_applied")
        if count == 0:
            response_data.update(
                self._explain_empty_result(
                    arguments=arguments,
                    gene=gene,
                    condition_term=condition_query_term,
                    condition_applied=condition_applied,
                    clnsig_param=_clnsig_param,
                    clnsig_components=clnsig_components,
                )
            )
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

    def _explain_empty_result(
        self,
        *,
        arguments: Dict[str, Any],
        gene: Optional[str],
        condition_term: Optional[str],
        condition_applied: Optional[bool],
        clnsig_param: str,
        clnsig_components: list,
    ) -> Dict[str, Any]:
        """Attribute an empty result to the input that actually caused it.

        A 0-count is only usable if the caller can tell "ClinVar holds no such
        record" from "one of my inputs is not something ClinVar indexes", so
        the evidence is established with count-only queries (retmax=0) on a
        path that has already come back empty, rather than assumed. Both the
        gene symbol and -- since a disease NAME missing from ClinVar's index
        empties a result exactly as silently as a wrong symbol does -- the
        condition are checked on their own before anything is blamed.
        """
        extras: Dict[str, Any] = {}
        condition = arguments.get("condition")
        has_gene = "gene" in arguments

        # Fix-R9B-2: a 0-count response for a `gene` filter is
        # indistinguishable from "this gene truly has no ClinVar
        # entries" whether the symbol was a typo (e.g. "MEPC2"), a
        # protein/full name instead of the HGNC gene symbol (e.g.
        # "dystrophin" instead of "DMD"), or a species mismatch --
        # confirmed live that ClinVar's [gene] index only matches an
        # exact current HGNC symbol and has no fuzzy/synonym fallback of
        # its own. Automatically retrying with an unrestricted free-text
        # search was tried and rejected: "dystrophin[All Fields]"
        # matches 12,000+ unrelated ClinVar records that merely mention
        # the word, which would silently swap a false-empty for a
        # false-positive result set -- worse than reporting nothing.
        # Surface the ambiguity instead of guessing.
        #
        # ...but only blame the GENE when the gene is actually what failed.
        # When other filters narrowed the query, a 0 count says nothing
        # about the symbol, and the hint used to send callers off to
        # re-verify a symbol that was never the problem. Establish the
        # facts with one cheap count-only query on the bare gene term
        # before attributing the empty result to anything.
        other_filters = [
            name
            for name, present in (
                ("condition", bool(condition)),
                ("variant_id", "variant_id" in arguments),
                ("variant_name", bool(arguments.get("variant_name"))),
                ("rsid", bool(arguments.get("rsid"))),
                ("raw_term", bool(arguments.get("raw_term"))),
                (clnsig_param, bool(clnsig_components)),
            )
            if present
        ]
        gene_only_count = (
            self._count_for_term(f"{gene}[gene]")
            if has_gene and other_filters
            else None
        )
        if gene_only_count is not None:
            extras["gene_only_match_count"] = gene_only_count
        # The same evidence, for the condition: `condition` is the only other
        # input whose value has to exist in an NCBI-curated index to match
        # anything, and a name that index does not carry (a synonym, a locus
        # name, a misspelling) empties the result just as silently as a wrong
        # gene symbol -- yet it used to go unmentioned while the hint sent the
        # caller off to re-verify the symbol.
        condition_only_count = (
            self._count_for_term(f"{condition_term}[dis]")
            if condition_term is not None
            else None
        )
        if condition_only_count is not None:
            extras["condition_only_match_count"] = condition_only_count

        gene_verdict = ""
        if has_gene and gene_only_count:
            gene_verdict = (
                f" The gene symbol '{arguments['gene']}' is not the problem: it "
                f"matches {gene_only_count} ClinVar record(s) on its own."
            )

        # 1. The condition never acted as a disease filter at all -- whatever
        #    else is true, this result is not the disease-filtered answer the
        #    caller asked for.
        if condition_term is not None and condition_applied is False:
            extras["zero_result_hint"] = (
                f"No ClinVar records matched, and the condition '{condition}' was "
                "not applied as a disease filter: Entrez did not keep the [dis] "
                "field tag for it (see query_translation), so this empty result "
                "says nothing about whether ClinVar holds records for this "
                f"condition.{gene_verdict} " + _CONDITION_INDEX_GUIDANCE
            )
            return extras
        # 2. The condition name matches nothing in ClinVar's disease index at
        #    all, so it -- not the gene, not the other filters -- is what
        #    emptied the result.
        if condition_term is not None and condition_only_count == 0:
            extras["zero_result_hint"] = (
                f"The condition '{condition}' matches no ClinVar records at all on "
                f"its own ({condition_term}[dis] returns 0 across every gene), so "
                "the empty result is attributable to the condition name rather "
                f"than to the other search inputs.{gene_verdict} "
                + _CONDITION_INDEX_GUIDANCE
            )
            return extras

        if has_gene and other_filters and gene_only_count is None:
            extras["zero_result_hint"] = (
                f"No ClinVar records matched gene '{arguments['gene']}' "
                f"combined with {', '.join(other_filters)}. The gene symbol "
                "could not be checked on its own (follow-up query failed), "
                "so it is unknown whether the symbol or the other filter(s) "
                "produced the empty result -- retry with the filters removed "
                "to tell them apart."
            )
        elif has_gene and gene_only_count:
            hint = (
                f"The gene symbol '{arguments['gene']}' is fine: it matches "
                f"{gene_only_count} ClinVar record(s) on its own. The empty "
                f"result comes from the other filter(s) -- "
                f"{', '.join(other_filters)} -- which no record for this gene "
                "satisfies. Relax or correct them (or drop them to see the "
                "gene's full record set) rather than re-checking the symbol."
            )
            if condition_only_count:
                hint += (
                    f" The condition '{condition}' is itself a recognized ClinVar "
                    f"disease term ({condition_only_count} record(s) across all "
                    "genes), so this gene and this condition simply have no record "
                    "in common."
                )
            extras["zero_result_hint"] = hint
        elif has_gene:
            extras["zero_result_hint"] = (
                f"No ClinVar records matched gene '{arguments['gene']}'. "
                "ClinVar's gene index only recognizes the current official "
                "HGNC symbol (e.g. 'DMD', not the protein name 'dystrophin' "
                "or an outdated/misspelled symbol) -- verify the symbol "
                "(e.g. via HGNC_search_genes or NCBIDatasets_get_gene) "
                "before concluding this gene has no reported variants."
            )
        elif condition_term is not None:
            remaining = [f for f in other_filters if f != "condition"]
            extras["zero_result_hint"] = (
                f"The condition '{condition}' is a recognized ClinVar disease term "
                f"({condition_only_count} record(s) on its own), so the empty "
                "result comes from the other filter(s)"
                + (f" -- {', '.join(remaining)} -- " if remaining else " ")
                + "rather than from the condition name."
            )
        return extras

    def _count_for_term(self, term: str) -> "int | None":
        """Count-only eSearch for `term` (retmax=0, no summaries fetched).

        Used to establish, rather than assume, which input caused an empty
        result. Best-effort: returns None on any failure, never raises.
        """
        try:
            result = self._make_request(
                self.endpoint,
                {"db": "clinvar", "term": term, "retmode": "json", "retmax": 0},
            )
            if result.get("status") != "success":
                return None
            return int(result["data"]["esearchresult"]["count"])
        except (KeyError, TypeError, ValueError, AttributeError):
            return None

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


# How many matching records one call fetches summaries for (500 ids = 3
# esummary requests). Entrez returns ids in Variation-ID order and db=clinvar
# has no sort field, so whatever falls off this cap is arbitrary with respect to
# span -- hence the cap is disclosed rather than silently applied.
_CANDIDATE_CAP = 500

# Bases immediately upstream of the region searched with NO length filter.
# Entrez's VLEN is "the difference between reference and alternate, except when
# there is no length difference (then the length of the allele itself)" (einfo,
# db=clinvar), so a 1 nt insertion recorded between two bases can be VLEN=1 even
# though ClinVar's own start/stop span two. This pad keeps such records out of
# the filtered part of the query, so the filter can never cost a real overlap.
_EDGE_PAD = 10


def _overlap_search_term(chrom, start, end, tag, margin):
    """The Entrez term for records that could overlap [start, end].

    One flat window widened by `margin` matches every record that merely STARTS
    in it -- 15,327 for a 4 Mb window on chr11:47332696, ~97% single-base
    substitutions that stop long before the region. A record starting upstream
    can only reach the region by occupying more than one base, so the upstream
    part of the window carries `NOT 1:1[VLEN]`, which drops the candidate set to
    245 in the same single esearch request.

    Written as a NOT rather than a positive `2:...[VLEN]` range on purpose:
    records with no VLEN indexed at all exist, and this tool's flagship example
    is one -- `1703527[VID] AND 0:1000000000[VLEN]` (the 1.5 Mb copy-number loss
    over chr7:155593770) returns 0 hits. A positive range would drop exactly the
    variant class this tool was built for.
    """
    edge_lo = max(1, int(start) - _EDGE_PAD)
    parts = [f"{chrom}[chr] AND {edge_lo}:{int(end)}[{tag}]"]
    upstream_lo = max(1, int(start) - int(margin))
    upstream_hi = edge_lo - 1
    if upstream_hi >= upstream_lo:
        parts.append(
            f"{chrom}[chr] AND {upstream_lo}:{upstream_hi}[{tag}] NOT 1:1[VLEN]"
        )
    return " OR ".join(f"({p})" for p in parts)


_OVERLAP_NOTE = (
    "Entrez matches a variant's START position, so this searches a window widened "
    "upstream by `margin` and keeps only variants whose span actually overlaps the "
    "region. Single-base records (VLEN=1) are excluded from the upstream part of "
    "that window -- occupying one base, they cannot reach the region from outside "
    "it -- which is what keeps widening `margin` cheap. Sorted smallest span first; "
    "`variants` is capped at `max_results`, `n_overlapping` is how many were found."
)

_OVERLAP_REMEDY = (
    "Narrow the region, or lower `margin`, to bring the match set under "
    f"{_CANDIDATE_CAP}; widening either makes the truncation worse."
)


def _truncation_disclosure(total, inspected, how_to_get_more):
    """The keys that tell a partial scan apart from a complete one.

    A dict fragment the caller merges, like `_condition_filter_disclosure`
    above, so any capped path here can disclose the same way. Field names follow
    the repo-wide convention (`total_available` / `truncated` /
    `truncation_note`; see cbioportal_tool._truncation_fields).
    """
    if total is None:
        return {
            "total_available": None,
            "truncated": True,
            "truncation_note": (
                f"Only the first {inspected} matching records were fetched and "
                "checked for overlap, and Entrez did not report how many matched "
                f"in total, so this may be a partial answer. {how_to_get_more}"
            ),
        }
    if inspected >= total:
        return {"total_available": total, "truncated": False}
    return {
        "total_available": total,
        "truncated": True,
        "truncation_note": (
            f"INCOMPLETE SCAN: {inspected} of {total} matching records "
            f"({100.0 * inspected / total:.1f}%) were fetched and checked for "
            "overlap. Entrez returns records in Variation-ID order and db=clinvar "
            "has no sort field, so the rest are arbitrary with respect to span -- a "
            "short or empty `variants` list is NOT evidence that nothing overlaps "
            f"this region. {how_to_get_more}"
        ),
    }


def clinvar_variants_overlapping(
    session,
    chrom,
    start,
    end,
    assembly="GRCh37",
    margin=2_000_000,
    significance=None,
    max_results=50,
    timeout=60,
):
    """ClinVar variants whose span OVERLAPS a region.

    Entrez `chrpos37`/`chrpos38` match a variant's START position, so a narrow
    window finds nothing that begins upstream of it -- and a pathogenic CNV can
    begin megabases away while still covering the region asked about. Searching
    an 11 bp window for chr7:155593770-155593780 returns 0 hits even though a
    1.5 Mb copy-number loss (Variation 1703527, chr7:154831466-156356088)
    covers it.

    So: search a window widened by `margin` (`_overlap_search_term` builds the
    query), then keep only records whose [start, stop] genuinely overlaps.

    Only the first `_CANDIDATE_CAP` matching records are inspected, so the
    envelope reports `total_available` beside `n_candidates` and flags any
    shortfall: a caller concluding "no pathogenic deletion overlaps this locus"
    needs to know when that rests on a partial scan.
    """
    tag = "chrpos38" if str(assembly).upper() in ("GRCH38", "HG38") else "chrpos37"
    term = _overlap_search_term(chrom, start, end, tag, margin)
    if significance:
        # [clinsig] is not a ClinVar eSearch field -- Entrez silently degraded
        # it to [All Fields] (confirmed live: chr17 BRCA1 window, 15508 hits
        # unfiltered vs 13782 with '"Pathogenic"[clinsig]', i.e. a free-text
        # match that also keeps "Likely pathogenic" and "Conflicting
        # classifications of pathogenicity" records). Use the same verified
        # [Filter]/[prop] clause the gene search uses. Values are validated by
        # the caller against _CLINSIG_ACCEPTED.
        components = (
            significance
            if isinstance(significance, list)
            else _normalize_clinsig(significance)
        )
        clause = _clinsig_query_clause(components)
        if clause:
            term = f"({term}) AND {clause}"

    es = session.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        params={
            "db": "clinvar",
            "term": term,
            "retmax": _CANDIDATE_CAP,
            "retmode": "json",
        },
        timeout=timeout,
    ).json()
    esearchresult = es.get("esearchresult") or {}
    ids = esearchresult.get("idlist") or []
    # esearch reports the size of the whole match set in `count` whatever retmax
    # is, so the honest denominator costs no extra request.
    try:
        total_available = int(esearchresult.get("count"))
    except (TypeError, ValueError):
        total_available = None

    out = []
    for chunk_start in range(0, len(ids), 200):
        chunk = ids[chunk_start : chunk_start + 200]
        summ = (
            session.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                params={"db": "clinvar", "id": ",".join(chunk), "retmode": "json"},
                timeout=timeout,
            )
            .json()
            .get("result", {})
        )
        for vid in chunk:
            rec = summ.get(vid) or {}
            for vset in rec.get("variation_set") or []:
                for loc in vset.get("variation_loc") or []:
                    if (
                        str(loc.get("assembly_name", "")).upper()
                        != str(assembly).upper()
                    ):
                        continue
                    try:
                        v_start, v_stop = int(loc.get("start")), int(loc.get("stop"))
                    except (TypeError, ValueError):
                        continue
                    if v_start <= int(end) and v_stop >= int(start):
                        out.append(
                            {
                                "variation_id": vid,
                                "title": rec.get("title"),
                                "obj_type": rec.get("obj_type"),
                                "chr": loc.get("chr"),
                                "start": v_start,
                                "stop": v_stop,
                                "span": v_stop - v_start + 1,
                                "classification": (
                                    rec.get("germline_classification") or {}
                                ).get("description"),
                            }
                        )
                    break
    # Smallest span first: the most specific variant covering the region.
    out.sort(key=lambda v: v["span"])
    return {
        "term": term,
        **_truncation_disclosure(total_available, len(ids), _OVERLAP_REMEDY),
        "n_candidates": len(ids),
        "n_overlapping": len(out),
        "variants": out[:max_results],
        "note": _OVERLAP_NOTE,
    }


@register_tool("ClinVarSearchByRegion")
class ClinVarSearchByRegion(ClinVarRESTTool):
    """ClinVar variants overlapping a genomic region, including spanning CNVs."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        chrom = (
            str(arguments.get("chrom") or arguments.get("chromosome") or "")
            .replace("chr", "")
            .strip()
        )
        start, end = arguments.get("start"), arguments.get("end")
        region = arguments.get("region")
        if region and (start is None or end is None):
            m = re.match(
                r"^\s*chr?([\w]+)\s*[:\s]\s*([\d,]+)\s*[-.]+\s*([\d,]+)", str(region)
            )
            if m:
                chrom = chrom or m.group(1)
                start, end = (
                    int(m.group(2).replace(",", "")),
                    int(m.group(3).replace(",", "")),
                )
        if not chrom or start is None or end is None:
            return {
                "status": "error",
                "error": "Provide chrom/start/end, or region like 'chr7:155593770-155593780'.",
            }
        # Same input validation as ClinVar_search_variants: an unrecognized
        # class must not reach the query, where it would silently filter the
        # region's variants down to nothing under a `status: success`.
        clnsig_param = (
            "clinical_significance"
            if arguments.get("clinical_significance")
            else "significance"
        )
        raw_clnsig = arguments.get("clinical_significance") or arguments.get(
            "significance"
        )
        clnsig_components = []
        if str(raw_clnsig or "").strip():
            clnsig_components = _normalize_clinsig(raw_clnsig)
            invalid_clnsig = [
                c for c in clnsig_components if c not in _CLINSIG_ACCEPTED_NORMALIZED
            ]
            if invalid_clnsig:
                return _invalid_clinsig_error(clnsig_param, raw_clnsig, invalid_clnsig)
        try:
            result = clinvar_variants_overlapping(
                self.session,
                chrom,
                int(start),
                int(end),
                assembly=arguments.get("assembly", "GRCh37"),
                margin=int(arguments.get("margin", 2_000_000)),
                significance=clnsig_components or None,
                max_results=int(arguments.get("max_results", 50)),
                timeout=self.timeout,
            )
        except Exception as e:
            return {
                "status": "error",
                "error": f"ClinVar region search failed: {str(e)[:200]}",
            }
        return {"status": "success", "data": result}
