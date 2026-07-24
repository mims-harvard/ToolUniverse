"""Regression guard for Fix-R17D-1: TheraSAbDab_search_by_target used plain
substring containment against the stored target string (e.g.
"PDCD1/CD279/PD1", or for bispecifics "LAG3/CD223;PDCD1/CD279/PD1"), so a
search for "PD-1" matched "pd1" inside "entpd1" (ENTPD1/CD39, an unrelated
target) -- confirmed live this silently polluted a PD-1 search with CD39
antibodies. The fix splits the stored target string into individual alias
tokens and requires an exact match against one of them.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.therasabdab_tool import TheraSAbDabTool

pytestmark = pytest.mark.unit

THERAPEUTICS = [
    {"inn_name": "pembrolizumab", "target": "PDCD1/CD279/PD1"},
    {"inn_name": "eltivutabart", "target": "ENTPD1/CD39"},
    {"inn_name": "ipilimumab", "target": "CTLA4/CD152"},
    {"inn_name": "some-bispecific", "target": "LAG3/CD223;PDCD1/CD279/PD1"},
    {"inn_name": "trastuzumab", "target": "ERBB2/CD340/HER2"},
]


def _tool():
    return TheraSAbDabTool({"name": "TheraSAbDab_search_by_target"})


def test_pd1_search_excludes_entpd1(monkeypatch):
    tool = _tool()
    monkeypatch.setattr(tool, "_load_all_therapeutics", lambda: list(THERAPEUTICS))

    result = tool._search_by_target({"target": "PD-1"})

    names = [t["inn_name"] for t in result["data"]["therapeutics"]]
    assert "eltivutabart" not in names
    assert "pembrolizumab" in names
    assert "some-bispecific" in names


def test_cd39_search_only_matches_entpd1(monkeypatch):
    tool = _tool()
    monkeypatch.setattr(tool, "_load_all_therapeutics", lambda: list(THERAPEUTICS))

    result = tool._search_by_target({"target": "CD39"})

    names = [t["inn_name"] for t in result["data"]["therapeutics"]]
    assert names == ["eltivutabart"]


def test_her2_search_still_matches(monkeypatch):
    tool = _tool()
    monkeypatch.setattr(tool, "_load_all_therapeutics", lambda: list(THERAPEUTICS))

    result = tool._search_by_target({"target": "HER2"})

    names = [t["inn_name"] for t in result["data"]["therapeutics"]]
    assert names == ["trastuzumab"]
