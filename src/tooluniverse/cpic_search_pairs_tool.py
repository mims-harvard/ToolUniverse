"""
CPIC Search Gene-Drug Pairs Tool.

Extends BaseRESTTool with automatic PostgREST operator normalization so users
can pass plain gene symbols (e.g., 'CYP2D6') instead of 'eq.CYP2D6'.
"""

from typing import Any, Dict, Optional, Tuple

import requests

from .base_rest_tool import BaseRESTTool
from .base_tool import BaseTool
from .tool_registry import register_tool

_CPIC_API = "https://api.cpicpgx.org/v1"


def _resolve_drug_to_guideline_id(
    drug_name: str,
) -> Optional[Tuple[int, Optional[str]]]:
    """Look up CPIC guideline ID and CPIC drug identifier for a drug name.

    Returns (guideline_id, drugid) tuple, or None if genuinely not found
    (the request succeeded but no matching drug/guideline exists). Raises
    requests.exceptions.RequestException on a request failure (network
    error, timeout, HTTP error) -- Fix-R56A-1: this used to swallow those
    the same way as a genuine "not found", so a transient CPIC API hiccup
    (confirmed live: a `Max retries exceeded`/connection error while testing
    this exact endpoint) was reported to the caller as "No CPIC guideline
    found for drug 'simvastatin'" even though simvastatin IS in CPIC's
    /drug table with a real guidelineid (100426) -- misleading a caller
    into concluding the drug has no CPIC coverage at all. The rest of this
    file already distinguishes RequestException from a genuine empty result
    (see CPICGetRecommendationsTool.run's own /recommendation call below);
    this makes the /drug lookup consistent with that same pattern instead
    of being the one place that still conflates them.

    Fix-R81A-1: this used to select `rxnormid` and the caller then filtered
    /recommendation with a hardcoded `eq.RxNorm:{rxnormid}`. CPIC's
    /recommendation.drugid is a *namespaced* identifier that is NOT always
    in the RxNorm namespace, so that assumption silently broke two ways
    (see CPICGetRecommendationsTool.run). CPIC's /drug table already
    publishes the authoritative `drugid` column -- select it directly
    instead of reconstructing it from a different column."""
    r = requests.get(
        f"{_CPIC_API}/drug",
        params={
            "select": "name,guidelineid,drugid",
            "name": f"ilike.*{drug_name}*",
        },
        timeout=15,
    )
    r.raise_for_status()
    rows = r.json()
    if not rows:
        return None
    # Fix-R35C-1: substring `ilike` matching picks a false first hit
    # whenever one drug name is a substring of another -- confirmed
    # live for "citalopram" (a substring of "escitalopram") and
    # "phenytoin" (a substring of "fosphenytoin"): querying the shorter
    # name silently returned the OTHER drug's guideline/rxnorm id
    # because it happened to sort first in CPIC's unordered response,
    # so CPIC_get_recommendations returned a different drug's dosing
    # guidance with no indication of the substitution. Prefer an exact
    # case-insensitive match; only fall back to the first fuzzy hit
    # when no exact match exists (genuine partial/typo queries).
    exact = next(
        (row for row in rows if row.get("name", "").lower() == drug_name.lower()),
        None,
    )
    row = exact or rows[0]
    if row.get("guidelineid"):
        return row["guidelineid"], row.get("drugid")
    return None


@register_tool("CPICGetRecommendationsTool")
class CPICGetRecommendationsTool(BaseTool):
    """
    Get CPIC dosing recommendations by guideline_id, or auto-resolve from drug name.

    Accepts either a numeric guideline_id directly, or a drug name that is
    resolved to a guideline_id via the CPIC /drug endpoint.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        guideline_id = arguments.get("guideline_id")
        # Fix-R81A-1: the CPIC drug identifier used by /recommendation.drugid.
        # `drug` is defined here too so the note-building code below can never
        # NameError when the caller passed guideline_id directly.
        drug_id: Optional[str] = None
        drug: Optional[str] = None

        if guideline_id is None:
            drug = arguments.get("drug") or arguments.get("drug_name")
            if not drug:
                return {
                    "status": "error",
                    "error": (
                        "Either guideline_id or drug name is required. "
                        "Use CPIC_list_guidelines to browse available guidelines."
                    ),
                }
            try:
                result = _resolve_drug_to_guideline_id(drug)
            except requests.exceptions.RequestException as e:
                return {
                    "status": "error",
                    "error": f"CPIC API error while resolving drug '{drug}': {e}",
                }
            if result is None:
                # Fix-R5C-2: CPIC's /drug table only has generic names (no
                # brand-name field), so a brand name like "zoloft" never
                # matches. The old message sent callers to browse guideline
                # IDs, which doesn't actually solve "I don't know the
                # generic name" -- name the real constraint instead.
                return {
                    "status": "error",
                    "error": (
                        f"No CPIC guideline found for drug '{drug}'. "
                        "CPIC only indexes generic drug names (e.g. "
                        "'sertraline', not 'Zoloft') -- try the generic "
                        "name, or use CPIC_list_guidelines to browse "
                        "available guidelines."
                    ),
                }
            guideline_id, drug_id = result

        limit = arguments.get("limit", 50) or 50
        offset = arguments.get("offset", 0) or 0
        # Fix-R79A-1: "gene"/"phenotype" are not real params (no
        # additionalProperties: false on this schema, so they were silently
        # accepted and dropped, not rejected) -- confirmed live that
        # {"drug": "clopidogrel", "gene": "CYP2C19", "phenotype": "Poor
        # Metabolizer"} returned all 24 rows across every phenotype and
        # population/context combination for the guideline, unfiltered, with
        # no indication either filter had zero effect. A caller very
        # naturally guesses these param names, since the tool's own
        # description says it "links genotype/phenotype to prescribing
        # actions" and every returned row already carries a `phenotypes`
        # dict keyed by gene symbol -- add real client-side filtering rather
        # than just erroring more clearly on the unrecognized names, since
        # the data to filter on is already present in every response.
        gene_filter = arguments.get("gene")
        phenotype_filter = arguments.get("phenotype")
        filtering = bool(gene_filter or phenotype_filter)

        try:
            url = f"{_CPIC_API}/recommendation"
            params: Dict[str, Any] = {
                "select": "*,drug(name)",
                "guidelineid": f"eq.{guideline_id}",
                # When filtering client-side, fetch a large batch up front so
                # limit/offset apply to the FILTERED results (matching a
                # caller's expectation of "page N of the phenotype-filtered
                # list"), not to an arbitrary slice of the raw, unfiltered
                # table that the filter would then be applied to piecemeal.
                "limit": 1000 if filtering else limit,
                "offset": 0 if filtering else offset,
            }
            # Filter by specific drug within multi-drug guidelines (e.g., CYP2D6/Opioids
            # covers codeine, tramadol, hydrocodone — filter to the requested drug).
            #
            # Fix-R81A-1: this used to build the filter as
            # `eq.RxNorm:{rxnormid}`, hardcoding the RxNorm namespace. CPIC's
            # drugid is namespaced and 3 of the 170 CPIC drugs that carry a
            # guideline are NOT in the RxNorm namespace (census re-derived
            # live from api.cpicpgx.org: 167 RxNorm, 2 ATC, 1 Drugbank), which
            # broke in two opposite and equally silent directions:
            #
            #  (a) FALSE NEGATIVE -- gentamicin has an rxnormid (1596450) but
            #      its drugid is `ATC:D06AX07`, so `eq.RxNorm:1596450` matched
            #      0 of the 33 rows on the MT-RNR1 aminoglycoside guideline
            #      (826283). The tool then emitted "...none specifically for
            #      'gentamicin'", asserting an absence that is not real: the 3
            #      rows exist and carry the "Avoid aminoglycoside antibiotics"
            #      recommendation for the m.1555A>G high-risk genotype. An
            #      audiologist checking before dosing got a confident no-data
            #      answer for the archetypal ototoxic aminoglycoside.
            #
            #  (b) FALSE POSITIVE -- lumiracoxib and ramosetron have a NULL
            #      rxnormid, so `if rxnorm_id:` was falsy and NO drug filter
            #      was applied at all. `{"drug": "lumiracoxib"}` returned all
            #      42 rows of NSAID guideline 110058 -- every one of which
            #      belongs to celecoxib/ibuprofen/meloxicam/piroxicam/
            #      flurbiprofen/lornoxicam/tenoxicam, and none to lumiracoxib
            #      -- presented as that drug's own recommendations.
            #
            # Filtering on the drugid CPIC itself publishes fixes both. For
            # every RxNorm-namespaced drug the built string is byte-identical
            # to the old one (drugid == "RxNorm:" + rxnormid holds for all 167
            # of them), so those queries are unchanged. All 324 CPIC drugids
            # are alphanumerics plus ':' only, so no PostgREST quoting is
            # needed for the eq. value.
            if drug_id:
                params["drugid"] = f"eq.{drug_id}"
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()

            available_phenotypes = None
            if filtering:
                available_phenotypes = sorted(
                    {
                        v
                        for row in data
                        for k, v in (row.get("phenotypes") or {}).items()
                        if not gene_filter or k.lower() == gene_filter.lower()
                    }
                )

                def _row_matches(row: Dict[str, Any]) -> bool:
                    phenotypes = row.get("phenotypes") or {}
                    if gene_filter:
                        gene_key = next(
                            (k for k in phenotypes if k.lower() == gene_filter.lower()),
                            None,
                        )
                        if gene_key is None:
                            return False
                        if phenotype_filter:
                            return (
                                phenotypes[gene_key].lower() == phenotype_filter.lower()
                            )
                        return True
                    # No gene given: match if ANY gene's phenotype value hits.
                    return any(
                        v.lower() == phenotype_filter.lower()
                        for v in phenotypes.values()
                    )

                data = [row for row in data if _row_matches(row)]
                data = data[offset : offset + limit]

            result: Dict[str, Any] = {
                "guideline_id": guideline_id,
                "recommendations": data,
                "count": len(data),
            }
            if filtering and not data:
                result["note"] = (
                    f"No recommendations matched gene={gene_filter!r} "
                    f"phenotype={phenotype_filter!r} for guideline {guideline_id}. "
                    f"Available phenotype values for this guideline"
                    + (f" and gene {gene_filter}" if gene_filter else "")
                    + f": {available_phenotypes or '[]'}."
                )
            # Fix-R31C-3: this note used to fire whenever `data` was empty and
            # always blame it on "guideline uses a dosing algorithm" -- but
            # confirmed live that's wrong for a multi-drug guideline filtered
            # to a specific drug (e.g. guideline 100416/CYP2D6-opioids has 66
            # real recommendation rows, just none for methadone/buprenorphine/
            # naltrexone specifically -- only codeine/tramadol/hydrocodone).
            # Distinguish "no table at all" (the real dosing-algorithm case,
            # e.g. warfarin/100425) from "table exists, not for this drug" by
            # checking whether the guideline has any rows once the drug
            # filter is dropped. Skip when a gene/phenotype filter caused the
            # emptiness -- the more specific note above already explains why.
            # Fix-R81A-1: when a drug name was given but CPIC publishes no
            # drugid for it, no drug filter could be applied, so these rows are
            # the WHOLE guideline and may belong to other drugs it covers. Say
            # so instead of letting the caller read them as this drug's own
            # recommendations. (No CPIC drug currently hits this -- all 324
            # have a drugid -- but the old code reached exactly this state via
            # the null-rxnormid path, so the response must be honest about it
            # rather than silently mislabeling another drug's guidance.)
            if data and drug and not drug_id:
                result["note"] = (
                    f"CPIC publishes no drug identifier for '{drug}', so these "
                    f"rows could NOT be filtered to it -- they are all "
                    f"recommendation rows in guideline {guideline_id} and may "
                    f"cover other drugs. Check each row's 'drug' field before "
                    "applying any of this guidance."
                )
            if not data and not filtering:
                guideline_has_other_rows = False
                if drug_id:
                    try:
                        check = requests.get(
                            url,
                            params={"guidelineid": f"eq.{guideline_id}", "limit": 1},
                            timeout=30,
                        )
                        check.raise_for_status()
                        guideline_has_other_rows = bool(check.json())
                    except requests.exceptions.RequestException:
                        pass
                if guideline_has_other_rows:
                    # Fix-R81A-1: name the identifier the absence was actually
                    # established against. This claim is only trustworthy
                    # because the filter now uses CPIC's own drugid; when it
                    # was a reconstructed `RxNorm:{rxnormid}` guess the same
                    # sentence asserted a false absence for gentamicin. Quoting
                    # the drugid makes the assertion auditable against
                    # /recommendation?drugid=eq.<id> rather than unfalsifiable.
                    result["note"] = (
                        f"Guideline {guideline_id} has recommendation rows for "
                        f"other drugs it covers, but none specifically for "
                        f"'{drug}' (CPIC drug identifier {drug_id}). See "
                        "https://cpicpgx.org/guidelines/ for the full "
                        "guideline document."
                    )
                else:
                    result["note"] = (
                        f"No discrete recommendations found for guideline {guideline_id}. "
                        "Some guidelines (e.g. warfarin, guideline 100425) use a dosing "
                        "algorithm rather than a recommendation table. "
                        "See https://cpicpgx.org/guidelines/ for the full guideline document."
                    )
            return {"status": "success", "data": result}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"CPIC API error: {e}"}


@register_tool("CPICListGuidelinesTool")
class CPICListGuidelinesTool(BaseTool):
    """
    List CPIC pharmacogenomic guidelines with optional gene-symbol filtering.

    Fetches all guidelines and optionally filters client-side by gene symbol,
    since the CPIC /guideline endpoint does not support server-side gene filtering.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene = (arguments.get("gene") or arguments.get("gene_symbol") or "").upper()
        original_drug = arguments.get("drug") or arguments.get("drug_name") or ""
        drug = original_drug.lower()

        try:
            r = requests.get(
                f"{_CPIC_API}/guideline",
                params={"select": "*,drug(name)"},
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"CPIC API error: {e}"}

        if gene:
            data = [
                g
                for g in data
                if any(s.upper() == gene for s in (g.get("genes") or []))
            ]

        # Client-side drug name filtering (Feature-123A-003)
        if drug:
            data = [
                g
                for g in data
                if any(
                    drug in (d.get("name") or "").lower() for d in (g.get("drug") or [])
                )
            ]

        return {
            "status": "success",
            "data": data,
            "metadata": {
                "total": len(data),
                "gene_filter": gene or None,
                "drug_filter": original_drug or None,
            },
        }


# PostgREST filter operator prefixes
_POSTGREST_OPS = (
    "eq.",
    "neq.",
    "gt.",
    "gte.",
    "lt.",
    "lte.",
    "like.",
    "ilike.",
    "is.",
    "in.(",
    "not.",
    "cs.",
    "cd.",
)


@register_tool("CPICSearchPairsTool")
class CPICSearchPairsTool(BaseRESTTool):
    """
    Search CPIC gene-drug pairs with automatic PostgREST operator normalization.

    Accepts plain gene symbols and CPIC levels (e.g., 'CYP2D6', 'A') and
    auto-prepends the required 'eq.' PostgREST operator so users do not need
    to know the PostgREST filter syntax.
    """

    # Parameters that are PostgREST column filters requiring the eq. prefix
    _FILTER_PARAMS = ("genesymbol", "cpiclevel")

    def _resolve_aliases(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve gene_symbol/gene aliases to genesymbol."""
        normalized = dict(args)
        if not normalized.get("genesymbol"):
            alias = normalized.pop("gene_symbol", None) or normalized.pop("gene", None)
            if alias:
                normalized["genesymbol"] = alias
        else:
            normalized.pop("gene_symbol", None)
            normalized.pop("gene", None)
        return normalized

    def _build_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        # Resolve aliases then auto-prepend 'eq.' to bare PostgREST filter values.
        # Only done here (not in _build_url) because the URL template already
        # embeds 'eq.' inline (e.g. ?genesymbol=eq.{genesymbol}).
        normalized = self._resolve_aliases(args)
        for key in self._FILTER_PARAMS:
            val = normalized.get(key)
            if (
                val
                and isinstance(val, str)
                and not any(val.startswith(op) for op in _POSTGREST_OPS)
            ):
                normalized[key] = f"eq.{val}"
        return super()._build_params(normalized)

    def _build_url(self, args: Dict[str, Any]) -> str:
        return super()._build_url(self._resolve_aliases(args))

    def _process_response(
        self, response: requests.Response, url: str
    ) -> Dict[str, Any]:
        """Report the URL that was actually requested, filters included.

        Feature-26C-4: the base class reports the endpoint *template* as the
        response's `url`, while the PostgREST filter clauses this tool builds
        (``genesymbol=eq.HLA-B``, ``cpiclevel=eq.A``, ``limit=...``) travel
        separately in the request's query params. Confirmed live that the two
        answers `{"gene": "HLA-B"}` (13 rows) and `{}` (635 rows) advertised a
        byte-identical url --
        `.../pair?select=genesymbol,drugid,cpiclevel,guidelineid,usedforrecommendation,clinpgxlevel,pgxtesting,drug(name)`
        -- which returns all 635 rows when pasted, so a caller spot-checking
        provenance concludes the gene filter was ignored (it was not; only the
        reported url was wrong). `response.url` is the URL requests actually
        sent, assembled from the very params object used for the request, so
        the advertised and requested URLs cannot drift apart again. This is the
        same shape CPICGetAllelesTool in this module already reports.
        """
        result = super()._process_response(response, url)
        if (
            isinstance(result, dict)
            and "url" in result
            and isinstance(response.url, str)
        ):
            result["url"] = response.url
        return result


@register_tool("CPICGetAllelesTool")
class CPICGetAllelesTool(BaseTool):
    """List CPIC star alleles for a gene, with a true total and paging.

    Fix-R4B-4: this tool ran as a plain BaseRESTTool over a URL template
    carrying `limit={limit}` with a default of 50, and the only count in the
    response was `count`, which reported the size of the returned page. So
    `CPIC_get_alleles {"genesymbol": "CYP2D6"}` came back with 50 alleles and
    `count: 50` -- indistinguishable from CYP2D6 genuinely having 50 alleles,
    when CPIC actually curates 208 (confirmed live via the PostgREST
    `Content-Range` header, `0-207/208`). A pharmacogenomics user calling
    star alleles from that page silently loses 158 of them, and there was no
    `offset` to walk the rest. Ask PostgREST for the exact count, report it,
    and page explicitly.

    Feature-33-2: the `select` clause also dropped CPIC's `frequency` object --
    the per-biogeographic-group star-allele frequencies -- so every row came
    back as just name/functionalstatus/activityvalue/clinicalfunctionalstatus.
    CPIC populates frequency on most but not all alleles (measured: 36 of 49
    for CYP2C19, 183 of 208 for CYP2D6), and it is the one field a
    pharmacogenomics counselling note needs; there is no other route to it in
    this tool. See `_SELECT_FIELDS` for what is now requested and why.
    """

    _DEFAULT_LIMIT = 50
    _MAX_LIMIT = 1000

    # `findings` is deliberately NOT selected: it is narrative prose restating
    # `strength`, and measured 78,541 bytes across CYP2D6's 208 alleles versus
    # 9,621 for `citations`, which grounds the same claim by PMID.
    _SELECT_FIELDS = (
        "name",
        "functionalstatus",
        "activityvalue",
        "clinicalfunctionalstatus",
        # CPIC's own biogeographic-group labels ("Sub-Saharan African",
        # "Central/South Asian", ...) are passed through verbatim -- remapping
        # them onto gnomAD population codes would relabel an ancestry group.
        # CPIC returns null (never {}) where it publishes no frequency, and a
        # published 0.0 for a group is real data: 16 of CYP2C19's 49 alleles
        # carry at least one 0.0, so null must never be collapsed to zero.
        "frequency",
        "inferredfrequency",
        "strength",
        "citations",
    )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch one page of alleles plus the gene's true allele count."""
        gene = arguments.get("genesymbol")
        if not gene:
            return {"status": "error", "error": "genesymbol is required (e.g. CYP2D6)"}
        gene = str(gene).upper()

        raw_limit = arguments.get("limit")
        limit = self._DEFAULT_LIMIT if raw_limit in (None, "") else int(raw_limit)
        limit = max(1, min(limit, self._MAX_LIMIT))
        offset = max(0, int(arguments.get("offset") or 0))

        params = {
            "genesymbol": f"eq.{gene}",
            "select": ",".join(self._SELECT_FIELDS),
            "limit": limit,
            "offset": offset,
        }
        try:
            # Prefer: count=exact makes PostgREST report the unpaged total in
            # the Content-Range response header ("0-49/208").
            response = requests.get(
                f"{_CPIC_API}/allele",
                params=params,
                headers={"Prefer": "count=exact"},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"CPIC API error: {e}"}

        total = self._total_from_content_range(response.headers.get("Content-Range"))
        if total is None:
            total = offset + len(data)

        result: Dict[str, Any] = {
            "status": "success",
            "data": data,
            "url": response.url,
            "count": len(data),
            "total_count": total,
            "offset": offset,
        }
        if data and offset + len(data) < total:
            result["note"] = (
                f"Showing alleles {offset + 1}-{offset + len(data)} of {total} curated "
                f"by CPIC for {gene}. Re-run with offset={offset + len(data)} for the "
                f"next page, or raise 'limit' (max {self._MAX_LIMIT})."
            )
        elif not data and total:
            result["note"] = (
                f"No alleles at offset={offset}; {gene} has {total} alleles in CPIC."
            )
        return result

    @staticmethod
    def _total_from_content_range(header: Optional[str]) -> Optional[int]:
        """Parse the unpaged total out of a PostgREST Content-Range header."""
        if not header or "/" not in header:
            return None
        total = header.rsplit("/", 1)[1].strip()
        return int(total) if total.isdigit() else None
