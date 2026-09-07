"""Regression guard for Fix-R19B-1: ClinGenTool's actionability methods'
`?flavor=flat` response is a JSON table -- {"columns": [...], "rows":
[[...], ...]} -- not a list of per-curation dicts. `_get_actionability`'s
`isinstance(curations, list)` guard was always False against this dict, so
a gene filter was silently skipped entirely (returning all 254 unfiltered
rows for BRCA1). The identical check in `_search_actionability` had the
opposite symptom: `matches` was never assigned, so it always returned
{"Adult": [], "Pediatric": []} even for BRCA1, which has real curated
actionability data. The table-to-dicts conversion itself
(`_actionability_rows_to_dicts`, a ClinGenTool static method) is covered
directly in test_clingen_actionability_columnar_parsing.py -- these tests
exercise the end-to-end gene-filtering behavior through `tool.run()`.

_get_variant_classifications's own speed/endpoint fix (Fix-R29) is covered
in test_clingen_variant_classifications_speed.py.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.clingen_tool import ClinGenTool

pytestmark = pytest.mark.unit


def _tool(operation):
    return ClinGenTool({"name": "clingen_test", "fields": {"operation": operation}})


def _resp(json_body):
    r = MagicMock()
    r.json.return_value = json_body
    r.raise_for_status = MagicMock()
    return r


TABLE_RESPONSE = {
    "columns": ["docId", "geneOrVariant", "disease"],
    "rows": [
        ["AC001", "CYP27A1", "Cerebrotendinous xanthomatosis"],
        ["AC002", "BRCA1,BRCA2", "Hereditary Breast and Ovarian Cancer"],
        ["AC003", "MLH1,MSH2,MSH6,PMS2", "Lynch Syndrome"],
    ],
}


def test_get_actionability_adult_filters_by_gene(monkeypatch):
    tool = _tool("get_actionability_adult")

    with patch("tooluniverse.clingen_tool.requests.get", return_value=_resp(TABLE_RESPONSE)):
        result = tool.run({"gene": "BRCA1"})

    assert result["status"] == "success"
    assert result["total"] == 1
    assert result["data"][0]["geneOrVariant"] == "BRCA1,BRCA2"


def test_get_actionability_adult_no_filter_returns_all(monkeypatch):
    tool = _tool("get_actionability_adult")

    with patch("tooluniverse.clingen_tool.requests.get", return_value=_resp(TABLE_RESPONSE)):
        result = tool.run({})

    assert result["total"] == 3


def test_search_actionability_returns_matches_for_both_contexts(monkeypatch):
    tool = _tool("search_actionability")

    with patch("tooluniverse.clingen_tool.requests.get", return_value=_resp(TABLE_RESPONSE)):
        result = tool.run({"gene": "BRCA1"})

    assert result["status"] == "success"
    data = result["data"]
    assert len(data["Adult"]) == 1
    assert len(data["Pediatric"]) == 1
    assert data["Adult"][0]["geneOrVariant"] == "BRCA1,BRCA2"


def test_search_actionability_fetches_both_contexts_concurrently_not_sequentially():
    """Fix-R53A-1: the Adult and Pediatric actionability endpoints are each
    independently slow (confirmed live: ~124s for a single context, against
    the actionability.clinicalgenome.org server) but were fetched one after
    the other despite being fully independent requests, so a caller paid
    the sum of both. Assert both requests actually go out through the
    thread pool (not a sequential for-loop) by confirming both URLs get
    hit exactly once regardless of call order."""
    tool = _tool("search_actionability")
    requested_urls = []

    def fake_get(url, headers=None, timeout=None):
        requested_urls.append(url)
        return _resp(TABLE_RESPONSE)

    with patch("tooluniverse.clingen_tool.requests.get", side_effect=fake_get):
        result = tool.run({"gene": "BRCA1"})

    assert result["status"] == "success"
    assert len(requested_urls) == 2
    assert any("Adult" in u for u in requested_urls)
    assert any("Pediatric" in u for u in requested_urls)


def test_search_actionability_one_context_failing_does_not_drop_the_other():
    """A timeout/502 on one context (confirmed live behavior for this
    endpoint) must not prevent the other, successfully-fetched context's
    real data from being returned."""
    tool = _tool("search_actionability")

    def fake_get(url, headers=None, timeout=None):
        if "Pediatric" in url:
            raise TimeoutError("simulated timeout")
        return _resp(TABLE_RESPONSE)

    with patch("tooluniverse.clingen_tool.requests.get", side_effect=fake_get):
        result = tool.run({"gene": "BRCA1"})

    assert result["status"] == "success"
    assert len(result["data"]["Adult"]) == 1
    assert result["data"]["Pediatric"] == []
    # Fix-R43-1: the surviving context's data is necessary but not sufficient.
    # The empty Pediatric list must also be marked as unmeasured -- see
    # test_failed_context_is_not_reported_as_a_genuine_zero below.
    assert "Pediatric" in result["failed_contexts"]


@pytest.mark.parametrize("failing", ["Adult", "Pediatric"])
def test_failed_context_is_not_reported_as_a_genuine_zero(failing):
    """Fix-R43-1: a context whose fetch fails must not be reported as a
    curation count of zero.

    The failure branch used to swallow the exception, leaving that context's
    list empty, and the tool answered status "success" with
    pediatric_count 0 -- indistinguishable from "ClinGen has curated no
    pediatric actionability for this gene", a clinically different statement.
    Confirmed live against the real endpoints before the fix: BRCA1 has 6
    adult and 1 pediatric curation, but with only the Pediatric fetch failing
    the tool still answered {"status": "success", "adult_count": 6,
    "pediatric_count": 0} with nothing marking the pediatric figure as
    unmeasured.
    """
    tool = _tool("search_actionability")

    def fake_get(url, headers=None, timeout=None):
        if failing in url:
            raise TimeoutError("simulated timeout")
        return _resp(TABLE_RESPONSE)

    with patch("tooluniverse.clingen_tool.requests.get", side_effect=fake_get):
        result = tool.run({"gene": "BRCA1"})

    # The count itself stays 0 -- there is nothing else it could be -- but the
    # caller must be able to tell 0 apart from "not retrieved".
    assert result[f"{failing.lower()}_count"] == 0
    assert set(result["failed_contexts"]) == {failing}
    assert "TimeoutError: simulated timeout" in result["failed_contexts"][failing]
    assert "not retrieved" in result["note"]
    # The other half is real data, so this is still a partial success.
    assert result["status"] == "success"


def test_every_context_failing_is_an_error_not_a_zero_count():
    """Reporting success with both counts 0 would be a fabricated
    "this gene has no actionability curation" answer. proteins_api_tool
    likewise reports error when nothing at all was retrieved."""
    tool = _tool("search_actionability")

    def fake_get(url, headers=None, timeout=None):
        raise ConnectionError("simulated outage")

    with patch("tooluniverse.clingen_tool.requests.get", side_effect=fake_get):
        result = tool.run({"gene": "BRCA1"})

    assert result["status"] == "error"
    assert "adult_count" not in result
    assert "pediatric_count" not in result
    assert set(result["failed_contexts"]) == {"Adult", "Pediatric"}


def test_clean_run_carries_no_failure_keys():
    """A run where both contexts succeed must carry the same keys and values
    as the pre-fix response -- the new keys appear only on partial or total
    failure. (Key insertion order does differ from pre-fix; only a consumer
    byte-comparing serialized output would notice.)"""
    tool = _tool("search_actionability")

    with patch(
        "tooluniverse.clingen_tool.requests.get",
        side_effect=lambda url, headers=None, timeout=None: _resp(TABLE_RESPONSE),
    ):
        result = tool.run({"gene": "BRCA1"})

    assert result["status"] == "success"
    assert result["adult_count"] == 1 and result["pediatric_count"] == 1
    assert "failed_contexts" not in result
    assert "note" not in result
