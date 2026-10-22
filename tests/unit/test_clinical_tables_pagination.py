import ast
import json
from pathlib import Path
from unittest.mock import patch

import jsonschema
import pytest

from tooluniverse.clinical_tables_tool import ClinicalTablesTool


pytestmark = pytest.mark.unit
_ROOT = Path(__file__).parents[2]
_CASES = (
    (
        "RxTerms_search_drugs",
        "metformin",
        ["metFORMIN XR (Oral Pill)"],
        [["metFORMIN XR (Oral Pill)", "500 mg XR Tab"]],
        {
            "STRENGTHS_AND_FORMS": [["500 mg XR Tab"]],
            "RXCUIS": [["860975"]],
        },
    ),
    (
        "HealthConditions_search",
        "hypertension",
        ["11185"],
        [["Hypertension", "High blood pressure"]],
        {"icd10cm_codes": ["I10"], "term_icd9_code": ["401.9"]},
    ),
    (
        "DiseaseNames_search",
        "breast cancer",
        ["CN379681"],
        [["Hereditary breast cancer"]],
        None,
    ),
)


def _config(name):
    path = _ROOT / "src/tooluniverse/data/clinical_tables_tools.json"
    return next(item for item in json.loads(path.read_text()) if item["name"] == name)


@pytest.mark.parametrize("name,terms,codes,rows,extra", _CASES)
def test_searches_use_count_offset_and_expose_continuation(
    name, terms, codes, rows, extra
):
    tool = ClinicalTablesTool(_config(name))
    with patch.object(
        tool, "_make_request", return_value=[46, codes, extra, rows]
    ) as request:
        result = tool.run({"terms": terms, "max_results": 2, "offset": 2})

    endpoint, params = request.call_args.args
    assert endpoint.endswith("/v3/search")
    assert params["count"] == 2
    assert params["offset"] == 2
    assert "maxList" not in params
    assert result["status"] == "success"
    assert result["data"]["results"][0]["code"] == codes[0]
    assert result["metadata"] == {
        "total_results": 46,
        "accessible_results": 46,
        "upstream_truncated": False,
        "returned_count": 1,
        "offset": 2,
        "max_results": 2,
        "has_more": True,
        "next_offset": 3,
        "truncated": True,
        "result_set_complete": False,
        "warning": None,
    }
    jsonschema.validate(result["data"], _config(name)["return_schema"])


@pytest.mark.parametrize("name,terms,codes,rows,extra", _CASES)
@pytest.mark.parametrize("max_results", [0, 501, -1, True, "20", 1.5])
def test_searches_reject_invalid_count_before_network(
    name, terms, codes, rows, extra, max_results
):
    tool = ClinicalTablesTool(_config(name))
    with patch.object(tool, "_make_request") as request:
        result = tool.run({"terms": terms, "max_results": max_results})

    assert result["status"] == "error"
    assert result["parameter"] == "max_results"
    request.assert_not_called()


@pytest.mark.parametrize("name,terms,codes,rows,extra", _CASES)
@pytest.mark.parametrize("offset", [-1, True, "2", 1.5])
def test_searches_reject_invalid_offset_before_network(
    name, terms, codes, rows, extra, offset
):
    tool = ClinicalTablesTool(_config(name))
    with patch.object(tool, "_make_request") as request:
        result = tool.run({"terms": terms, "offset": offset})

    assert result["status"] == "error"
    assert result["parameter"] == "offset"
    request.assert_not_called()


@pytest.mark.parametrize(
    "name", ["RxTerms_search_drugs", "HealthConditions_search", "DiseaseNames_search"]
)
def test_generated_wrappers_expose_offset(name):
    module = ast.parse((_ROOT / f"src/tooluniverse/tools/{name}.py").read_text())
    function = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    names = [argument.arg for argument in function.args.args]
    assert names == ["terms", "max_results", "offset"]
    assert [ast.literal_eval(value) for value in function.args.defaults] == [20, 0]


def test_metadata_discloses_upstream_retrieval_window():
    metadata = ClinicalTablesTool._pagination_metadata(
        {"total_count": 9000, "count": 2}, 7498, 2
    )

    assert metadata["accessible_results"] == 7500
    assert metadata["upstream_truncated"] is True
    assert metadata["has_more"] is False
    assert metadata["warning"]


def test_health_condition_schema_accepts_missing_legacy_icd9_crosswalk():
    data = {
        "total_count": 14,
        "count": 1,
        "search_terms": "hypertension",
        "results": [
            {
                "code": "374",
                "primary_name": "Hypertension",
                "consumer_name": "High blood pressure",
                "icd10cm_codes": "I10",
                "term_icd9_code": None,
            }
        ],
    }

    jsonschema.validate(data, _config("HealthConditions_search")["return_schema"])
