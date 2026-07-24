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
