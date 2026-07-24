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
    """Look up CPIC guideline ID and RxNorm ID for a drug name via CPIC API.

    Returns (guideline_id, rxnorm_id) tuple, or None if genuinely not found
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
    of being the one place that still conflates them."""
    r = requests.get(
        f"{_CPIC_API}/drug",
        params={
            "select": "name,guidelineid,rxnormid",
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
        return row["guidelineid"], row.get("rxnormid")
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
        rxnorm_id: Optional[str] = None

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
            guideline_id, rxnorm_id = result

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
            if rxnorm_id:
                params["drugid"] = f"eq.RxNorm:{rxnorm_id}"
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
            if not data and not filtering:
                guideline_has_other_rows = False
                if rxnorm_id:
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
                    result["note"] = (
                        f"Guideline {guideline_id} has recommendation rows for "
                        f"other drugs it covers, but none specifically for "
                        f"'{drug}'. See https://cpicpgx.org/guidelines/ for the "
                        "full guideline document."
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
