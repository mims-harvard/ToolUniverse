"""FAERS_rollup_meddra_hierarchy must not publish a page size as a total.

Fix-R38. Before this fix the tool sent
``count=patient.reaction.reactionmeddrapt.exact`` with no ``limit``, sliced
openFDA's 100-row default page down to 50, and published ``len(that slice)``
under the key ``total_unique_PTs`` -- so the answer was the constant 50 for
every drug (measured live 2026-08-11: HYDROMORPHONE and ONDANSETRON both
reported 50) with no truncation flag and no note. The same query at the
anonymous ceiling returns 999 distinct PT buckets whose 999th still carries
``count: 69``, i.e. the ranking is not exhausted and the true number of distinct
PTs is strictly greater than 999. The published figure understated it by more
than 20x, invisibly, because a stable plausible number reads as a measurement.

openFDA's ``count=`` response carries no grand total -- its ``meta`` block holds
only disclaimer/terms/license/last_updated -- so these tests assert that the
tool reports what it *returned*, flags truncation, and says a missing term is
not evidence of absence, rather than inventing a total it cannot know.

Every test here is hermetic: see the ``no_network`` fixture.
"""

import socket

import pytest
import requests

from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool
from tooluniverse.openfda_adv_tool import COUNT_MAX_LIMIT, COUNT_MAX_LIMIT_ANONYMOUS


def _config(operation):
    """Minimal tool_config -- only the `operation` const is load-bearing."""
    return {
        "name": f"FAERS_{operation}",
        "type": "FAERSAnalyticsTool",
        "parameter": {
            "type": "object",
            "required": [],
            "properties": {
                "operation": {"const": operation},
                "drug_name": {"type": "string"},
            },
        },
    }


class _FakeResponse:
    """Just the surface ``request_with_retry`` and this tool actually touch."""

    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.headers = {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


def _pt_rows(n):
    """`n` descending PT buckets, the last one still comfortably above zero.

    Mirrors what openFDA actually returns: the tail of a truncated ranking is
    NOT near-empty -- the 999th real HYDROMORPHONE bucket still carries 69
    reports -- which is exactly why a full page cannot be read as "that is all
    of them".
    """
    return [{"term": f"PREFERRED TERM {i:04d}", "count": 100000 - i} for i in range(n)]


@pytest.fixture
def no_network(monkeypatch):
    """Make any real network call an immediate, loud test failure.

    Patching one entry point is not enough to call a test hermetic: this module
    reaches openFDA through ``request_with_retry`` -> ``requests.request`` and,
    in other code paths, through ``requests.get``. Both are blocked here, along
    with ``requests.Session.request`` underneath them, and the socket layer
    underneath that -- so anything that slips past every ``requests`` entry
    point still cannot open a connection.
    """

    def _boom(*args, **kwargs):
        raise AssertionError(
            "a real network call escaped the stub -- this test is not hermetic"
        )

    for name in ("request", "get", "post", "head", "put", "delete"):
        monkeypatch.setattr(requests, name, _boom)
    monkeypatch.setattr(requests.Session, "request", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)
    monkeypatch.setattr(socket.socket, "connect", _boom)
    monkeypatch.setattr(socket, "getaddrinfo", _boom)


@pytest.fixture
def stub_openfda(monkeypatch, no_network):
    """Install a canned openFDA reply and record the URLs the tool asked for.

    Replaces ``requests.request`` only -- the real ``request_with_retry`` still
    runs on top of it, so the tool's retry/status handling is exercised rather
    than bypassed.
    """
    calls = []

    def install(*payloads):
        responses = [
            p if isinstance(p, _FakeResponse) else _FakeResponse(p) for p in payloads
        ]

        def fake_request(method, url, **kwargs):
            calls.append(url)
            return responses[min(len(calls) - 1, len(responses) - 1)]

        monkeypatch.setattr(requests, "request", fake_request)
        return calls

    return install


def _make_tool(monkeypatch, config, api_key=None):
    """Build the tool AFTER setting FDA_API_KEY -- it is read in __init__."""
    if api_key is None:
        monkeypatch.delenv("FDA_API_KEY", raising=False)
    else:
        monkeypatch.setenv("FDA_API_KEY", api_key)
    return FAERSAnalyticsTool(config)


def _rollup(monkeypatch, stub_openfda, rows, api_key=None):
    calls = stub_openfda({"results": rows})
    tool = _make_tool(monkeypatch, _config("rollup_meddra_hierarchy"), api_key=api_key)
    result = tool.run(
        {"operation": "rollup_meddra_hierarchy", "drug_name": "HYDROMORPHONE"}
    )
    assert result["status"] == "success", result
    return result["data"]["meddra_hierarchy"], calls


def test_full_page_reports_returned_count_and_sets_truncated(monkeypatch, stub_openfda):
    """999 rows back means 999 returned and truncated -- never a "total"."""
    hierarchy, _ = _rollup(monkeypatch, stub_openfda, _pt_rows(999))

    assert hierarchy["unique_PTs_returned"] == 999
    assert len(hierarchy["PT_level"]) == 999
    assert hierarchy["truncated"] is True
    assert hierarchy["limit"] == COUNT_MAX_LIMIT_ANONYMOUS


def test_no_output_key_claims_a_total_number_of_pts(monkeypatch, stub_openfda):
    """The old `total_unique_PTs` key is gone, not aliased to a new number.

    There is no honest value to serve under that name: openFDA reports no grand
    total for a `count=` query, and 999 is a page size, not a total either. A
    KeyError at the call site is the correct outcome -- a loud break beats a
    quiet wrong number, which is precisely the failure mode being fixed.
    """
    hierarchy, _ = _rollup(monkeypatch, stub_openfda, _pt_rows(999))

    assert "total_unique_PTs" not in hierarchy
    assert not any(key.startswith("total_") for key in hierarchy)
    # The old defect's signature: the constant 50, regardless of the drug.
    assert hierarchy["unique_PTs_returned"] != 50


def test_truncation_note_names_the_absence_of_evidence_caveat(
    monkeypatch, stub_openfda
):
    hierarchy, _ = _rollup(monkeypatch, stub_openfda, _pt_rows(999))
    note = hierarchy["truncation_note"]

    # A term's absence from a truncated ranking says nothing about FAERS.
    assert "NOT evidence that it was never reported" in note
    # openFDA genuinely cannot tell us how many distinct terms exist.
    assert "does not report how many distinct terms" in note
    # The rows are the most-reported ones, ranked descending -- not a sample.
    assert "most-reported" in note
    assert "descending report count" in note
    # The note quotes the count actually published, never a page size the
    # reader did not receive; `limit` is published as its own key instead.
    assert f"only the {hierarchy['unique_PTs_returned']} most-reported" in note


def test_short_facet_is_not_flagged_truncated(monkeypatch, stub_openfda):
    """A page openFDA did not fill is exhausted, so no truncation is claimed."""
    hierarchy, _ = _rollup(monkeypatch, stub_openfda, _pt_rows(43))

    assert hierarchy["unique_PTs_returned"] == 43
    assert hierarchy["truncated"] is False
    assert "truncation_note" not in hierarchy


@pytest.mark.parametrize(
    ("api_key", "expected_limit"),
    [
        # Measured live 2026-08-11: limit=1000 answers HTTP 403
        # {"code": "API_KEY_MISSING"} for an anonymous caller while limit=999
        # succeeds, so the anonymous ceiling is one below the documented max.
        (None, COUNT_MAX_LIMIT_ANONYMOUS),
        ("test-key", COUNT_MAX_LIMIT),
    ],
)
def test_page_size_honours_the_anonymous_cap(
    monkeypatch, stub_openfda, api_key, expected_limit
):
    hierarchy, calls = _rollup(monkeypatch, stub_openfda, _pt_rows(10), api_key=api_key)

    assert hierarchy["limit"] == expected_limit
    assert f"limit={expected_limit}" in calls[0]
    if api_key:
        assert "api_key=test-key" in calls[0]
    else:
        assert "api_key=" not in calls[0]


def test_anonymous_and_keyed_ceilings_differ_by_exactly_one():
    """Guards the constants themselves against a silent edit."""
    assert COUNT_MAX_LIMIT == 1000
    assert COUNT_MAX_LIMIT_ANONYMOUS == 999


def test_serious_events_discloses_its_own_truncated_ranking(monkeypatch, stub_openfda):
    """`top_serious_reactions` is a top-N slice, and now says so.

    `total_serious_events` here is honest -- it is `meta.results.total` from a
    plain search, a figure openFDA does report -- so only the reaction ranking
    needed a disclosure.
    """
    # 21 rows back: 20 to publish plus the probe row that proves more exist.
    calls = stub_openfda(
        {"results": _pt_rows(21)},
        {"meta": {"results": {"total": 12345}}},
    )
    tool = _make_tool(monkeypatch, _config("filter_serious_events"))
    result = tool.run(
        {"operation": "filter_serious_events", "drug_name": "HYDROMORPHONE"}
    )

    assert result["status"] == "success", result
    data = result["data"]
    assert data["total_serious_events"] == 12345
    assert len(data["top_serious_reactions"]) == 20
    assert data["top_serious_reactions_truncated"] is True
    note = data["top_serious_reactions_truncation_note"]
    assert "NOT evidence that it was never reported" in note
    assert "does not report how many distinct terms" in note
    # The probe row settles truncation as a fact, so the note says "exist",
    # not "may exist".
    assert "more terms exist beyond it" in note
    # Only one row past what is shown is fetched -- not openFDA's 100-row
    # default page, 80 rows of which would be parsed and thrown away.
    assert "limit=21" in calls[0]
    # The note must not quote a page size the reader never received.
    assert "limit=21" not in note
    assert len(calls) == 2


def test_serious_events_short_ranking_is_not_flagged_truncated(
    monkeypatch, stub_openfda
):
    """No probe row came back, so the published list is the whole ranking."""
    stub_openfda(
        {"results": _pt_rows(7)},
        {"meta": {"results": {"total": 99}}},
    )
    tool = _make_tool(monkeypatch, _config("filter_serious_events"))
    result = tool.run(
        {"operation": "filter_serious_events", "drug_name": "HYDROMORPHONE"}
    )

    data = result["data"]
    assert len(data["top_serious_reactions"]) == 7
    assert data["top_serious_reactions_truncated"] is False
    assert "top_serious_reactions_truncation_note" not in data


def test_country_stratification_uses_the_aggregatable_field(monkeypatch, stub_openfda):
    """`occurcountry` cannot be aggregated; only `occurcountry.exact` can.

    Measured live 2026-08-11: `count=occurcountry` answers HTTP 500
    "[illegal_argument_exception] Text fields are not optimised for operations
    that require per-document field data", so stratify_by="country" failed for
    every drug. `count=occurcountry.exact` returns 43 buckets for HYDROMORPHONE.
    """
    calls = stub_openfda(
        {"results": [{"term": "US", "count": 900}, {"term": "CA", "count": 100}]},
        {"meta": {"results": {"total": 2000}}},
    )
    tool = _make_tool(monkeypatch, _config("stratify_by_demographics"))
    result = tool.run(
        {
            "operation": "stratify_by_demographics",
            "drug_name": "HYDROMORPHONE",
            "stratify_by": "country",
        }
    )

    assert result["status"] == "success", result
    assert "count=occurcountry.exact" in calls[0]
    # `.exact` is an index-variant detail, not the field's name in the FAERS
    # record layout, so it must not leak into the prose a reader acts on.
    assert "occurcountry.exact" not in result["data"]["coverage_note"]
    assert "occurcountry" in result["data"]["coverage_note"]


def test_network_guard_actually_fires(no_network):
    """The hermeticity guard is itself verified, not merely installed."""
    for call in (
        lambda: requests.get("https://api.fda.gov/drug/event.json"),
        lambda: requests.request("GET", "https://api.fda.gov/drug/event.json"),
        lambda: requests.Session().request(
            "GET", "https://api.fda.gov/drug/event.json"
        ),
        lambda: socket.create_connection(("api.fda.gov", 443)),
        lambda: socket.getaddrinfo("api.fda.gov", 443),
    ):
        with pytest.raises(AssertionError, match="not hermetic"):
            call()
