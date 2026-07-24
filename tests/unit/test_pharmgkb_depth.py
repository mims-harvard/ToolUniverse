"""Unit tests for the three PharmGKB/ClinPGx depth tools.

Covers parsing and error paths for:
- PharmGKB_get_drug_label_annotations (drug_label_annotations op)
- PharmGKB_get_pathway (pathway op)
- PharmGKB_get_variant_annotations (variant_annotations op)

All HTTP is mocked at request_with_retry so no network access is needed.
"""

from unittest.mock import Mock, patch

import pytest

from tooluniverse.pharmgkb_tool import PharmGKBTool


def _make_tool(operation):
    return PharmGKBTool({"fields": {"operation": operation}, "timeout": 30})


def _mock_response(status_code, payload):
    resp = Mock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.text = str(payload)
    return resp


# ---------------------------------------------------------------------------
# GAP 1: drug-label annotations
# ---------------------------------------------------------------------------


def test_label_by_id_returns_full_annotation():
    tool = _make_tool("drug_label_annotations")
    payload = {
        "data": {
            "objCls": "Label Annotation",
            "id": "PA166114907",
            "name": "Annotation of FDA Label for bosutinib and ABL1, BCR",
            "biomarkerStatus": "On FDA Biomarker List",
            "alternateDrugAvailable": False,
            "cancerGenome": True,
            "dosingInformation": False,
        }
    }
    with patch(
        "tooluniverse.pharmgkb_tool.request_with_retry",
        return_value=_mock_response(200, payload),
    ):
        result = tool.run({"label_id": "PA166114907"})

    assert result["status"] == "success"
    assert result["data"]["id"] == "PA166114907"
    assert result["data"]["biomarkerStatus"] == "On FDA Biomarker List"
    assert result["data"]["cancerGenome"] is True


def test_label_list_by_source_truncates_with_note():
    tool = _make_tool("drug_label_annotations")
    items = [
        {"objCls": "Label Annotation", "id": f"PA{i}", "name": f"label {i}"}
        for i in range(10)
    ]
    payload = {"data": items}
    with patch(
        "tooluniverse.pharmgkb_tool.request_with_retry",
        return_value=_mock_response(200, payload),
    ):
        result = tool.run({"source": "FDA", "limit": 3})

    assert result["status"] == "success"
    assert len(result["data"]) == 3
    assert "note" in result
    assert "10" in result["note"]


def test_label_defaults_to_fda_source():
    tool = _make_tool("drug_label_annotations")
    payload = {"data": [{"id": "PA1", "name": "x"}]}
    captured = {}

    def _capture(session, method, url, **kwargs):
        captured["url"] = url
        captured["params"] = kwargs.get("params")
        return _mock_response(200, payload)

    with patch("tooluniverse.pharmgkb_tool.request_with_retry", side_effect=_capture):
        result = tool.run({})

    assert result["status"] == "success"
    assert captured["params"]["source"] == "FDA"
    assert captured["url"].endswith("/data/label")


def test_label_invalid_source_returns_error():
    tool = _make_tool("drug_label_annotations")
    result = tool.run({"source": "BOGUS"})
    assert result["status"] == "error"
    assert "Invalid source" in result["error"]


def test_label_no_results_404_is_empty_success():
    tool = _make_tool("drug_label_annotations")
    payload = {"status": "fail", "data": {"errors": [{"message": "No results"}]}}
    with patch(
        "tooluniverse.pharmgkb_tool.request_with_retry",
        return_value=_mock_response(404, payload),
    ):
        result = tool.run({"label_id": "PA000000000"})

    assert result["status"] == "success"
    assert result["data"] == []
    assert "note" in result


# ---------------------------------------------------------------------------
# GAP 2: pathway
# ---------------------------------------------------------------------------


def test_pathway_by_id_parses_core_fields():
    tool = _make_tool("pathway")
    payload = {
        "data": {
            "objCls": "Pathway",
            "id": "PA145011113",
            "name": "Warfarin Pathway, Pharmacokinetics",
            "authors": "Caroline Thorn.",
            "biopaxLink": "submission/PS206014-1450820295.owl",
            "description": {"id": 1, "html": "<p>Warfarin...</p>"},
        }
    }
    with patch(
        "tooluniverse.pharmgkb_tool.request_with_retry",
        return_value=_mock_response(200, payload),
    ):
        result = tool.run({"pathway_id": "PA145011113"})

    assert result["status"] == "success"
    assert result["data"]["name"] == "Warfarin Pathway, Pharmacokinetics"
    assert result["data"]["authors"] == "Caroline Thorn."
    assert "biopaxLink" in result["data"]


def test_pathway_id_alias_works():
    tool = _make_tool("pathway")
    payload = {"data": {"id": "PA145011113", "name": "x"}}
    captured = {}

    def _capture(session, method, url, **kwargs):
        captured["url"] = url
        return _mock_response(200, payload)

    with patch("tooluniverse.pharmgkb_tool.request_with_retry", side_effect=_capture):
        result = tool.run({"id": "PA145011113"})

    assert result["status"] == "success"
    assert captured["url"].endswith("/data/pathway/PA145011113")


def test_pathway_missing_id_returns_error():
    tool = _make_tool("pathway")
    result = tool.run({})
    assert result["status"] == "error"
    assert "pathway_id is required" in result["error"]


def test_pathway_not_found_404_is_empty_success():
    tool = _make_tool("pathway")
    payload = {"status": "fail", "data": {"errors": [{"code": "notFound"}]}}
    with patch(
        "tooluniverse.pharmgkb_tool.request_with_retry",
        return_value=_mock_response(404, payload),
    ):
        result = tool.run({"pathway_id": "PA000000000"})

    assert result["status"] == "success"
    assert result["data"] == []


# ---------------------------------------------------------------------------
# GAP 3: variant annotations
# ---------------------------------------------------------------------------


def test_variant_annotations_by_gene_uses_genes_filter():
    tool = _make_tool("variant_annotations")
    items = [
        {"id": i, "accessionId": f"PA{i}", "alleleGenotype": "*3"} for i in range(8)
    ]
    payload = {"data": items}
    captured = {}

    def _capture(session, method, url, **kwargs):
        captured["url"] = url
        captured["params"] = kwargs.get("params")
        return _mock_response(200, payload)

    with patch("tooluniverse.pharmgkb_tool.request_with_retry", side_effect=_capture):
        result = tool.run({"gene_id": "PA126", "limit": 5})

    assert result["status"] == "success"
    assert len(result["data"]) == 5
    assert captured["params"]["location.genes.accessionId"] == "PA126"
    assert "note" in result  # 8 total > 5 limit


def test_variant_annotations_by_chemical_uses_chemical_filter():
    tool = _make_tool("variant_annotations")
    payload = {"data": [{"id": 1, "accessionId": "PA166137084"}]}
    captured = {}

    def _capture(session, method, url, **kwargs):
        captured["params"] = kwargs.get("params")
        return _mock_response(200, payload)

    with patch("tooluniverse.pharmgkb_tool.request_with_retry", side_effect=_capture):
        result = tool.run({"chemical_id": "PA451906"})

    assert result["status"] == "success"
    assert captured["params"]["relatedChemicals.accessionId"] == "PA451906"
    assert "note" not in result  # only 1 result, no truncation


def test_variant_annotations_missing_filter_returns_error():
    tool = _make_tool("variant_annotations")
    result = tool.run({})
    assert result["status"] == "error"
    assert "gene_id" in result["error"]


def test_variant_annotations_no_results_404_is_empty_success():
    tool = _make_tool("variant_annotations")
    payload = {
        "status": "fail",
        "data": {"errors": [{"message": "No results matching criteria."}]},
    }
    with patch(
        "tooluniverse.pharmgkb_tool.request_with_retry",
        return_value=_mock_response(404, payload),
    ):
        result = tool.run({"chemical_id": "PA999999"})

    assert result["status"] == "success"
    assert result["data"] == []


def test_variant_annotations_http_400_is_error():
    tool = _make_tool("variant_annotations")
    payload = {"status": "fail", "data": {"errors": [{"message": "No such property"}]}}
    with patch(
        "tooluniverse.pharmgkb_tool.request_with_retry",
        return_value=_mock_response(400, payload),
    ):
        result = tool.run({"gene_id": "PA126"})

    assert result["status"] == "error"
    assert "400" in result["error"]


# ---------------------------------------------------------------------------
# Cross-cutting: run() never raises, even on transport failure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "operation,args",
    [
        ("drug_label_annotations", {"label_id": "PA166114907"}),
        ("pathway", {"pathway_id": "PA145011113"}),
        ("variant_annotations", {"gene_id": "PA126"}),
    ],
)
def test_run_returns_error_on_request_exception(operation, args):
    import requests

    tool = _make_tool(operation)
    with patch(
        "tooluniverse.pharmgkb_tool.request_with_retry",
        side_effect=requests.RequestException("boom"),
    ):
        result = tool.run(args)

    assert result["status"] == "error"
    assert "failed" in result["error"].lower()
