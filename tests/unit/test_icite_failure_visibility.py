"""Regression guard for Fix-R75A-1: iCite_search_publications's PubMed
eSearch and iCite batch-fetch helpers both returned an empty list on ANY
non-200 response (rate limit, outage, etc.), identical to what a genuine
zero-hit PubMed query also produces (confirmed live: PubMed eSearch returns
HTTP 200 with an empty idlist for zero hits, never a non-200). run()'s "No
PubMed results found for query: {query}" success message could not
distinguish "the search genuinely found nothing" from "the request to
PubMed/iCite failed" -- and a mid-batch iCite failure vanished silently
(extend() of an empty list) with no error and no indication some PMIDs'
citation data was simply dropped.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.icite_tool import ICiteSearchPublicationsTool

pytestmark = pytest.mark.unit


def _tool():
    return ICiteSearchPublicationsTool({"name": "iCite_search_publications"})


def _resp(status_code, json_body=None):
    r = MagicMock()
    r.status_code = status_code
    r.raise_for_status = MagicMock()
    if status_code >= 400:
        r.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"{status_code} error"
        )
    if json_body is not None:
        r.json.return_value = json_body
    return r


def test_genuine_zero_hit_query_reports_success_not_error():
    tool = _tool()
    with patch(
        "tooluniverse.icite_tool.request_with_retry",
        return_value=_resp(200, {"esearchresult": {"idlist": []}}),
    ):
        result = tool.run({"query": "zzznonexistentqueryxyz"})

    assert result["status"] == "success"
    assert result["data"] == []
    assert "No PubMed results found" in result["message"]


def test_pubmed_search_failure_is_surfaced_as_error_not_empty_success():
    """The core confirmed-live bug: a failed PubMed request (rate limit,
    outage) must not be silently indistinguishable from zero real hits."""
    tool = _tool()
    with patch(
        "tooluniverse.icite_tool.request_with_retry",
        return_value=_resp(503, None),
    ):
        result = tool.run({"query": "CRISPR gene editing"})

    assert result["status"] == "error"
    assert "message" not in result or "No PubMed results found" not in result.get(
        "message", ""
    )


def test_icite_batch_failure_is_surfaced_not_silently_dropped():
    """A failure fetching citation metrics for a batch of PMIDs (search
    succeeded, enrichment failed) must not silently vanish -- previously
    extend()'d an empty list with zero indication anything went wrong."""
    tool = _tool()

    def fake_request(session, method, url, **kwargs):
        if "esearch" in url:
            return _resp(200, {"esearchresult": {"idlist": ["12345", "67890"]}})
        return _resp(500, None)

    with patch(
        "tooluniverse.icite_tool.request_with_retry", side_effect=fake_request
    ):
        result = tool.run({"query": "CRISPR gene editing"})

    assert result["status"] == "error"


def test_successful_search_and_fetch_returns_data():
    tool = _tool()

    def fake_request(session, method, url, **kwargs):
        if "esearch" in url:
            return _resp(200, {"esearchresult": {"idlist": ["12345"]}})
        return _resp(
            200,
            {"data": [{"pmid": 12345, "citation_count": 42}]},
        )

    with patch(
        "tooluniverse.icite_tool.request_with_retry", side_effect=fake_request
    ):
        result = tool.run({"query": "CRISPR gene editing"})

    assert result.get("status") != "error"
    assert result["data"][0]["pmid"] == 12345
