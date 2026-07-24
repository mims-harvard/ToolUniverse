"""Regression guard for Fix-R16C-1: MobiDB returns HTTP 200 with a
completely empty body for an unrecognized identifier (confirmed live, e.g.
a UniProt entry name like "SNCA_HUMAN" instead of an accession like
"P37840") rather than a 404 -- so raise_for_status() never fires, and the
previous code called response.json() directly, letting a raw
json.JSONDecodeError ("Expecting value: line 1 column 1") leak through as
an opaque "Unexpected error" instead of an actionable not-found message.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.mobidb_tool import MobiDBTool

pytestmark = pytest.mark.unit


class _FakeResponse:
    def __init__(self, text="", status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        pass

    def json(self):
        import json

        return json.loads(self.text)


def _tool(endpoint):
    return MobiDBTool({"name": "MobiDB_test", "fields": {"endpoint": endpoint}})


def test_get_protein_empty_body_gives_actionable_error(monkeypatch):
    tool = _tool("get_protein")
    monkeypatch.setattr(
        "tooluniverse.mobidb_tool.requests.get", lambda *a, **k: _FakeResponse("")
    )

    result = tool.run({"accession": "SNCA_HUMAN"})

    assert result["status"] == "error"
    assert "SNCA_HUMAN" in result["error"]
    assert "UniProt accession" in result["error"]


def test_get_consensus_empty_body_gives_actionable_error(monkeypatch):
    tool = _tool("get_consensus")
    monkeypatch.setattr(
        "tooluniverse.mobidb_tool.requests.get", lambda *a, **k: _FakeResponse("")
    )

    result = tool.run({"accession": "SNCA_HUMAN"})

    assert result["status"] == "error"
    assert "SNCA_HUMAN" in result["error"]


def test_get_protein_valid_response_still_parses(monkeypatch):
    tool = _tool("get_protein")
    body = (
        '{"acc": "P37840", "gene": "SNCA", "name": "Alpha-synuclein", '
        '"organism": "Homo sapiens", "length": 140, "sequence": "M...", '
        '"prediction-disorder-mobidb_lite": {}, "curated-disorder-disprot": {}, '
        '"curated-lip-disprot": {}, "reviewed": true}'
    )
    monkeypatch.setattr(
        "tooluniverse.mobidb_tool.requests.get", lambda *a, **k: _FakeResponse(body)
    )

    result = tool.run({"accession": "P37840"})

    assert result["status"] == "success"
    assert result["data"]["accession"] == "P37840"
