"""Regression guard for Fix-R13D-1: a tool with unmet `required_api_keys`
(e.g. USPTO tools needing USPTO_API_KEY) is dropped from `all_tool_dict`
entirely during loading -- correct for keeping an agent's active tool list
clean -- but that made `tu grep`/`tu info` report such tools as flatly
nonexistent, contradicting `tu run`'s own "requires API key(s) not set"
message for the exact same tool name. Confirmed live: `tu grep uspto` and
`tu info get_patent_overview_by_text_query` both looked identical to "no
such tool", even though the tool exists, is correctly registered, and just
needs an env var set.

These tests cover the three layers of the fix:
  - GetToolInfoTool._not_found_error / GrepToolsTool.run: surface
    `_excluded_api_key_tools` instead of a bare "not found".
  - cli._render_info / cli._render_grep: render that distinction instead of
    collapsing every error back to a hardcoded "not found" message.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.tool_discovery_tools import GetToolInfoTool, GrepToolsTool

pytestmark = pytest.mark.unit


def _fake_tooluniverse(all_tool_dict=None, excluded=None):
    tu = MagicMock()
    tu.all_tool_dict = all_tool_dict or {}
    tu._excluded_api_key_tools = excluded or {}
    return tu


# ---------------------------------------------------------------------------
# GetToolInfoTool
# ---------------------------------------------------------------------------


def test_info_gated_tool_reports_missing_key_not_generic_not_found():
    tu = _fake_tooluniverse(
        excluded={"get_patent_overview_by_text_query": ["USPTO_API_KEY"]}
    )
    tool = GetToolInfoTool({"name": "get_tool_info"}, tooluniverse=tu)

    result = tool.run(
        {"tool_names": "get_patent_overview_by_text_query", "detail_level": "description"}
    )

    assert result["error"] != "not found"
    assert "USPTO_API_KEY" in result["error"]


def test_info_genuinely_missing_tool_still_says_not_found():
    tu = _fake_tooluniverse()
    tool = GetToolInfoTool({"name": "get_tool_info"}, tooluniverse=tu)

    result = tool.run(
        {"tool_names": "TotallyFakeToolName123", "detail_level": "description"}
    )

    assert result["error"] == "not found"


def test_info_batch_mode_distinguishes_gated_from_missing():
    tu = _fake_tooluniverse(excluded={"gated_tool": ["SOME_KEY"]})
    tool = GetToolInfoTool({"name": "get_tool_info"}, tooluniverse=tu)

    result = tool.run(
        {"tool_names": ["gated_tool", "fake_tool"], "detail_level": "description"}
    )

    by_name = {t["name"]: t["error"] for t in result["tools"]}
    assert "SOME_KEY" in by_name["gated_tool"]
    assert by_name["fake_tool"] == "not found"


# ---------------------------------------------------------------------------
# GrepToolsTool
# ---------------------------------------------------------------------------


def test_grep_zero_matches_surfaces_gated_tool_by_name():
    tu = _fake_tooluniverse(
        all_tool_dict={},
        excluded={"get_patent_overview_by_text_query": ["USPTO_API_KEY"]},
    )
    tool = GrepToolsTool({"name": "grep_tools"}, tooluniverse=tu)

    result = tool.run({"pattern": "patent_overview"})

    assert result["total_matches"] == 0
    assert result["gated_matches"] == [
        {"name": "get_patent_overview_by_text_query", "missing_api_keys": ["USPTO_API_KEY"]}
    ]


def test_grep_with_real_matches_does_not_surface_gated_tools():
    tu = _fake_tooluniverse(
        all_tool_dict={
            "PubMed_search_articles": {"name": "PubMed_search_articles", "description": "search pubmed"}
        },
        excluded={"unrelated_gated_tool": ["SOME_KEY"]},
    )
    tool = GrepToolsTool({"name": "grep_tools"}, tooluniverse=tu)

    result = tool.run({"pattern": "pubmed"})

    assert result["total_matches"] == 1
    assert "gated_matches" not in result


def test_grep_no_gated_matches_omits_the_key():
    tu = _fake_tooluniverse(all_tool_dict={}, excluded={"foo_tool": ["FOO_KEY"]})
    tool = GrepToolsTool({"name": "grep_tools"}, tooluniverse=tu)

    result = tool.run({"pattern": "totally_unrelated_zzz"})

    assert result["total_matches"] == 0
    assert "gated_matches" not in result


# ---------------------------------------------------------------------------
# CLI rendering
# ---------------------------------------------------------------------------


def test_render_info_shows_gated_message_verbatim():
    from tooluniverse.cli import _render_info

    d = {
        "name": "get_patent_overview_by_text_query",
        "error": "requires API key(s) not set: USPTO_API_KEY. Set them as environment variables and retry.",
    }
    result = _render_info(d)
    assert "USPTO_API_KEY" in result
    assert "Did you mean" not in result


def test_render_info_still_shows_did_you_mean_for_real_not_found():
    from tooluniverse.cli import _render_info

    d = {
        "error": "not found",
        "name": "UniProt_search_typo",
        "suggestions": ["UniProt_search", "UniProt_get_entry_by_accession"],
    }
    result = _render_info(d)
    assert "Did you mean" in result


def test_render_grep_shows_gated_matches():
    from tooluniverse.cli import _render_grep

    d = {
        "tools": [],
        "total_matches": 0,
        "field": "name",
        "pattern": "uspto",
        "gated_matches": [
            {"name": "get_patent_overview_by_text_query", "missing_api_keys": ["USPTO_API_KEY"]}
        ],
    }
    result = _render_grep(d)
    assert "get_patent_overview_by_text_query" in result
    assert "USPTO_API_KEY" in result
