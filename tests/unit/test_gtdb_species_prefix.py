"""Regression guard for Fix-R15E-1: GTDB's own /species/search endpoint
rejects the "s__" rank prefix outright (confirmed live: HTTP 400 with the
prefix, HTTP 200 without it), but GTDB_search_taxon -- the natural upstream
discovery tool for finding a species name -- returns names WITH that exact
prefix (e.g. "s__Faecalibacterium prausnitzii"), breaking the natural
search -> get_species chaining workflow.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.gtdb_tool import GTDBTool

pytestmark = pytest.mark.unit


def _tool():
    return GTDBTool({"name": "GTDB_get_species", "fields": {"operation": "get_species"}})


def test_strips_s_prefix_before_querying(monkeypatch):
    tool = _tool()
    captured = {}

    def fake_make_request(path, params=None):
        captured["path"] = path
        return {"ok": True, "data": {"name": "Faecalibacterium prausnitzii", "genomes": []}}

    monkeypatch.setattr(tool, "_make_request", fake_make_request)

    result = tool._get_species({"species": "s__Faecalibacterium prausnitzii"})

    assert result["status"] == "success"
    assert captured["path"] == "species/search/Faecalibacterium prausnitzii"


def test_unprefixed_species_name_unchanged(monkeypatch):
    tool = _tool()
    captured = {}

    def fake_make_request(path, params=None):
        captured["path"] = path
        return {"ok": True, "data": {"name": "Faecalibacterium prausnitzii", "genomes": []}}

    monkeypatch.setattr(tool, "_make_request", fake_make_request)

    tool._get_species({"species": "Faecalibacterium prausnitzii"})

    assert captured["path"] == "species/search/Faecalibacterium prausnitzii"
