"""Regression guard for Fix-R20A-1: UniProtIDMappingTool silently truncated
large mapping result sets.

Confirmed live for P00533 (EGFR) -> PDB: the UniProt ID Mapping status
endpoint sometimes 303-redirects straight into a results page instead of
ever reporting jobStatus=="FINISHED" -- and that redirected page uses its
own default page size (25 records), not the size=500 this tool asks for
when explicitly fetching results. The old code treated "results" showing up
in a status-poll response as the final answer and returned it directly,
silently truncating true 354-record result sets down to 25 with no
truncation indicator at all. Fixed by treating a status-poll response that
contains "results" as merely "job done" (like jobStatus=="FINISHED"), then
always re-fetching through _fetch_all_results(), which pages through with
size=500 and follows the Link header's rel="next" URL for results beyond a
single page.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.uniprot_idmapping_tool import UniProtIDMappingTool

pytestmark = pytest.mark.unit


def _tool(endpoint_type):
    return UniProtIDMappingTool(
        {"name": "uniprot_idmap_test", "fields": {"endpoint_type": endpoint_type}}
    )


def _resp(json_body, headers=None):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = json_body
    r.headers = headers or {}
    return r


def test_convert_ids_fetches_full_result_set_not_just_redirect_preview():
    """The status poll's first response embeds a "results" key with only
    25 records (mimicking the real, confirmed-live UniProt redirect
    behavior) -- the tool must not treat that as final and must instead
    fetch the full 354-record set from the results endpoint."""
    tool = _tool("convert")

    full_results = [{"from": "P00533", "to": f"PDB{i}"} for i in range(354)]

    def fake_post(url, data=None, **kwargs):
        return _resp({"jobId": "job123"})

    def fake_get(url, params=None, **kwargs):
        if url.endswith("/status/job123"):
            # Redirect-style response: only the first 25, no jobStatus key.
            return _resp({"results": full_results[:25]})
        if url.endswith("/results/job123"):
            return _resp({"results": full_results, "failedIds": []})
        raise AssertionError(f"unexpected URL {url}")

    with patch("tooluniverse.uniprot_idmapping_tool.requests.post", side_effect=fake_post):
        with patch("tooluniverse.uniprot_idmapping_tool.requests.get", side_effect=fake_get):
            result = tool.run(
                {"ids": "P00533", "from_db": "UniProtKB_AC-ID", "to_db": "PDB"}
            )

    assert result["status"] == "success"
    assert result["data"]["result_count"] == 354
    assert len(result["data"]["results"]) == 354
    assert result["data"]["truncated"] is False


def test_convert_ids_follows_link_header_pagination():
    """A results set spanning more than one page (Link: rel="next") is
    fully accumulated, not just the first page."""
    tool = _tool("convert")
    page1 = [{"from": "P00533", "to": f"PDB{i}"} for i in range(500)]
    page2 = [{"from": "P00533", "to": f"PDB{i}"} for i in range(500, 600)]

    def fake_post(url, data=None, **kwargs):
        return _resp({"jobId": "job456"})

    def fake_get(url, params=None, **kwargs):
        if url.endswith("/status/job456"):
            return _resp({"jobStatus": "FINISHED"})
        if url == "https://rest.uniprot.org/idmapping/results/job456":
            return _resp(
                {"results": page1, "failedIds": []},
                headers={
                    "Link": '<https://rest.uniprot.org/idmapping/results/job456?cursor=abc&size=500>; rel="next"'
                },
            )
        if "cursor=abc" in url:
            return _resp({"results": page2, "failedIds": []}, headers={})
        raise AssertionError(f"unexpected URL {url}")

    with patch("tooluniverse.uniprot_idmapping_tool.requests.post", side_effect=fake_post):
        with patch("tooluniverse.uniprot_idmapping_tool.requests.get", side_effect=fake_get):
            result = tool.run(
                {"ids": "P00533", "from_db": "UniProtKB_AC-ID", "to_db": "PDB"}
            )

    assert result["status"] == "success"
    assert result["data"]["result_count"] == 600
    # Display array is still capped at 500 for context-size reasons, but the
    # truncation is now honestly flagged instead of silent.
    assert len(result["data"]["results"]) == 500
    assert result["data"]["truncated"] is True


def test_small_result_set_unaffected_no_regression():
    """A genuinely small result set (fewer than the redirect's own default
    page size) still round-trips correctly."""
    tool = _tool("gene_to_uniprot")
    small_results = [{"from": "TP53", "to": "P04637"}]

    def fake_post(url, data=None, **kwargs):
        return _resp({"jobId": "job789"})

    def fake_get(url, params=None, **kwargs):
        if url.endswith("/status/job789"):
            return _resp({"jobStatus": "FINISHED"})
        if url.endswith("/results/job789"):
            return _resp({"results": small_results, "failedIds": []})
        raise AssertionError(f"unexpected URL {url}")

    with patch("tooluniverse.uniprot_idmapping_tool.requests.post", side_effect=fake_post):
        with patch("tooluniverse.uniprot_idmapping_tool.requests.get", side_effect=fake_get):
            result = tool.run({"gene_names": "TP53"})

    assert result["status"] == "success"
    assert result["data"]["result_count"] == 1
    assert result["data"]["truncated"] is False
    assert result["data"]["results"][0]["to"] == "P04637"


def test_job_error_status_still_returns_error():
    tool = _tool("convert")

    def fake_post(url, data=None, **kwargs):
        return _resp({"jobId": "jobErr"})

    def fake_get(url, params=None, **kwargs):
        return _resp({"jobStatus": "ERROR", "errorMessage": "bad request"})

    with patch("tooluniverse.uniprot_idmapping_tool.requests.post", side_effect=fake_post):
        with patch("tooluniverse.uniprot_idmapping_tool.requests.get", side_effect=fake_get):
            result = tool.run(
                {"ids": "BOGUS", "from_db": "UniProtKB_AC-ID", "to_db": "PDB"}
            )

    assert result["status"] == "error"
    assert "bad request" in result["error"]
