"""Unit tests for DiseaseTargetScoreTool's bounded pagination.

OpenTargets diseases can have >10,000 associated targets. The tool
paginates client-side over all of them; without a wall-clock bound the
loop issues hundreds of sequential requests and can run for minutes.
These tests pin the time-budget guard without touching the live API.
"""
from unittest.mock import patch

import pytest

import tooluniverse.graphql_tool as gqt
from tooluniverse.graphql_tool import DiseaseTargetScoreTool


def make_tool():
    return DiseaseTargetScoreTool(
        {
            "name": "disease_target_score",
            "type": "DiseaseTargetScoreTool",
            "query_schema": "query { disease { id } }",
            "parameter": {"type": "object", "properties": {}},
            "datasource_id": "chembl",
        }
    )


def _page(index, page_size, total, datasource="chembl"):
    """Build one associatedTargets page that always reports a huge total."""
    rows = [
        {
            "target": {"approvedSymbol": f"GENE{index}_{i}", "id": f"ENSG{index}_{i}"},
            "datasourceScores": [{"id": datasource, "score": 0.5}],
        }
        for i in range(page_size)
    ]
    return {
        "data": {
            "disease": {
                "id": "EFO_0000339",
                "name": "test disease",
                "associatedTargets": {"count": total, "rows": rows},
            }
        }
    }


@pytest.mark.unit
def test_pagination_stops_at_time_budget(monkeypatch):
    """A never-ending result set must terminate via the wall-clock budget."""
    # Force the budget to elapse after the 3rd page regardless of real time.
    fake_now = iter([0.0] + [i * 10.0 for i in range(1, 50)])
    monkeypatch.setattr(gqt.time, "monotonic", lambda: next(fake_now))

    calls = {"n": 0}

    def fake_execute(endpoint, query, variables):
        calls["n"] += 1
        # total far exceeds anything we will fetch → loop relies on the budget
        return _page(variables["index"], variables["size"], total=1_000_000)

    with patch.object(gqt, "execute_query", side_effect=fake_execute):
        result = make_tool().run(
            {"efoId": "EFO_0000339", "datasourceId": "chembl", "pageSize": 5}
        )

    assert result["status"] == "success"
    assert result["data"]["truncated"] is True
    assert "note" in result["data"]
    # Budget (25s) is crossed within a handful of pages, not hundreds.
    assert calls["n"] < 10


@pytest.mark.unit
def test_pagination_completes_without_truncation(monkeypatch):
    """When the result set is small, it finishes and is not marked truncated."""
    monkeypatch.setattr(gqt.time, "monotonic", lambda: 0.0)

    def fake_execute(endpoint, query, variables):
        # total == page_size → exactly one page, loop exits naturally
        return _page(variables["index"], variables["size"], total=variables["size"])

    with patch.object(gqt, "execute_query", side_effect=fake_execute):
        result = make_tool().run(
            {"efoId": "EFO_0000339", "datasourceId": "chembl", "pageSize": 5}
        )

    assert result["status"] == "success"
    assert "truncated" not in result["data"]
    assert result["data"]["total_targets_with_scores"] == 5
