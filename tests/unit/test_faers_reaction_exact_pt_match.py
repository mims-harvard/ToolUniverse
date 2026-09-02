"""FAERS analytics must count the Preferred Term it claims, not every PT containing it (Fix-R44).

Every reaction filter in `faers_analytics_tool` searched
`patient.reaction.reactionmeddrapt`, openFDA's ANALYSED variant of the field.
Its tokenizer splits on whitespace and hyphens, so a search for one Preferred
Term also matched every compound PT containing it as a token, and those reports
were counted into the 2x2 contingency table as though they were reports of the
requested PT.

Measured live at openFDA 2026-08-12 (`limit=1`, `meta.results.total`) for
reaction "Thrombocytopenia":

    drug         analysed field   .exact field   inflation
    heparin               6,805          2,778        2.45x
    bivalirudin             111             27        4.11x

The inflation is DIFFERENTIAL, which is what makes this a wrong answer rather
than a conservative one -- `_compare_drugs` divides the two arms' RORs, so a
factor that differs per drug moves the verdict itself. Live, the tool said
"heparin and bivalirudin show similar-strength detected signals"; on exact PT
counts heparin's ROR is 7.393 against bivalirudin's 4.563, i.e. "heparin's is
stronger". And the contaminating term is HEPARIN-INDUCED THROMBOCYTOPENIA
(3,968 reports), which is bivalirudin's INDICATION rather than its adverse
effect -- so an indication was inflating a comparator's adverse-event count.

These tests pin the query construction rather than live counts, so they stay
meaningful as FAERS grows.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

EXACT = 'patient.reaction.reactionmeddrapt.exact:"Thrombocytopenia"'
ANALYSED = 'patient.reaction.reactionmeddrapt:"Thrombocytopenia"'

CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "faers_analytics_tools.json"
)


def _tool():
    from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool

    return FAERSAnalyticsTool({"name": "t", "type": "FAERSAnalyticsTool"})


class _Response:
    """Minimal stand-in for the one `requests.Response` attribute set used."""

    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError(f"unexpected raise_for_status on {self.status_code}")


def _recording_transport(payload=None):
    """Patch the module's HTTP seam and record every URL it builds.

    Patches `request_with_retry` where the module looks it up. Patching
    `requests.request` would not be enough on its own to make this hermetic --
    the openFDA classes in this codebase use both `requests.request` and
    `requests.get` -- and `disable_network` is not autouse, so a test's
    hermeticity rests on its own patches.
    """
    urls = []
    body = payload if payload is not None else {"meta": {"results": {"total": 7}}}

    def fake(session, method, url, **kwargs):
        urls.append(url)
        return _Response(body)

    return urls, patch(
        "tooluniverse.faers_analytics_tool.request_with_retry", side_effect=fake
    )


def test_search_helper_filters_on_the_exact_field():
    """The shared query builder must use the un-analysed field variant."""
    from tooluniverse.faers_analytics_tool import _faers_search_query

    query = _faers_search_query("heparin", "Thrombocytopenia")

    assert EXACT in query
    # Substring-checking `.exact`'s absence is not enough: the analysed clause
    # is a prefix of the exact one, so assert the analysed form appears ONLY as
    # part of the exact form.
    assert query.count("patient.reaction.reactionmeddrapt") == 1


@pytest.mark.parametrize(
    "operation,arguments",
    [
        (
            "_filter_serious_events",
            {"drug_name": "heparin", "adverse_event": "Thrombocytopenia"},
        ),
        (
            "_analyze_temporal_trends",
            {"drug_name": "heparin", "adverse_event": "Thrombocytopenia"},
        ),
        (
            "_stratify_by_demographics",
            {
                "drug_name": "heparin",
                "adverse_event": "Thrombocytopenia",
                "stratify_by": "sex",
            },
        ),
    ],
)
def test_every_operation_filters_on_the_exact_field(operation, arguments):
    """No operation may search a different variant of the field than its siblings.

    Two of these built the reaction clause inline instead of calling the shared
    helper, which is exactly how the module came to have one filter field in
    theory and another in three places in practice.
    """
    tool = _tool()
    urls, transport = _recording_transport({"results": [], "meta": {"results": {}}})
    with transport:
        getattr(tool, operation)(arguments)

    assert urls, f"{operation} issued no request"
    reaction_urls = [u for u in urls if "reactionmeddrapt" in u]
    assert reaction_urls, f"{operation} never filtered on the reaction field"
    for url in reaction_urls:
        assert EXACT in url, f"{operation} used the analysed field: {url}"


def test_disproportionality_numerator_comes_from_the_exact_query():
    """The 2x2 `a` cell must be fetched with the exact-PT query, not the token one.

    Deliberately stubs the HTTP transport rather than `_get_faers_count`.
    Mocking the count helper would make this pass whatever field the code
    searched -- the assertion would be true by construction, and the whole point
    is which query produced the number.

    The fixture answers each distinct openFDA query with the count that query
    really returned live on 2026-08-12, so the contingency table is checked
    against measured reality rather than invented figures.
    """
    tool = _tool()
    live = {
        # (drug clause present, reaction clause present) -> live total
        (True, True): 2778,  # heparin AND Thrombocytopenia, exact PT
        (True, False): 74634,  # heparin, any reaction
        (False, True): 110034,  # Thrombocytopenia, any drug
        (False, False): 20687000,  # whole database
    }
    seen = []

    def fake(session, method, url, **kwargs):
        seen.append(url)
        has_drug = "medicinalproduct" in url
        has_reaction = "reactionmeddrapt" in url
        return _Response(
            {"meta": {"results": {"total": live[(has_drug, has_reaction)]}}}
        )

    with patch(
        "tooluniverse.faers_analytics_tool.request_with_retry", side_effect=fake
    ):
        result = tool._calculate_disproportionality(
            {"drug_name": "heparin", "adverse_event": "Thrombocytopenia"}
        )

    numerator_urls = [u for u in seen if "reactionmeddrapt" in u]
    assert numerator_urls, "no reaction-filtered query was issued"
    for url in numerator_urls:
        assert EXACT in url, f"numerator fetched with the analysed field: {url}"

    assert result["status"] == "success"
    assert result["contingency_table"] == {
        "a_drug_and_event": 2778,
        "b_drug_no_event": 74634 - 2778,
        "c_no_drug_event": 110034 - 2778,
        "d_no_drug_no_event": 20687000 - 74634 - 110034 + 2778,
    }


def test_non_preferred_term_is_named_as_such_and_suggests_real_terms():
    """A term that matches nothing must not surface as an arithmetic complaint.

    "bleeding" is not a MedDRA PT. The analysed field answered it with 34,436
    reports -- the union of GINGIVAL BLEEDING, HEAVY MENSTRUAL BLEEDING and
    every other PT containing the word -- and fed that union into the table as
    one event. The exact field matches nothing, which is correct but useless on
    its own, so the miss must be reported as a naming problem with real PTs to
    retry with.
    """
    tool = _tool()

    def fake_count(drug_name=None, adverse_event=None):
        if adverse_event:
            return 0  # no PT matches "bleeding" exactly
        return 20687000 if drug_name is None else 240000

    facet = {
        "results": [
            {"term": "GINGIVAL BLEEDING", "count": 13497},
            {"term": "NAUSEA", "count": 9001},  # co-reported, must be filtered out
            {"term": "HEAVY MENSTRUAL BLEEDING", "count": 7846},
        ]
    }
    _urls, transport = _recording_transport(facet)
    with patch.object(tool, "_get_faers_count", side_effect=fake_count), transport:
        result = tool._calculate_disproportionality(
            {"drug_name": "warfarin", "adverse_event": "bleeding"}
        )

    assert result["status"] == "error"
    assert "not a MedDRA Preferred Term" in result["error"]
    assert "Insufficient data" not in result["error"]
    assert result["suggested_preferred_terms"] == [
        "GINGIVAL BLEEDING",
        "HEAVY MENSTRUAL BLEEDING",
    ]
    # A PT co-reported on the same reports is not a suggestion for this term.
    assert "NAUSEA" not in result["error"]


def test_compare_surfaces_the_arms_reason_at_the_top_level():
    """`error` must carry the reason, not just say an arm failed.

    The CLI prints only the top-level `error`, so burying "not a Preferred Term"
    and its suggestions in `drug1_result` meant the tool's description promised
    naming that the caller never saw.
    """
    tool = _tool()
    arm_error = {
        "status": "error",
        "error": '"bleeding" is not a MedDRA Preferred Term in FAERS...',
        "suggested_preferred_terms": ["GINGIVAL BLEEDING"],
    }
    with patch.object(tool, "_calculate_disproportionality", return_value=arm_error):
        result = tool._compare_drugs(
            {"drug1": "heparin", "drug2": "bivalirudin", "adverse_event": "bleeding"}
        )

    assert result["status"] == "error"
    assert "not a MedDRA Preferred Term" in result["error"]
    assert result["suggested_preferred_terms"] == ["GINGIVAL BLEEDING"]
    # The second arm shares the reaction, so it cannot succeed where the first
    # failed; saying it was skipped explains the missing drug2_result.
    assert "bivalirudin was not queried" in result["error"]
    assert result["drug2_result"] is None


def test_transport_errors_never_echo_the_request_url():
    """An openFDA HTTP error must not carry the URL -- it holds the API key.

    Every URL this module builds goes through `_with_api_key`, which appends
    `&api_key=<FDA_API_KEY>`, and `requests` renders an HTTP error as
    "<status> ... for url: <full URL>". Reproduced live with FDA_API_KEY set:

        API request failed: 403 Client Error: Forbidden for url:
        https://api.fda.gov/drug/event.json?search=(...)&api_key=SECRETKEY123

    Pre-existing rather than introduced this round, but this round made the
    error path routine by switching to `.exact`, so it is closed here.
    """
    import requests as requests_module

    from tooluniverse.faers_analytics_tool import _api_request_failed_error

    exc = requests_module.exceptions.HTTPError(
        "403 Client Error: Forbidden for url: "
        "https://api.fda.gov/drug/event.json?search=x&api_key=SECRETKEY123"
    )
    result = _api_request_failed_error(exc)

    assert result["status"] == "error"
    assert "SECRETKEY123" not in result["error"]
    assert "api_key" not in result["error"]
    assert "api.fda.gov" not in result["error"]
    # The actionable part survives.
    assert "403 Client Error: Forbidden" in result["error"]


@pytest.mark.parametrize(
    "operation,arguments",
    [
        ("_stratify_by_demographics", {"drug_name": "warfarin", "stratify_by": "sex"}),
        ("_filter_serious_events", {"drug_name": "warfarin"}),
        ("_analyze_temporal_trends", {"drug_name": "warfarin"}),
        ("_rollup_meddra_hierarchy", {"drug_name": "warfarin"}),
    ],
)
def test_every_transport_handler_is_sanitized(operation, arguments):
    """All four RequestException handlers, not just the one that was tested."""
    import requests as requests_module

    tool = _tool()
    boom = requests_module.exceptions.HTTPError(
        "429 Client Error: Too Many Requests for url: "
        "https://api.fda.gov/drug/event.json?search=x&api_key=SECRETKEY123"
    )
    with patch(
        "tooluniverse.faers_analytics_tool.request_with_retry", side_effect=boom
    ):
        result = getattr(tool, operation)(arguments)

    assert result["status"] == "error"
    assert "SECRETKEY123" not in result["error"], result["error"]
    assert "api.fda.gov" not in result["error"], result["error"]


@pytest.mark.parametrize(
    "operation,arguments",
    [
        (
            "_filter_serious_events",
            {"drug_name": "warfarin", "adverse_event": "bleeding"},
        ),
        (
            "_analyze_temporal_trends",
            {"drug_name": "warfarin", "adverse_event": "bleeding"},
        ),
        (
            "_stratify_by_demographics",
            {
                "drug_name": "warfarin",
                "adverse_event": "bleeding",
                "stratify_by": "sex",
            },
        ),
    ],
)
def test_sibling_operations_survive_a_non_preferred_term(operation, arguments):
    """Switching to `.exact` must not turn a loose match into a raw 404.

    Regression introduced by this same fix and caught before shipping. These
    three operations previously searched the ANALYSED field, where a colloquial
    term still matched something, so their `raise_for_status()` was survivable.
    Under `.exact` openFDA answers a miss with 404 rather than an empty 200, and
    they returned, live::

        Error: API request failed: 404 Client Error: Not Found for url:
        https://api.fda.gov/drug/event.json?search=(...)+AND+
        patient.reaction.reactionmeddrapt.exact:%22bleeding%22&count=receivedate

    which is unhelpful and is also a path by which a configured FDA_API_KEY ends
    up inside a returned string, since `_with_api_key` appends it to that URL.
    """
    tool = _tool()

    def fake(session, method, url, **kwargs):
        # The reaction-filtered query misses; the "is this a PT at all?" probe
        # answers zero; the suggestion facet returns real terms.
        if "count=" in url and "reactionmeddrapt" in url and "search=" in url:
            if "medicinalproduct" not in url:
                return _Response(
                    {"results": [{"term": "GINGIVAL BLEEDING", "count": 13497}]}
                )
        if "reactionmeddrapt" in url and "count=" not in url:
            return _Response({"meta": {"results": {"total": 0}}})
        return _Response({}, status_code=404)

    with patch(
        "tooluniverse.faers_analytics_tool.request_with_retry", side_effect=fake
    ):
        result = getattr(tool, operation)(arguments)

    assert result["status"] == "error"
    assert "not a MedDRA Preferred Term" in result["error"]
    assert "404" not in result["error"]
    assert "api.fda.gov" not in result["error"]


def test_third_drug_is_refused_rather_than_dropped():
    """A three-drug list must not return a confident two-drug verdict.

    Live, `{"drugs": ["heparin", "argatroban", "bivalirudin"]}` returned status
    "success", a verdict naming only the first two, and comparison_caveat null,
    with "bivalirudin" appearing nowhere in the response.
    """
    tool = _tool()
    urls, transport = _recording_transport()
    with transport:
        result = tool.run(
            {
                "operation": "compare_drugs",
                "drugs": ["heparin", "argatroban", "bivalirudin"],
                "adverse_event": "Thrombocytopenia",
            }
        )

    assert result["status"] == "error"
    assert "exactly two" in result["error"]
    assert "bivalirudin" in result["error"]
    # Refused before spending any openFDA calls.
    assert urls == []


def test_two_drug_list_still_works():
    """The rejection must not catch the supported two-drug form."""
    tool = _tool()
    with patch.object(
        tool, "_compare_drugs", return_value={"status": "success"}
    ) as compare:
        tool.run(
            {
                "operation": "compare_drugs",
                "drugs": ["heparin", "bivalirudin"],
                "adverse_event": "Thrombocytopenia",
            }
        )

    arguments = compare.call_args[0][0]
    assert arguments["drug1"] == "heparin"
    assert arguments["drug2"] == "bivalirudin"


def test_schema_pins_the_pair_and_stops_promising_capitalization():
    """The config must state the contract the code now enforces.

    The old guidance ("use exact MedDRA Preferred Term capitalization") pointed
    at the wrong thing in both directions: `.exact` is case-INSENSITIVE at
    openFDA (verified live -- "Thrombocytopenia", "THROMBOCYTOPENIA",
    "thrombocytopenia" and "ThRoMbOcYtOpEnIa" all return the identical 110,034),
    while whole-term-ness, which is what actually decides the answer, went
    unmentioned.
    """
    configs = json.loads(CONFIG_PATH.read_text())
    compare = next(c for c in configs if c["name"] == "FAERS_compare_drugs")

    drugs = compare["parameter"]["properties"]["drugs"]
    assert drugs["minItems"] == 2
    assert drugs["maxItems"] == 2

    for config in configs:
        event = config["parameter"]["properties"].get("adverse_event")
        if not event:
            continue
        assert "WHOLE MedDRA Preferred Term" in event["description"], config["name"]
        assert "capitalization" not in event["description"], config["name"]
