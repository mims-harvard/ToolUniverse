"""Regression guard for Fix-R18A-2/R18C-6 and Fix-R18C-1/R18D-3: `tu run`'s
human-readable error renderer (`_render_run`) had two related gaps --

1. `is_not_found` matched a plain "not found" substring anywhere in the
   error message, so a tool's own HTTP-404-shaped error (e.g. PDBe's
   "404 Client Error: Not Found for url: ...", or CTD's "'cadmium' was not
   found in the RENCI CTD mirror") triggered misleading "check tool name
   spelling" / "run tu find" / "run tu grep" tips meant for a genuinely
   unknown tool NAME, not a bad parameter value. A real unknown-tool-name
   error is reliably tagged error_details.type == "ToolUnavailableError";
   that's now the discriminator instead of message-text matching.
2. Two other actionable fields were silently dropped from the rendered
   Tips: section: the top-level "suggestion" string some tools use for a
   single redirect hint (e.g. CTD_get_gene_diseases -> OpenTargets), and
   the top-level "detail" dict some BaseRESTTool-backed tools use for
   PostgREST-style upstream error detail (e.g. IEDB's shared query tool).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.cli import _render_run

pytestmark = pytest.mark.unit


def test_tool_http_404_does_not_trigger_tool_not_found_tips():
    result = {
        "status": "error",
        "error": "PDBe API error: 404 Client Error: Not Found for url: https://example/zzzz",
    }

    rendered = _render_run(result)

    assert "Check tool name spelling" not in rendered
    assert "tu find" not in rendered
    assert "tu grep" not in rendered


def test_genuine_tool_unavailable_error_still_triggers_tool_not_found_tips():
    result = {
        "status": "error",
        "error": "Tool 'NonexistentToolXYZ' not found even after loading tools",
        "error_details": {"type": "ToolUnavailableError"},
    }

    rendered = _render_run(result)

    assert "Check tool name spelling" in rendered
    assert "tu find" in rendered
    assert "tu grep" in rendered


def test_top_level_suggestion_field_is_surfaced():
    result = {
        "status": "error",
        "error": "Gene→disease relationships are not available in the RENCI CTD mirror.",
        "suggestion": "Use OpenTargets_get_associated_diseases instead.",
    }

    rendered = _render_run(result)

    assert "Tips:" in rendered
    assert "Use OpenTargets_get_associated_diseases instead." in rendered


def test_top_level_detail_dict_hint_is_surfaced():
    result = {
        "status": "error",
        "error": "HTTP request failed",
        "detail": {
            "code": "42883",
            "hint": "You might need to add explicit type casts.",
            "message": "operator does not exist: character varying[] ~~* unknown",
        },
    }

    rendered = _render_run(result)

    assert "Tips:" in rendered
    assert "You might need to add explicit type casts." in rendered


def test_detail_dict_falls_back_to_message_when_no_hint():
    result = {
        "status": "error",
        "error": "HTTP request failed",
        "detail": {"message": "some upstream error message", "hint": None},
    }

    rendered = _render_run(result)

    assert "some upstream error message" in rendered


def test_plain_string_detail_is_not_shown_twice():
    """Fix (PR #339 review): when `detail` is a plain (non-JSON) string,
    _extract_detail_hint's fallback used to return that exact same string,
    so it was printed once as "Detail: ..." and then again as
    "Upstream detail: ..." -- redundant duplication of the same info."""
    result = {
        "status": "error",
        "error": "Tool X API error",
        "detail": "Not Found: the resource does not exist",
    }

    rendered = _render_run(result)

    assert rendered.count("Not Found: the resource does not exist") == 1
    assert "Detail: Not Found: the resource does not exist" in rendered
    assert "Upstream detail:" not in rendered


def test_json_detail_with_extractable_key_still_shows_both_lines():
    """A JSON-encoded detail that _extract_detail_hint can actually pull a
    more specific sub-field out of is NOT a pure duplicate -- both the raw
    "Detail:" line and the extracted "Upstream detail:" line should still
    appear, since they show genuinely different content."""
    result = {
        "status": "error",
        "error": "SASBDB API error",
        "detail": '{"code": "404", "status": "The Uniprot code p00698 does not exist in the SASBDB"}',
    }

    rendered = _render_run(result)

    assert 'Detail: {"code": "404"' in rendered
    assert (
        "Upstream detail: The Uniprot code p00698 does not exist in the SASBDB"
        in rendered
    )
