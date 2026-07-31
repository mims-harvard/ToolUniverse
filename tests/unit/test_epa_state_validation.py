"""Regression guard for Fix-R15C-2: EPA_search_tri_facilities and
EPA_search_frs_facilities (both via the shared `_run_state_search` on
`_EnvirofactsBase`) accepted any string as `state`, including a full state
name like "Louisiana" -- which matches zero rows in Envirofacts' 2-letter
state_code column, silently returning an empty result set indistinguishable
from "this state genuinely has zero facilities" (confirmed live the same
state has hundreds of real rows under its actual 2-letter code "LA").
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.epa_envirofacts_tool import EPATRIFacilitiesTool, EPAFRSFacilitiesTool

pytestmark = pytest.mark.unit


def test_full_state_name_is_rejected():
    tool = EPATRIFacilitiesTool({"name": "EPA_search_tri_facilities"})

    result = tool._run_state_search({"state": "Louisiana", "limit": 3})

    assert result["status"] == "error"
    assert "2-letter" in result["error"]


def test_valid_2_letter_code_still_queries(monkeypatch):
    tool = EPATRIFacilitiesTool({"name": "EPA_search_tri_facilities"})
    captured = {}

    def fake_fetch(path):
        captured["path"] = path
        return []

    monkeypatch.setattr(tool, "_fetch", fake_fetch)

    result = tool._run_state_search({"state": "LA", "limit": 3})

    assert result["status"] == "success"
    assert "LA" in captured["path"]


def test_lowercase_2_letter_code_is_normalized(monkeypatch):
    tool = EPATRIFacilitiesTool({"name": "EPA_search_tri_facilities"})
    captured = {}

    def fake_fetch(path):
        captured["path"] = path
        return []

    monkeypatch.setattr(tool, "_fetch", fake_fetch)

    result = tool._run_state_search({"state": "la", "limit": 3})

    assert result["status"] == "success"
    assert "LA" in captured["path"]


def test_frs_facilities_tool_shares_the_same_validation():
    tool = EPAFRSFacilitiesTool({"name": "EPA_search_frs_facilities"})

    result = tool._run_state_search({"state": "California", "limit": 3})

    assert result["status"] == "error"
    assert "2-letter" in result["error"]


def test_non_alpha_state_code_is_rejected():
    tool = EPATRIFacilitiesTool({"name": "EPA_search_tri_facilities"})

    result = tool._run_state_search({"state": "12", "limit": 3})

    assert result["status"] == "error"
