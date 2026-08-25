import re
import requests
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

_EFO_ID_RE = re.compile(r"^[A-Z]+[_:]\d+")

# Fix-R31-1: the GWAS Catalog REST API v2 has NO server-side p-value filter.
# Verified against the published OpenAPI document
#   https://www.ebi.ac.uk/gwas/rest/api/v2/rest-api-doc.yaml
# (linked from https://www.ebi.ac.uk/gwas/rest/api/v2/swagger-ui/index.html):
# GET /v2/associations declares exactly these query parameters --
_V2_ASSOCIATION_QUERY_PARAMS = (
    "pubmed_id, rs_id, full_pvalue_set, accession_id, efo_trait, efo_id, "
    "show_child_trait, mapped_gene, extended_geneset, sort, direction, page, size"
)
# -- and nothing else. A `p_upper=` parameter looks supported because the API
# echoes unknown query parameters back inside the HAL `_links` hrefs, but it is
# silently ignored: confirmed live that
#   /v2/associations?efo_id=EFO_0009184&size=100&sort=p_value&direction=asc&p_upper=1e-300
# still returns all 68 associations (p-values down to 3e-30), identical to the
# unfiltered call. The same is true of p_value, pvalue_upper, p_value_max,
# pUpper, p_value_lte, ... -- every candidate returns the full 68 rows.
# The threshold therefore has to stay CLIENT-SIDE, and that fact plus its
# consequences must be disclosed to the caller rather than silently mistaken
# for a property of the trait.
_CLIENT_SIDE_FILTER_NOTE = (
    "The p_value threshold is applied CLIENT-SIDE, to the page of associations "
    "fetched from GWAS Catalog -- not by the API. The GWAS Catalog REST API v2 "
    "exposes no server-side p-value filter: its OpenAPI document "
    "(https://www.ebi.ac.uk/gwas/rest/api/v2/rest-api-doc.yaml) declares only "
    f"[{_V2_ASSOCIATION_QUERY_PARAMS}] on GET /v2/associations, and unknown "
    "parameters such as 'p_upper' are echoed back in _links but do not filter "
    "anything. To make the client-side threshold meaningful this tool fetches "
    "the page in p_value-ascending (most-significant-first) order, so the rows "
    "it filters are the ones that can actually pass."
)


def _order_ci_bounds(record: Dict[str, Any]) -> Dict[str, Any]:
    """Swap ``ci_lower``/``ci_upper`` when the upstream record has them inverted.

    GWAS Catalog derives these two numbers by splitting its own ``range``
    string, and sometimes writes that string high-bound-first, so the values
    arrive under field names that assert the opposite ordering. Measured live on
    2026-08-11 over 1,172 associations (periodontitis MONDO_0005076, asthma
    MONDO_0004979, BMI EFO_0004340), 4 were inverted -- all 4 in periodontitis,
    where they are 4 of its 172 rows:

        range=[0.07-0.03]  ci_lower=0.07  ci_upper=0.03  rs75933965 TCF7L2 p=6e-13
        range=[0.06-0.02]  ci_lower=0.06  ci_upper=0.02  rs149290349 ZFP36L2
        range=[0.1-0.06]   ci_lower=0.1   ci_upper=0.06  rs76895963 CCND2
        range=[0.05-0.01]  ci_lower=0.05  ci_upper=0.01  rs77464186 ARAP1

    The first is the TCF7L2 locus, a top periodontitis hit, so it lands in any
    results table. Confirmed at
    https://www.ebi.ac.uk/gwas/rest/api/v2/associations/105855749.

    The bounds are ordered from the two NUMERIC fields; ``range`` is deliberately
    never re-parsed. Its bounds are joined by a bare "-" that is also the minus
    sign of a negative bound, so a ``split("-")`` would corrupt exactly the rows
    it looks safe on: the same sweep found 3 genuinely negative ranges, e.g.
    "[-0.00131-0.00151]", whose upstream ci_lower/ci_upper (-0.00131, 0.00151)
    are already correct and already correctly ordered. ``range`` is therefore
    passed through verbatim, and remains the record of what upstream sent.
    """
    lower, upper = record.get("ci_lower"), record.get("ci_upper")
    # 15 of the 172 periodontitis rows have no bounds at all -- upstream sends
    # range "-" or "[NR]" and ci_lower/ci_upper null -- so both must be numbers
    # before they can be compared.
    if (
        isinstance(lower, (int, float))
        and isinstance(upper, (int, float))
        and lower > upper
    ):
        return {**record, "ci_lower": upper, "ci_upper": lower}
    return record


class GWASRESTTool(BaseTool):
    """Base class for GWAS Catalog REST API tools."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = "https://www.ebi.ac.uk/gwas/rest/api"
        self.endpoint = ""  # Will be set by subclasses

    def _make_request(
        self, endpoint: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make a request to the GWAS Catalog API."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}

    def _coerce_str(self, value: Any) -> Optional[str]:
        """Return a stripped string, or None."""
        if not isinstance(value, str):
            return None
        s = value.strip()
        return s or None

    def _coerce_int(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _coerce_float(value: Any) -> Optional[float]:
        if value is None or isinstance(value, bool):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _efo_id_from_uri_or_id(self, value: Any) -> Optional[str]:
        """
        Best-effort normalize an EFO/OBA/etc identifier.

        Accepts either a full URI (e.g., 'http://www.ebi.ac.uk/efo/OBA_2050062')
        or a bare ID (e.g., 'OBA_2050062' or 'OBA:2050062').

        Note: The GWAS Catalog v2 REST API supports filtering by `efo_id` (and
        sometimes `efo_trait`) on associations/studies endpoints. Passing a full
        URI via `efo_uri` is not consistently supported; we normalize to `efo_id`.
        """
        s = self._coerce_str(value)
        if not s:
            return None
        if s.startswith(("http://", "https://")):
            s = s.rstrip("/").rsplit("/", 1)[-1]
        # Support CURIE-style IDs like "EFO:0001645" or "OBA:2050062" by converting
        # ":" to "_" (GWAS Catalog expects underscore form, e.g., "EFO_0001645").
        if ":" in s and "/" not in s and " " not in s:
            left, right = s.split(":", 1)
            if left and right:
                s = f"{left}_{right}"
        s = s.strip()
        return s or None

    def _resolve_trait_to_efo(self, disease_trait: str) -> Optional[Dict[str, Any]]:
        """Resolve a disease trait name to an EFO term.

        Returns ``{"efo_id": ..., "efo_label": ..., "source": ...}`` or None.

        Tries the GWAS Catalog efoTraits endpoint first, then falls back to
        a study-based resolution. The /v2/associations endpoint ignores the
        disease_trait query parameter, so we must resolve to an EFO ID.

        Fix-R31-2: this used to return the bare ID, so callers could only
        surface ``resolved_efo_id`` with no label -- and a *substitution* was
        indistinguishable from an exact hit. Confirmed live:
        disease_trait="cardiorespiratory fitness" finds nothing in efoTraits
        and falls through to /v2/studies, whose single matching study
        (GCST90310239, disease_trait "Cardiorespiratory fitness") is tagged
        EFO_0009184 = "heart rate response to exercise" -- a different
        physiological construct from VO2max (EFO_0004887, "maximal oxygen
        uptake measurement"). The label travels with the ID now so callers
        can see the substitution instead of trusting a bare accession.
        """
        # Primary: GWAS Catalog efoTraits endpoint (v1)
        try:
            resp = requests.get(
                f"{self.base_url}/efoTraits/search/findByEfoTrait",
                params={"trait": disease_trait},
                timeout=15,
            )
            if resp.status_code == 200:
                traits = resp.json().get("_embedded", {}).get("efoTraits", [])
                if traits:
                    short_name = traits[0].get("shortForm")
                    if short_name:
                        return {
                            "efo_id": short_name,
                            "efo_label": self._coerce_str(traits[0].get("trait")),
                            "source": "GWAS Catalog efoTraits trait-label lookup",
                        }
        except Exception:
            pass

        # Fallback: search studies by disease_trait, extract efo_id from first result
        try:
            resp = requests.get(
                f"{self.base_url}/v2/studies",
                params={"disease_trait": disease_trait, "size": 1},
                timeout=15,
            )
            if resp.status_code == 200:
                studies = resp.json().get("_embedded", {}).get("studies", [])
                if studies:
                    efo_traits = studies[0].get("efo_traits", [])
                    if efo_traits:
                        efo_id = efo_traits[0].get("efo_id")
                        if efo_id:
                            return {
                                "efo_id": efo_id,
                                "efo_label": self._coerce_str(
                                    efo_traits[0].get("efo_trait")
                                ),
                                "source": (
                                    "EFO term tagged on GWAS Catalog study "
                                    f"{studies[0].get('accession_id')} "
                                    f"(reported trait: "
                                    f"{studies[0].get('disease_trait')!r})"
                                ),
                            }
        except Exception:
            pass

        return None

    def _resolve_trait_to_efo_id(self, disease_trait: str) -> Optional[str]:
        """Backwards-compatible wrapper returning only the EFO ID."""
        resolved = self._resolve_trait_to_efo(disease_trait)
        return resolved.get("efo_id") if resolved else None

    def _trait_candidates_from_free_text_search(
        self, disease_trait: str, max_studies: int = 3
    ) -> List[Dict[str, str]]:
        """Look up candidate EFO terms via GWAS Catalog's own free-text search.

        Fix-R31-2 (additive): both resolver tiers above are exact-ish label
        matches, so a common informal name hard-errors even when the Catalog
        plainly holds the data -- e.g. 'VO2max' and 'maximal oxygen uptake'
        both fail, yet https://www.ebi.ac.uk/gwas/api/search?q=VO2max finds
        study GCST90296672 tagged EFO_0004887 "maximal oxygen uptake
        measurement".

        This deliberately does NOT auto-select a term: the top study for
        'VO2max' is tagged both EFO_0007768 ("response to exercise", a broad
        parent) and EFO_0004887, and picking one would be exactly the kind of
        silent substitution Fix-R31-2 exists to prevent. The candidates are
        only used to turn an unhelpful hard error into an actionable one.
        """
        candidates: List[Dict[str, str]] = []
        seen = set()
        try:
            resp = requests.get(
                "https://www.ebi.ac.uk/gwas/api/search",
                params={"q": disease_trait, "max": 10},
                timeout=15,
            )
            if resp.status_code != 200:
                return []
            docs = resp.json().get("response", {}).get("docs", []) or []
        except Exception:
            return []

        accessions = []
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            acc = doc.get("accessionId")
            if acc and acc not in accessions:
                accessions.append(acc)
            if len(accessions) >= max_studies:
                break

        for acc in accessions:
            study = self._fetch_study(acc)
            if not study:
                continue
            for term in study.get("efo_traits", []) or []:
                efo_id = term.get("efo_id")
                if not efo_id or efo_id in seen:
                    continue
                seen.add(efo_id)
                candidates.append(
                    {
                        "efo_id": efo_id,
                        "efo_label": term.get("efo_trait") or "",
                        "study_accession": acc,
                        "study_reported_trait": study.get("disease_trait") or "",
                    }
                )
        return candidates

    def _fetch_study(self, accession_id: str) -> Optional[Dict[str, Any]]:
        """Fetch one study record, or None if it cannot be retrieved."""
        try:
            resp = requests.get(
                f"{self.base_url}/v2/studies/{accession_id}", timeout=15
            )
            if resp.status_code == 200:
                study = resp.json()
                return study if isinstance(study, dict) else None
        except Exception:
            pass
        return None

    def _unresolved_trait_hint(self, disease_trait: str) -> str:
        """Suffix listing candidate EFO terms found by free-text search."""
        candidates = self._trait_candidates_from_free_text_search(disease_trait)
        if not candidates:
            return ""
        rendered = "; ".join(
            f"{c['efo_id']} ({c['efo_label']}) -- from study "
            f"{c['study_accession']} '{c['study_reported_trait']}'"
            for c in candidates
        )
        return (
            " GWAS Catalog's own free-text search DOES find studies matching "
            f"'{disease_trait}'. Candidate EFO terms tagged on them: {rendered}. "
            "Re-run with efo_id set to whichever of those is the phenotype you "
            "mean -- this tool will not guess between them for you."
        )

    @staticmethod
    def _trait_substitution_note(
        disease_trait: str, efo_id: str, efo_label: Optional[str], source: str
    ) -> Optional[str]:
        """Warn when the resolved EFO label is not the submitted trait."""
        if not efo_label:
            return (
                f"Your trait query '{disease_trait}' was resolved to EFO term "
                f"'{efo_id}' ({source}); GWAS Catalog returned no label for that "
                "term, so the substitution could not be verified. Results below "
                f"describe '{efo_id}', not necessarily '{disease_trait}'."
            )
        if efo_label.strip().casefold() == disease_trait.strip().casefold():
            return None
        return (
            f"TRAIT SUBSTITUTION: your query '{disease_trait}' was resolved to "
            f"EFO term '{efo_id}' whose label is '{efo_label}', which is NOT an "
            f"exact match for what you asked for ({source}). Every result below "
            f"describes '{efo_label}'. Confirm that is the phenotype you meant "
            "before using these associations; if it is not, pass efo_id "
            "explicitly."
        )

    def _annotate_trait_resolution(
        self, result: Dict[str, Any], disease_trait: Optional[str], resolution: Any
    ) -> None:
        """Attach resolved EFO id + label + original query to a result."""
        if not disease_trait or not isinstance(result, dict):
            return
        if isinstance(resolution, dict):
            efo_id = resolution.get("efo_id")
            efo_label = resolution.get("efo_label")
            source = resolution.get("source")
        else:
            efo_id, efo_label, source = resolution, None, None
        if not efo_id:
            return
        result["query_trait"] = disease_trait
        result["resolved_efo_id"] = efo_id
        if not source:
            # The caller supplied efo_id explicitly; no lookup happened, so
            # there is no substitution to disclose.
            result["trait_resolution_source"] = (
                "efo_id supplied by the caller (the trait text was not used "
                "to look anything up)"
            )
            return
        result["resolved_efo_label"] = efo_label
        result["trait_resolution_source"] = source
        note = self._trait_substitution_note(disease_trait, efo_id, efo_label, source)
        if note:
            result["trait_resolution_note"] = note

    def _resolve_trait_or_error(
        self, disease_trait: Optional[str], efo_id: Optional[str]
    ) -> Dict[str, Any]:
        """Resolve disease_trait to efo_id if needed.

        Returns {"efo_id": <str>, "efo_label": <str|None>, "source": <str|None>}
        on success, or {"error": <dict>} when resolution fails and would produce
        an unfiltered query.
        Callers check ``"error" in result`` and return ``result["error"]``.
        """
        if disease_trait and not efo_id:
            resolved = self._resolve_trait_to_efo(disease_trait)
            if resolved:
                return dict(resolved)
            return {
                "error": {
                    "status": "error",
                    "error": (
                        f"Could not resolve trait '{disease_trait}' to an EFO ID. "
                        "GWAS Catalog uses specific EFO/MONDO terms. "
                        "For drug response traits, use the underlying disease instead "
                        "(e.g., 'depression' or 'major depressive disorder' instead of "
                        "'antidepressant response'). Or provide efo_id directly "
                        "(e.g., 'MONDO_0002009' for major depressive disorder, "
                        "'EFO_0000305' for breast carcinoma)."
                        + self._unresolved_trait_hint(disease_trait)
                    ),
                },
            }
        return {"efo_id": efo_id, "efo_label": None, "source": None}

    @staticmethod
    def _empty_result_note(efo_id: str) -> str:
        """Return a suggestion note when no associations are found for an EFO ID."""
        # Fix-R11B-2: this note previously suggested retrying with a
        # different disease_trait text query, using a hardcoded, unrelated
        # example ("colorectal cancer") that didn't adapt to the caller's
        # actual query. Confirmed live that for a real empty-result case
        # (LCT/lactase persistence), the trait itself was resolvable but
        # simply had no directly-tagged associations -- the associations
        # existed under other EFO terms, and the tool that actually found
        # them was GWAS_search_associations_by_gene/gwas_get_snps_for_gene
        # (gene-based lookup), not a reworded trait string. Point to that
        # real fallback instead of a generic, non-adaptive example.
        #
        # Fix-R13C-1: GWAS Catalog's own trait-label search (used to
        # resolve a plain-text disease_trait) isn't restricted to EFO --
        # it also returns HPO/Orphanet/MONDO terms, and does no synonym
        # expansion, so the exact current clinical term for a disease can
        # resolve to a real-but-disconnected ontology term with zero
        # tagged associations while an older/alternate synonym resolves
        # to a term with real data. Confirmed live: "premature ovarian
        # insufficiency" resolves to HP_0008209 (0 associations), but the
        # older synonym "premature ovarian failure" resolves to
        # MONDO_0005387 (9 real associations, e.g. PMID 21989058).
        non_efo = not efo_id.upper().startswith("EFO")
        ontology_hint = (
            f" '{efo_id}' is not an EFO term (GWAS Catalog's trait search "
            "also returns HPO/Orphanet/MONDO terms), and this ontology "
            "does no synonym expansion, so it may resolve a current "
            "clinical term to a real-but-disconnected entry."
            if non_efo
            else ""
        )
        return (
            f"No associations found for EFO ID '{efo_id}'.{ontology_hint} "
            "GWAS Catalog may tag related associations under a different "
            "EFO/MONDO term, or under pleiotropic traits rather than this "
            "specific one -- try an older/alternate clinical synonym of "
            "the trait (e.g. an outdated but still-indexed name) if one "
            "exists. If you know the gene of interest, try "
            "GWAS_search_associations_by_gene or gwas_get_snps_for_gene "
            "instead, which search by gene rather than by trait term."
        )

    @staticmethod
    def _filtered_to_empty_note(
        efo_id: Optional[str],
        removed: int,
        threshold: Any,
        total_elements: Any,
    ) -> str:
        """Note for 'empty because a CLIENT-SIDE filter removed every row'.

        Fix-R31-1: this case used to fall through to _empty_result_note, which
        blames the trait term and tells the caller to try a synonym or a
        gene-based tool -- advice that is guaranteed useless, because the trait
        was never the problem. Confirmed live: efo_id=EFO_0004340 (BMI) with
        p_value=5e-08 returned data=[] together with, in the same payload,
        pagination.totalElements=23608. The message must name the filter.
        """
        subject = f"EFO ID '{efo_id}'" if efo_id else "this query"
        catalog_total = ""
        if isinstance(total_elements, int):
            catalog_total = (
                f" GWAS Catalog holds {total_elements} association(s) for "
                f"{subject} in total (see metadata.pagination.totalElements, "
                "which counts the UNFILTERED set)."
            )
        return (
            f"0 associations returned because the client-side p_value <= "
            f"{threshold} filter removed all {removed} association(s) fetched "
            f"for {subject}. The filter removed them -- the trait term is NOT "
            f"the problem.{catalog_total} Re-run without p_value, or with a "
            "less strict threshold, to see the associations that do exist. "
            + _CLIENT_SIDE_FILTER_NOTE
        )

    def _add_empty_result_note(
        self,
        result: Dict[str, Any],
        efo_id: Optional[str],
        filter_removed: int = 0,
        filter_threshold: Any = None,
    ) -> None:
        """Add a suggestion note to result if the data list is empty.

        ``filter_removed`` is the number of rows a client-side filter deleted.
        When it is non-zero the emptiness is attributed to the filter, not to
        the trait term (Fix-R31-1).
        """
        if not (isinstance(result.get("data"), list) and not result["data"]):
            return
        if filter_removed:
            total_elements = (
                (result.get("metadata") or {}).get("pagination") or {}
            ).get("totalElements")
            result["note"] = self._filtered_to_empty_note(
                efo_id, filter_removed, filter_threshold, total_elements
            )
            return
        if efo_id:
            result["note"] = self._empty_result_note(efo_id)

    def _get_one(self, record_id: Any) -> Dict[str, Any]:
        """Fetch one record by ID, with the same row repair the list path applies.

        The three ``*ByID`` tools all fetch ``{endpoint}/{id}`` and return the
        record verbatim, bypassing ``_extract_embedded_data`` -- so without a
        shared seam here each of them has to remember ``_order_ci_bounds``
        separately, and a fourth one added later would silently forget. Only
        associations carry confidence bounds today; the repair is keyed on the
        field pair, so it is a no-op for studies and SNPs.
        """
        return _order_ci_bounds(self._make_request(f"{self.endpoint}/{record_id}"))

    def _extract_embedded_data(
        self, data: Dict[str, Any], data_type: str
    ) -> Dict[str, Any]:
        """Extract data from the _embedded structure and add metadata."""
        if "error" in data:
            if "status" not in data:
                return {"status": "error", **data}
            return data

        result: Dict[str, Any] = {"status": "success", "data": [], "metadata": {}}
        metadata: Dict[str, Any] = {}

        # Extract the main data from _embedded
        if "_embedded" in data and data_type in data["_embedded"]:
            result["data"] = [
                _order_ci_bounds(row) for row in data["_embedded"][data_type]
            ]

        # Extract pagination metadata
        if "page" in data:
            metadata["pagination"] = data["page"]

        # Extract links metadata
        if "_links" in data:
            metadata["links"] = data["_links"]

        if metadata:
            result["metadata"] = metadata

        # If no _embedded structure and no array was extracted, keep data as empty array
        # This handles the case where API returns pagination metadata but no results

        return result

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        return self._make_request(self.endpoint, arguments)


@register_tool("GWASAssociationSearch")
class GWASAssociationSearch(GWASRESTTool):
    """Search for GWAS associations by various criteria."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/associations"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for associations with optional filters."""
        params = {}

        # Handle various search parameters
        # accept 'query' and 'trait' as aliases for 'disease_trait'
        disease_trait = self._coerce_str(
            arguments.get("disease_trait")
            or arguments.get("query")
            or arguments.get("trait")
        )

        # Prefer efo_id filtering. If user provided efo_uri, normalize to efo_id.
        efo_id = self._efo_id_from_uri_or_id(arguments.get("efo_id"))
        if not efo_id:
            efo_id = self._efo_id_from_uri_or_id(arguments.get("efo_uri"))

        # Feature-111A-004: if disease_trait looks like an EFO/OBA/HP ID, treat as efo_id
        if disease_trait and not efo_id and _EFO_ID_RE.match(disease_trait):
            efo_id = self._efo_id_from_uri_or_id(disease_trait)
            disease_trait = None

        # Feature-79C: /v2/associations ignores disease_trait param server-side.
        # Auto-resolve trait name to efo_id for reliable filtering.
        # Feature-81B-008: if resolution fails, return error instead of silently
        # running an unfiltered search that returns 1M+ unrelated associations.
        resolution: Optional[Dict[str, Any]] = None
        if disease_trait and not efo_id:
            resolution = self._resolve_trait_to_efo(disease_trait)
            if resolution:
                efo_id = resolution["efo_id"]
            else:
                return {
                    "status": "error",
                    "error": (
                        f"Could not resolve trait '{disease_trait}' to an EFO ID. "
                        "GWAS Catalog uses specific EFO/MONDO disease terms. "
                        "For drug response traits, use the underlying disease "
                        "(e.g., 'depression' instead of 'antidepressant response', "
                        "'coronary artery disease' instead of 'statin response'). "
                        "Or provide efo_id directly (e.g., 'MONDO_0002009' for "
                        "major depressive disorder, 'EFO_0001645' for myocardial infarction)."
                        + self._unresolved_trait_hint(disease_trait)
                    ),
                }

        if efo_id:
            params["efo_id"] = efo_id

        efo_trait = self._coerce_str(arguments.get("efo_trait"))
        if efo_trait:
            params["efo_trait"] = efo_trait

        rs_id = self._coerce_str(arguments.get("rs_id"))
        if rs_id:
            params["rs_id"] = rs_id

        accession_id = self._coerce_str(arguments.get("accession_id"))
        if accession_id:
            params["accession_id"] = accession_id

        p_threshold = self._coerce_float(
            arguments.get("p_value")
            if arguments.get("p_value") is not None
            else arguments.get("p_value_threshold")
        )

        sort = self._coerce_str(arguments.get("sort"))
        direction = self._coerce_str(arguments.get("direction"))
        # The API returns associations UNSORTED by default, so a plain
        # discovery call with no explicit sort (e.g. just disease_trait+size)
        # returns whichever page the API happens to store first -- which can
        # be a low-information niche study with empty mapped_genes/locations,
        # while the near-identical gwas_get_associations_for_trait tool
        # defaults to sort=p_value and returns the expected top hit
        # (Feature-4B-2). Default to most-significant-first here too, for
        # consistency and so a p-value threshold (applied CLIENT-SIDE below,
        # since the API has no server-side p-value filter) actually sees the
        # top hits instead of missing them (SLE p<=1e-100 -> 0 even though
        # hits exist at p=2e-298).
        if not sort:
            sort = "p_value"
            if not direction:
                direction = "asc"

        # Fix-R31-1: defaulting the sort is not enough. When the caller asks
        # for direction=desc AND a p_value threshold, page 0 holds the LEAST
        # significant rows, so the client-side filter deletes every one of
        # them and the tool reports "no associations for this trait" for a
        # trait with tens of thousands of them (EFO_0004340 / BMI: data=[]
        # alongside pagination.totalElements=23608). Since the API cannot do
        # the filtering (see _CLIENT_SIDE_FILTER_NOTE), fetch the page in
        # p_value-ascending order whenever a threshold is present and the
        # caller is sorting by p_value, then present the surviving rows in
        # the direction the caller actually asked for. Any other sort field
        # (or_value, beta_num, ...) is left exactly as requested.
        fetch_sort, fetch_direction = sort, direction
        sort_override: Optional[Dict[str, Any]] = None
        if p_threshold is not None and sort == "p_value":
            fetch_sort = "p_value"
            if direction and direction != "asc":
                sort_override = {
                    "requested_sort": sort,
                    "requested_direction": direction,
                    "fetched_sort": "p_value",
                    "fetched_direction": "asc",
                    "reason": (
                        "A p_value threshold can only be honoured by scanning "
                        "the most-significant end of the result set; the page "
                        "was fetched p_value-ascending and the surviving rows "
                        f"were re-ordered '{direction}' for you."
                    ),
                }
            fetch_direction = "asc"

        if fetch_sort:
            params["sort"] = fetch_sort
        if fetch_direction:
            params["direction"] = fetch_direction

        size = self._coerce_int(arguments.get("size") or arguments.get("limit"))
        if size is not None:
            params["size"] = size

        page = self._coerce_int(arguments.get("page"))
        if page is not None:
            params["page"] = page

        # Feature-81B-008: require at least one filter to prevent returning 1M+ results
        filter_keys = {"efo_id", "efo_trait", "rs_id", "accession_id"}
        if not filter_keys.intersection(params):
            return {
                "status": "error",
                "error": (
                    "At least one filter is required: disease_trait, efo_id, "
                    "efo_trait, rs_id, or accession_id."
                ),
            }

        data = self._make_request(self.endpoint, params)
        result = self._extract_embedded_data(data, "associations")

        removed = 0
        if p_threshold is not None and result.get("status") == "success":
            removed = self._apply_client_side_p_value_filter(
                result,
                p_threshold=p_threshold,
                params=params,
                prefix_scan=(fetch_sort == "p_value" and fetch_direction == "asc"),
                sort_override=sort_override,
            )

        self._add_empty_result_note(
            result, efo_id, filter_removed=removed, filter_threshold=p_threshold
        )
        # Fix-R31-2: surface the resolved EFO term's label and the caller's
        # original query string so a trait substitution is visible.
        self._annotate_trait_resolution(result, disease_trait, resolution)
        return result

    def _apply_client_side_p_value_filter(
        self,
        result: Dict[str, Any],
        p_threshold: float,
        params: Dict[str, Any],
        prefix_scan: bool,
        sort_override: Optional[Dict[str, Any]],
    ) -> int:
        """Apply the p_value threshold client-side and disclose that it was.

        Returns the number of rows removed. Also records, in ``metadata``:

        * ``p_value_filter_scope`` / ``p_value_filter_note`` -- the filter is
          client-side, so its result is a property of *this page*, not of the
          trait (Fix-R31-1).
        * ``pagination_totals_are_prefilter`` -- ``pagination.totalElements``
          and ``pagination.totalPages`` keep their existing (UNFILTERED)
          meaning; this flag plus ``filtered_total`` say so explicitly rather
          than re-meaning an established key.
        * ``filtered_total`` / ``filtered_total_is_exact`` -- how many rows in
          the whole result set pass the threshold, when that is knowable.
        """
        assocs = result.get("data")
        if not isinstance(assocs, list):
            return 0

        kept: List[Any] = []
        removed_over_threshold = 0
        removed_missing_p = 0
        for assoc in assocs:
            p_value = (
                self._coerce_float(assoc.get("p_value"))
                if isinstance(assoc, dict)
                else None
            )
            if p_value is None:
                removed_missing_p += 1
                continue
            if p_value <= p_threshold:
                kept.append(assoc)
            else:
                removed_over_threshold += 1

        if sort_override:
            # Present the surviving rows in the direction the caller asked for.
            kept.sort(
                key=lambda a: self._coerce_float(a.get("p_value")) or 0.0,
                reverse=True,
            )

        result["data"] = kept
        metadata = result.setdefault("metadata", {})
        metadata["p_value_filter"] = p_threshold
        metadata["filtered_count"] = len(kept)
        metadata["total_before_filter"] = len(assocs)
        metadata["p_value_filter_scope"] = "client-side (applied to the fetched page)"
        metadata["p_value_filter_note"] = _CLIENT_SIDE_FILTER_NOTE
        metadata["pagination_totals_are_prefilter"] = True
        if sort_override:
            metadata["sort_override"] = sort_override

        pagination = metadata.get("pagination") or {}
        page_size = self._coerce_int(pagination.get("size")) or self._coerce_int(
            params.get("size")
        )
        page_number = self._coerce_int(pagination.get("number"))
        if page_number is None:
            page_number = self._coerce_int(params.get("page")) or 0
        rows_before_this_page = (page_size or 0) * page_number

        # With the page fetched p_value-ascending, the rows that pass the
        # threshold are a PREFIX of the full ordering. So if this page contains
        # the crossover (i.e. some row failed), everything after it fails too
        # and the filtered total is known exactly.
        if prefix_scan and removed_over_threshold > 0 and removed_missing_p == 0:
            metadata["filtered_total"] = rows_before_this_page + len(kept)
            metadata["filtered_total_is_exact"] = True
            metadata["filtered_total_note"] = (
                f"{metadata['filtered_total']} association(s) in the whole "
                f"result set pass p_value <= {p_threshold}. "
                "pagination.totalElements / totalPages below keep their "
                "original meaning and describe the UNFILTERED set "
                f"({pagination.get('totalElements')} element(s)), so they will "
                "not match the number of rows returned."
            )
        else:
            metadata["filtered_total"] = None
            metadata["filtered_total_is_exact"] = False
            if prefix_scan:
                metadata["filtered_total_at_least"] = rows_before_this_page + len(kept)
            metadata["filtered_total_note"] = (
                "The number of associations passing the threshold across the "
                "WHOLE result set is not known from this single page. "
                "pagination.totalElements / totalPages below describe the "
                "UNFILTERED set and are unaffected by p_value."
            )
        return removed_over_threshold + removed_missing_p


@register_tool("GWASStudySearch")
class GWASStudySearch(GWASRESTTool):
    """Search for GWAS studies by various criteria."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/studies"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for studies with optional filters."""
        params = {}

        disease_trait = self._coerce_str(arguments.get("disease_trait"))
        if disease_trait:
            params["disease_trait"] = disease_trait

        efo_id = self._efo_id_from_uri_or_id(arguments.get("efo_id"))
        if not efo_id:
            efo_id = self._efo_id_from_uri_or_id(arguments.get("efo_uri"))
        if efo_id:
            params["efo_id"] = efo_id

        efo_trait = self._coerce_str(arguments.get("efo_trait"))
        if efo_trait:
            params["efo_trait"] = efo_trait

        cohort = self._coerce_str(arguments.get("cohort"))
        if cohort:
            params["cohort"] = cohort

        if arguments.get("gxe") is not None:
            params["gxe"] = bool(arguments.get("gxe"))
        if arguments.get("full_pvalue_set") is not None:
            params["full_pvalue_set"] = bool(arguments.get("full_pvalue_set"))

        size = self._coerce_int(arguments.get("size"))
        if size is not None:
            params["size"] = size
        page = self._coerce_int(arguments.get("page"))
        if page is not None:
            params["page"] = page

        data = self._make_request(self.endpoint, params)
        return self._extract_embedded_data(data, "studies")


@register_tool("GWASSNPSearch")
class GWASSNPSearch(GWASRESTTool):
    """Search for GWAS single nucleotide polymorphisms (SNPs)."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/single-nucleotide-polymorphisms"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for SNPs with optional filters."""
        params = {}

        rs_id = arguments.get("rs_id") or arguments.get("rsid")
        if rs_id:
            params["rs_id"] = rs_id
        if "mapped_gene" in arguments:
            params["mapped_gene"] = arguments["mapped_gene"]
        if "size" in arguments:
            params["size"] = arguments["size"]
        if "page" in arguments:
            params["page"] = arguments["page"]

        data = self._make_request(self.endpoint, params)
        return self._extract_embedded_data(data, "snps")


# Get by ID tools
@register_tool("GWASAssociationByID")
class GWASAssociationByID(GWASRESTTool):
    """Get a specific GWAS association by its ID."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/associations"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get association by ID."""
        if "association_id" not in arguments:
            return {"status": "error", "error": "association_id is required"}

        return self._get_one(arguments["association_id"])


@register_tool("GWASStudyByID")
class GWASStudyByID(GWASRESTTool):
    """Get a specific GWAS study by its ID."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/studies"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get study by ID."""
        # Feature-4B-4: sibling tools (e.g. GWASAssociationsForStudy, and the
        # "accession_id" field on every association record) use "accession_id"
        # for this same GCST identifier, so accept it as an alias to avoid a
        # natural chaining mistake when passing an ID straight from one tool
        # to another.
        study_id = arguments.get("study_id") or arguments.get("accession_id")
        if not study_id:
            return {"status": "error", "error": "study_id is required"}

        return self._get_one(study_id)


@register_tool("GWASSNPByID")
class GWASSNPByID(GWASRESTTool):
    """Get a specific GWAS SNP by its rs ID."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/single-nucleotide-polymorphisms"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get SNP by rs ID."""
        if "rs_id" not in arguments:
            return {"status": "error", "error": "rs_id is required"}

        return self._get_one(arguments["rs_id"])


# Specialized search tools based on common use cases from examples
@register_tool("GWASVariantsForTrait")
class GWASVariantsForTrait(GWASRESTTool):
    """Get all variants associated with a specific trait."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/associations"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get variants for a trait with pagination support."""
        disease_trait = self._coerce_str(
            arguments.get("disease_trait") or arguments.get("trait")
        )
        efo_id = self._efo_id_from_uri_or_id(
            arguments.get("efo_id")
        ) or self._efo_id_from_uri_or_id(arguments.get("efo_uri"))
        efo_trait = self._coerce_str(arguments.get("efo_trait"))

        if disease_trait and not efo_id and _EFO_ID_RE.match(disease_trait):
            efo_id = self._efo_id_from_uri_or_id(disease_trait)
            disease_trait = None

        # /v2/associations ignores disease_trait — resolve to efo_id
        resolution = self._resolve_trait_or_error(disease_trait, efo_id)
        if "error" in resolution:
            return resolution["error"]
        efo_id = resolution["efo_id"]

        if not disease_trait and not efo_id and not efo_trait:
            return {
                "status": "error",
                "error": "Provide at least one of: disease_trait, efo_id (or efo_uri), efo_trait.",
            }

        page_size = (
            self._coerce_int(arguments.get("size") or arguments.get("limit")) or 200
        )
        # Fix-R4B-1: /v2/associations returns associations UNSORTED, and this
        # tool never asked for a sort -- so the first page was an arbitrary
        # slice of the trait's associations rather than its strongest loci.
        # Confirmed live: efo_id=MONDO_0004979 (asthma, 3219 associations)
        # returned p-values 2e-06 .. 2e-24 here, while the sibling
        # GWASAssociationsForTrait -- same endpoint, but sending
        # sort=p_value&direction=asc -- returned 7e-288, 8e-223, 2e-156 ...
        # A user reading the top of this tool's page therefore missed every
        # genome-wide-significant hit. Default to significance order and let
        # callers override, matching the sibling tools.
        params: Dict[str, Any] = {
            "size": page_size,
            "page": self._coerce_int(arguments.get("page")) or 0,
            "sort": self._coerce_str(arguments.get("sort")) or "p_value",
            "direction": self._coerce_str(arguments.get("direction")) or "asc",
        }
        if efo_id:
            params["efo_id"] = efo_id
        elif efo_trait:
            params["efo_trait"] = efo_trait

        data = self._make_request(self.endpoint, params)
        result = self._extract_embedded_data(data, "associations")
        self._add_empty_result_note(result, efo_id)
        if efo_id and disease_trait:
            self._annotate_trait_resolution(result, disease_trait, resolution)
        return result


@register_tool("GWASAssociationsForTrait")
class GWASAssociationsForTrait(GWASRESTTool):
    """Get all associations for a specific trait, sorted by p-value."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/associations"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get associations for a trait, sorted by significance."""
        disease_trait = self._coerce_str(
            arguments.get("disease_trait") or arguments.get("trait")
        )
        efo_id = self._efo_id_from_uri_or_id(
            arguments.get("efo_id")
        ) or self._efo_id_from_uri_or_id(arguments.get("efo_uri"))
        efo_trait = self._coerce_str(arguments.get("efo_trait"))

        if disease_trait and not efo_id and _EFO_ID_RE.match(disease_trait):
            efo_id = self._efo_id_from_uri_or_id(disease_trait)
            disease_trait = None

        # /v2/associations ignores disease_trait — resolve to efo_id
        resolution = self._resolve_trait_or_error(disease_trait, efo_id)
        if "error" in resolution:
            return resolution["error"]
        efo_id = resolution["efo_id"]

        if not disease_trait and not efo_id and not efo_trait:
            return {
                "status": "error",
                "error": "Provide at least one of: disease_trait, efo_id (or efo_uri), efo_trait.",
            }

        params: Dict[str, Any] = {
            "sort": "p_value",
            "direction": "asc",
            "size": arguments.get("size", 40),
            "page": arguments.get("page", 0),
        }
        if efo_id:
            params["efo_id"] = efo_id
        elif efo_trait:
            params["efo_trait"] = efo_trait

        data = self._make_request(self.endpoint, params)
        result = self._extract_embedded_data(data, "associations")
        self._add_empty_result_note(result, efo_id)
        if efo_id and disease_trait:
            self._annotate_trait_resolution(result, disease_trait, resolution)
        return result


@register_tool("GWASAssociationsForSNP")
class GWASAssociationsForSNP(GWASRESTTool):
    """Get all associations for a specific SNP."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/associations"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get associations for a SNP."""
        rs_id = self._coerce_str(arguments.get("rs_id"))
        if not rs_id:
            return {"status": "error", "error": "rs_id is required"}

        params = {
            "rs_id": rs_id,
            "size": self._coerce_int(arguments.get("size")) or 200,
            "page": self._coerce_int(arguments.get("page")) or 0,
        }

        sort = self._coerce_str(arguments.get("sort"))
        if sort:
            params["sort"] = sort
        direction = self._coerce_str(arguments.get("direction"))
        if direction:
            params["direction"] = direction

        data = self._make_request(self.endpoint, params)
        return self._extract_embedded_data(data, "associations")


@register_tool("GWASStudiesForTrait")
class GWASStudiesForTrait(GWASRESTTool):
    """Get studies for a specific trait with optional filters."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/studies"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get studies for a trait with optional filters."""
        disease_trait = self._coerce_str(arguments.get("disease_trait"))
        efo_id = self._efo_id_from_uri_or_id(
            arguments.get("efo_id")
        ) or self._efo_id_from_uri_or_id(arguments.get("efo_uri"))
        efo_trait = self._coerce_str(arguments.get("efo_trait"))
        if not disease_trait and not efo_id and not efo_trait:
            return {
                "status": "error",
                "error": "Provide at least one of: disease_trait, efo_id (or efo_uri), efo_trait.",
            }

        params = {
            "size": self._coerce_int(arguments.get("size")) or 200,
            "page": self._coerce_int(arguments.get("page")) or 0,
        }

        if disease_trait:
            params["disease_trait"] = disease_trait
        if efo_id:
            params["efo_id"] = efo_id
        if efo_trait:
            params["efo_trait"] = efo_trait

        cohort = self._coerce_str(arguments.get("cohort"))
        if cohort:
            params["cohort"] = cohort
        if arguments.get("gxe") is not None:
            params["gxe"] = bool(arguments.get("gxe"))
        if arguments.get("full_pvalue_set") is not None:
            params["full_pvalue_set"] = bool(arguments.get("full_pvalue_set"))

        data = self._make_request(self.endpoint, params)
        return self._extract_embedded_data(data, "studies")


@register_tool("GWASSNPsForGene")
class GWASSNPsForGene(GWASRESTTool):
    """Get SNPs mapped to a specific gene."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Feature-83B-001: v2 /single-nucleotide-polymorphisms?mapped_gene= returns
        # HTTP 500 for all gene queries. The v1 endpoint
        # /singleNucleotidePolymorphisms/search/findByGene?geneName= works correctly.
        self.endpoint = "/singleNucleotidePolymorphisms/search/findByGene"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get SNPs for a gene."""
        gene = (
            arguments.get("gene_symbol")
            or arguments.get("mapped_gene")
            or arguments.get("gene")
        )
        if not gene:
            return {"status": "error", "error": "gene_symbol is required"}

        params = {
            "geneName": gene,
            "size": arguments.get("size", 50),
            "page": arguments.get("page", 0),
        }

        data = self._make_request(self.endpoint, params)
        # v1 endpoint returns key "singleNucleotidePolymorphisms", not "snps"
        result = self._extract_embedded_data(data, "singleNucleotidePolymorphisms")

        # Feature-4B-3: the v1 findByGene endpoint repeats identical SNP
        # records (verified: byte-for-byte duplicate objects for the same
        # rsId), inflating apparent SNP counts. Dedupe by rsId.
        if result.get("status") == "success" and isinstance(result.get("data"), list):
            seen: set = set()
            deduped = []
            for snp in result["data"]:
                rs_id = snp.get("rsId") if isinstance(snp, dict) else None
                if rs_id:
                    if rs_id in seen:
                        continue
                    seen.add(rs_id)
                deduped.append(snp)
            if len(deduped) != len(result["data"]):
                result.setdefault("metadata", {})["duplicates_removed"] = len(
                    result["data"]
                ) - len(deduped)
            result["data"] = deduped

        return result


@register_tool("GWASAssociationsForStudy")
class GWASAssociationsForStudy(GWASRESTTool):
    """Get all associations for a specific study."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/v2/associations"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get associations for a study."""
        if "accession_id" not in arguments:
            return {"status": "error", "error": "accession_id is required"}

        params = {
            "accession_id": arguments["accession_id"],
            "sort": "p_value",
            "direction": "asc",
            "size": arguments.get("size", 200),
            "page": arguments.get("page", 0),
        }

        data = self._make_request(self.endpoint, params)
        return self._extract_embedded_data(data, "associations")
