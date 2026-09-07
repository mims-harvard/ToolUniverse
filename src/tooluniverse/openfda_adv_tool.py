import re
import os
import copy
import time
import requests
import urllib.parse
from .base_tool import BaseTool
from .cache.memory_cache import LRUCache
from .http_utils import request_with_retry
from .tool_registry import register_tool


# ---- FAERS report-total memo ----
#
# Every FAERS count tool asks openFDA the same two questions before it can
# describe its own facet: how many reports match the search at all, and how many
# of them named the queried drug. Neither depends on which field the tool is
# counting, so a workup that asks several questions about one drug re-sends them
# verbatim once per tool.
#
# Measured live 2026-08-13 on a four-tool CYANOKIT workup
# (FAERS_count_reactions_by_drug_event, FAERS_count_patient_age_distribution,
# FAERS_count_seriousness_by_drug_event, FAERS_count_outcomes_by_drug_event):
# 12 HTTP requests, 6 distinct URLs, so 6 of the 12 were re-asks -- each probe
# fetched 4 times. Only the four `count=` facets genuinely differ. Memoised, the
# same workup makes 6 requests and repeats nothing.
#
# Keyed on (endpoint, search query) rather than on the built URL. `limit=0` and
# `limit=1` are the same question and must share an answer; the api_key is part
# of the URL but not part of the question, so keying on it fragments the map and
# stops keyed and anonymous callers sharing; and this module already treats a
# built URL as secret-bearing (faers_analytics_tool._api_request_failed_error
# exists solely to strip api_key= out of error text), so a URL key would put
# that secret in a process-global dict key.
#
# faers_analytics_tool writes here too. The two used to spell the same question
# differently -- faers_drug_name_clause always quoted the drug name while
# _render_clause quoted only when the value contained a space -- and an earlier
# comment here called that divergence deliberate on both sides. It was not:
# Fix-54B-1 established that the unquoted spelling is simply wrong for a
# hyphenated name (the hyphen is a Lucene operator, so the name is reparsed
# into a union of different drugs), and _render_clause now quotes too. Both
# paths therefore render the same clause for the same drug and share entries.
# Quoting still remains the property that makes the key correct: a quoted and
# an unquoted name really are different openFDA queries, so if a caller ever
# reintroduces an unquoted spelling the key must keep the two apart.
#
# LRUCache is the package's own thread-safe, size-bounded cache; it stores a
# timestamp but does not expire on it, so the TTL is applied here. Bounded on
# both axes because tool processes are long-lived: entries expire so a refreshed
# FAERS snapshot cannot be served indefinitely, and the map is capped so a
# session querying thousands of drugs cannot grow it without limit.
#
# Deliberately NOT single-flight. Threads that miss concurrently -- the normal
# shape when an agent dispatches a workup in parallel -- will each issue the
# request, so the 12->6 figure above is measured for sequential calls and is the
# best case. cache.memory_cache.SingleFlight is the tool for closing that, at
# the cost of making one openFDA probe block on another; not taken here.
_QUERY_TOTAL_TTL_SECONDS = 300.0
_query_total_memo = LRUCache(max_size=256)


def _memoized_report_total(key):
    """A cached total for this (endpoint, search), or None if there is not one.

    None is also what a genuine miss looks like, which is safe because the only
    value ever stored is an int -- failures are deliberately not cached (see
    `_memoize_report_total`), so "no entry" and "measured and failed" both
    correctly mean "go ask openFDA".
    """
    entry = _query_total_memo.get(key)
    if entry is None:
        return None
    stored_at, total = entry
    if time.monotonic() - stored_at > _QUERY_TOTAL_TTL_SECONDS:
        _query_total_memo.delete(key)
        return None
    return total


def _memoize_report_total(key, total):
    """Remember a successful probe result.

    Rejects anything that is not an int, which is what keeps a transient failure
    from becoming sticky: a rate-limited probe returns None, and caching that
    None would make every later caller in the process inherit one unlucky moment
    for the whole TTL. Callers generally check this themselves to decide their
    own return value; the guard is repeated here because poisoning a shared
    cache is the more expensive mistake.
    """
    if isinstance(total, int):
        _query_total_memo.set(key, (time.monotonic(), total))


def faers_report_total_key(endpoint_url, search_query):
    """The memo key two modules must agree on to share an answer."""
    return f"{endpoint_url}|{search_query or ''}"


# ---- openFDA `count=` aggregation paging ----
#
# openFDA answers a `count=` query with only the most frequent values and does
# NOT report how many distinct values exist -- its `meta` block carries just
# disclaimer/terms/license/last_updated, never a grand total. Measured live
# 2026-08 against
#   https://api.fda.gov/drug/event.json?search=...&count=patient.reaction.reactionmeddrapt.exact
# an unqualified count query returns exactly 100 rows, so 100 is the effective
# default page size for these aggregations.
COUNT_DEFAULT_LIMIT = 100

# Documented maximum for `limit`: "Currently, the largest allowed value for the
# `limit` parameter is 1000." -- https://open.fda.gov/apis/query-parameters/
COUNT_MAX_LIMIT = 1000

# Measured, undocumented: anonymous callers are capped one below the documented
# maximum. limit=1000 (and above) answers HTTP 403 {"code": "API_KEY_MISSING"}
# while limit=999 succeeds, reproduced across both count and plain search
# queries. Callers with FDA_API_KEY set may use the full documented maximum.
COUNT_MAX_LIMIT_ANONYMOUS = 999

# How many values of the counted field ONE report can carry, declared per tool as
# "count_field_cardinality". openFDA's `count=` facet counts VALUES, not reports:
# a field nested under patient.reaction[] or patient.drug[] is recorded once per
# reaction / per drug, so a single report lands in several buckets and the rows
# sum ABOVE the number of matching reports. A report-level field (occurcountry,
# serious, seriousnessdeath) can only put a report in one bucket, so its rows sum
# at or BELOW that number -- reports missing the field are dropped from the facet
# rather than bucketed as unknown. Both distortions are invisible in the rows
# themselves, and they run in opposite directions, so `coverage_note` has to name
# which one applies. Measured live 2026-08 for
# search=(patient.drug.medicinalproduct:"vasopressin" OR
#         patient.drug.openfda.generic_name:"vasopressin"), 4,741 matching reports:
#   patient.reaction.reactionoutcome            5,514  = 116% of the reports
#   patient.drug.drugadministrationroute.exact  9,273  = 196%
#   patient.drug.medicinalproduct.exact        71,874  = 1516%
#   occurcountry.exact                          3,949  =  83%
#   patient.patientagegroup                       906  =  19%
# "per_report" is the default because it is the conservative claim: it promises
# only that rows are a subset, never that they double-count.
COUNT_FIELD_UNITS = {"per_reaction": "reaction", "per_drug": "drug"}

# ---- The one field list every FAERS drug-name lookup searches ----
#
# A FAERS report names its drug in up to three places and openFDA indexes them
# separately: `patient.drug.medicinalproduct` is the free text the reporter
# typed, while `patient.drug.openfda.generic_name` and
# `patient.drug.openfda.brand_name` are added only when openFDA managed to
# resolve that text against an SPL. NONE of the three is a superset of the
# others, so any subset silently undercounts -- and which subset loses depends
# on the drug, so there is no "best two" to settle on. Measured live against
# https://api.fda.gov/drug/event.json?search=<clause>&limit=0 on 2026-08-11
# (`meta.results.total`):
#
#   drug          MP only   MP+GN     GN+BN     union of all three
#   TOFACITINIB    13,075   186,783   186,746   186,783   <- MP alone is 14.3x low
#   MEFLOQUINE        751       751       156       751   <- GN+BN is 4.8x low
#   SEROQUEL       87,960    87,960   164,138   165,010   <- union beats all three
#   XELJANZ       178,937   178,937   183,405   183,467   <- union beats all three
#
# The last two rows are the reason this is a UNION and not a choice: 165,010 >
# 164,138 and 183,467 > 183,405, i.e. some reports name the drug in
# medicinalproduct and in neither openFDA field, so dropping medicinalproduct
# loses real reports even for a brand name. Symmetrically, MEFLOQUINE and
# YELLOW FEVER VACCINE (GN+BN = 0) show the openFDA fields are empty for whole
# classes of products, so they cannot stand alone either.
#
# Widening is safe here, checked rather than assumed: SODIUM CHLORIDE counts
# 353,707 under the union, nowhere near the 779,180 that the old
# double-encoding defect produced by collapsing the name to the bare token
# "SODIUM", and YELLOW FEVER VACCINE counts 111 under the union -- exactly its
# medicinalproduct-only total, so the extra fields add no spurious matches.
#
# THE BUG THIS CONSTANT PREVENTS IS DRIFT, not any one wrong number. Four
# families of FAERS tools each grew their own field list (medicinalproduct
# only; medicinalproduct + generic_name; generic_name + brand_name), so the
# same question about the same drug returned three different totals depending
# on which tool a caller happened to pick, with nothing in any response saying
# the totals were not comparable. Every FAERS drug-name lookup -- Python
# builders and `fields.search_fields` in the JSON configs alike -- must resolve
# to exactly this list; tests/unit/test_faers_drug_name_field_union.py fails if
# one of them wanders off again.
FAERS_DRUG_NAME_FIELDS = [
    "patient.drug.medicinalproduct",
    "patient.drug.openfda.generic_name",
    "patient.drug.openfda.brand_name",
]

# ---- What the union costs, and why it has to be disclosed ----
#
# The union above is right (see the table) but it is not free: the two openFDA
# fields are ANNOTATIONS, not what the reporter wrote. openFDA resolves the
# reported product text against an SPL and then attaches EVERY brand and generic
# name registered for that product's active ingredient. So a report that named
# plain "HYDROXOCOBALAMIN" carries openfda.brand_name = ["CYANOKIT",
# "HYDROXOCOBALAMIN"], and a search for CYANOKIT matches it.
#
# That is usually harmless -- XELJANZ and TOFACITINIB really are the same
# product -- and occasionally dangerous, because a brand and its ingredient can
# serve different populations entirely. Measured live 2026-08-12 against
# `meta.results.total`, "named" = medicinalproduct alone, "matched" = the union:
#
#   query          named    matched   matched-only   share
#   IOSAT              6      1,395          1,389   99.6%
#   CYANOKIT         238      4,119          3,881   94.2%
#   SUBLOCADE      5,134     28,481         23,347   82.0%
#   ADVIL         67,159    264,100        196,941   74.6%
#   XGEVA         36,039     51,441         15,402   29.9%
#   OZEMPIC       66,161     66,161              0    0.0%
#   MAKENA        22,729     22,729              0    0.0%
#
# CYANOKIT is the cyanide-poisoning antidote; hydroxocobalamin is also a routine
# vitamin B12 supplement, and 3,881 of the 4,119 "CYANOKIT" reports are B12
# reports -- sampled directly, e.g. safetyreportid 10016092, medicinalproduct
# HYDROXOCOBALAMIN, drugindication MICROCYTIC ANAEMIA. Before this disclosure
# FAERS_count_reactions_by_drug_event{"medicinalproduct": "CYANOKIT"} answered
# ACUTE KIDNEY INJURY 211 against total_reports_matching_query 4,119 with
# nothing saying the denominator was mostly vitamin recipients. IOSAT is the
# same shape for a radiation countermeasure vs potassium iodide the supplement.
#
# The OZEMPIC and MAKENA rows are why a static warning would be wrong and a
# measured one is right: the share is a property of the drug rather than of the
# query, and for some drugs it is exactly zero, so a fixed caveat would fire
# where there is nothing to caveat. The seven rows above were chosen to span the
# range, so they say nothing about how common either end is.
FAERS_REPORTED_NAME_FIELD = FAERS_DRUG_NAME_FIELDS[0]


def faers_drug_name_clause(drug_name, joiner="+OR+"):
    """Parenthesized OR group matching `drug_name` in every FAERS name field.

    For the callers that build their openFDA query as a plain string rather than
    through this module's config-driven builders (faers_analytics_tool and
    openfda_tool). Shared so those two cannot drift from FAERS_DRUG_NAME_FIELDS
    or from each other.

    This used to spell the quoting rule out for itself, justified as a
    "deliberate difference" from `_render_clause`: it always quoted, while
    `_render_clause` quoted only when the value contained a space. Fix-54B-1
    established that the space-gated rule was simply wrong for a hyphenated
    name, so `_render_clause` now quotes by default and the two rules are the
    same rule. It is called rather than restated here, because a divergence
    between these two spellings is exactly what Fix-54B-1 had to repair.

    Two differences from `_render_field_group` remain, which is why this joins
    the clauses itself rather than calling it:

    * `joiner` is configurable because openfda_tool hands its finished query to
      `requests` as a `params` value, where a literal "+" is percent-encoded to
      %2B and reaches openFDA as a plus sign instead of a separator; that
      caller passes " OR ".
    * the parentheses are unconditional. They are not optional in either
      caller: both AND a reaction filter onto this clause, and Lucene binds AND
      tighter than OR. `_render_field_group` drops them for a single field,
      which is safe for its own callers but would silently lose the grouping
      here if FAERS_DRUG_NAME_FIELDS ever held one entry.
    """
    return (
        "("
        + joiner.join(_render_clause(f, drug_name) for f in FAERS_DRUG_NAME_FIELDS)
        + ")"
    )


def faers_meta_total(payload):
    """openFDA's ``meta.results.total``, or None when it does not report one.

    One home for an extraction that had drifted into three variants inside this
    package on the day it was written: ``_fetch_query_total`` below omitted the
    bool exclusion, and ``openfda_approval_tool`` defaulted to 0 -- and 0 is the
    one value this must never invent, because "openFDA did not say" and "nothing
    matched" are different answers.
    """
    total = ((payload or {}).get("meta") or {}).get("results", {}).get("total")
    if isinstance(total, bool) or not isinstance(total, int):
        return None
    return total


def faers_detail_envelope(reports, total, limit, skip):
    """Wrap a page of FAERS case reports with the size of the set it came from.

    Fix-R55B-1: the six ``FAERS_search_*`` detail tools returned the page as a
    bare list and dropped openFDA's ``meta.results.total`` on the floor, so a
    page was indistinguishable from the complete answer. Measured live against
    api.fda.gov on 2026-08-13, co-occurrence searches at the default limit of
    10::

        rifampin + methadone      10 returned, meta.results.total = 35
        clozapine + fluvoxamine   10 returned, meta.results.total = 736
        warfarin + amiodarone     10 returned, meta.results.total = 5941

    A pharmacovigilance reviewer asking "how often are warfarin and amiodarone
    co-reported" received ten case reports with nothing to say the answer was
    5941 -- an understatement of the signal by more than two orders of
    magnitude, presented as a complete result.

    The total costs no extra request: openFDA already returns it in the same
    response body these tools were parsing for ``results``. It is deliberately
    NOT written into the ``_query_total_memo`` shared with the ``count=``
    aggregation tools, because those build a differently-shaped search string
    for the same question and a total filed under a near-miss key is worse than
    no cache hit.

    Key names are the repo-wide disclosure vocabulary -- ``count``,
    ``total_available``, ``truncated``, ``truncation_note`` -- as used by
    ``BaseRESTTool._apply_pagination_disclosure`` and
    ``CBioPortalRESTTool._truncation_fields``. That method cannot be called
    here: it derives ``truncated`` as ``returned < total`` with no offset
    concept, which would report the last ``skip`` page of a FAERS search as
    partial.

    ``total_available`` is None when openFDA omits ``meta.results.total``; None
    means "not reported", never zero.
    """
    count = len(reports)
    envelope = {
        "status": "success",
        "reports": reports,
        "count": count,
        "total_available": total,
        "limit": limit,
        "skip": skip,
        "truncated": total is not None and skip + count < total,
    }
    if envelope["truncated"]:
        envelope["truncation_note"] = (
            f"Partial result: reports {skip + 1}-{skip + count} of "
            f"{total} matching this search. Page through the rest with "
            f"'skip' (limit is capped at 100 per request), or use the "
            f"FAERS_count_* tools if you need aggregate counts rather than "
            f"individual case narratives."
        )
    return envelope


def _is_error_payload(payload):
    """True when ``_search`` returned an error sentinel rather than count rows."""
    return (
        isinstance(payload, list)
        and len(payload) > 0
        and isinstance(payload[0], dict)
        and "error" in payload[0]
        and "term" not in payload[0]
    )


def _is_range(value):
    """True for a Lucene range such as "[20141001 TO 20141231]".

    These carry spaces yet must be sent unquoted; quoting turns the range into a
    literal term and the query matches nothing.
    """
    return bool(
        isinstance(value, str)
        and re.match(r"^\s*[\[\{].+\sTO\s.+[\]\}]\s*$", value, re.IGNORECASE)
    )


def _render_clause(fda_field_name, value):
    """Render a single ``field:value`` Lucene clause for an openFDA search.

    This is the ONE place that decides whether a mapped parameter value gets
    quoted. A multi-word term ("ACUTE KIDNEY INJURY") must be quoted, otherwise
    Lucene splits it and the trailing words become free-text clauses; a Lucene
    range ("[20141001 TO 20141231]") also contains spaces but must NOT be quoted,
    because quoting makes openFDA match it as a literal string and return
    nothing.

    The rule used to be spelled out separately in each builder's multi-field and
    single-field branches, and they drifted: the range exemption was added to the
    multi-field branches only, so `receivedate` -- which maps to a single field --
    kept being quoted and a date-bounded query such as
    ``FAERS_count_reactions_by_drug_event(receivedate="[20141001 TO 20141231]")``
    silently returned zero rows. Keep this logic here so the paths cannot drift
    again.

    Fix-54B-1: the test used to be "contains a space", which sent a
    single-token HYPHENATED name unquoted -- and a hyphen is a Lucene operator,
    so the name was reparsed into its parts and the query silently became a
    union of different drugs. `faers_drug_name_clause` always quotes for
    exactly this reason and its docstring names this exact case
    ("CO-TRIMOXAZOLE"), so the two paths disagreed on the input each was
    written about. Measured against api.fda.gov on 2026-08-13, unquoted vs
    quoted total for the same field:value::

        patient.drug.medicinalproduct:sumatriptan-naproxen  124792  vs      13
        patient.drug.medicinalproduct:CO-TRIMOXAZOLE         24806  vs    1416

    FAERS_count_reactions_by_drug_event(medicinalproduct="sumatriptan-naproxen")
    reported 219,048 matching reports -- the union of sumatriptan (51,295) and
    naproxen (172,094) across the three name fields, for a combination product
    with 1,438 reports under its actual brand name. A combination product
    outnumbering its own components is the tell; the same held for
    metoprolol-hydrochlorothiazide (595,912) vs metoprolol alone (371,421).

    Quoting is now the default for STRING values, with a Lucene range as the
    only carve-out among them; a non-string value (an int age, say) is still
    rendered bare, since only a string can carry an operator character.
    The cost of widening it was measured over every other value shape these
    builders send -- single-token drug names, generic_name, brand_name, single
    and multi-word reaction terms, all eight HUMAN_TO_FDA_MAP coded values
    ("1", "2", "048", "800", ...), occurcountry and a numeric patientonsetage.
    Quoted and unquoted returned IDENTICAL totals for all of them, so no query
    changes except the ones that were wrong. The range carve-out is load-
    bearing and was re-confirmed the same way: ``receivedate:[20141001 TO
    20141231]`` returns 197,676 unquoted and HTTP 404 NOT_FOUND quoted.

    ``receivedate`` is documented as accepting a single ``YYYYMMDD`` date as
    well as a range, and that form is NOT a range, so it is now quoted. It was
    measured separately for the same reason: ``receivedate:20141001`` returns
    2,415 quoted and unquoted, and ``receiptdate:20141001`` returns 2,375
    either way.

    One shape is knowingly outside the measured set: a caller-supplied Lucene
    wildcard (``aspirin*``) is now matched literally. No parameter here
    documents wildcards as supported.
    """
    if isinstance(value, str) and not _is_range(value):
        return f'{fda_field_name}:"{value}"'
    return f"{fda_field_name}:{value}"


def _render_field_group(fda_fields, value):
    """Render the clause for one parameter across every FDA field it maps to.

    Several fields for one parameter are OR-ed, and the group MUST be
    parenthesized: openFDA/Lucene binds AND tighter than OR, so an un-grouped
    "a:x OR b:x AND c:y OR d:y" parses as "a:x OR (b:x AND c:y) OR d:y" --
    wrong. That silently broke every filtered multi-field query, e.g. FAERS
    colistin + reaction "acute kidney injury" returned 0 (HTTP 404) even though
    the unfiltered count shows ACUTE KIDNEY INJURY = 151. Wrapping keeps
    "(a OR b) AND (c OR d)".
    """
    clauses = [_render_clause(name, value) for name in fda_fields]
    if len(clauses) == 1:
        return clauses[0]
    return "(" + "+OR+".join(clauses) + ")"


# ---- Helper: human readable -> openFDA code mapping ----
HUMAN_TO_FDA_MAP = {
    "fulfillexpeditecriteria": {"Yes": "1", "No": "2"},
    "patient.patientsex": {"Unknown": "0", "Male": "1", "Female": "2"},
    "patient.patientagegroup": {
        "Neonate": "1",
        "Infant": "2",
        "Child": "3",
        "Adolescent": "4",
        "Adult": "5",
        "Elderly": "6",
    },
    "patientonsetageunit": {
        "Decade": "800",
        "Year": "801",
        "Month": "802",
        "Week": "803",
        "Day": "804",
        "Hour": "805",
    },
    "patient.reaction.reactionoutcome": {
        "Recovered/resolved": "1",
        "Recovering/resolving": "2",
        "Not recovered/not resolved": "3",
        "Recovered/resolved with sequelae": "4",
        "Fatal": "5",
        "Unknown": "6",
    },
    "serious": {"Yes": "1", "No": "2"},
    "seriousnessdeath": {"Yes": "1"},
    "seriousnesshospitalization": {"Yes": "1"},
    "seriousnessdisabling": {"Yes": "1"},
    "seriousnesslifethreatening": {"Yes": "1"},
    "seriousnessother": {"Yes": "1"},
    "primarysource.qualification": {
        "Physician": "1",
        "Pharmacist": "2",
        "Other health professional": "3",
        "Lawyer": "4",
        "Consumer or non-health professional": "5",
    },
    "patient.drug.drugcharacterization": {
        "Suspect": "1",
        "Concomitant": "2",
        "Interacting": "3",
    },
    "patient.drug.drugadministrationroute": {
        "Oral": "048",
        "Intravenous": "042",
        "Intramuscular": "030",
        "Subcutaneous": "058",
        "Rectal": "054",
        "Topical": "061",
        "Respiratory (inhalation)": "055",
        "Ophthalmic": "047",
        "Unknown": "065",
    },
}


# ---- Base Tool Class ----
@register_tool("FDADrugAdverseEventTool")
class FDADrugAdverseEventTool(BaseTool):
    # The argument carrying the drug name, overridden by the multi-drug
    # subclass. Named here so `_add_name_scope_disclosure` can find it without
    # guessing.
    DRUG_PARAMETER = "medicinalproduct"

    def _drug_name_fields(self, override=None):
        """FDA fields this tool's drug-name parameter searches.

        One home for the lookup, because its FALLBACK is load-bearing and used
        to be spelled differently at each site: a config that forgets the map
        must still ask the same question as every other FAERS tool, which means
        the canonical union rather than medicinalproduct alone. Reading it as
        `... or []` instead -- as the scope disclosure first did -- silently
        skipped the disclosure for exactly that config, the one whose query is
        the most widened.

        `override` is the single degree of freedom any caller needs: the scope
        probe re-asks the same query with the name narrowed to
        FAERS_REPORTED_NAME_FIELD.
        """
        if override is not None:
            return override
        return self.search_fields.get(self.DRUG_PARAMETER) or FAERS_DRUG_NAME_FIELDS

    def __init__(
        self,
        tool_config,
        endpoint_url="https://api.fda.gov/drug/event.json",
        api_key=None,
    ):
        super().__init__(tool_config)
        self.endpoint_url = endpoint_url
        self.api_key = api_key or os.getenv("FDA_API_KEY")
        self.search_fields = tool_config.get("fields", {}).get("search_fields", {})
        self.return_fields = tool_config.get("fields", {}).get("return_fields", [])
        self.count_field = tool_config.get("count_field") or (
            self.return_fields[0] if self.return_fields else None
        )
        self.return_fields_mapping = tool_config.get("fields", {}).get(
            "return_fields_mapping", {}
        )

        if not self.count_field:
            raise ValueError(
                "Either 'count_field' or 'return_fields' must be defined in tool_config."
            )

        # Opt-in per tool. An openFDA `count=` facet never sums to the number of
        # matching reports, and the caller cannot tell from the rows which way it
        # is off: a report-level field (seriousnessdeath) drops reports that do
        # not record it, so the rows sum BELOW the total, while a field nested
        # under patient.reaction[] or patient.drug[] is recorded once per
        # reaction / per drug, so one report lands in several buckets and the
        # rows sum ABOVE it -- measured 196% of the report total for
        # `patient.drug.drugadministrationroute` on vasopressin. Either way the
        # next step a reader takes ("case fatality = fatal / row sum") is wrong,
        # so every count tool in this family sets "disclose_denominator": true
        # and declares "count_field_cardinality" so `coverage_note` can name the
        # direction. This was previously reserved for report-level fields on the
        # grounds that a coverage fraction is meaningless for a multi-valued
        # field; the fraction is indeed not a coverage share there, but stating
        # the true denominator and the double-counting is exactly what stops the
        # bogus rate, so the multi-valued tools need it more, not less.
        #
        # Disclosure costs one extra openFDA request per call and fails soft.
        # Every subclass inherits it, because run() is shared.
        self.disclose_denominator = bool(tool_config.get("disclose_denominator", False))
        # "per_report" (default), "per_reaction" or "per_drug" -- see
        # COUNT_FIELD_UNITS. An unrecognized value degrades to the conservative
        # "per_report" wording rather than raising.
        self.count_field_cardinality = tool_config.get(
            "count_field_cardinality", "per_report"
        )
        # Optional per-tool sentence about what the counted field actually means,
        # prepended to `coverage_note`. Needed where the field name invites a
        # clinical misreading -- see the FAERS_count_death_related_by_drug config.
        self.count_field_note = tool_config.get("count_field_note", "")

        # Store allowed enum values
        self.parameter_enums = {}
        if "parameter" in tool_config and "properties" in tool_config["parameter"]:
            for param_name, param_def in tool_config["parameter"]["properties"].items():
                if "enum" in param_def:
                    self.parameter_enums[param_name] = param_def["enum"]

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)

        # Validate enum parameters
        validation_error = self.validate_enum_arguments(arguments)
        if validation_error:
            return {"status": "error", "error": validation_error}

        limit_error, limit = self._resolve_count_limit(arguments)
        if limit_error:
            return {"status": "error", "error": limit_error}

        # Store reactionmeddraverse for filtering results
        reaction_filter = arguments.get("reactionmeddraverse")

        response = self._search(arguments, limit=self._fetch_limit(limit))
        if _is_error_payload(response):
            return response
        envelope = self._build_count_envelope(
            response, limit, reaction_filter=reaction_filter
        )
        if self.disclose_denominator:
            self._add_coverage_disclosure(envelope, arguments)
        return envelope

    # ---- count paging / truncation disclosure ----

    def _limit_ceiling(self):
        """Highest `limit` this caller may send to openFDA."""
        return COUNT_MAX_LIMIT if self.api_key else COUNT_MAX_LIMIT_ANONYMOUS

    def _resolve_count_limit(self, arguments):
        """Pop and validate `limit`, returning ``(error_message, limit)``."""
        limit = arguments.pop("limit", COUNT_DEFAULT_LIMIT)
        if limit is None:
            limit = COUNT_DEFAULT_LIMIT
        if isinstance(limit, bool) or not isinstance(limit, int):
            message = (
                f"Invalid value '{limit}' for 'limit'. Expected an integer between 1 "
                f"and {COUNT_MAX_LIMIT}."
            )
            return message, None
        if limit < 1 or limit > COUNT_MAX_LIMIT:
            message = (
                f"'limit' must be between 1 and {COUNT_MAX_LIMIT} "
                f"(openFDA's documented maximum); got {limit}."
            )
            return message, None
        if limit > self._limit_ceiling():
            message = (
                f"'limit' above {COUNT_MAX_LIMIT_ANONYMOUS} requires an openFDA API "
                "key: set the FDA_API_KEY environment variable, or lower 'limit' to "
                f"{COUNT_MAX_LIMIT_ANONYMOUS} or below."
            )
            return message, None
        return None, limit

    def _fetch_limit(self, limit):
        """Ask openFDA for one extra row so truncation can be reported exactly.

        openFDA never states how many distinct values a `count=` aggregation has,
        so the only way to know whether the caller's page is the whole story is
        to request one row past it and see whether it comes back.
        """
        return min(limit + 1, self._limit_ceiling())

    def _build_count_envelope(self, response, limit, reaction_filter=None):
        """Return count rows alongside a top-level truncation disclosure."""
        if not isinstance(response, list):
            response = []

        fetch_limit = self._fetch_limit(limit)
        probed = fetch_limit > limit
        if probed:
            # The probe row came back, so more terms definitely exist.
            truncated = len(response) > limit
        else:
            # Already at the ceiling: a full page is all we can observe, so the
            # honest answer is "possibly incomplete", not "complete".
            truncated = len(response) >= limit

        rows = self._post_process(response[:limit], reaction_filter=reaction_filter)

        envelope = {
            "results": rows,
            "result_count": len(rows),
            "limit": limit,
            "truncated": truncated,
        }
        if truncated:
            certainty = (
                "more terms exist beyond that limit"
                if probed
                else "openFDA filled the page exactly, so more terms may exist beyond it"
            )
            # When a term filter is applied client-side, 'results' is a subset of
            # the ranked list; say so, so the flag is not read as "your one row
            # is incomplete".
            scope = (
                " 'results' was then narrowed to the requested term, so the "
                "truncation applies to the underlying ranking rather than to the "
                "rows shown."
                if reaction_filter
                else ""
            )
            envelope["truncation_note"] = (
                f"openFDA returned only the {min(len(response), limit)} most-reported "
                f"terms for this query (limit={limit}), ranked by descending report "
                f"count; {certainty}. openFDA's count endpoint does not report how "
                "many distinct terms there are in total, so the size of the remainder "
                f"is unknown. Pass a larger 'limit' (maximum {COUNT_MAX_LIMIT}) to "
                "retrieve more. A term missing from this list is NOT evidence that it "
                f"was never reported -- query the term directly to check.{scope}"
            )
        return envelope

    # ---- openFDA `count=` facet coverage disclosure ----

    def _fetch_query_total(self, arguments, drug_fields=None):
        """Reports matching this tool's own search, or ``None`` if unavailable.

        A `count=` response carries no grand total -- openFDA reports the size of
        a search only in `meta.results.total` of a plain (non-count) request, so
        the denominator needs a second call. It is built from the SAME
        ``_build_search_query`` as the facet, otherwise the two figures would not
        be comparable.

        `limit=0` asks for the size without any report bodies: it returns the
        same `meta.results.total` in ~0.5 KB where `limit=1` ships a whole FAERS
        report (~120 KB, mostly `openfda` arrays) only to discard it. A search
        with no matches still answers HTTP 404 either way.
        """
        query_error, search_query = self._build_search_query(
            arguments, drug_fields=drug_fields
        )
        if query_error:
            return None
        search_encoded = urllib.parse.quote(search_query, safe='+:"')
        key = f"api_key={self.api_key}&" if self.api_key else ""
        url = f"{self.endpoint_url}?{key}search={search_encoded}&limit=0"
        memo_key = faers_report_total_key(self.endpoint_url, search_query)
        cached = _memoized_report_total(memo_key)
        if cached is not None:
            return cached
        try:
            # request_with_retry backs off on 429, which these probes make more
            # likely by raising the tool's request rate -- one retry is cheaper
            # than degrading to a null denominator. Note the Retry-After sleep
            # happens OUTSIDE the per-request timeout, hence capping it too:
            # 10 + 5 + 10 = 25s per probe rather than the default helper's 90s.
            #
            # This method now serves TWO probes per call -- the denominator and
            # the drug-name scope measurement -- so a drug-name query issues
            # three requests, not two, and the caller's worst case is the facet's
            # 30s plus 25s per probe = 80s. The probes are therefore the majority
            # of that worst case, which the earlier "must not dominate" framing
            # got wrong; what keeps it bounded is that both probes fail soft, and
            # that a null denominator suppresses the scope probe rather than
            # piling a second retry onto an API that is already rate-limiting.
            response = request_with_retry(
                requests,
                "GET",
                url,
                timeout=10,
                max_attempts=2,
                max_retry_after_seconds=5,
            )
            # openFDA answers a search with no matches with HTTP 404, which here
            # means a genuine zero rather than a failure to measure.
            if response.status_code == 404:
                _memoize_report_total(memo_key, 0)
                return 0
            response.raise_for_status()
            total = faers_meta_total(response.json())
            if total is None:
                return None
            _memoize_report_total(memo_key, total)
            return total
        except (requests.exceptions.RequestException, ValueError):
            return None

    def _count_field_label(self):
        """The counted field named as a caller should read it.

        openFDA's `.exact` suffix selects the un-analysed variant of a string
        field; it is a query detail, not part of the field's identity, and
        naming "occurcountry.exact" in prose invites the reader to go looking
        for a field of that name in the FAERS record layout.
        """
        field = self.count_field or ""
        suffix = ".exact"
        return field[: -len(suffix)] if field.endswith(suffix) else field

    def _coverage_note(self, subset, query_total, truncated, narrowed=False):
        """Prose stating what the facet does and does NOT sum to, and which way.

        The two distortions run in opposite directions (see COUNT_FIELD_UNITS),
        so the note is built from the declared cardinality of the counted field
        AND the measured direction -- a multi-valued field whose reports mostly
        omit it can still land below the total, and saying only "reports are
        excluded" there would hide the double-counting.

        `narrowed` says a reaction-term filter cut 'results' down to the single
        requested term after openFDA ranked the facet. The multi-row prose does
        not apply there -- one term cannot double-count against other rows that
        are no longer present -- so that case gets its own branch rather than
        being described by wording written for a full ranking.
        """
        field = self._count_field_label()
        unit = COUNT_FIELD_UNITS.get(self.count_field_cardinality)
        coverage = (subset / query_total * 100) if query_total else 0.0
        parts = []

        if query_total is None:
            if unit:
                parts.append(
                    "The total number of reports matching this query could not "
                    "be retrieved (the extra openFDA request failed, commonly "
                    "HTTP 429 rate limiting on the anonymous tier), so "
                    "total_reports_matching_query is null. "
                    f"stratified_report_count ({subset:,}) is the sum of the "
                    f"facet rows, and {field} is recorded once per {unit} rather "
                    "than once per report, so a report with several "
                    f"{unit}s is counted in several rows: that sum counts "
                    f"recorded {field} values, NOT reports, and may exceed the "
                    "number of matching reports. Do not use it as a "
                    "denominator. Retry for the total, or set the FDA_API_KEY "
                    "environment variable to raise the rate limit "
                    "(https://open.fda.gov/apis/authentication/)."
                )
            else:
                parts.append(
                    "The total number of reports matching this query could not be "
                    "retrieved (the extra openFDA request failed, commonly HTTP 429 "
                    "rate limiting on the anonymous tier), so "
                    "total_reports_matching_query is null. "
                    f"stratified_report_count ({subset:,}) counts only reports where "
                    f"{field} is recorded and is therefore a LOWER BOUND "
                    "on the number of matching reports -- do not read it as the "
                    "total, and do not divide a row by it to obtain a rate. Retry "
                    "for the total, or set the FDA_API_KEY environment variable to "
                    "raise the rate limit "
                    "(https://open.fda.gov/apis/authentication/)."
                )
        elif query_total == 0 and subset == 0:
            # openFDA answers a search with no matches with HTTP 404, which the
            # probe reads as a true zero. There is no coverage to describe, and
            # the usual prose ("0, 0.0% of 0") reads as a malfunction.
            parts.append(
                "No reports match this query (total_reports_matching_query is "
                "0), so 'results' is empty and there is no facet coverage to "
                "report."
            )
        elif narrowed:
            if subset == 0:
                # openFDA matched the term, so query_total counts real reports,
                # but the client-side narrowing keeps only rows whose term is
                # string-equal to it and kept none. Two causes, and the response
                # cannot tell them apart, so name both: measured for MODAFINIL +
                # "arrest", 176 reports match while no preferred term IS
                # "arrest" (they are CARDIAC ARREST, RESPIRATORY ARREST...).
                # Returning the empty list unexplained reads as "never
                # reported", which is the opposite of what the data says.
                parts.append(
                    f"'results' is empty, yet {query_total:,} report(s) match this "
                    "query including the reaction term you asked for, so this is "
                    "NOT evidence the term was never reported. 'results' keeps only "
                    "rows whose MedDRA term is exactly the term you asked for, and "
                    "none was: either it falls outside the top-'limit' slice of the "
                    "ranking (raise 'limit', maximum 1,000), or openFDA matched your "
                    "text inside longer preferred terms rather than as a term in its "
                    "own right (e.g. 'arrest' matches CARDIAC ARREST and RESPIRATORY "
                    "ARREST). Omit the reaction term to see which terms actually "
                    "matched."
                )
            else:
                parts.append(
                    "'results' has been narrowed to the single reaction term you "
                    f"requested, so stratified_report_count ({subset:,}) is that "
                    "term's own count and total_reports_matching_query "
                    f"({query_total:,}) is every report matching the same search "
                    f"({coverage:.1f}%). One term cannot double-count against rows "
                    "that are no longer present, so unlike a full ranking this "
                    f"percentage is meaningful -- but openFDA counts recorded "
                    f"{field} values rather than reports, so it is a close upper "
                    "bound on the share of reports affected, not exactly that "
                    "share."
                )
        else:
            if unit and subset > query_total:
                # The dangerous direction: the rows sum to more reports than
                # exist, so any rate computed off them is silently deflated.
                parts.append(
                    f"total_reports_matching_query ({query_total:,}) is every "
                    "report matching this query, but the rows in 'results' sum "
                    f"to {subset:,} -- {coverage:.1f}% of it, i.e. MORE than the "
                    f"number of matching reports. {field} is multi-valued: it is "
                    f"recorded once per {unit}, not once per report, so a report "
                    f"with several {unit}s is counted in several rows. The rows "
                    "therefore DOUBLE-COUNT reports and their sum "
                    f"(stratified_report_count, {subset:,}) is a count of "
                    f"recorded {field} values, NOT of reports: do NOT use it as "
                    "a denominator and do NOT divide one row by it to obtain a "
                    "rate. If you need a denominator, use "
                    "total_reports_matching_query, and read each row as "
                    f"'{unit}s recorded', not 'reports affected'. Reports that "
                    f"record no {field} at all are separately EXCLUDED from the "
                    "facet rather than bucketed as unknown."
                )
            elif unit:
                # Multi-valued, yet still below the total: both distortions are
                # present and they cancel to an unknowable degree. Only claim
                # the exclusion is what pulled the sum under when the rows are
                # the whole facet -- with a truncated ranking the missing tail
                # explains it just as well, and the truncation sentence below
                # says so.
                why_below = (
                    ""
                    if truncated
                    else ", which is why the sum still lands below the total"
                )
                parts.append(
                    f"total_reports_matching_query ({query_total:,}) is every "
                    "report matching this query; the rows in 'results' sum to "
                    f"{subset:,} ({coverage:.1f}% of it). Two distortions apply "
                    f"here and they pull in opposite directions: {field} is "
                    f"multi-valued -- recorded once per {unit}, not once per "
                    f"report -- so a report with several {unit}s is counted in "
                    "several rows and the rows DOUBLE-COUNT reports; while "
                    f"reports that record no {field} are EXCLUDED from the facet "
                    f"entirely rather than bucketed as unknown{why_below}. "
                    "stratified_report_count is "
                    f"therefore a count of recorded {field} values, NOT of "
                    "reports, and must not be used as a denominator; use "
                    "total_reports_matching_query if you need one."
                )
            elif subset > query_total:
                # Not expected for a report-level field: say so rather than
                # asserting an explanation that the numbers contradict.
                parts.append(
                    f"total_reports_matching_query ({query_total:,}) is every "
                    "report matching this query, yet the rows in 'results' sum "
                    f"to {subset:,} ({coverage:.1f}% of it). {field} holds at "
                    "most one value per report, so the rows were expected to sum "
                    "at or below the total; treat both figures as approximate "
                    "and do NOT divide a row by either to obtain a rate."
                )
            else:
                parts.append(
                    f"total_reports_matching_query ({query_total:,}) is every report "
                    f"matching this query; stratified_report_count ({subset:,}, "
                    f"{coverage:.1f}% of them) is the subset where {field} "
                    "is recorded, and only that subset is counted in 'results'. "
                    "openFDA computes a count facet solely over records that populate "
                    "the counted field, so reports missing it are EXCLUDED from the "
                    "rows entirely rather than bucketed as unknown. "
                    f"{field} holds at most one value per report, so the rows do "
                    "not double-count reports -- but neither figure is the "
                    "population at risk, so dividing a row by either does not "
                    "give a rate."
                )

        # Not when narrowed: the truncation is then of the ranking the narrowing
        # was applied to rather than of 'results', so this sentence would be
        # describing a sum that is no longer on screen. `truncation_note` already
        # spells that distinction out for the narrowed case.
        if truncated and not narrowed:
            # 'results' is the top-N of a longer ranking, so the sum describes
            # the rows shown rather than the whole facet.
            parts.append(
                "'results' is truncated (see 'truncation_note'), so "
                "stratified_report_count sums only the rows shown, not the "
                "whole facet -- the true facet sum is larger."
            )
        return " ".join(parts)

    def _add_coverage_disclosure(self, envelope, arguments):
        """Add the true denominator next to the facet, without changing it.

        An openFDA `count=` facet never sums to the number of matching reports,
        and nothing in the rows says so. A report-level field such as
        `seriousnessdeath` is missing from roughly half of FAERS reports, and
        openFDA drops those reports from the facet rather than bucketing them,
        so the rows sum BELOW the report total. A field nested under
        patient.reaction[] or patient.drug[] is recorded once per reaction / per
        drug, so one report lands in several buckets and the rows sum ABOVE it:
        `patient.reaction.reactionoutcome` for vasopressin sums to 5,514 against
        4,741 matching reports, and `patient.drug.drugadministrationroute` to
        9,273. Either way the reader's next step -- case fatality = 1,477 / row
        sum -- is a number that ends up on a clinical slide. Report both figures
        under self-describing names and say which way the facet is off.

        Purely additive: `results`, `result_count`, `limit` and `truncated` are
        untouched, and a failed denominator request leaves a null rather than
        turning a working call into an error.
        """
        # stratified_report_count is documented as what the counts in 'results'
        # sum to, so sum 'results'. This previously summed the RAW facet page on
        # the grounds that facet coverage is a property of the whole facet --
        # but a client-side reaction filter subsets 'results' to the one
        # requested term, and the number then described neither the rows shown
        # nor the whole facet: it was the sum of the top-`limit` ranking page, so
        # it moved with `limit` while 'results' did not. Measured for
        # PROMETHAZINE + somnolence, 'results' was the single row SOMNOLENCE
        # 1,438 at every limit while stratified_report_count read 1,438 / 2,630 /
        # 6,492 at limit 1 / 5 / 50, and the coverage prose asserted "the rows in
        # 'results' sum to 6,492". Worse, the comparison inverted: for MODAFINIL
        # + tachycardia the single row is 200 against 322 matching reports --
        # BELOW the total -- yet the note read "946 -- 293.8% of it, i.e. MORE
        # than the number of matching reports", telling a reader to discount a
        # near-1:1 signal as threefold double-counted.
        #
        # Read the narrowing off `arguments` rather than taking it as a flag:
        # the only thing that can subset 'results' is the same key `_post_process`
        # filters on, so deriving it here keeps the prose and the filtering from
        # drifting apart.
        narrowed = arguments.get("reactionmeddraverse") is not None
        subset = sum(
            row["count"]
            for row in envelope["results"]
            if isinstance(row, dict) and isinstance(row.get("count"), int)
        )
        query_total = self._fetch_query_total(arguments)

        envelope["stratified_report_count"] = subset
        envelope["total_reports_matching_query"] = query_total

        coverage_note = self._coverage_note(
            subset, query_total, bool(envelope.get("truncated")), narrowed=narrowed
        )
        if self.count_field_note:
            coverage_note = f"{self.count_field_note} {coverage_note}"
        envelope["coverage_note"] = coverage_note

        self._add_name_scope_disclosure(envelope, arguments, query_total)

    # ---- drug-name scope disclosure ----

    def _add_name_scope_disclosure(self, envelope, arguments, query_total):
        """Say how many matched reports actually NAMED the drug that was asked for.

        The drug-name search is a union over FAERS_DRUG_NAME_FIELDS, two thirds
        of which are openFDA's ingredient-level annotation rather than the
        reported product text, so a brand-name query returns every product
        sharing that brand's active ingredient. The share is a property of the
        drug, not of the query, so it is measured per call -- see the table on
        FAERS_REPORTED_NAME_FIELD for what it ranges over.

        Costs ONE extra openFDA request, re-asking the same query with only the
        drug name narrowed. Purely additive and fails soft: existing keys are
        untouched and a failed probe leaves a null. It is skipped -- and so
        costs nothing -- when no drug name was passed, when the name searches a
        single field and so cannot widen, when the facet came back empty, and
        when the denominator is unavailable or zero (which also keeps a
        rate-limited call from spending a second retry).

        Rides on `disclose_denominator` because it measures its split against
        that same denominator; every tool in this family sets the flag.
        """
        drug_value = arguments.get(self.DRUG_PARAMETER)
        fda_fields = self._drug_name_fields()
        if not drug_value or len(set(fda_fields)) < 2:
            return
        if not query_total or query_total < 0 or not envelope.get("results"):
            return

        named_total = self._fetch_query_total(
            arguments, drug_fields=[FAERS_REPORTED_NAME_FIELD]
        )
        if named_total is None:
            # Measured and failed, which is not the same as "not applicable":
            # the null says the split is unknown for this call.
            envelope["reports_naming_queried_drug"] = None
            return

        matched_only = query_total - named_total
        if matched_only < 0:
            # The reported-name set is a strict subset of the union, so a
            # negative can only be the two probes landing either side of
            # openFDA's daily refresh. Publish NEITHER figure: a
            # reports_naming_queried_drug larger than
            # total_reports_matching_query is a subset bigger than its
            # superset, which is why this returns before either key is set
            # rather than after.
            return
        envelope["reports_naming_queried_drug"] = named_total
        envelope["reports_matched_by_name_resolution_only"] = matched_only
        if matched_only == 0:
            return

        names = (
            ", ".join(f"'{d}'" for d in drug_value)
            if isinstance(drug_value, list)
            else f"'{drug_value}'"
        )
        envelope["drug_name_scope_note"] = (
            f"{query_total:,} report(s) match this query, but only "
            f"{named_total:,} of them named {names} as the product. The other "
            f"{matched_only:,} ({100.0 * matched_only / query_total:.1f}%) "
            "matched through openFDA's SPL annotation, which tags a report with "
            "EVERY brand and generic name registered for the active ingredient "
            "of a product the report did name. The counts in 'results' "
            "therefore describe that whole active-ingredient population, not "
            f"{names} specifically. This tool searched "
            f"{', '.join(fda_fields)}, and the rows cannot be narrowed to the "
            "reported name: reports_naming_queried_drug is the only figure "
            "here restricted to it."
        )

    def validate_enum_arguments(self, arguments):
        """Validate that enum-based arguments match the allowed values"""
        for param_name, value in arguments.items():
            if param_name in self.parameter_enums and value is not None:
                allowed_values = self.parameter_enums[param_name]
                if value not in allowed_values:
                    return f"Invalid value '{value}' for parameter '{param_name}'. Allowed values are: {', '.join(allowed_values)}"
        return None

    def _post_process(self, response, reaction_filter=None):
        if not response or not isinstance(response, list):
            return []

        mapped_results = []
        for item in response:
            try:
                # Pass through error sentinels from _search untouched so an
                # upstream API failure surfaces instead of being masked as a
                # bogus {"term": None, "count": 0} row.
                if isinstance(item, dict) and "error" in item and "term" not in item:
                    mapped_results.append(item)
                    continue

                term = item.get("term")
                count = item.get("count", 0)

                # If reaction_filter is specified, only include matching reactions
                if reaction_filter is not None:
                    # Case-insensitive comparison
                    if term and term.upper() != reaction_filter.upper():
                        continue

                # Apply mapping if available. Fall back to the raw code as a
                # string (not the original int/etc) so an FDA code absent
                # from our mapping (e.g. an undocumented drugcharacterization
                # value) still satisfies the documented "term is a string"
                # contract instead of leaking a raw int through.
                if self.return_fields_mapping:
                    mapped_term = self.return_fields_mapping.get(
                        self.count_field, {}
                    ).get(str(term), str(term))
                    mapped_results.append({"term": mapped_term, "count": count})
                else:
                    mapped_results.append({"term": term, "count": count})
            except Exception:
                # Keep the original term in case of an exception
                if reaction_filter is None or (
                    isinstance(item, dict)
                    and item.get("term", "").upper() == reaction_filter.upper()
                ):
                    mapped_results.append(item)

        return mapped_results

    def _build_search_query(self, arguments, drug_fields=None):
        """Build the Lucene `search=` expression, returning ``(error, query)``.

        Kept separate from the request so the same query can also be reused for
        the denominator probe in ``_fetch_query_total``.

        ``drug_fields`` narrows the fields the DRUG-NAME parameter searches, and
        nothing else: the scope probe has to re-ask this exact query with only
        the name restricted, or the two report counts would not be comparable.
        It is deliberately not a whole-map override -- an override forgotten by
        a future subclass then degrades to "no narrowing", which reads as a
        measured 0% rather than as a failure to measure.
        """
        search_parts = []
        for param_name, value in arguments.items():
            # Only forward parameters defined in the search-field map; an
            # unrecognized argument (e.g. a stray 'limit') must NOT become a
            # bogus FDA filter like 'limit:2', which matches nothing and yields
            # a silent empty result.
            if param_name == self.DRUG_PARAMETER:
                # Through the accessor, so the documented fallback is real on
                # this path too. Reading self.search_fields directly here meant
                # a config that forgot the map dropped the drug name from the
                # FACET while the scope probe -- which keys off DRUG_PARAMETER,
                # not off the map -- still applied it, producing a note that
                # blamed SPL annotation for the entire corpus.
                fda_fields = self._drug_name_fields(drug_fields)
            else:
                fda_fields = self.search_fields.get(param_name)
            if not fda_fields:
                continue
            # Use the first field name for value mapping
            fda_field = fda_fields[0]

            # Apply value mapping using FDA field name
            # (for proper enum mapping)
            mapping_error, mapped_value = self._map_value(fda_field, value)
            if mapping_error:
                return mapping_error, None
            if mapped_value is None:
                continue  # Skip this field if instructed

            # Build search parts using FDA field name(s). Multiple fields for the
            # same parameter are OR-ed inside a parenthesized group.
            search_parts.append(_render_field_group(fda_fields, mapped_value))

        # Final search query - join different parameters with AND
        return None, "+AND+".join(search_parts)

    def _search(self, arguments, limit=None):
        query_error, search_query = self._build_search_query(arguments)
        if query_error:
            return [{"error": query_error}]
        search_encoded = urllib.parse.quote(search_query, safe='+:"')

        # Build URL. `limit` is appended after `count` so it is never mistaken
        # for part of the Lucene search clause.
        if self.api_key:
            url = f"{self.endpoint_url}?api_key={self.api_key}&search={search_encoded}&count={self.count_field}"
        else:
            url = (
                f"{self.endpoint_url}?search={search_encoded}&count={self.count_field}"
            )
        if limit is not None:
            url = f"{url}&limit={limit}"

        # API request (30s timeout so a hung connection cannot block the caller)
        try:
            response = requests.get(url, timeout=30)
            # Handle 404 as "no matches found" - return empty list instead of error
            if response.status_code == 404:
                try:
                    error_data = response.json()
                    if "error" in error_data and "No matches found" in str(
                        error_data.get("error", {})
                    ):
                        return []  # Return empty list for no matches
                except (ValueError, KeyError):
                    pass
            response.raise_for_status()
            response = response.json()
            if "results" in response:
                response = response["results"]
            return response
        except requests.exceptions.RequestException as e:
            return [{"error": f"API request failed: {str(e)}"}]

    def _map_value(self, param_name, value):
        # Special handling for seriousness fields: if value is "No", skip this field
        seriousness_fields = {
            "seriousnessdeath",
            "seriousnesshospitalization",
            "seriousnessdisabling",
            "seriousnesslifethreatening",
            "seriousnessother",
        }
        if param_name in seriousness_fields:
            if value == "No":
                return None, None  # Signal to skip this field
            # Feature-66B-005: also accept native openFDA integer 1 or string "1" as "Yes"
            if value in ("Yes", 1, "1"):
                return None, "1"
            # If not Yes/No/1, error
            return (
                f"Invalid value '{value}' for '{param_name}'. Allowed values: ['Yes'] (omit to include all).",
                None,
            )

        if param_name in HUMAN_TO_FDA_MAP:
            value_map = HUMAN_TO_FDA_MAP[param_name]
            if value not in value_map:
                print("No mapping found for value:", value, "skipping")
                allowed_values = list(value_map.keys())
                return (
                    f"Invalid value '{value}' for '{param_name}'. Allowed values: {allowed_values}",
                    None,
                )
            return None, value_map[value]
        return None, value


@register_tool("FDACountAdditiveReactionsTool")
class FDACountAdditiveReactionsTool(FDADrugAdverseEventTool):
    """Count an openFDA facet across SEVERAL drugs in one request.

    Only the search clause differs from the parent -- ``medicinalproducts`` is a
    LIST whose names are OR-ed (a union, not a co-occurrence) -- so only
    ``_build_search_query`` is overridden and everything downstream stays the
    parent's, including the denominator probe that reuses this same query.
    """

    DRUG_PARAMETER = "medicinalproducts"

    def _build_search_query(self, arguments, drug_fields=None):
        # Read the FDA field(s) through the shared accessor, which carries the
        # fallback: a config that forgets the map still asks the same question
        # as every other FAERS tool (see FAERS_DRUG_NAME_FIELDS).
        fda_fields = self._drug_name_fields(drug_fields)

        # Each name goes through the shared renderer for the same reason every
        # other value does: a multi-word name needs Lucene quotes, several FDA
        # fields for one parameter must be OR-ed inside parens, and the
        # percent-encoding happens ONCE, later, on the finished query.
        #
        # Percent-encoding the name here as well used to double-encode it. The
        # space in "SODIUM CHLORIDE" became %2520; openFDA decoded that once to
        # the literal term "SODIUM%20CHLORIDE", whose analyzer split it and left
        # the field bound to the first token alone. The query silently widened
        # to every product whose name merely contains "SODIUM" -- and because it
        # returned MORE data rather than none, nothing looked broken. Verified
        # live against the API: medicinalproduct:"SODIUM CHLORIDE" counts
        # 74,079 serious + 16,715 non-serious = 90,794, while the double-encoded
        # form returns 605,620 + 173,560 = 779,180, exactly equal to the count
        # for the bare term "SODIUM" -- an 8.6x over-count.
        or_clause = "+OR+".join(
            _render_field_group(fda_fields, drug)
            for drug in arguments.get(self.DRUG_PARAMETER, ())
        )

        # Every other filter is the parent's job, so the quoting and grouping
        # rules keep exactly one home. The drug list is withheld rather than
        # popped: run() hands the SAME dict to the facet and to the denominator
        # probe, and mutating it would leave the probe counting reports for the
        # filters alone.
        filter_error, filter_query = super()._build_search_query(
            {k: v for k, v in arguments.items() if k != self.DRUG_PARAMETER}
        )
        if filter_error:
            return filter_error, None

        query = f"({or_clause})"
        if filter_query:
            query = f"{query}+AND+{filter_query}"
        return None, query

    def run(self, arguments):
        drugs = arguments.get(self.DRUG_PARAMETER)
        if not drugs:
            return {
                "status": "error",
                "error": f"`{self.DRUG_PARAMETER}` list is required.",
            }
        if not isinstance(drugs, list):
            return {
                "status": "error",
                "error": f"`{self.DRUG_PARAMETER}` must be a list of drug names.",
            }
        return super().run(arguments)


@register_tool("FDADrugAdverseEventDetailTool")
class FDADrugAdverseEventDetailTool(BaseTool):
    """
    Tool for retrieving detailed adverse event reports from FAERS.
    Uses limit/skip parameters instead of count aggregation.
    """

    def __init__(
        self,
        tool_config,
        endpoint_url="https://api.fda.gov/drug/event.json",
        api_key=None,
    ):
        super().__init__(tool_config)
        self.tool_config = tool_config
        self.endpoint_url = endpoint_url
        self.api_key = api_key or os.getenv("FDA_API_KEY")
        self.search_fields = tool_config.get("fields", {}).get("search_fields", {})
        self.return_fields = tool_config.get("fields", {}).get("return_fields", [])

        # Store allowed enum values
        self.parameter_enums = {}
        if "parameter" in tool_config and "properties" in tool_config["parameter"]:
            for param_name, param_def in tool_config["parameter"]["properties"].items():
                if "enum" in param_def:
                    self.parameter_enums[param_name] = param_def["enum"]

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)

        # Validate enum parameters
        validation_error = self.validate_enum_arguments(arguments)
        if validation_error:
            return {"status": "error", "error": validation_error}

        response = self._search(arguments)
        return response

    def validate_enum_arguments(self, arguments):
        """Validate that enum-based arguments match the allowed values"""
        for param_name, value in arguments.items():
            if param_name in self.parameter_enums and value is not None:
                allowed_values = self.parameter_enums[param_name]
                if value not in allowed_values:
                    return f"Invalid value '{value}' for parameter '{param_name}'. Allowed values are: {', '.join(allowed_values)}"
        return None

    def _build_search_query(self, arguments):
        """Render the Lucene query for one detail search.

        Returns ``(error_message, query)``; subclasses asking a different
        question override only this. ``arguments`` arrives with ``limit`` and
        ``skip`` already removed, matching the contract
        ``FDACountAdditiveReactionsTool`` already has with its own parent.
        """
        search_parts = []
        for param_name, value in arguments.items():
            # Only forward parameters defined in the search-field map; an
            # unrecognized argument (e.g. a stray 'limit') must NOT become a
            # bogus FDA filter like 'limit:2', which matches nothing and yields
            # a silent empty result.
            fda_fields = self.search_fields.get(param_name)
            if not fda_fields:
                continue
            # Use the first field name for value mapping
            fda_field = fda_fields[0]

            # Apply value mapping using FDA field name
            # (for proper enum mapping)
            mapping_error, mapped_value = self._map_value(fda_field, value)
            if mapping_error:
                return mapping_error, ""
            if mapped_value is None:
                continue  # Skip this field if instructed

            # Build search parts using FDA field name(s). Multiple fields for the
            # same parameter are OR-ed inside a parenthesized group.
            search_parts.append(_render_field_group(fda_fields, mapped_value))

        # Final search query - join different parameters with AND
        return None, "+AND+".join(search_parts)

    def _search(self, arguments):
        # Extract limit and skip from arguments
        limit = arguments.pop("limit", 10)
        skip = arguments.pop("skip", 0)

        # Validate limit
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            return {
                "status": "error",
                "error": "limit must be an integer between 1 and 100",
            }
        if not isinstance(skip, int) or skip < 0:
            return {"status": "error", "error": "skip must be a non-negative integer"}

        error, search_query = self._build_search_query(arguments)
        if error:
            return {"status": "error", "error": error}
        search_encoded = urllib.parse.quote(search_query, safe='+:"')

        # Build URL with limit and skip (not count)
        if self.api_key:
            url = (
                f"{self.endpoint_url}?api_key={self.api_key}"
                f"&search={search_encoded}&limit={limit}&skip={skip}"
            )
        else:
            url = (
                f"{self.endpoint_url}?search={search_encoded}&limit={limit}&skip={skip}"
            )

        # API request
        try:
            response = requests.get(url)
            # 404 is openFDA's "no matches found", not a server error. It is a
            # real, complete answer -- zero reports matched -- so it reports a
            # total of 0 rather than the "not reported" None.
            if response.status_code == 404:
                try:
                    error_data = response.json()
                    if "error" in error_data and "No matches found" in str(
                        error_data.get("error", {})
                    ):
                        return faers_detail_envelope([], 0, limit, skip)
                except (ValueError, KeyError):
                    pass
            response.raise_for_status()
            response_data = response.json()
            results = response_data.get("results", [])
            total = faers_meta_total(response_data)

            # If return_fields is specified, filter the results
            if self.return_fields:
                filtered_results = []
                for result in results:
                    filtered_result = {}
                    for field in self.return_fields:
                        # Handle nested fields (e.g., "patient.reaction.reactionmeddrapt")
                        field_parts = field.split(".")
                        value = result
                        for part in field_parts:
                            if isinstance(value, dict):
                                value = value.get(part)
                            elif isinstance(value, list) and part.isdigit():
                                value = (
                                    value[int(part)] if int(part) < len(value) else None
                                )
                            else:
                                value = None
                                break
                        if value is not None:
                            filtered_result[field] = value
                    if filtered_result:
                        filtered_results.append(filtered_result)
                return faers_detail_envelope(filtered_results, total, limit, skip)

            # Extract essential fields if configured
            extract_essential = self.tool_config.get("fields", {}).get(
                "extract_essential", False
            )
            if extract_essential:
                results = [self._extract_essential_fields(r) for r in results]

            return faers_detail_envelope(results, total, limit, skip)
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"API request failed: {str(e)}"}

    def _extract_essential_fields(self, report):
        """
        Extract only essential fields from a FAERS report.
        Removes verbose metadata like openfda to keep output concise.
        Can be customized via tool_config['fields']['essential_fields'].
        """
        # Get custom essential fields from config, or use default
        essential_fields_config = self.tool_config.get("fields", {}).get(
            "essential_fields", None
        )

        if essential_fields_config:
            # Use custom field extraction logic from config
            return self._extract_custom_fields(report, essential_fields_config)

        # Default essential fields extraction
        essential = {
            # Report identification
            "safetyreportid": report.get("safetyreportid"),
            "safetyreportversion": report.get("safetyreportversion"),
            # Seriousness indicators
            "serious": report.get("serious"),
            "seriousnessdeath": report.get("seriousnessdeath"),
            "seriousnesshospitalization": report.get("seriousnesshospitalization"),
            "seriousnesslifethreatening": report.get("seriousnesslifethreatening"),
            "seriousnessdisabling": report.get("seriousnessdisabling"),
            # Location
            "occurcountry": report.get("occurcountry"),
            "primarysourcecountry": report.get("primarysourcecountry"),
            # Dates
            "transmissiondate": report.get("transmissiondate"),
            "receivedate": report.get("receivedate"),
        }

        # Patient information (essential fields only)
        patient = report.get("patient", {})
        if patient:
            essential_patient = {
                "patientsex": patient.get("patientsex"),
                "patientagegroup": patient.get("patientagegroup"),
                "patientonsetage": patient.get("patientonsetage"),
                "patientonsetageunit": patient.get("patientonsetageunit"),
                "patientweight": patient.get("patientweight"),
            }

            # Drugs (essential fields only, no openfda metadata)
            drugs = patient.get("drug", [])
            if drugs:
                essential_drugs = []
                for drug in drugs:
                    essential_drug = {
                        "medicinalproduct": drug.get("medicinalproduct"),
                        "drugindication": drug.get("drugindication"),
                        "drugadministrationroute": drug.get("drugadministrationroute"),
                        "drugdosagetext": drug.get("drugdosagetext"),
                        "drugdosageform": drug.get("drugdosageform"),
                        "drugstartdate": drug.get("drugstartdate"),
                        "actiondrug": drug.get("actiondrug"),
                    }
                    # Only include non-empty fields
                    essential_drug = {
                        k: v for k, v in essential_drug.items() if v is not None
                    }
                    if essential_drug:
                        essential_drugs.append(essential_drug)
                if essential_drugs:
                    essential_patient["drug"] = essential_drugs

            # Reactions (all fields are essential)
            reactions = patient.get("reaction", [])
            if reactions:
                essential_reactions = []
                for reaction in reactions:
                    essential_reaction = {
                        "reactionmeddrapt": reaction.get("reactionmeddrapt"),
                        "reactionmeddraversionpt": reaction.get(
                            "reactionmeddraversionpt"
                        ),
                        "reactionoutcome": reaction.get("reactionoutcome"),
                    }
                    # Only include non-empty fields
                    essential_reaction = {
                        k: v for k, v in essential_reaction.items() if v is not None
                    }
                    if essential_reaction:
                        essential_reactions.append(essential_reaction)
                if essential_reactions:
                    essential_patient["reaction"] = essential_reactions

            # Summary if available
            if "summary" in patient:
                essential_patient["summary"] = patient["summary"]

            essential["patient"] = essential_patient

        # Remove None values
        essential = {k: v for k, v in essential.items() if v is not None}
        return essential

    def _extract_custom_fields(self, report, field_config):
        """
        Extract fields based on custom configuration.
        field_config can be a list of field paths or a dict with inclusion rules.
        """
        if isinstance(field_config, list):
            # Simple list of field paths to include
            result = {}
            for field_path in field_config:
                value = self._get_nested_value(report, field_path)
                if value is not None:
                    self._set_nested_value(result, field_path, value)
            return result
        else:
            # Use default extraction
            return self._extract_essential_fields(report)

    def _get_nested_value(self, obj, path):
        """Get value from nested dict using dot notation path"""
        parts = path.split(".")
        value = obj
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdigit():
                value = value[int(part)] if int(part) < len(value) else None
            else:
                return None
            if value is None:
                return None
        return value

    def _set_nested_value(self, obj, path, value):
        """Set value in nested dict using dot notation path"""
        parts = path.split(".")
        current = obj
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def _map_value(self, param_name, value):
        # Special handling for seriousness fields: if value is "No", skip this field
        seriousness_fields = {
            "seriousnessdeath",
            "seriousnesshospitalization",
            "seriousnessdisabling",
            "seriousnesslifethreatening",
            "seriousnessother",
        }
        if param_name in seriousness_fields:
            if value == "No":
                return None, None  # Signal to skip this field
            # Feature-66B-005: also accept native openFDA integer 1 or string "1" as "Yes"
            if value in ("Yes", 1, "1"):
                return None, "1"
            # If not Yes/No/1, error
            return (
                f"Invalid value '{value}' for '{param_name}'. Allowed values: ['Yes'] (omit to include all).",
                None,
            )

        if param_name in HUMAN_TO_FDA_MAP:
            value_map = HUMAN_TO_FDA_MAP[param_name]
            if value not in value_map:
                print("No mapping found for value:", value, "skipping")
                allowed_values = list(value_map.keys())
                return (
                    f"Invalid value '{value}' for '{param_name}'. Allowed values: {allowed_values}",
                    None,
                )
            return None, value_map[value]
        return None, value


@register_tool("FDADrugInteractionDetailTool")
class FDADrugInteractionDetailTool(FDADrugAdverseEventDetailTool):
    """Detailed FAERS reports where several drugs co-occur on the SAME report.

    Identical to its parent apart from the question it asks, so it overrides
    only ``_build_search_query``. It used to be a sibling ``BaseTool`` holding
    a byte-identical copy of ``__init__``, ``run``, ``validate_enum_arguments``,
    ``_search``'s request/response handling and all five field-extraction
    helpers -- 318 duplicated lines, which meant every fix to a FAERS detail
    tool had to be made twice and could silently be made only once.
    ``FDACountAdditiveReactionsTool`` already relates to its own parent this
    way.
    """

    def _build_search_query(self, arguments):
        """AND the per-drug clauses: was every named drug on the same report?"""
        drugs = arguments.pop("medicinalproducts", [])
        if not drugs:
            return "medicinalproducts list is required", ""
        if not isinstance(drugs, list) or len(drugs) < 2:
            return "medicinalproducts must be a list of at least 2 drug names", ""

        # Build AND clause for multiple drugs (all must be present). Routed
        # through the shared clause renderer so a multi-word name gets Lucene
        # quotes and is percent-encoded exactly once, on the finished query
        # in _search -- encoding it here too widened each clause to the name's
        # first token (see the matching note in
        # FDACountAdditiveReactionsTool._build_search_query).
        #
        # Each drug searches the full FAERS_DRUG_NAME_FIELDS union, read from the
        # config's own search-field map like every other parameter so the
        # declared spec and the query cannot disagree.
        #
        # The per-drug group MUST stay parenthesized: these clauses are AND-ed (a
        # co-occurrence question -- was every named drug on the SAME report), and
        # Lucene binds AND tighter than OR, so an unwrapped group would parse as
        # "a:X OR (b:X AND a:Y) OR b:Y" and answer "either drug" instead.
        # _render_field_group does the wrapping; the query reads
        # (a:X+OR+b:X+OR+c:X)+AND+(a:Y+OR+b:Y+OR+c:Y), with a multi-word name
        # additionally Lucene-quoted.
        drug_fields = self.search_fields.get("medicinalproducts") or (
            FAERS_DRUG_NAME_FIELDS
        )
        drug_parts = [_render_field_group(drug_fields, drug) for drug in drugs]

        # The remaining filters are AND-ed on exactly as the parent does them.
        error, filter_query = super()._build_search_query(arguments)
        if error:
            return error, ""
        parts = drug_parts + ([filter_query] if filter_query else [])
        return None, "+AND+".join(parts)
