from unittest.mock import MagicMock, patch

import pytest
import requests

from tooluniverse.oncotree_tool import (
    OncoTreeGetTypeTool,
    OncoTreeListTissuesTool,
    OncoTreeSearchTool,
)


pytestmark = pytest.mark.unit


def _record(code="LUAD", name="Lung Adenocarcinoma", tissue="Lung"):
    return {
        "code": code,
        "name": name,
        "mainType": "Non-Small Cell Lung Cancer",
        "tissue": tissue,
        "color": "Gainsboro",
        "parent": "NSCLC",
        "level": 3,
        "history": [{"version": "old"}],
        "children": {"child": "LUAS"},
        "precursors": [{"code": "OLD"}],
        "revocations": [{"code": "REVOKED"}],
        "externalReferences": {"NCI": ["C3512"], "UMLS": ["C0152013"]},
    }


@pytest.mark.parametrize(
    "arguments,error",
    [
        ({"query": 1}, "query"),
        ({"query": "lung", "field": 1}, "field"),
        ({"query": "lung", "field": "unknown"}, "field must"),
        ({"query": "lung", "exact_match": "false"}, "boolean"),
        ({"query": "lung", "version": " "}, "version"),
    ],
)
def test_search_rejects_invalid_controls_before_network(arguments, error):
    tool = OncoTreeSearchTool({})
    with patch.object(tool, "_get") as get:
        result = tool.run(arguments)
    assert result["status"] == "error"
    assert error in result["error"]
    get.assert_not_called()


def test_search_preserves_all_source_relationship_fields():
    tool = OncoTreeSearchTool({})
    with patch.object(tool, "_get", return_value=[_record()]):
        result = tool.run({"query": "LUAD", "field": "code", "exact_match": True})
    item = result["data"][0]
    assert item["color"] == "Gainsboro"
    assert item["history"] == [{"version": "old"}]
    assert item["children"] == {"child": "LUAS"}
    assert item["precursors"] == [{"code": "OLD"}]
    assert item["revocations"] == [{"code": "REVOKED"}]
    assert item["external_references"]["NCI"] == ["C3512"]
    assert result["metadata"]["source_records_complete"] is True


def test_search_404_is_an_empty_success_result():
    response = MagicMock(status_code=404)
    error = requests.exceptions.HTTPError(response=response)
    tool = OncoTreeSearchTool({})
    with patch.object(tool, "_get", side_effect=error):
        result = tool.run({"query": "NOT_A_REAL_CODE", "field": "code"})
    assert result["status"] == "success"
    assert result["data"] == []
    assert result["metadata"]["count"] == 0


def test_exact_search_rejects_mismatched_payload():
    tool = OncoTreeSearchTool({})
    with patch.object(tool, "_get", return_value=[_record(code="LUAS")]):
        result = tool.run({"query": "LUAD", "field": "code", "exact_match": True})
    assert result["status"] == "error"
    assert result["mismatched_values"] == ["LUAS"]


def test_get_type_404_reaches_specific_not_found_error():
    response = MagicMock(status_code=404)
    error = requests.exceptions.HTTPError(response=response)
    tool = OncoTreeGetTypeTool({})
    with patch.object(tool, "_get", side_effect=error):
        result = tool.run({"code": "NONE"})
    assert result["status"] == "error"
    assert "not found" in result["error"]
    assert "HTTP" not in result["error"]


@pytest.mark.parametrize(
    "records,error_fragment",
    [
        ([_record(), _record()], "not unique"),
        ([_record(code="LUAS")], "different code"),
    ],
)
def test_get_type_requires_one_exact_matching_code(records, error_fragment):
    tool = OncoTreeGetTypeTool({})
    with patch.object(tool, "_get", return_value=records):
        result = tool.run({"code": "LUAD"})
    assert result["status"] == "error"
    assert error_fragment in result["error"]


def test_get_type_reports_verified_complete_record():
    tool = OncoTreeGetTypeTool({})
    with patch.object(tool, "_get", return_value=[_record()]):
        result = tool.run({"code": "luad"})
    assert result["data"]["children"] == {"child": "LUAS"}
    assert result["metadata"]["exact_code_verified"] is True
    assert result["metadata"]["source_record_complete"] is True


def test_list_tissues_reports_full_catalog_scan():
    tool = OncoTreeListTissuesTool({})
    records = [_record(tissue="Lung"), _record(code="BRCA", tissue="Breast")]
    with patch.object(tool, "_get", return_value=records):
        result = tool.run({})
    assert result["data"] == ["Breast", "Lung"]
    assert result["metadata"]["tumor_types_scanned"] == 2
    assert result["metadata"]["complete_source_scan"] is True
