"""Unit test: OpenTargets target->diseases rows include the aggregate score.

Regression: OpenTargets_get_diseases_phenotypes_by_target_ensembl returned rows
with only `datasourceScores` (per-source), NOT the top-level aggregate `score`
that the reciprocal disease->targets endpoint exposes. Users ranking a target's
diseases (flagged by 3 separate personas) had to hand-aggregate. The API DOES
expose `score`; the query just omitted it.
"""
import glob
import json

import pytest


def _load(name):
    for f in glob.glob("src/tooluniverse/data/*.json"):
        try:
            data = json.load(open(f))
        except ValueError:
            continue
        if isinstance(data, list):
            for tool in data:
                if isinstance(tool, dict) and tool.get("name") == name:
                    return tool
    raise AssertionError(f"tool config not found: {name}")


@pytest.mark.unit
def test_query_requests_aggregate_score():
    query = _load("OpenTargets_get_diseases_phenotypes_by_target_ensembl")[
        "query_schema"
    ]
    # The aggregate score must be requested at the row level, not only inside
    # datasourceScores.
    rows_block = query.split("rows {", 1)[1].split("datasourceScores", 1)[0]
    assert "score" in rows_block
    assert "disease" in rows_block
