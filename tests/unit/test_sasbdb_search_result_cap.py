"""Regression guard for Fix-R20B-3: SASBDB_search's free-text fallback (it
correctly self-documents that SASBDB has no full-text search and lists all
published entries instead) had no way to cap the response -- confirmed
live it returned all ~5432 entries (~350KB) with no limit/offset
parameter available, a large mostly-useless payload for an LLM-agent
caller. Fixed by adding a `max_results` argument (default 50) that caps
the returned list client-side, with total_entries/truncated fields so the
caller can tell it was capped.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.sasbdb_tool import SASBDBTextSearchTool

pytestmark = pytest.mark.unit


def _tool():
    return SASBDBTextSearchTool({"name": "sasbdb_test"})


def _resp(status_code, json_body):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body
    return r


def test_free_text_query_capped_at_default_50():
    tool = _tool()
    all_entries = [{"code": f"SASD{i:04d}"} for i in range(5432)]

    with patch(
        "tooluniverse.sasbdb_tool.request_with_retry",
        return_value=_resp(200, all_entries),
    ):
        result = tool.run({"query": "lysozyme"})

    assert result["status"] == "success"
    assert len(result["data"]) == 50
    assert result["total_entries"] == 5432
    assert result["truncated"] is True


def test_free_text_query_respects_custom_max_results():
    tool = _tool()
    all_entries = [{"code": f"SASD{i:04d}"} for i in range(5432)]

    with patch(
        "tooluniverse.sasbdb_tool.request_with_retry",
        return_value=_resp(200, all_entries),
    ):
        result = tool.run({"query": "lysozyme", "max_results": 5})

    assert len(result["data"]) == 5
    assert result["truncated"] is True


def test_small_catalog_not_marked_truncated():
    tool = _tool()
    all_entries = [{"code": "SASD0001"}]

    with patch(
        "tooluniverse.sasbdb_tool.request_with_retry",
        return_value=_resp(200, all_entries),
    ):
        result = tool.run({"query": "lysozyme"})

    assert result["truncated"] is False
    assert len(result["data"]) == 1


def test_uniprot_accession_path_unaffected_by_cap():
    tool = _tool()
    entry = {"code": "SASDAC2", "uniprot": "P00698"}

    with patch(
        "tooluniverse.sasbdb_tool.request_with_retry", return_value=_resp(200, entry)
    ):
        result = tool.run({"query": "P00698"})

    assert result["status"] == "success"
    assert result["data"] == entry
    assert "total_entries" not in result
