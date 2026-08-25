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


def _analytics():
    from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool

    return FAERSAnalyticsTool({"name": "t", "type": "FAERSAnalyticsTool"})


class TestTheAnalyticsToolUsesTheMemo:
    def test_a_repeat_probe_makes_no_request(self):
        """This is what actually pays for the cohort disclosure's extra probes.

        A second disproportionality analysis of the same drug re-asks the
        drug's own total, its reported-name total and the whole-database
        total. Those are the same three questions, so they must cost nothing
        the second time.
        """
        tool, calls = _analytics(), []

        def spy(*args, **kwargs):
            calls.append(kwargs.get("url") or args[2])
            return _Response(4119)

        with patch(
            "tooluniverse.faers_analytics_tool.request_with_retry", side_effect=spy
        ):
            assert tool._get_faers_count("CYANOKIT") == 4119
            assert len(calls) == 1
            assert tool._get_faers_count("CYANOKIT") == 4119
        assert len(calls) == 1

    def test_a_body_with_no_total_is_a_failure_not_a_zero(self):
        """And must not be memoised, or the fabricated zero becomes sticky."""
        tool, calls = _analytics(), []

        def spy(*args, **kwargs):
            calls.append(1)
            return _Response(total=None)

        with patch(
            "tooluniverse.faers_analytics_tool.request_with_retry", side_effect=spy
        ):
            assert tool._get_faers_count("CYANOKIT") is None
            assert tool._get_faers_count("CYANOKIT") is None
        assert len(calls) == 2

    def test_it_shares_every_drug_name_with_the_count_tools(self):
        """Both modules must spell the same question the same way.

        This test used to pin the OPPOSITE, asserting that a single-word name
        produced different keys in the two modules, and justified it thus:
        "normalising the quoting would be wrong, because quoted and unquoted
        are different openFDA queries for a hyphenated name."

        Fix-54B-1: quoted and unquoted really are different queries for a
        hyphenated name -- and the unquoted one is simply WRONG, because the
        hyphen is a Lucene operator, so the name is reparsed and the query
        silently becomes a union of different drugs. Measured against
        api.fda.gov: patient.drug.medicinalproduct:CO-TRIMOXAZOLE returns
        24,806 unquoted and 1,416 quoted. `_render_clause` now quotes too, so
        the two paths agree and the keys coincide for every name, not just
        multi-word ones. Quoting is not merely cosmetic here, so the keys
        would legitimately diverge again if either path stopped quoting --
        which is what these assertions now guard.
        """
        from tooluniverse.faers_analytics_tool import FDA_BASE_URL, _faers_search_query
        from tooluniverse.openfda_adv_tool import (
            FAERS_REPORTED_NAME_FIELD,
            faers_report_total_key,
        )

        count_tool = _tool()

        def count_key(drug):
            _, q = count_tool._build_search_query(
                {"medicinalproduct": drug}, drug_fields=[FAERS_REPORTED_NAME_FIELD]
            )
            return faers_report_total_key(count_tool.endpoint_url, q)

        def analytics_key(drug):
            return faers_report_total_key(
                FDA_BASE_URL, _faers_search_query(drug, reported_name_only=True)
            )

        assert count_key("CYANOKIT") == analytics_key("CYANOKIT")
        assert count_key("SODIUM CHLORIDE") == analytics_key("SODIUM CHLORIDE")
        # The case that motivated the change: a hyphenated name must be spelled
        # the one correct (quoted) way by both paths.
        assert count_key("CO-TRIMOXAZOLE") == analytics_key("CO-TRIMOXAZOLE")
