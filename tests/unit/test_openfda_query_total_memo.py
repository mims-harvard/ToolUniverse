"""The FAERS denominator/scope probes must not be re-sent once per tool.

Every FAERS count tool asks openFDA the same two `limit=0` questions before it
can describe its own facet -- how many reports match the search, and how many of
them named the queried drug. Neither depends on which field the tool counts, so
a workup that asks several questions about one drug re-sent them verbatim once
per tool.

Measured live 2026-08-13 on a four-tool CYANOKIT workup
(FAERS_count_reactions_by_drug_event, FAERS_count_patient_age_distribution,
FAERS_count_seriousness_by_drug_event, FAERS_count_outcomes_by_drug_event):

    before: 12 HTTP requests, 6 distinct URLs -- 6 redundant
    after:   6 HTTP requests, 6 distinct URLs -- 0 redundant

On the anonymous tier that doubles how many workups fit under the daily cap.

Offline: the HTTP transport is patched, so no openFDA request is made.
"""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clear_memo():
    """Isolate each test -- the memo is module-level and outlives instances."""
    from tooluniverse import openfda_adv_tool

    openfda_adv_tool._query_total_memo.clear()
    yield
    openfda_adv_tool._query_total_memo.clear()


class _Response:
    def __init__(self, total=None, status_code=200):
        self.status_code = status_code
        self._total = total

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return {"meta": {"results": {"total": self._total}}}


def _tool():
    from tooluniverse.openfda_adv_tool import FDADrugAdverseEventTool

    return FDADrugAdverseEventTool(
        {
            "name": "t",
            "type": "FDADrugAdverseEventTool",
            "count_field": "patient.reaction.reactionmeddrapt.exact",
            "fields": {
                "search_fields": {"medicinalproduct": "patient.drug.medicinalproduct"},
            },
        }
    )


def _probe(tool, calls, response):
    """Call _fetch_query_total once, recording whether HTTP was reached."""

    def spy(*args, **kwargs):
        calls.append(kwargs.get("url") or args[2])
        if isinstance(response, Exception):
            raise response
        return response

    with patch("tooluniverse.openfda_adv_tool.request_with_retry", side_effect=spy):
        return tool._fetch_query_total({"medicinalproduct": "CYANOKIT"})


class TestIdenticalProbesAreAskedOnce:
    def test_second_identical_probe_makes_no_request(self):
        tool, calls = _tool(), []
        assert _probe(tool, calls, _Response(4119)) == 4119
        assert len(calls) == 1
        assert _probe(tool, calls, _Response(4119)) == 4119
        assert len(calls) == 1, "the repeat probe re-sent the same URL"

    def test_a_separate_tool_instance_reuses_the_same_answer(self):
        """The redundancy is across tools, so an instance-local cache is no use."""
        calls = []
        assert _probe(_tool(), calls, _Response(4119)) == 4119
        assert _probe(_tool(), calls, _Response(4119)) == 4119
        assert len(calls) == 1

    def test_a_different_search_is_not_served_from_the_memo(self):
        tool, calls = _tool(), []
        _probe(tool, calls, _Response(4119))

        def spy(*args, **kwargs):
            calls.append(kwargs.get("url") or args[2])
            return _Response(66161)

        with patch("tooluniverse.openfda_adv_tool.request_with_retry", side_effect=spy):
            other = tool._fetch_query_total({"medicinalproduct": "OZEMPIC"})
        assert other == 66161
        assert len(calls) == 2

    def test_a_genuine_zero_is_cached_like_any_other_count(self):
        """openFDA answers an empty search with 404, which means zero, not failure."""
        tool, calls = _tool(), []
        assert _probe(tool, calls, _Response(status_code=404)) == 0
        assert _probe(tool, calls, _Response(status_code=404)) == 0
        assert len(calls) == 1


class TestFailuresAreNotCached:
    def test_a_failed_probe_is_retried_rather_than_remembered(self):
        """Caching None would make one rate-limited moment stick for the TTL."""
        import requests

        tool, calls = _tool(), []
        assert _probe(tool, calls, requests.exceptions.Timeout("429")) is None
        assert len(calls) == 1
        assert _probe(tool, calls, _Response(4119)) == 4119
        assert len(calls) == 2

    def test_a_malformed_total_is_not_cached(self):
        tool, calls = _tool(), []
        assert _probe(tool, calls, _Response(total="not-a-number")) is None
        assert _probe(tool, calls, _Response(4119)) == 4119
        assert len(calls) == 2


class TestBoundedness:
    def test_an_expired_entry_is_re_measured(self):
        """FAERS is refreshed periodically; a memo must not outlive a snapshot."""
        from tooluniverse import openfda_adv_tool

        tool, calls = _tool(), []
        _probe(tool, calls, _Response(4119))
        key, (stored_at, total) = next(iter(openfda_adv_tool._query_total_memo.items()))
        openfda_adv_tool._query_total_memo.set(
            key, (stored_at - openfda_adv_tool._QUERY_TOTAL_TTL_SECONDS - 1, total)
        )
        assert _probe(tool, calls, _Response(4200)) == 4200
        assert len(calls) == 2

    def test_the_memo_cannot_grow_without_limit(self):
        """A long-lived process querying many drugs must not leak memory."""
        from tooluniverse import openfda_adv_tool

        tool = _tool()
        cap = openfda_adv_tool._query_total_memo.max_size
        with patch(
            "tooluniverse.openfda_adv_tool.request_with_retry",
            side_effect=lambda *a, **k: _Response(1),
        ):
            for i in range(cap + 25):
                tool._fetch_query_total({"medicinalproduct": f"DRUG{i}"})
        assert len(openfda_adv_tool._query_total_memo) == cap


class TestSharedWithTheAnalyticsTool:
    def test_the_analytics_probe_reuses_a_count_tools_answer(self):
        """The two modules ask openFDA the same question in different words.

        `openfda_adv_tool` spells it `limit=0` with the api_key first;
        `faers_analytics_tool` spelled it `limit=1` with the api_key last. Keyed
        on the built URL those never collide, so the memo could not repay the
        extra probes the cohort disclosure adds. Keyed on the search, they do.
        """
        from tooluniverse.faers_analytics_tool import (
            FDA_BASE_URL,
            FAERSAnalyticsTool,
            _faers_search_query,
        )
        from tooluniverse.openfda_adv_tool import (
            _memoize_report_total,
            faers_report_total_key,
        )

        search = _faers_search_query("CYANOKIT", reported_name_only=True)
        _memoize_report_total(faers_report_total_key(FDA_BASE_URL, search), 238)

        analytics = FAERSAnalyticsTool({"name": "t", "type": "FAERSAnalyticsTool"})
        with patch(
            "tooluniverse.faers_analytics_tool.request_with_retry",
            side_effect=AssertionError("the analytics probe bypassed the memo"),
        ):
            assert (
                analytics._get_faers_count("CYANOKIT", reported_name_only=True) == 238
            )
