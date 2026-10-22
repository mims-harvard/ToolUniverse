"""Unit test: STRING_get_protein_interactions honors `limit` as an output cap.

Regression: `limit` is documented as "Maximum number of interactions to return"
but STRING interprets it as a network node-expansion count and returns EVERY
pairwise edge -- so limit=50 yielded 300+ rows. The tool now returns at most
`limit` interactions, keeping the highest-confidence ones.
"""
from unittest.mock import patch

import pytest

from tooluniverse.string_tool import STRINGRESTTool


def _tool():
    return STRINGRESTTool(
        {
            "name": "STRING_get_protein_interactions",
            "type": "STRINGRESTTool",
            "fields": {"endpoint": "/tsv/network"},
            "parameter": {
                "type": "object",
                "properties": {},
                "required": ["protein_ids"],
            },
        }
    )


def _rows(n):
    # n rows with ascending score 0.01 .. n*0.01 (so truncation must sort).
    return [
        {"preferredName_A": "CFTR", "preferredName_B": f"P{i}", "score": f"{i / 100:.2f}"}
        for i in range(1, n + 1)
    ]


@pytest.mark.unit
def test_limit_caps_and_keeps_highest_scores():
    tool = _tool()
    api = {"data": _rows(30), "header": ["preferredName_A", "preferredName_B", "score"]}
    with patch.object(STRINGRESTTool, "_make_request", return_value=api):
        result = tool.run({"protein_ids": ["CFTR"], "species": 9606, "limit": 5})
    data = result["data"]
    assert len(data) == 5
    # Kept the 5 highest scores (0.30, 0.29, ...), sorted descending.
    assert [r["score"] for r in data] == ["0.30", "0.29", "0.28", "0.27", "0.26"]
    assert result["metadata"]["truncated_to_limit"] == 5
    assert result["metadata"]["total_interactions"] == 30
    assert result["metadata"]["interaction_offset"] == 0
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_interaction_offset"] == 5


@pytest.mark.unit
def test_interaction_offset_recovers_second_page_in_stable_score_order():
    tool = _tool()
    api = {"data": _rows(12), "header": ["preferredName_A", "preferredName_B", "score"]}
    with patch.object(STRINGRESTTool, "_make_request", return_value=api):
        result = tool.run(
            {
                "protein_ids": ["CFTR"],
                "species": 9606,
                "limit": 5,
                "interaction_offset": 5,
            }
        )

    assert [r["score"] for r in result["data"]] == [
        "0.07",
        "0.06",
        "0.05",
        "0.04",
        "0.03",
    ]
    assert result["metadata"]["total_interactions"] == 12
    assert result["metadata"]["next_interaction_offset"] == 10


@pytest.mark.unit
def test_tail_page_terminates():
    tool = _tool()
    api = {"data": _rows(12), "header": ["preferredName_A", "preferredName_B", "score"]}
    with patch.object(STRINGRESTTool, "_make_request", return_value=api):
        result = tool.run(
            {"protein_ids": ["CFTR"], "limit": 5, "interaction_offset": 10}
        )

    assert [r["score"] for r in result["data"]] == ["0.02", "0.01"]
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_interaction_offset"] is None


@pytest.mark.unit
def test_no_truncation_when_rows_within_limit():
    tool = _tool()
    api = {"data": _rows(3), "header": ["preferredName_A", "preferredName_B", "score"]}
    with patch.object(STRINGRESTTool, "_make_request", return_value=api):
        result = tool.run({"protein_ids": ["CFTR"], "species": 9606, "limit": 10})
    assert len(result["data"]) == 3
    assert "truncated_to_limit" not in result["metadata"]
    assert result["metadata"]["result_set_complete"] is True


@pytest.mark.unit
def test_no_limit_returns_all():
    tool = _tool()
    api = {"data": _rows(12), "header": ["preferredName_A", "preferredName_B", "score"]}
    with patch.object(STRINGRESTTool, "_make_request", return_value=api):
        result = tool.run({"protein_ids": ["CFTR"], "species": 9606})
    assert len(result["data"]) == 12


@pytest.mark.unit
def test_invalid_interaction_offset_is_rejected():
    tool = _tool()
    api = {"data": _rows(3), "header": ["preferredName_A", "preferredName_B", "score"]}
    with patch.object(STRINGRESTTool, "_make_request", return_value=api):
        result = tool.run(
            {"protein_ids": ["CFTR"], "limit": 2, "interaction_offset": -1}
        )

    assert result["status"] == "error"
    assert "interaction_offset" in result["error"]
