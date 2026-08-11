# faers_analytics_tool.py

import os
import requests
import math
from typing import Dict, Any, List, Tuple, Optional
from .base_tool import BaseTool
from .http_utils import request_with_retry
from .openfda_adv_tool import (
    COUNT_MAX_LIMIT,
    COUNT_MAX_LIMIT_ANONYMOUS,
    faers_drug_name_clause,
)
from .tool_registry import register_tool

FDA_BASE_URL = "https://api.fda.gov/drug/event.json"

# The openFDA facet every reaction rollup in this module counts over.
#
# Fix-R38: `_rollup_meddra_hierarchy` sent this facet with no `limit`, took the
# first 50 rows of openFDA's 100-row default page, and published
# `len(that slice)` under the key `total_unique_PTs`. That number was therefore
# the constant 50 for every drug -- measured live 2026-08-11, HYDROMORPHONE and
# ONDANSETRON both reported `total_unique_PTs: 50` -- with no `truncated` flag
# and no note, so a stable, plausible-looking page size was being read as "this
# drug has 50 distinct reported reactions".
#
# How far off: the same query at the anonymous ceiling
#   count=patient.reaction.reactionmeddrapt.exact&limit=999
# returns 999 distinct PT buckets for HYDROMORPHONE and the 999th still carries
# `count: 69`, i.e. the ranking is nowhere near exhausted and the true number of
# distinct PTs is strictly greater than 999. The published figure understated it
# by more than 20x.
#
# There is no honest total to publish instead: an openFDA `count=` response
# carries NO grand total -- its `meta` block holds only
# disclaimer/terms/license/last_updated -- so the number of distinct values is
# genuinely unknowable from the response (same constraint documented at
# openfda_adv_tool.COUNT_DEFAULT_LIMIT). The fix is to report what was returned
# under a name that says so, flag truncation, and say plainly that a term's
# absence from the list is not evidence it was never reported.
PT_COUNT_FIELD = "patient.reaction.reactionmeddrapt.exact"

# How many rows `_filter_serious_events` publishes under
# "top_serious_reactions". Named because it also sizes that method's request:
# it asks openFDA for exactly one row more than this, so the extra row's
# presence proves the ranking continues past what is shown.
_TOP_SERIOUS_REACTIONS = 20

# How far apart two RORs must be before `_compare_drugs` calls one "stronger"
# rather than "similar-strength".
_SIMILAR_STRENGTH_RATIO = 1.5

# Fix-R37: an arm only supports that call when its own 95% interval is narrower
# than the band itself. On the log scale the ROR standard error is
# sqrt(1/a + 1/b + 1/c + 1/d), and with b, c and d in the tens of thousands to
# millions the 1/a term dominates outright, leaving SE ~= 1/sqrt(a). Requiring
# exp(1.96 / sqrt(a)) < _SIMILAR_STRENGTH_RATIO gives
# a > (1.96 / ln(1.5))^2 = 23.4, rounded up to a round 25. Kept as its own
# literal rather than computed from the ratio, since ceil() of that expression
# is 24 and would quietly move the threshold.
_SMALL_CASE_COUNT_THRESHOLD = 25


def _comparison_arm(name: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """One drug's side of a comparison, built from its disproportionality run.

    Fix-R37: `contingency_table` is passed through verbatim rather than rebuilt,
    so an arm can never disagree with FAERS_calculate_disproportionality about
    the same drug/event pair, and both tools name the cells identically.
    """
    return {
        "name": name,
        "contingency_table": result.get("contingency_table"),
        "metrics": result.get("metrics"),
        "signal_detection": result.get("signal_detection"),
    }


def _small_count_caveat(arms: List[Dict[str, Any]]) -> Optional[str]:
    """Qualify a two-drug verdict whose arms rest on too few co-reported cases.

    Returns None when every arm clears `_SMALL_CASE_COUNT_THRESHOLD` -- and also
    when an arm's count is simply unavailable, since there is then nothing to
    qualify it with.
    """
    small = []
    for arm in arms:
        a = (arm.get("contingency_table") or {}).get("a_drug_and_event")
        if isinstance(a, int) and a < _SMALL_CASE_COUNT_THRESHOLD:
            small.append((arm.get("name"), a))

    if not small:
        return None

    counts = "; ".join(
        f"{name} rests on {a} co-reported case{'' if a == 1 else 's'}"
        for name, a in small
    )
    return (
        f"{counts} -- fewer than the {_SMALL_CASE_COUNT_THRESHOLD} needed for an "
        "arm's own 95% ROR interval to be narrower than the "
        f"{_SIMILAR_STRENGTH_RATIO}x ratio this comparison uses to separate "
        "'similar-strength' from 'stronger'. Read `comparison` as provisional "
        "rather than an equal-confidence statement, and check each arm's "
        "`contingency_table` before acting on it."
    )


def _drug_clause(drug_name: str) -> str:
    """openFDA search clause matching a drug across every field that names it.

    Matching only `generic_name` makes every brand name look like a drug with
    zero reports, which for the disproportionality math is indistinguishable
    from a genuinely unreported drug (confirmed live: "XELJANZ" yielded
    a=0, b=0 and an "Insufficient data" error while its generic "tofacitinib"
    returned a real ROR; the generic-or-brand form returns 183,405 reports for
    the same brand name). Brand names are what prescribers and labels use, so
    they must resolve to the same reports as the generic.

    `patient.drug.medicinalproduct` is required for the same reason in the
    opposite direction. The openFDA name fields are populated only when the
    reporter's free text resolved to an SPL, so for anything that did not
    resolve they are sparse or empty and generic-or-brand alone silently shrinks
    the contingency table. Measured live 2026-08-11 (`limit=0`,
    `meta.results.total`): MEFLOQUINE has 751 reports under medicinalproduct but
    only 156 under generic-or-brand, so this tool was computing ROR/PRR from 21%
    of the drug's reports; YELLOW FEVER VACCINE has 111 under medicinalproduct
    and 0 under generic-or-brand, making vaccines entirely invisible to
    disproportionality analysis while looking like a legitimate "no reports"
    answer.

    The field list and the rendering both live in openfda_adv_tool so this
    tool's numerator stays comparable with the FAERS count/detail tools' -- see
    FAERS_DRUG_NAME_FIELDS there for the full measured table.
    """
    return faers_drug_name_clause(drug_name)


def _ranked_terms_truncation_note(label: str, returned: int, observed: bool) -> str:
    """Disclosure for a ranked `count=` list that does not show every term.

    Deliberately mirrors openfda_adv_tool._build_count_envelope's
    `truncation_note` so both FAERS families make the same promise about the
    same openFDA behaviour: the rows are the most-reported terms in descending
    order, the size of the remainder is unknowable, and absence from the list is
    not absence from FAERS.

    `observed` is True when a row beyond the published list actually came back,
    which proves more terms exist; False when the page merely filled exactly,
    which only makes it likely. The distinction is the same one
    `_build_count_envelope` draws with its `probed` flag.

    Takes only the count actually published, never the page size that produced
    it. The two differ whenever a caller fetches a probe row it does not show,
    and quoting the request's `limit` here would then describe a page the reader
    never received; callers that want to expose the page size publish it as its
    own key instead.
    """
    certainty = (
        "more terms exist beyond it"
        if observed
        else "openFDA filled the page exactly, so more terms may exist beyond it"
    )
    return (
        f"openFDA returned only the {returned} most-reported {label} for this "
        f"query, ranked by descending report count; {certainty}. "
        "openFDA's count endpoint does not report how many distinct terms there "
        "are in total -- its `meta` block carries only "
        "disclaimer/terms/license/last_updated -- so the size of the remainder is "
        f"unknown and no total number of distinct {label} can be given. A term "
        "missing from this list is NOT evidence that it was never reported for "
        "this query -- query the term directly to check."
    )


def _faers_search_query(
    drug_name: Optional[str] = None, adverse_event: Optional[str] = None
) -> str:
    """openFDA `search=` clause for a drug, optionally narrowed to one reaction.

    Shared so a `count=` facet and the `meta.results.total` request that supplies
    its denominator cannot drift apart -- the two numbers are only comparable if
    they came from the identical query. Returns "" when neither is given, which
    callers use to mean "the whole database".
    """
    parts = []
    if drug_name:
        parts.append(_drug_clause(drug_name))
    if adverse_event:
        parts.append(f'patient.reaction.reactionmeddrapt:"{adverse_event}"')
    return "+AND+".join(parts)


@register_tool("FAERSAnalyticsTool")
class FAERSAnalyticsTool(BaseTool):
    """
    FAERS Analytics Tool for statistical signal detection in adverse event data.

    Provides:
    - Disproportionality analysis (ROR, PRR, IC, EBGM)
    - Demographic stratification
    - Serious event filtering
    - Drug comparison
    - Temporal trend analysis
    - MedDRA hierarchy rollups
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.api_key = os.getenv("FDA_API_KEY")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to analytics operation."""
        # Normalize aliases
        if not arguments.get("adverse_event") and arguments.get("reaction"):
            arguments = dict(arguments, adverse_event=arguments["reaction"])
        if not arguments.get("stratify_by") and arguments.get("demographic"):
            arguments = dict(arguments, stratify_by=arguments["demographic"])
        # Normalize drug_name aliases: 'drug' → 'drug_name'
        if not arguments.get("drug_name") and arguments.get("drug"):
            arguments = dict(arguments, drug_name=arguments["drug"])
        # Normalize seriousness_type alias: 'event_type' → 'seriousness_type'
        if not arguments.get("seriousness_type") and arguments.get("event_type"):
            arguments = dict(arguments, seriousness_type=arguments["event_type"])
        # Normalize compare_drugs alias: 'drugs' list → 'drug1', 'drug2'
        if arguments.get("drugs") and not arguments.get("drug1"):
            drugs_list = arguments["drugs"]
            if isinstance(drugs_list, list) and len(drugs_list) >= 2:
                arguments = dict(arguments, drug1=drugs_list[0], drug2=drugs_list[1])
        # Normalize stratify_by: 'age_group' → 'age'
        if arguments.get("stratify_by") == "age_group":
            arguments = dict(arguments, stratify_by="age")
        operation = arguments.get("operation")
        # Auto-fill operation from tool config const if not provided by user
        if not operation:
            operation = self.get_schema_const_operation()

        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        if operation == "calculate_disproportionality":
            operation_result = self._calculate_disproportionality(arguments)
        elif operation == "stratify_by_demographics":
            operation_result = self._stratify_by_demographics(arguments)
        elif operation == "filter_serious_events":
            operation_result = self._filter_serious_events(arguments)
        elif operation == "compare_drugs":
            operation_result = self._compare_drugs(arguments)
        elif operation == "analyze_temporal_trends":
            operation_result = self._analyze_temporal_trends(arguments)
        elif operation == "rollup_meddra_hierarchy":
            operation_result = self._rollup_meddra_hierarchy(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

        return self._with_data_payload(operation_result)

    def _with_api_key(self, url: str) -> str:
        """Append FDA_API_KEY (if set) to an openFDA request URL -- reduces
        how often the anonymous tier's low rate limit is hit (see
        _get_faers_count)."""
        if self.api_key:
            separator = "&" if "?" in url else "?"
            return f"{url}{separator}api_key={self.api_key}"
        return url

    def _count_limit(self) -> int:
        """Highest `limit` this caller may send to an openFDA `count=` query.

        Measured live 2026-08-11 against
        `count=patient.reaction.reactionmeddrapt.exact` for HYDROMORPHONE:
        limit=1000 answers HTTP 403 {"code": "API_KEY_MISSING"} for an anonymous
        caller while limit=999 succeeds, so the anonymous ceiling sits one below
        openFDA's documented maximum of 1000. The constants live in
        openfda_adv_tool and are imported rather than restated so this module's
        facets cannot page differently from the FAERS count tools there.
        """
        return COUNT_MAX_LIMIT if self.api_key else COUNT_MAX_LIMIT_ANONYMOUS

    def _with_data_payload(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure successful operation responses include a standardized data wrapper."""
        if not isinstance(result, dict):
            return {"status": "success", "data": {"value": result}, "value": result}

        if result.get("status") != "success":
            return result

        if "data" in result:
            return result

        # Feature-81A-004: move non-status keys into data to avoid duplicating
        # every field at both the top level and inside data.
        data = {k: v for k, v in result.items() if k != "status"}
        return {"status": "success", "data": data}

    def _calculate_disproportionality(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate disproportionality measures (ROR, PRR, IC) with 95% confidence intervals.

        Uses 2x2 contingency table:
                    Event+    Event-
        Drug+         a         b
        Drug-         c         d
        """
        try:
            drug_name = arguments.get("drug_name")
            adverse_event = arguments.get("adverse_event")

            if not drug_name or not adverse_event:
                return {
                    "status": "error",
                    "error": "Must provide drug_name and adverse_event",
                }

            # Get counts for 2x2 table. Each call is Optional[int]: None means
            # the openFDA request itself failed (e.g. rate limited), which
            # must not be treated as a genuine zero count -- see
            # _get_faers_count.
            a = self._get_faers_count(drug_name, adverse_event)
            drug_total = self._get_faers_count(drug_name, None)
            event_total = self._get_faers_count(None, adverse_event)
            total = self._get_faers_total_count()

            if None in (a, drug_total, event_total, total):
                return {
                    "status": "error",
                    "error": (
                        "One or more openFDA FAERS count queries failed "
                        "(commonly HTTP 429 rate limiting on the anonymous "
                        "tier), so a disproportionality analysis cannot be "
                        "computed right now. Retry in a moment, or set the "
                        "FDA_API_KEY environment variable to raise the rate "
                        "limit (https://open.fda.gov/apis/authentication/)."
                    ),
                }

            # b = drug + no event (all drug reports - drug+event)
            b = drug_total - a
            # c = no drug + event (all event reports - drug+event)
            c = event_total - a
            # d = no drug + no event (total - a - b - c)
            d = total - a - b - c

            # Check for valid counts
            if a <= 0 or b <= 0 or c <= 0 or d <= 0:
                return {
                    "status": "error",
                    "error": f"Insufficient data: a={a}, b={b}, c={c}, d={d}. Need all counts > 0 for analysis.",
                    "contingency_table": {"a": a, "b": b, "c": c, "d": d},
                }

            # Calculate ROR (Reporting Odds Ratio)
            ror = (a / b) / (c / d) if b > 0 and d > 0 else None
            ror_ci = self._calculate_ror_ci(a, b, c, d) if ror else None

            # Calculate PRR (Proportional Reporting Ratio)
            prr = (a / (a + b)) / (c / (c + d)) if (a + b) > 0 and (c + d) > 0 else None
            prr_ci = self._calculate_prr_ci(a, b, c, d) if prr else None

            # Calculate IC (Information Component)
            ic = self._calculate_ic(a, b, c, d)
            ic_ci = self._calculate_ic_ci(a, b, c, d) if ic is not None else None

            # Determine signal strength
            signal_detected = False
            signal_strength = "No signal"

            if ror and ror_ci:
                if ror_ci["lower"] > 1.0 and a >= 3:  # Standard threshold
                    signal_detected = True
                    if ror >= 4.0:
                        signal_strength = "Strong signal"
                    elif ror >= 2.0:
                        signal_strength = "Moderate signal"
                    else:
                        signal_strength = "Weak signal"

            # The note must agree with signal_detection above. It used to assert a
            # potential signal unconditionally, so a result whose own verdict was
            # "No signal" still read as though a signal had been found.
            if signal_detected:
                verdict = (
                    "Disproportionality analysis indicates a potential safety signal "
                    f"({signal_strength})."
                )
            elif ror_ci and ror_ci["upper"] < 1.0:
                verdict = (
                    "No safety signal: this event is reported disproportionately LESS "
                    "often for this drug than across all other drugs. This is not "
                    "evidence of a protective effect."
                )
            else:
                verdict = (
                    "No safety signal by the stated criteria (ROR lower CI > 1.0 and "
                    "case count >= 3). Absence of a signal does NOT establish absence "
                    "of risk, particularly where case counts are small."
                )

            note = (
                f"{verdict} Disproportionality measures reporting patterns, not risk, "
                "and does NOT prove causation. Requires clinical evaluation."
            )

            return {
                "status": "success",
                "drug_name": drug_name,
                "adverse_event": adverse_event,
                "contingency_table": {
                    "a_drug_and_event": a,
                    "b_drug_no_event": b,
                    "c_no_drug_event": c,
                    "d_no_drug_no_event": d,
                },
                "metrics": {
                    "ROR": {
                        "value": round(ror, 3) if ror else None,
                        "ci_95_lower": round(ror_ci["lower"], 3) if ror_ci else None,
                        "ci_95_upper": round(ror_ci["upper"], 3) if ror_ci else None,
                        "interpretation": "Reporting odds ratio - measures association strength",
                    },
                    "PRR": {
                        "value": round(prr, 3) if prr else None,
                        "ci_95_lower": round(prr_ci["lower"], 3) if prr_ci else None,
                        "ci_95_upper": round(prr_ci["upper"], 3) if prr_ci else None,
                        "interpretation": "Proportional reporting ratio - probability ratio",
                    },
                    "IC": {
                        "value": round(ic, 3) if ic is not None else None,
                        "ci_95_lower": round(ic_ci["lower"], 3) if ic_ci else None,
                        "ci_95_upper": round(ic_ci["upper"], 3) if ic_ci else None,
                        "interpretation": "Information component - Bayesian measure",
                    },
                },
                "signal_detection": {
                    "signal_detected": signal_detected,
                    "signal_strength": signal_strength,
                    "criteria": "ROR lower CI > 1.0 and case count >= 3",
                },
                "note": note,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Disproportionality calculation failed: {str(e)}",
            }

    def _stratify_by_demographics(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Stratify adverse event data by demographics (age, sex, country)."""
        try:
            drug_name = arguments.get("drug_name")
            adverse_event = arguments.get("adverse_event")
            stratify_by = arguments.get("stratify_by", "sex")  # sex, age, country

            if not drug_name:
                return {
                    "status": "error",
                    "error": "Must provide drug_name",
                }

            if stratify_by not in ["sex", "age", "country"]:
                return {
                    "status": "error",
                    "error": "stratify_by must be 'sex', 'age', or 'country'",
                }

            # Map stratification to FAERS fields.
            #
            # Fix-R38: "country" counted the analysed `occurcountry` field, which
            # openFDA cannot aggregate at all -- measured live 2026-08-11, that
            # request answers HTTP 500 "[illegal_argument_exception] Text fields
            # are not optimised for operations that require per-document field
            # data", so stratify_by="country" failed for every drug and surfaced
            # only as "API request failed: 500 Server Error". The `.exact`
            # (un-analysed) variant aggregates normally: 43 country buckets for
            # HYDROMORPHONE. The two numeric fields need no `.exact` because they
            # are not text.
            field_map = {
                "sex": "patient.patientsex",
                "age": "patient.patientagegroup",
                "country": "occurcountry.exact",
            }

            count_field = field_map[stratify_by]
            # `.exact` selects openFDA's un-analysed index variant; it is a query
            # detail, not part of the field's name in the FAERS record layout, so
            # it is stripped everywhere the field is named in prose.
            field_label = count_field.removesuffix(".exact")

            # Feature-121A-003: adverse_event is optional — filter by drug alone if omitted
            base_query = _faers_search_query(drug_name, adverse_event)

            # Ask for the full page this caller is entitled to. These facets are
            # short -- 3 sex buckets, 6 age-group buckets and 43 country buckets
            # for HYDROMORPHONE, against ~250 ISO country codes in the worst case
            # -- so the ceiling guarantees the facet is exhausted and the
            # percentages below really are shares of the whole stratifiable
            # subset. openFDA's 100-row default would not guarantee that for
            # country.
            limit = self._count_limit()
            url = self._with_api_key(
                f"{FDA_BASE_URL}?search={base_query}&count={count_field}&limit={limit}"
            )

            response = request_with_retry(requests, "GET", url, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            # Format stratified data.
            #
            # Fix-R33: this sum is the STRATIFIABLE SUBSET, not the total number
            # of reports. An openFDA `count=` facet is computed only over records
            # where the counted field is populated -- records missing
            # patient.patientagegroup / patient.patientsex / occurcountry are
            # silently dropped from the facet rather than bucketed as unknown.
            # Demographic coverage in FAERS is partial (age group is recorded on
            # well under a fifth of ondansetron reports), so emitting this sum as
            # "total_reports" understated the drug's report count more than
            # fivefold. The percentages below are still correct -- a share of the
            # stratifiable subset is the right denominator for a stratification --
            # but the true total has to be fetched separately and reported next
            # to it so neither number can be mistaken for the other.
            #
            # _get_faers_count builds its URL from the same _faers_search_query,
            # so the total is always the total for the query the facet ran on.
            stratified_data = []
            total_count = sum(r.get("count", 0) for r in results)
            query_total = self._get_faers_count(drug_name, adverse_event)

            for result in results:
                term = result.get("term", "Unknown")
                count = result.get("count", 0)
                percentage = (count / total_count * 100) if total_count > 0 else 0

                # Interpret codes (API returns integers; normalize to str for dict lookup)
                term_key = str(term)
                if stratify_by == "sex":
                    term = {"0": "Unknown", "1": "Male", "2": "Female"}.get(
                        term_key, term
                    )
                elif stratify_by == "age":
                    age_map = {
                        "1": "Neonate",
                        "2": "Infant",
                        "3": "Child",
                        "4": "Adolescent",
                        "5": "Adult",
                        "6": "Elderly",
                    }
                    term = age_map.get(term_key, term)

                stratified_data.append(
                    {"group": term, "count": count, "percentage": round(percentage, 2)}
                )

            if query_total is None:
                coverage_note = (
                    "The total number of reports matching this query could not be "
                    "retrieved (the extra openFDA request failed, commonly HTTP 429 "
                    "rate limiting on the anonymous tier), so "
                    "total_reports_matching_query is null. "
                    f"stratified_report_count ({total_count:,}) counts only reports "
                    f"where {field_label} is recorded and is therefore a LOWER BOUND "
                    "on the drug's report count -- do not read it as the total. "
                    "Retry for the total, or set the FDA_API_KEY environment "
                    "variable to raise the rate limit "
                    "(https://open.fda.gov/apis/authentication/)."
                )
            else:
                coverage = (total_count / query_total * 100) if query_total else 0.0
                coverage_note = (
                    f"total_reports_matching_query ({query_total:,}) is every report "
                    f"matching this query; stratified_report_count ({total_count:,}, "
                    f"{coverage:.1f}% of them) is the subset where {field_label} is "
                    "recorded, and only that subset is stratified below. openFDA "
                    "computes a count facet solely over records that populate the "
                    "counted field, so reports missing this demographic are absent "
                    "from the groups entirely rather than bucketed as unknown. Each "
                    "percentage is a share of stratified_report_count, not of the "
                    "full total. total_reports repeats stratified_report_count for "
                    "backward compatibility -- it is NOT the drug's report count."
                )

            # No truncation disclosure is owed here, unlike the PT facets in this
            # module: requesting the ceiling makes these facets provably whole.
            # Their value sets are bounded and tiny -- 3 sex codes, 6 age-group
            # codes, and ~250 ISO country codes against a 999-row page -- so
            # `results` always holds every bucket and every percentage above
            # really is a share of the complete stratifiable subset.
            return {
                "status": "success",
                "drug_name": drug_name,
                "adverse_event": adverse_event,
                "stratified_by": stratify_by,
                "total_reports": total_count,
                "stratified_report_count": total_count,
                "total_reports_matching_query": query_total,
                "stratification": sorted(
                    stratified_data, key=lambda x: x["count"], reverse=True
                ),
                "coverage_note": coverage_note,
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Stratification failed: {str(e)}"}

    def _filter_serious_events(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Filter for serious adverse events (death, hospitalization, disability, life-threatening)."""
        try:
            drug_name = arguments.get("drug_name")
            adverse_event = arguments.get("adverse_event")
            seriousness_type = arguments.get(
                "seriousness_type", "all"
            )  # all, death, hospitalization, disability, life_threatening

            if not drug_name:
                return {"status": "error", "error": "Must provide drug_name"}

            # Build query for serious events
            base_query = _drug_clause(drug_name)

            # Add specific reaction filter if provided
            if adverse_event:
                base_query += (
                    f'+AND+patient.reaction.reactionmeddrapt:"{adverse_event}"'
                )

            # Add seriousness filter
            seriousness_map = {
                "all": "+AND+serious:1",
                "death": "+AND+seriousnessdeath:1",
                "hospitalization": "+AND+seriousnesshospitalization:1",
                "disability": "+AND+seriousnessdisabling:1",
                "life_threatening": "+AND+seriousnesslifethreatening:1",
            }

            if seriousness_type not in seriousness_map:
                return {
                    "status": "error",
                    "error": f"Invalid seriousness_type. Must be one of: {list(seriousness_map.keys())}",
                }

            search_query = base_query + seriousness_map[seriousness_type]

            # Get top reactions for serious events. Ask for exactly one row past
            # what gets published: the probe row's presence settles truncation as
            # a fact rather than an inference, and anything beyond it would be
            # parsed only to be discarded. Same idiom as
            # openfda_adv_tool._fetch_limit. Without this the request fell back
            # to openFDA's 100-row default page and threw 80 rows away.
            facet_limit = min(_TOP_SERIOUS_REACTIONS + 1, self._count_limit())
            url = self._with_api_key(
                f"{FDA_BASE_URL}?search={search_query}"
                f"&count={PT_COUNT_FIELD}&limit={facet_limit}"
            )

            response = request_with_retry(requests, "GET", url, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            # Get total serious event count
            total_url = self._with_api_key(
                f"{FDA_BASE_URL}?search={search_query}&limit=1"
            )
            total_response = request_with_retry(requests, "GET", total_url, timeout=30)
            total_data = total_response.json()
            total_serious = (
                total_data.get("meta", {}).get("results", {}).get("total", 0)
            )

            # Format results
            serious_reactions = [
                {"reaction": r.get("term"), "count": r.get("count")}
                for r in results[:_TOP_SERIOUS_REACTIONS]
            ]

            # Fix-R38: `total_serious_events` is honest -- it is
            # `meta.results.total` from a plain search, which openFDA does
            # report. `top_serious_reactions` is not a total of anything and is
            # named accordingly, but it silently dropped the rest of a ranking
            # whose length is unknowable (the same facet returns 999 rows and is
            # still not exhausted for HYDROMORPHONE + serious:1, the 999th
            # bucket carrying count 69). Rows beyond the slice were directly
            # observed in `results`, so the truncation is a fact here rather than
            # an inference.
            truncated = len(results) > len(serious_reactions)

            result: Dict[str, Any] = {
                "drug_name": drug_name,
                "seriousness_type": seriousness_type,
                "total_serious_events": total_serious,
                "top_serious_reactions": serious_reactions,
                "top_serious_reactions_truncated": truncated,
                "note": f"Serious events: {'All' if seriousness_type == 'all' else seriousness_type.replace('_', ' ')}",
            }
            if truncated:
                result["top_serious_reactions_truncation_note"] = (
                    _ranked_terms_truncation_note(
                        "serious reactions", len(serious_reactions), observed=True
                    )
                )
            if adverse_event:
                result["adverse_event_filter"] = adverse_event.upper()
            return {"status": "success", "data": result}

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"API request failed: {str(e)}"}
        except Exception as e:
            return {
                "status": "error",
                "error": f"Serious event filtering failed: {str(e)}",
            }

    def _compare_drugs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Compare safety profiles of two drugs for the same adverse event.

        Fix-R38 audit: this method issues no `count=` facet of its own. Both arms
        come from `_calculate_disproportionality`, whose counts are
        `meta.results.total` on plain `limit=1` searches -- a figure openFDA does
        report -- so there is no page size here that could be mistaken for a
        total.
        """
        try:
            drug1 = arguments.get("drug1")
            drug2 = arguments.get("drug2")
            adverse_event = arguments.get("adverse_event")

            if not drug1 or not drug2 or not adverse_event:
                return {
                    "status": "error",
                    "error": "Must provide drug1, drug2, and adverse_event",
                }

            # Calculate disproportionality for both drugs
            result1 = self._calculate_disproportionality(
                {
                    "operation": "calculate_disproportionality",
                    "drug_name": drug1,
                    "adverse_event": adverse_event,
                }
            )

            result2 = self._calculate_disproportionality(
                {
                    "operation": "calculate_disproportionality",
                    "drug_name": drug2,
                    "adverse_event": adverse_event,
                }
            )

            if result1.get("status") != "success" or result2.get("status") != "success":
                return {
                    "status": "error",
                    "error": "Failed to calculate metrics for one or both drugs",
                    "drug1_result": result1,
                    "drug2_result": result2,
                }

            # Extract ROR values
            ror1 = result1.get("metrics", {}).get("ROR", {}).get("value")
            ror2 = result2.get("metrics", {}).get("ROR", {}).get("value")

            # Fix-19B-2: comparison text used to rank drugs purely by raw ROR
            # magnitude ("X shows stronger signal than Y") even when NEITHER
            # drug actually crossed this tool's own signal-detection
            # threshold (signal_detection.signal_detected, from ROR lower CI
            # > 1.0 and case count >= 3) -- confirmed live with
            # nirsevimab/palivizumab + anaphylactic reaction, where both
            # drugs had signal_detected=False (ROR < 1, i.e. no elevated-risk
            # association) but the narrative still said one showed a
            # "stronger signal" than the other. Ground the wording in
            # signal_detected so "signal" language only appears when a
            # signal was actually detected.
            sig1 = result1.get("signal_detection", {}).get("signal_detected", False)
            sig2 = result2.get("signal_detection", {}).get("signal_detected", False)

            comparison = "Inconclusive"
            if ror1 and ror2:
                if not sig1 and not sig2:
                    comparison = (
                        f"Neither {drug1} nor {drug2} shows a detected safety signal "
                        f"for {adverse_event} (ROR does not meet the signal-detection "
                        "threshold for either drug); the higher raw ROR is not a "
                        "meaningful difference."
                    )
                elif sig1 and not sig2:
                    comparison = (
                        f"{drug1} shows a detected safety signal for {adverse_event}; "
                        f"{drug2} does not."
                    )
                elif sig2 and not sig1:
                    comparison = (
                        f"{drug2} shows a detected safety signal for {adverse_event}; "
                        f"{drug1} does not."
                    )
                elif ror1 > ror2 * _SIMILAR_STRENGTH_RATIO:
                    comparison = f"Both show a detected signal; {drug1}'s is stronger than {drug2}'s"
                elif ror2 > ror1 * _SIMILAR_STRENGTH_RATIO:
                    comparison = f"Both show a detected signal; {drug2}'s is stronger than {drug1}'s"
                else:
                    comparison = (
                        f"{drug1} and {drug2} show similar-strength detected signals"
                    )

            # Fix-R37: each arm now carries the 2x2 case counts its metrics were
            # computed from. _calculate_disproportionality had already built
            # them above and this method discarded them, so a reader could not
            # tell a verdict backed by thousands of co-reported cases from one
            # backed by a handful without issuing two more calls -- and nothing
            # in the output prompted them to.
            arms = [
                _comparison_arm(drug1, result1),
                _comparison_arm(drug2, result2),
            ]

            return {
                "status": "success",
                "adverse_event": adverse_event,
                "drug1": arms[0],
                "drug2": arms[1],
                "comparison": comparison,
                "comparison_caveat": _small_count_caveat(arms),
                "note": "Direct comparison of safety signals. Both drugs may show signals due to different baseline risks.",
            }

        except Exception as e:
            return {"status": "error", "error": f"Drug comparison failed: {str(e)}"}

    def _analyze_temporal_trends(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze temporal trends in adverse event reporting."""
        try:
            drug_name = arguments.get("drug_name")
            adverse_event = arguments.get("adverse_event")

            if not drug_name:
                return {"status": "error", "error": "Must provide drug_name"}

            # Build base query
            if adverse_event:
                search_query = f'{_drug_clause(drug_name)}+AND+patient.reaction.reactionmeddrapt:"{adverse_event}"'
            else:
                search_query = _drug_clause(drug_name)

            # Get counts by receive date (year).
            #
            # Fix-R38 audit: unlike a term facet, a DATE facet is not paged --
            # openFDA returns the whole series and ignores `limit`. Measured live
            # 2026-08-11 for HYDROMORPHONE: count=receivedate returns 6,557 daily
            # buckets with no `limit` and the identical 6,557 with `limit=999`.
            # So no truncation disclosure is owed here and the year totals below
            # are complete. Do NOT "fix" this by adding a limit -- that would cap
            # the series rather than extend it.
            url = self._with_api_key(
                f"{FDA_BASE_URL}?search={search_query}&count=receivedate"
            )

            response = request_with_retry(requests, "GET", url, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            # Parse and aggregate by year
            yearly_counts = {}
            for result in results:
                # OpenFDA count=receivedate returns "time" key, not "term"
                date_str = result.get("time") or result.get("term", "")
                if len(date_str) >= 4:
                    year = date_str[:4]
                    count = result.get("count", 0)
                    yearly_counts[year] = yearly_counts.get(year, 0) + count

            # Format temporal data
            temporal_data = [
                {"year": year, "count": count}
                for year, count in sorted(yearly_counts.items())
            ]

            # Calculate trend
            if len(temporal_data) >= 2:
                first_year_count = temporal_data[0]["count"]
                last_year_count = temporal_data[-1]["count"]
                percent_change = (
                    ((last_year_count - first_year_count) / first_year_count * 100)
                    if first_year_count > 0
                    else 0
                )
                trend = (
                    "Increasing"
                    if percent_change > 10
                    else ("Decreasing" if percent_change < -10 else "Stable")
                )
            else:
                percent_change = 0
                trend = "Insufficient data"

            return {
                "status": "success",
                "drug_name": drug_name,
                "adverse_event": adverse_event or "All events",
                "temporal_data": temporal_data,
                "trend_analysis": {
                    "trend": trend,
                    "percent_change": round(percent_change, 1),
                    "years_analyzed": len(temporal_data),
                },
                "note": "Temporal trends may reflect increased awareness, reporting, or actual incidence changes",
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Temporal analysis failed: {str(e)}"}

    def _rollup_meddra_hierarchy(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate adverse events by MedDRA hierarchy levels (PT → HLT → SOC)."""
        try:
            drug_name = arguments.get("drug_name")

            if not drug_name:
                return {"status": "error", "error": "Must provide drug_name"}

            # Get preferred term (PT) level reactions. Ask for the whole page
            # this caller is entitled to rather than openFDA's 100-row default:
            # the ranking is far longer than either (>999 distinct PTs for
            # HYDROMORPHONE, see PT_COUNT_FIELD), so every extra row is a real
            # reaction that would otherwise be silently absent.
            search_query = _drug_clause(drug_name)
            limit = self._count_limit()
            url = self._with_api_key(
                f"{FDA_BASE_URL}?search={search_query}"
                f"&count={PT_COUNT_FIELD}&limit={limit}"
            )

            response = request_with_retry(requests, "GET", url, timeout=30)
            response.raise_for_status()

            data = response.json()
            pt_results = data.get("results", [])

            # Format PT level. Every returned row is kept -- slicing here is what
            # produced the constant "total" this fix removes.
            pt_level = [
                {"preferred_term": r.get("term"), "count": r.get("count")}
                for r in pt_results
            ]

            # `limit` is already the ceiling, so there is no row past it to probe
            # with: a full page is all that can be observed and the honest reading
            # is "possibly incomplete", never "complete". A short page, by
            # contrast, exhausted the facet, so unique_PTs_returned is then the
            # true number of distinct PTs.
            truncated = len(pt_level) >= limit

            # Note: Full MedDRA hierarchy requires MedDRA license and the FAERS
            # API doesn't provide HLT/SOC directly, so nothing here is rolled up
            # above PT -- there is no derived SOC/HLT total that could inherit
            # the truncation described above.
            hierarchy: Dict[str, Any] = {
                "PT_level": pt_level,
                "unique_PTs_returned": len(pt_level),
                "limit": limit,
                "truncated": truncated,
            }
            if truncated:
                hierarchy["truncation_note"] = _ranked_terms_truncation_note(
                    "preferred terms (PTs)", len(pt_level), observed=False
                )

            return {
                "status": "success",
                "data": {
                    "drug_name": drug_name,
                    "meddra_hierarchy": hierarchy,
                    "note": "Full MedDRA hierarchy (HLT, SOC) requires MedDRA license. Showing Preferred Term (PT) level only.",
                    "recommendation": "Use MedDRA dictionary to map PTs to higher-level terms for system organ class analysis",
                },
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"MedDRA rollup failed: {str(e)}"}

    # Helper methods for statistical calculations

    def _get_faers_count(
        self, drug_name: str = None, adverse_event: str = None
    ) -> Optional[int]:
        """Get count of FAERS reports matching criteria.

        Returns None (not 0) if the request fails (e.g. rate limited or a
        network error), so a failure isn't mistaken for a genuine zero
        count -- a failed fetch used to be silently treated as a genuine
        zero-count result, so `_calculate_disproportionality` reported
        "Insufficient data: a=0, b=0, c=0, d=0" for well-known drug/event
        pairs during a rate-limit window, indistinguishable from "this
        combination truly has no FAERS reports" (confirmed live: retrying
        the exact same query after the rate limit cleared returned correct
        nonzero counts and a real ROR/PRR/IC signal). Callers must check
        for None before doing arithmetic.
        """
        try:
            search_query = _faers_search_query(drug_name, adverse_event)
            if search_query:
                url = f"{FDA_BASE_URL}?search={search_query}&limit=1"
            else:
                # No filters: the whole-database total.
                url = f"{FDA_BASE_URL}?limit=1"

            url = self._with_api_key(url)

            response = request_with_retry(requests, "GET", url, timeout=30)
            if response.status_code == 404:
                # openFDA returns 404 (not an empty 200) for a query with no matches.
                return 0
            response.raise_for_status()

            data = response.json()
            return data.get("meta", {}).get("results", {}).get("total", 0)

        except Exception:
            return None

    def _get_faers_total_count(self) -> Optional[int]:
        """Get total number of reports in FAERS database."""
        return self._get_faers_count(None, None)

    def _calculate_ror_ci(self, a: int, b: int, c: int, d: int) -> Dict[str, float]:
        """Calculate 95% confidence interval for ROR."""
        ror = (a / b) / (c / d)
        se_log_ror = math.sqrt((1 / a) + (1 / b) + (1 / c) + (1 / d))
        log_ror = math.log(ror)

        # 95% CI (z = 1.96)
        lower = math.exp(log_ror - 1.96 * se_log_ror)
        upper = math.exp(log_ror + 1.96 * se_log_ror)

        return {"lower": lower, "upper": upper}

    def _calculate_prr_ci(self, a: int, b: int, c: int, d: int) -> Dict[str, float]:
        """Calculate 95% confidence interval for PRR."""
        prr = (a / (a + b)) / (c / (c + d))
        se_log_prr = math.sqrt((b / (a * (a + b))) + (d / (c * (c + d))))
        log_prr = math.log(prr)

        lower = math.exp(log_prr - 1.96 * se_log_prr)
        upper = math.exp(log_prr + 1.96 * se_log_prr)

        return {"lower": lower, "upper": upper}

    def _calculate_ic(self, a: int, b: int, c: int, d: int) -> float:
        """Calculate Information Component (IC)."""
        n = a + b + c + d
        expected = ((a + b) * (a + c)) / n

        if expected <= 0 or a <= 0:
            return 0.0

        ic = math.log2((a + 0.5) / (expected + 0.5))
        return ic

    def _calculate_ic_ci(self, a: int, b: int, c: int, d: int) -> Dict[str, float]:
        """Calculate 95% confidence interval for IC."""
        n = a + b + c + d
        expected = ((a + b) * (a + c)) / n

        if expected <= 0 or a <= 0:
            return {"lower": 0.0, "upper": 0.0}

        # Approximate variance
        variance = (
            (1 / (a + 0.5))
            - (1 / ((a + b) + 0.5))
            - (1 / ((a + c) + 0.5))
            + (1 / (n + 0.5))
        )
        se = math.sqrt(variance) / math.log(2)

        ic = self._calculate_ic(a, b, c, d)
        lower = ic - 1.96 * se
        upper = ic + 1.96 * se

        return {"lower": lower, "upper": upper}
