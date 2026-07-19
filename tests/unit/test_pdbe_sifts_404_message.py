"""Regression guard for Fix-R18A-3: PDBeSIFTSTool's shared HTTPError handler
gave a bare "PDBe SIFTS API HTTP error: 404" for every 404, regardless of
cause -- confirmed live for PDBeSIFTS_get_scop_mapping on PDB 3k34 (a real,
valid entry that simply has no SCOP classification), which gave no way to
tell "no mapping data for this entry" apart from "the request itself is
broken." 404s now get an endpoint-aware message clarifying this; other
status codes and successful responses are unaffected.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.pdbe_sifts_tool import PDBeSIFTSTool

pytestmark = pytest.mark.unit


def _tool(endpoint):
    return PDBeSIFTSTool(
        {"name": "PDBeSIFTS_get_scop_mapping", "fields": {"endpoint": endpoint}}
    )


def _http_error(status_code):
    resp = MagicMock()
    resp.status_code = status_code
    err = requests.exceptions.HTTPError(response=resp)
    return err


def test_404_gives_data_gap_message_not_bare_status_code(monkeypatch):
    tool = _tool("scop")

    def fake_get(*a, **k):
        raise _http_error(404)

    monkeypatch.setattr("tooluniverse.pdbe_sifts_tool.requests.get", fake_get)

    result = tool.run({"pdb_id": "3k34"})

    assert result["status"] == "error"
    assert "404" in result["error"]
    assert "scop" in result["error"]
    assert "no data of this specific type" in result["error"]


def test_non_404_http_error_keeps_bare_status_code(monkeypatch):
    tool = _tool("scop")

    def fake_get(*a, **k):
        raise _http_error(500)

    monkeypatch.setattr("tooluniverse.pdbe_sifts_tool.requests.get", fake_get)

    result = tool.run({"pdb_id": "3k34"})

    assert result["status"] == "error"
    assert result["error"] == "PDBe SIFTS API HTTP error: 500"
