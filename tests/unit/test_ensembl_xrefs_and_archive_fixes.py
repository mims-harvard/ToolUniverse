"""Regression guard for Fix-R19A-1/2:

- EnsemblXrefsTool._get_xrefs silently truncated `xrefs` to 100 entries
  while `database_summary` was computed from the full, untruncated list --
  confirmed live for TP53 (ENSG00000141510, 157 real xrefs) that the
  per-database counts didn't match what was actually present in the
  truncated array, with no flag indicating truncation happened. The cap
  is now high enough to essentially never trigger, and an explicit
  `truncated` flag is set when it does.
- EnsemblArchiveTool blanket-mapped every upstream HTTP 400 to "Invalid
  Ensembl ID format", discarding the real message -- confirmed live for a
  syntactically valid but nonexistent ID (ENSG00000999999), which
  Ensembl's own archive endpoint returns as HTTP 400 with body
  {"error": "No object found for ENSG00000999999"}, not a format problem.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.ensembl_xrefs_tool import EnsemblXrefsTool
from tooluniverse.ensembl_archive_tool import EnsemblArchiveTool

pytestmark = pytest.mark.unit


def _xrefs_tool():
    return EnsemblXrefsTool({"name": "xrefs_test", "fields": {"endpoint": "xrefs_by_id"}})


def _archive_tool():
    return EnsemblArchiveTool({"name": "archive_test", "fields": {"endpoint": "get_id_history"}})


def _resp(json_body):
    r = MagicMock()
    r.json.return_value = json_body
    r.raise_for_status = MagicMock()
    return r


def test_xrefs_database_summary_matches_returned_xrefs_count():
    tool = _xrefs_tool()
    # 157 entries across a couple of databases, like the real TP53 response.
    raw = [
        {"dbname": "HGNC", "primary_id": f"HGNC:{i}", "display_id": "TP53"}
        for i in range(100)
    ] + [
        {"dbname": "EntrezGene", "primary_id": f"{i}", "display_id": "TP53"}
        for i in range(57)
    ]

    with patch("tooluniverse.ensembl_xrefs_tool.requests.get", return_value=_resp(raw)):
        result = tool.run({"ensembl_id": "ENSG00000141510"})

    data = result["data"]
    assert len(data["xrefs"]) == 157
    assert data["truncated"] is False
    assert sum(data["database_summary"].values()) == len(data["xrefs"])
    assert result["metadata"]["total_xrefs"] == 157


def test_xrefs_truncation_flag_set_when_cap_exceeded():
    tool = _xrefs_tool()
    raw = [{"dbname": "HGNC", "primary_id": str(i)} for i in range(600)]

    with patch("tooluniverse.ensembl_xrefs_tool.requests.get", return_value=_resp(raw)):
        result = tool.run({"ensembl_id": "ENSG00000141510"})

    data = result["data"]
    assert len(data["xrefs"]) == 500
    assert data["truncated"] is True


def test_archive_400_surfaces_upstream_not_found_message(monkeypatch):
    tool = _archive_tool()
    resp = MagicMock()
    resp.status_code = 400
    resp.json.return_value = {"error": "No object found for ENSG00000999999"}
    http_error = requests.exceptions.HTTPError(response=resp)

    def fake_get(*a, **k):
        raise http_error

    with patch("tooluniverse.ensembl_archive_tool.requests.get", side_effect=fake_get):
        result = tool.run({"ensembl_id": "ENSG00000999999"})

    assert result["status"] == "error"
    assert result["error"] == "No object found for ENSG00000999999"
    assert "Invalid Ensembl ID format" not in result["error"]


def test_archive_400_falls_back_to_generic_message_when_no_body(monkeypatch):
    tool = _archive_tool()
    resp = MagicMock()
    resp.status_code = 400
    resp.json.side_effect = ValueError("not json")
    http_error = requests.exceptions.HTTPError(response=resp)

    def fake_get(*a, **k):
        raise http_error

    with patch("tooluniverse.ensembl_archive_tool.requests.get", side_effect=fake_get):
        result = tool.run({"ensembl_id": "not-even-an-id"})

    assert result["status"] == "error"
    assert "Invalid Ensembl ID format" in result["error"]
