"""EuropePMC_search_articles reported an upstream glitch as "0 results, success".

Observed live: a query that normally has 66,695 hits came back as ``count: 0`` with
``total_results: None`` and no error. Europe PMC had answered HTTP 200 with a body that
was not a search response (no ``hitCount``, no ``resultList``), which the tool read as an
empty result list. A genuine empty search carries ``hitCount: 0``. A body with neither is
now retried once and, if it is still not a search response, reported in the tool's
documented error shape (an Error row, ``retryable: true``).
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.europe_pmc_tool import EuropePMCTool

pytestmark = pytest.mark.unit

GOOD = {
    "hitCount": 66695,
    "resultList": {
        "result": [
            {"id": "MED1", "source": "MED", "title": "Article", "pubYear": "2026"}
        ]
    },
}


def _response(payload, status=200):
    response = MagicMock(status_code=status)
    response.json.return_value = payload
    return response


def _run(bodies):
    """Serve ``bodies`` to successive core requests; lite requests get the good body."""
    core_bodies = list(bodies)
    calls = {"core": 0}

    def fake(session, method, url, params=None, **kwargs):
        if params["resultType"] == "lite":
            return _response(GOOD)
        calls["core"] += 1
        return _response(core_bodies.pop(0))

    tool = EuropePMCTool({"name": "EuropePMC_search_articles"})
    with (
        patch("tooluniverse.europe_pmc_tool.request_with_retry", side_effect=fake),
        patch("time.sleep"),
    ):
        result = tool.run(
            {"query": "bacterial antibiotic resistance evolution", "limit": 5}
        )
    return result, calls["core"]


def test_a_body_that_is_not_a_search_response_twice_is_a_retryable_error():
    result, core_calls = _run([{"version": "6.9"}, {"version": "6.9"}])
    assert core_calls == 2  # one retry
    (row,) = result["data"]
    assert row["title"] == "Error" and row["retryable"] is True
    assert "unexpected response" in row["error"]
    assert result["metadata"]["total_results"] is None


def test_a_transient_bad_body_recovers_on_the_retry():
    result, core_calls = _run([{"version": "6.9"}, GOOD])
    assert core_calls == 2
    assert result["metadata"]["total_results"] == 66695
    assert result["data"][0]["title"] == "Article"


def test_a_real_empty_result_is_still_an_empty_success_without_a_retry():
    empty = {"hitCount": 0, "resultList": {"result": []}}
    result, core_calls = _run([empty])
    assert core_calls == 1
    assert result["status"] == "success" and result["data"] == []
    assert result["metadata"]["total_results"] == 0


def test_a_normal_response_makes_a_single_core_request():
    result, core_calls = _run([GOOD])
    assert core_calls == 1
    assert result["metadata"]["total_results"] == 66695
