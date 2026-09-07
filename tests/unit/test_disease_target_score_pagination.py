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
            "datasource_id": "clinical_precedence",
        }
    )


def _page(index, page_size, total, datasource="clinical_precedence"):
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
            {
                "efoId": "EFO_0000339",
                "datasourceId": "clinical_precedence",
                "pageSize": 5,
            }
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
            {
                "efoId": "EFO_0000339",
                "datasourceId": "clinical_precedence",
                "pageSize": 5,
            }
        )

    assert result["status"] == "success"
    assert "truncated" not in result["data"]
    assert result["data"]["total_targets_with_scores"] == 5


# Fix-R37A-1: disease_target_score_tools.json required "pageSize" in every
# one of these 9 tools' schemas even though pageSize's own description says
# "default: 100" and DiseaseTargetScoreTool.run() already reads it via
# arguments.get("pageSize", 100) -- confirmed live that omitting it (the
# natural reading of "default: 100") previously hit a hard schema
# validation error before this fallback ever ran.
@pytest.mark.unit
def test_omitted_page_size_falls_back_to_100(monkeypatch):
    monkeypatch.setattr(gqt.time, "monotonic", lambda: 0.0)

    captured = {}

    def fake_execute(endpoint, query, variables):
        captured["size"] = variables["size"]
        return _page(variables["index"], variables["size"], total=variables["size"])

    with patch.object(gqt, "execute_query", side_effect=fake_execute):
        result = make_tool().run(
            {"efoId": "EFO_0000339", "datasourceId": "clinical_precedence"}
        )

    assert result["status"] == "success"
    assert captured["size"] == 100


@pytest.mark.unit
def test_retired_datasource_id_is_remapped(monkeypatch):
    """A retired datasource ID must not silently return zero scores.

    Open Targets renamed 'ot_genetics_portal' to 'gwas_credible_sets' without
    keeping the old name as an alias, so the stale ID matched nothing and the
    tool returned a successful empty result that read as "no genetic evidence".
    """
    monkeypatch.setattr(gqt.time, "monotonic", lambda: 0.0)

    def fake_execute(endpoint, query, variables):
        return _page(
            variables["index"],
            variables["size"],
            total=variables["size"],
            datasource="gwas_credible_sets",
        )

    with patch.object(gqt, "execute_query", side_effect=fake_execute):
        result = make_tool().run(
            {
                "efoId": "EFO_0000339",
                "datasourceId": "ot_genetics_portal",
                "pageSize": 5,
            }
        )

    assert result["status"] == "success"
    assert result["data"]["datasource"] == "gwas_credible_sets"
    assert result["data"]["total_targets_with_scores"] == 5
    assert "ot_genetics_portal" in result["data"]["datasource_rename_note"]


@pytest.mark.unit
def test_scores_are_sorted_strongest_first(monkeypatch):
    """Truncated runs must still surface the strongest associations first."""
    monkeypatch.setattr(gqt.time, "monotonic", lambda: 0.0)

    def fake_execute(endpoint, query, variables):
        page = _page(variables["index"], variables["size"], total=variables["size"])
        rows = page["data"]["disease"]["associatedTargets"]["rows"]
        for i, row in enumerate(rows):
            row["datasourceScores"][0]["score"] = i / 10.0
        return page

    with patch.object(gqt, "execute_query", side_effect=fake_execute):
        result = make_tool().run(
            {
                "efoId": "EFO_0000339",
                "datasourceId": "clinical_precedence",
                "pageSize": 5,
            }
        )

    scores = [r["score"] for r in result["data"]["target_scores"]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.unit
def test_unknown_datasource_reports_available_ids(monkeypatch):
    """An empty result must say which datasource IDs the disease actually has."""
    monkeypatch.setattr(gqt.time, "monotonic", lambda: 0.0)

    def fake_execute(endpoint, query, variables):
        return _page(
            variables["index"],
            variables["size"],
            total=variables["size"],
            datasource="europepmc",
        )

    with patch.object(gqt, "execute_query", side_effect=fake_execute):
        result = make_tool().run(
            {"efoId": "EFO_0000339", "datasourceId": "not_a_source", "pageSize": 5}
        )

    assert result["status"] == "success"
    assert result["data"]["total_targets_with_scores"] == 0
    assert result["data"]["available_datasources"] == ["europepmc"]
