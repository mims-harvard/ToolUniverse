"""Regression guard for Fix-R76A-1: Orphanet_get_genes's internal helpers
(_fetch_genes_for_code, _find_subtype_codes) swallowed ALL request failures
(non-200, exceptions) into an empty list, identical in shape to a genuine
"this disease has no known gene associations" result. Confirmed via code
reading and live testing: the caller then unconditionally reported
"status": "success" with "genes": [] regardless of whether Orphadata
genuinely had no data or the request itself failed (rate limit, 5xx,
timeout) -- clinically indistinguishable outcomes for a rare-disease
gene-association lookup tool. Fixed by threading a (result, failed) tuple
through both helpers so the caller can tell the difference, while
preserving the existing subtype-fallback resilience behavior (still
attempted regardless of *why* the primary lookup came up empty).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.orphanet_tool import OrphanetTool

pytestmark = pytest.mark.unit


def _tool():
    return OrphanetTool({"name": "Orphanet_get_genes"})


def _name_resp(disease_name="Test Disease"):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = {"Preferred term": disease_name}
    return r


def _genes_resp(status_code, associations=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = {
        "data": {"results": {"DisorderGeneAssociation": associations or []}}
    }
    return r


def _route(name_response, genes_response):
    def fake_get(url, timeout=None, headers=None):
        if "ClinicalEntity" in url:
            return name_response
        return genes_response

    return fake_get


def test_genuinely_no_genes_reports_success():
    """A confirmed-empty result (200, zero associations, no disease name to
    even try the subtype fallback with) must stay a clean success."""
    tool = _tool()
    with patch(
        "tooluniverse.orphanet_tool.requests.get",
        side_effect=_route(_name_resp(""), _genes_resp(200, [])),
    ):
        result = tool.run({"operation": "get_genes", "orpha_code": "999999"})

    assert result["status"] == "success"
    assert result["data"]["genes"] == []


def test_failed_gene_fetch_is_not_reported_as_confirmed_empty():
    """The core confirmed bug: a request failure (503) must not produce
    the same "status": "success", "genes": [] shape as a genuine empty
    result -- that's clinically misleading for a gene-association lookup."""
    tool = _tool()
    with patch(
        "tooluniverse.orphanet_tool.requests.get",
        side_effect=_route(_name_resp(""), _genes_resp(503)),
    ):
        result = tool.run({"operation": "get_genes", "orpha_code": "558"})

    assert result["status"] == "error"


def test_successful_direct_lookup_unaffected():
    tool = _tool()
    associations = [
        {
            "DisorderGeneAssociationType": {"name": "Disease-causing"},
            "Gene": {
                "Symbol": "FBN1",
                "Name": "fibrillin 1",
                "GeneType": {"name": "gene with protein product"},
                "LocusList": {"Locus": []},
            },
            "SourceOfValidation": None,
        }
    ]
    with patch(
        "tooluniverse.orphanet_tool.requests.get",
        side_effect=_route(_name_resp("Marfan syndrome"), _genes_resp(200, associations)),
    ):
        result = tool.run({"operation": "get_genes", "orpha_code": "284963"})

    assert result["status"] == "success"
    assert len(result["data"]["genes"]) == 1
    assert result["data"]["genes"][0]["Symbol"] == "FBN1"


def test_fetch_genes_for_code_returns_failed_flag():
    tool = _tool()
    with patch(
        "tooluniverse.orphanet_tool.requests.get",
        return_value=_genes_resp(500),
    ):
        genes, failed = tool._fetch_genes_for_code("558", {})

    assert genes == []
    assert failed is True


def test_fetch_genes_for_code_confirmed_empty_not_marked_failed():
    tool = _tool()
    with patch(
        "tooluniverse.orphanet_tool.requests.get",
        return_value=_genes_resp(200, []),
    ):
        genes, failed = tool._fetch_genes_for_code("558", {})

    assert genes == []
    assert failed is False
