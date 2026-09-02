"""Regression guard: EuropePMC_search_articles must surface upstream hitCount.

Europe PMC returns the true number of matching records as `hitCount` in every
search response (verified live: `.../search?query=NSCLC%20radiogenomics%20EGFR
%20CT%20radiomics%20TCIA&format=json&pageSize=1` -> `"hitCount": 103`). The
tool parsed that payload and discarded the figure, reporting only
`metadata.count` -- the number of records returned -- which is
indistinguishable from the number that matched.

`metadata.total_results` now always carries the upstream total, `count` keeps
its old meaning, and a truncated answer is flagged at the top level.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.europe_pmc_tool import EuropePMCTool

pytestmark = pytest.mark.unit


def _record(idx):
    return {
        "id": f"MED{idx}",
        "source": "MED",
        "title": f"Article {idx}",
        "abstractText": "abstract",
        "pubYear": "2026",
    }


def _payload(hit_count, n_records):
    return {
        "hitCount": hit_count,
        "resultList": {"result": [_record(i) for i in range(n_records)]},
    }


def _response(payload, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    return response


def _run(hit_count, n_records, arguments):
    tool = EuropePMCTool({"name": "EuropePMC_search_articles"})
    response = _response(_payload(hit_count, n_records))
    with patch(
        "tooluniverse.europe_pmc_tool.request_with_retry", return_value=response
    ):
        return tool.run(arguments)


def test_hit_count_is_reported_and_truncation_disclosed():
    result = _run(103, 6, {"query": "NSCLC radiogenomics EGFR", "limit": 6})

    assert result["status"] == "success"
    assert len(result["data"]) == 6
    assert result["metadata"]["count"] == 6, "count stays the number returned"
    assert result["metadata"]["total_results"] == 103
    assert result["truncated"] is True
    assert "103" in result["truncation_note"]
    assert "limit" in result["truncation_note"]


def test_complete_result_set_is_not_flagged_truncated():
    result = _run(2, 2, {"query": "a very specific query", "limit": 10})

    assert result["metadata"]["count"] == 2
    assert result["metadata"]["total_results"] == 2
    assert result["truncated"] is False
    assert "truncation_note" not in result


def test_zero_hits_reports_zero_total():
    result = _run(0, 0, {"query": "nonexistent gibberish", "limit": 5})

    assert result["data"] == []
    assert result["metadata"]["count"] == 0
    assert result["metadata"]["total_results"] == 0
    assert result["truncated"] is False


def test_missing_hit_count_reports_unknown_rather_than_returned_count():
    """A total the upstream did not give must not be faked from `count`."""
    tool = EuropePMCTool({"name": "EuropePMC_search_articles"})
    payload = {"resultList": {"result": [_record(0)]}}
    with patch(
        "tooluniverse.europe_pmc_tool.request_with_retry",
        return_value=_response(payload),
    ):
        result = tool.run({"query": "q", "limit": 5})

    assert result["metadata"]["count"] == 1
    assert result["metadata"]["total_results"] is None
    assert "truncated" not in result


def test_upstream_error_still_returns_the_documented_error_shape():
    tool = EuropePMCTool({"name": "EuropePMC_search_articles"})
    response = MagicMock()
    response.status_code = 503
    response.reason = "Service Unavailable"
    with patch(
        "tooluniverse.europe_pmc_tool.request_with_retry", return_value=response
    ):
        result = tool.run({"query": "q", "limit": 5})

    assert result["status"] == "success"
    assert result["data"][0]["error"].startswith("Europe PMC API error 503")
    assert result["data"][0]["retryable"] is True
    assert result["metadata"]["total_results"] is None
