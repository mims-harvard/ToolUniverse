"""Pharos_search_targets / Pharos_get_disease_targets silently returned 10 rows.

Pharos' GraphQL API ignores ``top`` and ``skip`` and answers every ``targets`` query
with a fixed page of 10 (checked live: top 2, 5 and 50 gave the same 10 targets).
Callers who asked for 3 got 10, and callers who asked for 20 (the disease default)
got 10 without being told. The tools now truncate to ``top`` and say so when fewer
than requested come back.
"""

from unittest.mock import patch

import pytest

from tooluniverse import pharos_tool
from tooluniverse.pharos_tool import PharosTool

pytestmark = pytest.mark.unit


def _targets(n):
    return [{"sym": f"G{i}"} for i in range(n)]


def _run(operation, arguments, page, count):
    tool = PharosTool(
        {"name": "Pharos_" + operation, "fields": {"operation": operation}}
    )
    graphql = {
        "status": "success",
        "data": {"targets": {"count": count, "targets": page}},
    }
    with patch.object(tool, "_execute_graphql", return_value=graphql):
        return tool.run({"operation": operation, **arguments})


def test_smaller_top_truncates_the_fixed_page():
    result = _run("search_targets", {"query": "kinase", "top": 3}, _targets(10), 1934)
    assert [t["sym"] for t in result["data"]["targets"]] == ["G0", "G1", "G2"]
    assert result["data"]["count"] == 1934
    assert "note" not in result["data"]


def test_larger_top_than_the_api_returns_is_disclosed():
    result = _run("search_targets", {"query": "kinase", "top": 50}, _targets(10), 1934)
    assert len(result["data"]["targets"]) == 10
    assert "10 of 1934" in result["data"]["note"]
    assert "ignores top/skip" in result["data"]["note"]


def test_disease_targets_default_top_of_20_gets_the_same_note():
    result = _run("get_disease_targets", {"disease": "asthma"}, _targets(10), 300)
    assert len(result["data"]["targets"]) == 10
    assert "10 of 300" in result["data"]["note"]


def test_no_note_when_everything_matching_was_returned():
    result = _run("search_targets", {"query": "rare", "top": 20}, _targets(4), 4)
    assert len(result["data"]["targets"]) == 4
    assert "note" not in result["data"]


def test_apply_top_never_returns_fewer_than_one_for_top_zero():
    shown, _ = pharos_tool._apply_top(_targets(5), 0, 5)
    assert len(shown) == 1
