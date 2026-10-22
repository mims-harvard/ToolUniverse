"""Regression tests for Thera-SAbDab completeness and phase statistics."""

from unittest.mock import patch

import pytest

from tooluniverse.therasabdab_tool import TheraSAbDabTool

pytestmark = pytest.mark.unit


def _row(index, target="PDCD1/CD279/PD1", phase="Phase-II"):
    return {
        "inn_name": f"antibody-{index:03d}",
        "format": "Whole mAb",
        "clinical_trial": phase,
        "status": "Active",
        "target": target,
        "year_proposed": "2020",
    }


def _tool(operation):
    return TheraSAbDabTool({"fields": {"operation": operation}})


def test_broad_name_search_is_paginated_without_losing_matches():
    rows = [_row(i) for i in range(55)]
    tool = _tool("search_therapeutics")
    with patch.object(tool, "_load_all_therapeutics", return_value=rows):
        result = tool.run({"query": "antibody", "limit": 20, "offset": 20})

    data = result["data"]
    assert data["count"] == 20
    assert data["total_therapeutics"] == 55
    assert data["returned"] == 20
    assert data["offset"] == 20
    assert data["has_more"] is True
    assert data["next_offset"] == 40
    assert data["therapeutics"][0]["inn_name"] == "antibody-020"


def test_target_search_second_page_is_reachable():
    rows = [_row(i) for i in range(55)] + [_row(99, target="ERBB2/HER2")]
    tool = _tool("search_by_target")
    with patch.object(tool, "_load_all_therapeutics", return_value=rows):
        result = tool.run({"target": "PD-1", "limit": 20, "offset": 40})

    data = result["data"]
    assert data["count"] == 15
    assert data["total_therapeutics"] == 55
    assert data["returned"] == 15
    assert data["has_more"] is False
    assert data["next_offset"] is None
    assert data["therapeutics"][0]["inn_name"] == "antibody-040"


def test_catalog_uses_clinical_trial_field_and_exposes_page():
    rows = [
        _row(0, phase="Approved"),
        _row(1, phase="Phase-II"),
        _row(2, phase="Phase-II"),
    ]
    tool = _tool("get_all_therapeutics")
    with patch.object(tool, "_load_all_therapeutics", return_value=rows):
        result = tool.run({"limit": 1, "offset": 1})

    data = result["data"]
    assert data["by_phase"] == {"Approved": 1, "Phase-II": 2}
    assert data["therapeutics"] == [rows[1]]
    assert data["returned"] == 1
    assert data["next_offset"] == 2


@pytest.mark.parametrize(
    ("operation", "arguments"),
    [
        ("search_therapeutics", {"query": "mab", "limit": "bad"}),
        ("search_by_target", {"target": "PD-1", "offset": "bad"}),
        ("get_all_therapeutics", {"limit": None}),
    ],
)
def test_invalid_pagination_is_explicit(operation, arguments):
    result = _tool(operation).run(arguments)

    assert result["status"] == "error"
    assert "integers" in result["error"]
