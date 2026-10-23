import ast
import json
from pathlib import Path

import pytest
from jsonschema import validate

from tooluniverse.allen_brain_tool import AllenBrainTool


ROOT = Path(__file__).parents[2]
CONFIGS = {
    item["name"]: item
    for item in json.loads(
        (ROOT / "src/tooluniverse/data/allen_brain_tools.json").read_text()
    )
}


@pytest.mark.parametrize(
    "name,arguments",
    [
        ("AllenBrain_search_genes", {"gene_name": "kinase"}),
        ("AllenBrain_search_structures", {"name": "cortex"}),
        ("AllenBrain_get_expression_datasets", {"gene_acronym": "Gad1"}),
        (
            "AllenBrain_get_structure_expression_values",
            {"section_data_set_id": 75457539},
        ),
    ],
)
def test_allen_list_endpoints_forward_start_and_report_continuation(
    monkeypatch, name, arguments
):
    captured = {}

    def fake_query(criteria, num_rows=50, start_row=0, include=None):
        captured.update(
            {
                "criteria": criteria,
                "num_rows": num_rows,
                "start_row": start_row,
                "include": include,
            }
        )
        rows = [{"id": 3}, {"id": 4}]
        return {
            "success": True,
            "msg": rows,
            "total_rows": 12,
            "num_rows": 2,
            "start_row": 3,
        }

    tool = AllenBrainTool(CONFIGS[name])
    monkeypatch.setattr(tool, "_make_rma_query", fake_query)
    result = tool.run({**arguments, "num_rows": 2, "start_row": 3})

    assert captured["num_rows"] == 2
    assert captured["start_row"] == 3
    if name == "AllenBrain_get_expression_datasets":
        assert result["metadata"]["total_results"] is None
        assert result["metadata"]["total_results_is_exact"] is False
        assert result["metadata"]["total_results_including_failed"] == 12
    else:
        assert result["metadata"]["total_results"] == 12
        assert result["metadata"]["total_results_is_exact"] is True
    assert result["metadata"]["returned"] == 2
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_start_row"] == 5
    assert result["metadata"]["truncated"] is True
    validate(result["data"], CONFIGS[name]["return_schema"])


def test_expression_dataset_metadata_does_not_claim_filtered_page_is_total(monkeypatch):
    tool = AllenBrainTool(CONFIGS["AllenBrain_get_expression_datasets"])
    monkeypatch.setattr(
        tool,
        "_make_rma_query",
        lambda *_args, **_kwargs: {
            "success": True,
            "msg": [{"id": 1, "failed": False}, {"id": 2, "failed": True}],
            "total_rows": 22,
            "num_rows": 2,
        },
    )
    result = tool.run({"gene_acronym": "Gad1", "num_rows": 2, "start_row": 0})
    assert len(result["data"]) == 1
    assert result["metadata"]["total_results_including_failed"] == 22
    assert result["metadata"]["total_results"] is None
    assert result["metadata"]["failed_rows_on_page"] == 1
    assert result["metadata"]["usable_total_is_unknown"] is True
    assert result["metadata"]["next_start_row"] == 2


@pytest.mark.parametrize("value", [0, 2001, True, "50", 1.5])
def test_allen_rejects_invalid_num_rows_before_network(monkeypatch, value):
    tool = AllenBrainTool(CONFIGS["AllenBrain_search_genes"])
    monkeypatch.setattr(
        tool,
        "_make_rma_query",
        lambda *_args, **_kwargs: pytest.fail("network must not be called"),
    )
    result = tool.run({"gene_acronym": "Gad1", "num_rows": value})
    assert result["status"] == "error"
    assert result["parameter"] == "num_rows"


@pytest.mark.parametrize("value", [-1, True, "2", 1.5])
def test_allen_rejects_invalid_start_row_before_network(monkeypatch, value):
    tool = AllenBrainTool(CONFIGS["AllenBrain_search_structures"])
    monkeypatch.setattr(
        tool,
        "_make_rma_query",
        lambda *_args, **_kwargs: pytest.fail("network must not be called"),
    )
    result = tool.run({"name": "cortex", "start_row": value})
    assert result["status"] == "error"
    assert result["parameter"] == "start_row"


@pytest.mark.parametrize(
    "filename,expected_defaults",
    [
        ("AllenBrain_search_genes.py", [None, None, 50, 0]),
        ("AllenBrain_search_structures.py", [None, None, 50, 0]),
        ("AllenBrain_get_expression_datasets.py", [1, 50, 0]),
        ("AllenBrain_get_structure_expression_values.py", [True, 50, 0]),
    ],
)
def test_generated_allen_wrappers_publish_start_row(filename, expected_defaults):
    path = ROOT / "src/tooluniverse/tools" / filename
    function = next(
        node
        for node in ast.parse(path.read_text()).body
        if isinstance(node, ast.FunctionDef)
    )
    assert [
        ast.literal_eval(node) for node in function.args.defaults
    ] == expected_defaults
