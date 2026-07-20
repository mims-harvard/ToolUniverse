"""Regression guard for Fix-R19B-1/3: ClinGenTool's actionability and
variant-classification methods had two related bugs, both confirmed live --

1. The actionability API's `?flavor=flat` response is a JSON table --
   {"columns": [...], "rows": [[...], ...]} -- not a list of per-curation
   dicts. `_get_actionability`'s `isinstance(curations, list)` guard was
   always False against this dict, so a gene filter was silently skipped
   entirely (returning all 254 unfiltered rows for BRCA1). The identical
   check in `_search_actionability` had the opposite symptom: `matches`
   was never assigned, so it always returned {"Adult": [], "Pediatric":
   []} even for BRCA1, which has real curated actionability data. The
   table-to-dicts conversion itself (`_actionability_rows_to_dicts`, a
   ClinGenTool static method) is covered directly in
   test_clingen_actionability_columnar_parsing.py -- these tests exercise
   the end-to-end gene-filtering behavior through `tool.run()`.
2. `_get_variant_classifications` downloaded the ENTIRE, unpaginated
   ClinGen Evidence Repository (confirmed live: 28+MB and still streaming
   after 200s) and filtered client-side afterward. A fast, already
   gene-filtered JSON endpoint exists (`/classifications?gene=X`,
   confirmed live ~1s response) and is now used instead; a request with
   no gene now errors immediately rather than hanging.
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


def test_get_variant_classifications_requires_gene():
    tool = _tool("get_variant_classifications")

    result = tool.run({})

    assert result["status"] == "error"
    assert "gene" in result["error"]


def test_get_variant_classifications_uses_fast_filtered_endpoint(monkeypatch):
    tool = _tool("get_variant_classifications")
    api_response = {
        "variantInterpretations": [
            {
                "caid": "CAR:CA000895",
                "gene": {"label": "BRCA1"},
                "condition": {"label": "BRCA1-related cancer predisposition"},
                "publishedDate": "2024-06-11",
                "hgvs": ["NM_007294.4:c.135-1G>T"],
                "guidelines": [{"outcome": {"label": "Pathogenic"}}],
            }
        ]
    }
    captured = {}

    def fake_get(url, params=None, **kwargs):
        captured["url"] = url
        captured["params"] = params
        return _resp(api_response)

    with patch("tooluniverse.clingen_tool.requests.get", side_effect=fake_get):
        result = tool.run({"gene": "BRCA1"})

    assert result["status"] == "success"
    assert result["total"] == 1
    assert result["data"][0]["classification"] == "Pathogenic"
    assert result["data"][0]["caid"] == "CAR:CA000895"
    assert "classifications/all" not in captured["url"]
    assert captured["params"] == {"gene": "BRCA1"}


def test_get_variant_classifications_variant_filter_matches_hgvs(monkeypatch):
    tool = _tool("get_variant_classifications")
    api_response = {
        "variantInterpretations": [
            {"caid": "CAR:CA1", "hgvs": ["NM_1:c.1A>T"], "guidelines": []},
            {"caid": "CAR:CA2", "hgvs": ["NM_2:c.2A>T"], "guidelines": []},
        ]
    }

    with patch("tooluniverse.clingen_tool.requests.get", return_value=_resp(api_response)):
        result = tool.run({"gene": "BRCA1", "variant": "CA1"})

    assert result["total"] == 1
    assert result["data"][0]["caid"] == "CAR:CA1"
