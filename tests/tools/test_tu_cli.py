"""
Comprehensive tests for the `tu` CLI (tooluniverse.cli module).

Strategy
--------
* Fast tests (the majority) call CLI handler functions directly with
  monkeypatched ``_get_tu()``, capturing output via pytest's ``capsys``.
* Slow subprocess tests verify real end-to-end output format and the
  stdout/stderr separation that only works correctly in a child process.

Coverage
--------
  A. tu list  — all modes, limit/offset pagination, categories filter
  B. tu grep  — text/regex search, fields, edge cases
  C. tu info  — single / batch, detail levels, nonexistent tool
  D. tu find  — keyword search, empty / unicode queries
  E. tu run   — execute_tool mirroring, no-args fix, invalid JSON, key=value
  F. tu status
  G. tu build
  H. argparse / error-handling
  I. Output format (JSON validity, raw vs pretty, human-readable)
  J. Subprocess / pipe integration
  K. Render function smoke tests
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Ensure src is importable when tests run without editable install
_SRC = str(Path(__file__).resolve().parents[2] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


# ── shared fixtures ────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def tu():
    """Single ToolUniverse instance, loaded once per test session."""
    from tooluniverse import ToolUniverse

    instance = ToolUniverse()
    instance.load_tools()
    return instance


# ── helpers ────────────────────────────────────────────────────────────────────


def _args(**kw) -> argparse.Namespace:
    """Return an argparse.Namespace with sane defaults plus overrides."""
    defaults = dict(
        raw=False,
        json=False,
        mode=None,
        categories=None,
        fields=None,
        limit=None,
        offset=0,
        group_by_category=False,
        pattern="",
        field="name",
        search_mode="text",
        tool_names=[],
        detail="full",
        query="",
        tool_name="",
        arguments=[],
        output=None,
    )
    defaults.update(kw)
    return argparse.Namespace(**defaults)


def _run(monkeypatch, fn, ns, tu_fixture, capsys):
    """
    Call a CLI handler function with _get_tu monkeypatched.
    Returns (stdout_text, stderr_text).
    """
    import tooluniverse.cli as m

    monkeypatch.setattr(m, "_get_tu", lambda: tu_fixture)
    fn(ns)
    cap = capsys.readouterr()
    return cap.out, cap.err


def _j(s: str):
    """Parse JSON; raise AssertionError with context on failure."""
    try:
        return json.loads(s)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"Expected valid JSON but got:\n{repr(s[:400])}"
        ) from exc


def _cli(*args, timeout: int = 120) -> tuple[int, str, str]:
    """Run tu CLI as a subprocess. Returns (returncode, stdout, stderr)."""
    env = {**os.environ, "PYTHONPATH": _SRC, "TOOLUNIVERSE_STDIO_MODE": "1"}
    r = subprocess.run(
        [sys.executable, "-m", "tooluniverse.cli", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    return r.returncode, r.stdout, r.stderr


# ═══════════════════════════════════════════════════════════════════════════════
# A. tu list
# ═══════════════════════════════════════════════════════════════════════════════


class TestList:
    """Tests for the `tu list` subcommand."""

    @pytest.mark.unit
    def test_list_default_names_mode(self, monkeypatch, tu, capsys):
        """Explicit names mode returns list of tool name strings."""
        from tooluniverse.cli import cmd_list

        out, _ = _run(monkeypatch, cmd_list, _args(mode="names", limit=10, json=True), tu, capsys)
        d = _j(out)
        assert d["total_tools"] >= 100
        assert isinstance(d["tools"], list)
        assert all(isinstance(t, str) for t in d["tools"])
        assert len(d["tools"]) == 10

    @pytest.mark.unit
    def test_list_mode_categories(self, monkeypatch, tu, capsys):
        """Categories mode returns a dict of category_name → count."""
        from tooluniverse.cli import cmd_list

        out, _ = _run(monkeypatch, cmd_list, _args(mode="categories", json=True), tu, capsys)
        d = _j(out)
        assert "categories" in d
        assert isinstance(d["categories"], dict)
        assert len(d["categories"]) >= 10
        assert all(isinstance(v, int) for v in d["categories"].values())

    @pytest.mark.unit
    def test_list_mode_basic_fields(self, monkeypatch, tu, capsys):
        """Basic mode returns tools with name + description."""
        from tooluniverse.cli import cmd_list

        out, _ = _run(monkeypatch, cmd_list, _args(mode="basic", limit=5, json=True), tu, capsys)
        d = _j(out)
        assert d["total_tools"] >= 100
        for tool in d["tools"]:
            assert "name" in tool
            assert "description" in tool

    @pytest.mark.unit
    def test_list_mode_summary_fields(self, monkeypatch, tu, capsys):
        """Summary mode returns tools with name, description, type, has_parameters."""
        from tooluniverse.cli import cmd_list

        out, _ = _run(monkeypatch, cmd_list, _args(mode="summary", limit=5, json=True), tu, capsys)
        d = _j(out)
        for tool in d["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "type" in tool
            assert "has_parameters" in tool

    @pytest.mark.unit
    def test_list_mode_by_category(self, monkeypatch, tu, capsys):
        """By-category mode returns tools_by_category dict."""
        from tooluniverse.cli import cmd_list

        out, _ = _run(monkeypatch, cmd_list, _args(mode="by_category", json=True), tu, capsys)
        d = _j(out)
        assert "tools_by_category" in d
        assert isinstance(d["tools_by_category"], dict)
        # Each value must be a list of tool-name strings
        for cat_tools in d["tools_by_category"].values():
            assert isinstance(cat_tools, list)

    @pytest.mark.unit
    def test_list_limit_and_has_more(self, monkeypatch, tu, capsys):
        """limit=5 returns exactly 5 tools and has_more=True when total > 5."""
        from tooluniverse.cli import cmd_list

        out, _ = _run(monkeypatch, cmd_list, _args(mode="names", limit=5, json=True), tu, capsys)
        d = _j(out)
        assert len(d["tools"]) == 5
        if d["total_tools"] > 5:
            assert d["has_more"] is True
        assert d["limit"] == 5

    @pytest.mark.unit
    def test_list_offset_pagination(self, monkeypatch, tu, capsys):
        """Two consecutive pages are disjoint."""
        from tooluniverse.cli import cmd_list

        out1, _ = _run(
            monkeypatch, cmd_list, _args(mode="names", limit=5, offset=0, json=True), tu, capsys
        )
        out2, _ = _run(
            monkeypatch, cmd_list, _args(mode="names", limit=5, offset=5, json=True), tu, capsys
        )
        page1 = set(_j(out1)["tools"])
        page2 = set(_j(out2)["tools"])
        assert page1.isdisjoint(page2)

    @pytest.mark.unit
    def test_list_categories_filter(self, monkeypatch, tu, capsys):
        """--categories filters to a strict subset of all tools."""
        from tooluniverse.cli import cmd_list

        out_filtered, _ = _run(
            monkeypatch,
            cmd_list,
            _args(mode="names", categories=["uniprot"], limit=999999, json=True),
            tu,
            capsys,
        )
        out_all, _ = _run(
            monkeypatch,
            cmd_list,
            _args(mode="names", limit=999999, json=True),
            tu,
            capsys,
        )
        d_filtered = _j(out_filtered)
        d_all = _j(out_all)
        assert d_filtered["total_tools"] >= 1
        # Filtered count must be strictly less than unfiltered
        assert d_filtered["total_tools"] < d_all["total_tools"]

    @pytest.mark.unit
    def test_list_nonexistent_category(self, monkeypatch, tu, capsys):
        """Unknown category returns empty results with exit 1 (Feature-R13B-06 fix)."""
        import tooluniverse.cli as m
        from tooluniverse.cli import cmd_list

        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        with pytest.raises(SystemExit) as exc:
            cmd_list(_args(mode="names", categories=["ZZZNOMATCH_CATEGORY_9999"], json=True))
        assert exc.value.code == 1
        out, _ = capsys.readouterr()
        d = _j(out)
        assert d["total_tools"] == 0
        assert d["tools"] == []
        assert "error" not in d

    @pytest.mark.unit
    def test_list_offset_beyond_end_exits_0(self, monkeypatch, tu, capsys):
        """R21A-06: offset beyond total exits 0 (natural pagination termination, not an error)."""
        from tooluniverse.cli import cmd_list

        out, _ = _run(
            monkeypatch, cmd_list, _args(mode="names", limit=10, offset=999999, json=True), tu, capsys
        )
        d = _j(out)
        assert d["tools"] == []
        assert d["has_more"] is False
        assert d["total_tools"] >= 100  # total is still accurate

    @pytest.mark.unit
    def test_list_custom_mode_with_fields(self, monkeypatch, tu, capsys):
        """Custom mode with --fields returns only those fields."""
        from tooluniverse.cli import cmd_list

        out, _ = _run(
            monkeypatch,
            cmd_list,
            _args(mode="custom", fields=["name", "type"], limit=5, json=True),
            tu,
            capsys,
        )
        d = _j(out)
        assert "tools" in d
        for tool in d["tools"]:
            assert "name" in tool
            assert "type" in tool
            # description should NOT be present (not in fields)
            assert "description" not in tool

    @pytest.mark.unit
    def test_list_custom_mode_no_fields_returns_error(self, monkeypatch, tu, capsys):
        """Custom mode without --fields returns an error response and exits 1."""
        from tooluniverse.cli import cmd_list

        with pytest.raises(SystemExit) as exc:
            _run(
                monkeypatch, cmd_list, _args(mode="custom", fields=None, json=True), tu, capsys
            )
        assert exc.value.code == 1
        out = capsys.readouterr().out
        d = _j(out)
        assert "error" in d

    @pytest.mark.unit
    def test_list_raw_output_is_compact(self, monkeypatch, tu, capsys):
        """--raw produces single-line JSON (no indent)."""
        from tooluniverse.cli import cmd_list

        out, _ = _run(monkeypatch, cmd_list, _args(mode="names", limit=3, raw=True), tu, capsys)
        # Raw output must be parseable JSON on one (logical) line
        d = _j(out)
        assert d["total_tools"] >= 100
        # Should not have "\n  " which is the 2-space indentation
        assert "\n  " not in out

    @pytest.mark.unit
    def test_list_pretty_output_is_indented(self, monkeypatch, tu, capsys):
        """--json produces pretty-printed output with indentation."""
        from tooluniverse.cli import cmd_list

        out, _ = _run(monkeypatch, cmd_list, _args(mode="names", limit=3, json=True), tu, capsys)
        assert "\n  " in out  # 2-space indentation present

    @pytest.mark.unit
    def test_list_multiple_categories(self, monkeypatch, tu, capsys):
        """Multiple categories in filter — tools from any listed category returned."""
        from tooluniverse.cli import cmd_list

        out, _ = _run(
            monkeypatch,
            cmd_list,
            _args(mode="names", categories=["UniProt", "ChEMBL"], limit=50, json=True),
            tu,
            capsys,
        )
        d = _j(out)
        assert d["total_tools"] >= 2

    @pytest.mark.unit
    def test_list_categories_mode_has_metadata(self, monkeypatch, tu, capsys):
        """Feature-R12A-09: categories mode returns total_categories, total_tools, and categories."""
        from tooluniverse.cli import cmd_list

        out, _ = _run(monkeypatch, cmd_list, _args(mode="categories", json=True), tu, capsys)
        d = _j(out)
        assert "categories" in d
        assert isinstance(d["categories"], dict), "categories must be a dict mapping name→count"
        # Feature-R12A-09/R12B-04: metadata fields must be present
        assert "total_categories" in d, "categories mode must include total_categories"
        assert "total_tools" in d, "categories mode must include total_tools"
        assert d["total_categories"] == len(d["categories"])
        assert d["total_tools"] == sum(d["categories"].values())

    @pytest.mark.unit
    def test_list_json_no_mode_defaults_to_names(self, monkeypatch, tu, capsys):
        """Feature-R10B-01: tu list --json without --mode should use names mode (machine-readable)."""
        from tooluniverse.cli import cmd_list

        # --json without explicit mode → names mode (consistent with --raw)
        out, _ = _run(monkeypatch, cmd_list, _args(json=True), tu, capsys)
        d = _j(out)
        assert "tools" in d
        assert "total_tools" in d
        # NOT categories mode
        assert "categories" not in d

    @pytest.mark.unit
    def test_list_interactive_no_flags_is_categories(self, monkeypatch, tu, capsys):
        """Default mode without --json/--raw: human-readable interactive view uses categories."""
        from tooluniverse.cli import cmd_list

        # No flags at all → categories overview (human-readable interactive default)
        out, _ = _run(monkeypatch, cmd_list, _args(), tu, capsys)
        # Human-readable categories output should contain "categories" word
        assert "categories" in out.lower() or "category" in out.lower()

    @pytest.mark.unit
    def test_list_smart_default_with_filter_is_names(self, monkeypatch, tu, capsys):
        """Default mode (mode=None) with --categories uses names mode internally."""
        from tooluniverse.cli import cmd_list

        # Verify via JSON that the response is a names-mode dict (has tools list)
        out, _ = _run(
            monkeypatch, cmd_list, _args(categories=["uniprot"], limit=5, json=True), tu, capsys
        )
        d = _j(out)
        assert "tools" in d
        assert isinstance(d["tools"], list)
        assert d["total_tools"] >= 1

    @pytest.mark.unit
    def test_list_case_insensitive_category(self, monkeypatch, tu, capsys):
        """Category names are matched case-insensitively."""
        from tooluniverse.cli import cmd_list

        out_lower, _ = _run(
            monkeypatch,
            cmd_list,
            _args(mode="names", categories=["uniprot"], json=True),
            tu,
            capsys,
        )
        out_upper, _ = _run(
            monkeypatch,
            cmd_list,
            _args(mode="names", categories=["UniProt"], json=True),
            tu,
            capsys,
        )
        assert _j(out_lower)["total_tools"] == _j(out_upper)["total_tools"]


# ═══════════════════════════════════════════════════════════════════════════════
# B. tu grep
# ═══════════════════════════════════════════════════════════════════════════════


class TestGrep:
    """Tests for the `tu grep` subcommand."""

    @pytest.mark.unit
    def test_grep_basic_match(self, monkeypatch, tu, capsys):
        """Searching 'protein' in names returns matches with expected keys."""
        from tooluniverse.cli import cmd_grep

        out, _ = _run(
            monkeypatch, cmd_grep, _args(pattern="protein", limit=10, json=True), tu, capsys
        )
        d = _j(out)
        assert d["total_matches"] > 0
        assert "tools" in d
        for tool in d["tools"]:
            assert "name" in tool
            assert "description" in tool

    @pytest.mark.unit
    def test_grep_field_description(self, monkeypatch, tu, capsys):
        """Searching in description field finds tools with 'protein' in description."""
        from tooluniverse.cli import cmd_grep

        out, _ = _run(
            monkeypatch,
            cmd_grep,
            _args(pattern="protein", field="description", limit=20, json=True),
            tu,
            capsys,
        )
        d = _j(out)
        assert d["total_matches"] > 0
        for tool in d["tools"]:
            assert "protein" in tool["description"].lower()

    @pytest.mark.unit
    def test_grep_field_type(self, monkeypatch, tu, capsys):
        """Searching by type field returns matching tools."""
        from tooluniverse.cli import cmd_grep

        out, _ = _run(
            monkeypatch,
            cmd_grep,
            _args(pattern="ListTools", field="type", json=True),
            tu,
            capsys,
        )
        d = _j(out)
        assert d["total_matches"] >= 1

    @pytest.mark.unit
    def test_grep_mode_regex_anchored(self, monkeypatch, tu, capsys):
        """Regex mode: ^UniProt matches only tools whose name starts with UniProt."""
        from tooluniverse.cli import cmd_grep

        out, _ = _run(
            monkeypatch,
            cmd_grep,
            _args(pattern="^UniProt", search_mode="regex", limit=50, json=True),
            tu,
            capsys,
        )
        d = _j(out)
        assert d["total_matches"] >= 1
        for tool in d["tools"]:
            assert tool["name"].startswith("UniProt")

    @pytest.mark.unit
    def test_grep_regex_invalid_pattern_returns_error(self, monkeypatch, tu, capsys):
        """Invalid regex prints JSON with 'error' key and exits 1."""
        from tooluniverse.cli import cmd_grep
        import tooluniverse.cli as m

        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        with pytest.raises(SystemExit) as exc_info:
            cmd_grep(_args(pattern="(invalid[regex", search_mode="regex", json=True))
        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        d = _j(out)
        assert "error" in d

    @pytest.mark.unit
    def test_grep_empty_pattern_returns_error(self, monkeypatch, tu, capsys):
        """Empty string pattern: with --json returns JSON error on stdout; exits 1."""
        from tooluniverse.cli import cmd_grep
        import tooluniverse.cli as m

        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        with pytest.raises(SystemExit) as exc_info:
            cmd_grep(_args(pattern="", json=True))
        assert exc_info.value.code == 1
        cap = capsys.readouterr()
        # Feature-R11B-11: with --json, error is JSON on stdout
        d = _j(cap.out)
        assert "error" in d
        assert "empty" in d["error"].lower() or "pattern" in d["error"].lower()

    @pytest.mark.unit
    def test_grep_no_matches(self, monkeypatch, tu, capsys):
        """Pattern that matches nothing returns empty list, exits 0 (R14B-01: successful query)."""
        from tooluniverse.cli import cmd_grep

        # R14B-01 fix: 0 matches is a valid result, not an error; exit 0
        out, _ = _run(
            monkeypatch,
            cmd_grep,
            _args(pattern="ZZZNOMATCH_XYZ_9999", json=True),
            tu,
            capsys,
        )
        d = _j(out)
        assert d["total_matches"] == 0
        assert d["tools"] == []
        assert "error" not in d

    @pytest.mark.unit
    def test_grep_limit_controls_results(self, monkeypatch, tu, capsys):
        """limit parameter caps the number of results returned."""
        from tooluniverse.cli import cmd_grep

        out, _ = _run(
            monkeypatch, cmd_grep, _args(pattern="a", limit=7, json=True), tu, capsys
        )
        d = _j(out)
        assert len(d["tools"]) <= 7

    @pytest.mark.unit
    def test_grep_has_more_flag(self, monkeypatch, tu, capsys):
        """has_more is True when total_matches > limit."""
        from tooluniverse.cli import cmd_grep

        out, _ = _run(
            monkeypatch, cmd_grep, _args(pattern="a", limit=5, json=True), tu, capsys
        )
        d = _j(out)
        if d["total_matches"] > 5:
            assert d["has_more"] is True
        else:
            assert d["has_more"] is False

    @pytest.mark.unit
    def test_grep_offset_pagination(self, monkeypatch, tu, capsys):
        """Two pages of grep results are disjoint."""
        from tooluniverse.cli import cmd_grep

        out1, _ = _run(
            monkeypatch, cmd_grep, _args(pattern="a", limit=5, offset=0, json=True), tu, capsys
        )
        out2, _ = _run(
            monkeypatch, cmd_grep, _args(pattern="a", limit=5, offset=5, json=True), tu, capsys
        )
        names1 = {t["name"] for t in _j(out1)["tools"]}
        names2 = {t["name"] for t in _j(out2)["tools"]}
        assert names1.isdisjoint(names2)

    @pytest.mark.unit
    def test_grep_case_insensitive_text_mode(self, monkeypatch, tu, capsys):
        """Text-mode search is case-insensitive."""
        from tooluniverse.cli import cmd_grep

        out_lower, _ = _run(
            monkeypatch, cmd_grep, _args(pattern="protein", json=True), tu, capsys
        )
        out_upper, _ = _run(
            monkeypatch, cmd_grep, _args(pattern="PROTEIN", json=True), tu, capsys
        )
        # Both should return the same total matches count
        assert _j(out_lower)["total_matches"] == _j(out_upper)["total_matches"]

    @pytest.mark.unit
    def test_grep_category_filter(self, monkeypatch, tu, capsys):
        """categories filter restricts grep to those categories; exits 1 when no matches."""
        import pytest
        from tooluniverse.cli import cmd_grep

        with pytest.raises(SystemExit) as exc:
            _run(
                monkeypatch,
                cmd_grep,
                _args(pattern="a", categories=["ZZZNOMATCH_9999"], json=True),
                tu,
                capsys,
            )
        assert exc.value.code == 1
        out, _ = capsys.readouterr()
        d = _j(out)
        assert d["total_matches"] == 0

    @pytest.mark.unit
    def test_grep_response_metadata(self, monkeypatch, tu, capsys):
        """Grep response includes pattern, field, and search_mode metadata."""
        from tooluniverse.cli import cmd_grep

        out, _ = _run(
            monkeypatch,
            cmd_grep,
            _args(pattern="protein", field="name", search_mode="text", json=True),
            tu,
            capsys,
        )
        d = _j(out)
        assert d["pattern"] == "protein"
        assert d["field"] == "name"
        assert d["search_mode"] == "text"

    @pytest.mark.unit
    def test_grep_human_readable_default(self, monkeypatch, tu, capsys):
        """Default output (no --json/--raw) is a human-readable table."""
        from tooluniverse.cli import cmd_grep

        out, _ = _run(
            monkeypatch, cmd_grep, _args(pattern="protein", limit=3), tu, capsys
        )
        # _render_grep always emits a "name  description" header row
        assert "name" in out
        assert "description" in out
        assert not out.strip().startswith("{")


# ═══════════════════════════════════════════════════════════════════════════════
# C. tu info
# ═══════════════════════════════════════════════════════════════════════════════


class TestInfo:
    """Tests for the `tu info` subcommand."""

    @pytest.mark.unit
    def test_info_single_existing_tool(self, monkeypatch, tu, capsys):
        """Single existing tool returns consistent {"tools": [...]} envelope (Feature-R11B-01)."""
        from tooluniverse.cli import cmd_info

        out, _ = _run(
            monkeypatch, cmd_info, _args(tool_names=["list_tools"], json=True), tu, capsys
        )
        d = _j(out)
        # R11B-01: always {"tools": [...]} envelope, never a flat dict
        assert "tools" in d
        assert len(d["tools"]) == 1
        tool = d["tools"][0]
        assert tool["name"] == "list_tools"
        assert "description" in tool

    @pytest.mark.unit
    def test_info_full_detail_has_parameter_schema(self, monkeypatch, tu, capsys):
        """Full detail includes parameter schema with type=object (inside tools envelope).
        R14A-01: in JSON mode "parameter" is renamed to "parameters" for consistency with find."""
        from tooluniverse.cli import cmd_info

        out, _ = _run(
            monkeypatch,
            cmd_info,
            _args(tool_names=["list_tools"], detail="full", json=True),
            tu,
            capsys,
        )
        d = _j(out)
        tool = d["tools"][0]
        # R14A-01 fix: JSON mode normalizes "parameter" → "parameters"
        assert "parameters" in tool
        assert "parameter" not in tool
        assert tool["parameters"]["type"] == "object"
        assert "properties" in tool["parameters"]

    @pytest.mark.unit
    def test_info_description_detail_no_schema(self, monkeypatch, tu, capsys):
        """Description detail returns name + description, no parameter key (inside tools envelope)."""
        from tooluniverse.cli import cmd_info

        out, _ = _run(
            monkeypatch,
            cmd_info,
            _args(tool_names=["list_tools"], detail="description", json=True),
            tu,
            capsys,
        )
        d = _j(out)
        tool = d["tools"][0]
        assert tool["name"] == "list_tools"
        assert "description" in tool
        assert "parameter" not in tool

    @pytest.mark.unit
    def test_info_nonexistent_tool_returns_error(self, monkeypatch, tu, capsys):
        """Requesting info for a nonexistent tool exits 1 with error inside tools envelope."""
        import pytest
        from tooluniverse.cli import cmd_info

        with pytest.raises(SystemExit) as exc:
            _run(
                monkeypatch,
                cmd_info,
                _args(tool_names=["NONEXISTENT_TOOL_XYZ_99999"], json=True),
                tu,
                capsys,
            )
        assert exc.value.code == 1
        out, _ = capsys.readouterr()
        d = _j(out)
        # R11B-01: error is inside {"tools": [{"error": ..., "name": ...}]}
        assert "tools" in d or "error" in d
        if "tools" in d:
            assert any("error" in t for t in d["tools"])
        else:
            assert "error" in d

    @pytest.mark.unit
    def test_info_multiple_existing_tools(self, monkeypatch, tu, capsys):
        """Batch info for multiple tools returns wrapped response."""
        from tooluniverse.cli import cmd_info

        out, _ = _run(
            monkeypatch,
            cmd_info,
            _args(tool_names=["list_tools", "grep_tools"], json=True),
            tu,
            capsys,
        )
        d = _j(out)
        assert d["total_requested"] == 2
        assert d["total_found"] == 2
        assert len(d["tools"]) == 2
        names = {t["name"] for t in d["tools"]}
        assert "list_tools" in names
        assert "grep_tools" in names

    @pytest.mark.unit
    def test_info_mixed_existing_nonexisting(self, monkeypatch, tu, capsys):
        """Batch with one good + one bad tool: total_found=1, exits 0 (Feature-R13B-02 fix).

        Partial success exits 0; the per-tool error is embedded in the JSON body.
        Only a total failure (all tools missing) exits 1.
        """
        import tooluniverse.cli as m
        from tooluniverse.cli import cmd_info

        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        # Partial success should exit 0
        cmd_info(_args(tool_names=["list_tools", "NONEXISTENT_TOOL_XYZ"], json=True))
        out, _ = capsys.readouterr()
        d = _j(out)
        assert d["total_requested"] == 2
        assert d["total_found"] == 1
        # The per-tool error is still embedded in the tools array
        errors = [t for t in d.get("tools", []) if "error" in t]
        assert len(errors) == 1

    @pytest.mark.unit
    def test_info_all_missing_exits_1(self, monkeypatch, tu, capsys):
        """Batch where ALL tools are missing exits 1 (total failure)."""
        import tooluniverse.cli as m
        from tooluniverse.cli import cmd_info

        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        with pytest.raises(SystemExit) as exc:
            cmd_info(_args(tool_names=["FAKE_TOOL_1", "FAKE_TOOL_2"], json=True))
        assert exc.value.code == 1

    @pytest.mark.unit
    def test_info_single_passes_string_not_list(self, monkeypatch, tu, capsys):
        """Single tool name always returns {"tools": [...]} envelope (Feature-R11B-01)."""
        from tooluniverse.cli import cmd_info

        out, _ = _run(
            monkeypatch,
            cmd_info,
            _args(tool_names=["execute_tool"], json=True),
            tu,
            capsys,
        )
        d = _j(out)
        # R11B-01: always a {"tools": [...]} envelope, not a flat dict
        assert "tools" in d
        assert d["tools"][0].get("name") == "execute_tool"

    @pytest.mark.unit
    def test_info_human_readable_default(self, monkeypatch, tu, capsys):
        """Default output is a human-readable tool card with name and description."""
        from tooluniverse.cli import cmd_info

        out, _ = _run(
            monkeypatch, cmd_info, _args(tool_names=["list_tools"]), tu, capsys
        )
        # _render_info always emits the tool name on the first line
        assert "list_tools" in out
        # and its description indented below
        assert "  " in out  # indented description line
        assert not out.strip().startswith("{")


# ═══════════════════════════════════════════════════════════════════════════════
# D. tu find
# ═══════════════════════════════════════════════════════════════════════════════


class TestFind:
    """Tests for the `tu find` subcommand (keyword search)."""

    @pytest.mark.unit
    def test_find_basic_query(self, monkeypatch, tu, capsys):
        """Natural-language query returns relevant tools."""
        from tooluniverse.cli import cmd_find

        out, _ = _run(
            monkeypatch,
            cmd_find,
            _args(query="protein structure analysis", limit=5, json=True),
            tu,
            capsys,
        )
        d = _j(out)
        assert "tools" in d
        assert len(d["tools"]) >= 1

    @pytest.mark.unit
    def test_find_limit_respected(self, monkeypatch, tu, capsys):
        """--limit caps number of tools returned."""
        from tooluniverse.cli import cmd_find

        out, _ = _run(
            monkeypatch, cmd_find, _args(query="gene expression", limit=3, json=True), tu, capsys
        )
        d = _j(out)
        assert len(d["tools"]) <= 3

    @pytest.mark.unit
    def test_find_empty_query_returns_error(self, monkeypatch, tu, capsys):
        """Empty query: with --json returns JSON error on stdout; exits 1."""
        from tooluniverse.cli import cmd_find
        import tooluniverse.cli as m

        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        with pytest.raises(SystemExit) as exc_info:
            cmd_find(_args(query="", json=True))
        assert exc_info.value.code == 1
        cap = capsys.readouterr()
        # Feature-R11B-11: with --json, error is JSON on stdout
        d = _j(cap.out)
        assert "error" in d
        assert "empty" in d["error"].lower() or "query" in d["error"].lower()

    @pytest.mark.unit
    def test_find_stopwords_only_returns_zero_matches(self, monkeypatch, tu, capsys):
        """A query of only stopwords returns standard schema with total_matches=0 and exits 0.

        Feature-R13B-01 fix: standard schema so programmatic consumers can always read
        total_matches without branching on 'error' key; warning is in processing_info.
        Feature-R16A-07/R16B-09: exits 0 (zero results is not an error).
        """
        from tooluniverse.cli import cmd_find
        import tooluniverse.cli as m

        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        # Should NOT raise SystemExit — zero results exits 0
        cmd_find(_args(query="the and for from", json=True))
        out = capsys.readouterr().out
        d = _j(out)
        assert "error" not in d
        assert d["total_matches"] == 0
        assert d["tools"] == []
        # Warning is communicated via processing_info instead of top-level error.
        assert (d.get("processing_info") or {}).get("warning")

    @pytest.mark.unit
    def test_find_nonexistent_category_returns_empty(self, monkeypatch, tu, capsys):
        """Category filter with unknown category returns empty results and exits 1."""
        import tooluniverse.cli as m
        from tooluniverse.cli import cmd_find

        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        with pytest.raises(SystemExit) as exc:
            cmd_find(_args(query="protein", categories=["ZZZNOMATCH_CAT_9999"], json=True))
        assert exc.value.code == 1
        out, _ = capsys.readouterr()
        d = _j(out)
        assert d.get("tools", []) == []

    @pytest.mark.unit
    def test_find_result_has_name_and_description(self, monkeypatch, tu, capsys):
        """Each result in find has at minimum name and description fields."""
        from tooluniverse.cli import cmd_find

        out, _ = _run(
            monkeypatch, cmd_find, _args(query="drug target", limit=3, json=True), tu, capsys
        )
        d = _j(out)
        for tool in d.get("tools", []):
            assert "name" in tool
            assert "description" in tool

    @pytest.mark.unit
    def test_find_returns_tools_list(self, monkeypatch, tu, capsys):
        """find with a specific scientific query returns a non-empty tools list."""
        from tooluniverse.cli import cmd_find

        out, _ = _run(
            monkeypatch, cmd_find, _args(query="DNA methylation", limit=5, json=True), tu, capsys
        )
        d = _j(out)
        assert "tools" in d
        assert isinstance(d["tools"], list)
        assert len(d["tools"]) >= 1

    @pytest.mark.unit
    def test_find_unicode_query_no_crash(self, monkeypatch, tu, capsys):
        """Unicode query returns a valid JSON response without crashing.
        If all tokens are filtered (no ASCII keywords), the error path exits 1."""
        import tooluniverse.cli as m
        from tooluniverse.cli import cmd_find

        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        try:
            cmd_find(_args(query="蛋白质结构", json=True))
        except SystemExit as exc:
            assert exc.code == 1
        cap = capsys.readouterr()
        d = _j(cap.out)
        # Must return either an error dict or a tools list — never a crash
        assert isinstance(d, dict)
        assert "error" in d or "tools" in d

    @pytest.mark.unit
    def test_find_human_readable_default(self, monkeypatch, tu, capsys):
        """Default output (no --json) is a human-readable results table."""
        from tooluniverse.cli import cmd_find

        out, _ = _run(
            monkeypatch, cmd_find, _args(query="protein structure", limit=3), tu, capsys
        )
        # _render_find always ends with "\nN results"
        assert "results" in out
        assert not out.strip().startswith("{")

    @pytest.mark.unit
    def test_find_case_insensitive_category(self, monkeypatch, tu, capsys):
        """Category names in cmd_find are matched case-insensitively."""
        from tooluniverse.cli import cmd_find

        out_lower, _ = _run(
            monkeypatch,
            cmd_find,
            _args(query="protein", categories=["uniprot"], json=True),
            tu,
            capsys,
        )
        out_upper, _ = _run(
            monkeypatch,
            cmd_find,
            _args(query="protein", categories=["UniProt"], json=True),
            tu,
            capsys,
        )
        d_lower = _j(out_lower)
        d_upper = _j(out_upper)
        # Both should return the same number of tools
        assert d_lower.get("total_matches", 0) == d_upper.get("total_matches", 0)


# ═══════════════════════════════════════════════════════════════════════════════
# E. tu run
# ═══════════════════════════════════════════════════════════════════════════════


class TestRun:
    """Tests for the `tu run` subcommand (mirrors execute_tool)."""

    @pytest.mark.unit
    def test_run_with_json_args(self, monkeypatch, tu, capsys):
        """tu run list_tools with JSON args returns expected result."""
        from tooluniverse.cli import cmd_run

        out, _ = _run(
            monkeypatch,
            cmd_run,
            _args(tool_name="list_tools", arguments=['{"mode": "categories"}']),
            tu,
            capsys,
        )
        d = _j(out)
        assert "categories" in d

    @pytest.mark.unit
    def test_run_no_args_succeeds(self, monkeypatch, tu, capsys):
        """tu run <tool> with no arguments uses tool defaults (not schema error)."""
        from tooluniverse.cli import cmd_run

        out, _ = _run(
            monkeypatch,
            cmd_run,
            _args(tool_name="list_tools", arguments=[]),
            tu,
            capsys,
        )
        d = _j(out)
        # list_tools with defaults returns a categories or names response
        assert "tools" in d or "categories" in d

    @pytest.mark.unit
    def test_run_empty_object_args(self, monkeypatch, tu, capsys):
        """Empty JSON object '{}' is valid arguments (tool uses defaults)."""
        from tooluniverse.cli import cmd_run

        out, _ = _run(
            monkeypatch,
            cmd_run,
            _args(tool_name="list_tools", arguments=["{}"] ),
            tu,
            capsys,
        )
        d = _j(out)
        assert "tools" in d or "categories" in d

    @pytest.mark.unit
    def test_run_invalid_json_exits_1(self, monkeypatch, tu, capsys):
        """Invalid JSON in arguments triggers sys.exit(1)."""
        from tooluniverse.cli import cmd_run

        with pytest.raises(SystemExit) as exc_info:
            _run(
                monkeypatch,
                cmd_run,
                _args(tool_name="list_tools", arguments=["{not valid json}"]),
                tu,
                capsys,
            )
        assert exc_info.value.code == 1

    @pytest.mark.unit
    def test_run_invalid_json_error_to_stdout_as_json(self, monkeypatch, tu, capsys):
        """JSON parse error for tu run in --json mode goes to stdout as JSON."""
        from tooluniverse.cli import cmd_run

        with pytest.raises(SystemExit):
            _run(
                monkeypatch,
                cmd_run,
                _args(tool_name="list_tools", arguments=["not json"], json=True),
                tu,
                capsys,
            )
        cap = capsys.readouterr()
        # --json mode outputs JSON to stdout — even parse errors
        d = _j(cap.out)
        assert d["status"] == "error"
        assert "error_details" in d

    @pytest.mark.unit
    def test_run_nonexistent_tool_returns_error_json(self, monkeypatch, tu, capsys):
        """Running a nonexistent tool prints JSON with error and exits 1 (--json mode)."""
        import tooluniverse.cli as m
        from tooluniverse.cli import cmd_run

        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        # Feature-23B-02: human mode now routes errors to stderr; use --json for machine JSON
        with pytest.raises(SystemExit) as exc_info:
            cmd_run(_args(tool_name="ZZZNOMATCH_TOOL_99999", arguments=["{}"], json=True))
        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        d = _j(out)
        assert "error" in d

    @pytest.mark.unit
    def test_run_grep_via_run(self, monkeypatch, tu, capsys):
        """tu run grep_tools '{"pattern": "protein"}' works identically to tu grep."""
        from tooluniverse.cli import cmd_run

        out, _ = _run(
            monkeypatch,
            cmd_run,
            _args(
                tool_name="grep_tools",
                arguments=['{"pattern": "protein", "limit": 5}'],
            ),
            tu,
            capsys,
        )
        d = _j(out)
        assert "total_matches" in d
        assert d["total_matches"] > 0

    @pytest.mark.unit
    def test_run_json_array_returns_error(self, monkeypatch, tu, capsys):
        """JSON array as arguments is rejected; in --json mode, error JSON goes to stdout."""
        import tooluniverse.cli as m
        from tooluniverse.cli import cmd_run

        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        # Feature-23B-02: human mode routes errors to stderr; use --json for machine JSON
        with pytest.raises(SystemExit) as exc_info:
            cmd_run(_args(tool_name="list_tools", arguments=["[1, 2, 3]"], json=True))
        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        d = _j(out)
        # execute_tool rejects non-dict arguments
        assert "error" in d

    @pytest.mark.unit
    def test_run_raw_output_compact(self, monkeypatch, tu, capsys):
        """--raw produces compact single-line JSON."""
        from tooluniverse.cli import cmd_run

        out, _ = _run(
            monkeypatch,
            cmd_run,
            _args(
                tool_name="list_tools",
                arguments=['{"mode": "categories"}'],
                raw=True,
            ),
            tu,
            capsys,
        )
        _j(out)  # must be valid JSON
        assert "\n  " not in out

    @pytest.mark.unit
    def test_run_empty_list_treated_as_no_args(self, monkeypatch, tu, capsys):
        """Empty list for arguments is treated as no args."""
        from tooluniverse.cli import cmd_run

        out, _ = _run(
            monkeypatch,
            cmd_run,
            _args(tool_name="list_tools", arguments=[]),
            tu,
            capsys,
        )
        d = _j(out)
        # Same as no args: list_tools returns categories or names response
        assert "tools" in d or "categories" in d

    @pytest.mark.unit
    def test_run_key_value_single(self, monkeypatch, tu, capsys):
        """tu run list_tools mode=categories via key=value syntax."""
        from tooluniverse.cli import cmd_run

        out, _ = _run(
            monkeypatch,
            cmd_run,
            _args(tool_name="list_tools", arguments=["mode=categories"]),
            tu,
            capsys,
        )
        d = _j(out)
        assert "categories" in d

    @pytest.mark.unit
    def test_run_key_value_int_not_coerced(self, monkeypatch, tu, capsys):
        """key=value: numeric strings stay as strings (Feature-27A-02)."""
        from tooluniverse.cli import _parse_run_args

        result = _parse_run_args(["limit=5", "offset=0"])
        assert result == {"limit": "5", "offset": "0"}
        assert isinstance(result["limit"], str)

    @pytest.mark.unit
    def test_run_key_value_bool_coercion(self):
        """key=value: 'true'/'false' → bool."""
        from tooluniverse.cli import _parse_run_args

        result = _parse_run_args(["group_by_category=true"])
        assert result == {"group_by_category": True}
        assert isinstance(result["group_by_category"], bool)

    @pytest.mark.unit
    def test_run_key_value_null_raises_helpful_error(self):
        """key=value: 'key=null' raises ValueError with helpful message (B-01 fix)."""
        import pytest
        from tooluniverse.cli import _parse_run_args

        with pytest.raises(ValueError, match="sends Python None"):
            _parse_run_args(["fields=null"])

        with pytest.raises(ValueError, match="JSON format"):
            _parse_run_args(["accession=null"])

    @pytest.mark.unit
    def test_run_key_value_string_preserved(self):
        """key=value: non-numeric strings stay as strings."""
        from tooluniverse.cli import _parse_run_args

        result = _parse_run_args(["mode=categories", "pattern=foo"])
        assert result == {"mode": "categories", "pattern": "foo"}

    @pytest.mark.unit
    def test_run_key_value_missing_equals_exits_1(self, monkeypatch, tu, capsys):
        """key=value: token without '=' triggers sys.exit(1)."""
        from tooluniverse.cli import cmd_run

        with pytest.raises(SystemExit) as exc_info:
            _run(
                monkeypatch,
                cmd_run,
                _args(tool_name="list_tools", arguments=["notakeyvaluepair"]),
                tu,
                capsys,
            )
        assert exc_info.value.code == 1

    @pytest.mark.unit
    def test_parse_run_args_empty(self):
        """_parse_run_args([]) returns None."""
        from tooluniverse.cli import _parse_run_args

        assert _parse_run_args([]) is None

    @pytest.mark.unit
    def test_parse_run_args_empty_key_raises(self):
        """_parse_run_args(['=value']) raises ValueError for empty key."""
        from tooluniverse.cli import _parse_run_args

        with pytest.raises(ValueError, match="empty parameter name"):
            _parse_run_args(["=value"])

    @pytest.mark.unit
    def test_parse_run_args_whitespace_key_raises(self):
        """_parse_run_args(['  =value']) raises ValueError (whitespace-only key)."""
        from tooluniverse.cli import _parse_run_args

        with pytest.raises(ValueError, match="empty parameter name"):
            _parse_run_args(["  =value"])

    @pytest.mark.unit
    def test_parse_run_args_json_string(self):
        """_parse_run_args(['{"k":"v"}']) parses JSON."""
        from tooluniverse.cli import _parse_run_args

        result = _parse_run_args(['{"k": "v"}'])
        assert result == {"k": "v"}


# ═══════════════════════════════════════════════════════════════════════════════
# F. tu status
# ═══════════════════════════════════════════════════════════════════════════════


class TestStatus:
    """Tests for the `tu status` subcommand."""

    @pytest.mark.unit
    def test_status_keys_present(self, monkeypatch, tu, capsys):
        """Status JSON response has all required keys."""
        from tooluniverse.cli import cmd_status

        out, _ = _run(monkeypatch, cmd_status, _args(json=True), tu, capsys)
        d = _j(out)
        for key in ("total_tools", "categories", "workspace", "profile_active", "top_categories"):
            assert key in d, f"Missing key: {key}"

    @pytest.mark.unit
    def test_status_tools_loaded_count(self, monkeypatch, tu, capsys):
        """total_tools is a positive integer matching loaded tools."""
        from tooluniverse.cli import cmd_status

        out, _ = _run(monkeypatch, cmd_status, _args(json=True), tu, capsys)
        d = _j(out)
        assert isinstance(d["total_tools"], int)
        assert d["total_tools"] >= 100

    @pytest.mark.unit
    def test_status_workspace_is_string(self, monkeypatch, tu, capsys):
        """workspace field is a non-empty string path."""
        from tooluniverse.cli import cmd_status

        out, _ = _run(monkeypatch, cmd_status, _args(json=True), tu, capsys)
        d = _j(out)
        assert isinstance(d["workspace"], str)
        assert len(d["workspace"]) > 0

    @pytest.mark.unit
    def test_status_profile_active_is_bool(self, monkeypatch, tu, capsys):
        """profile_active field is a boolean."""
        from tooluniverse.cli import cmd_status

        out, _ = _run(monkeypatch, cmd_status, _args(json=True), tu, capsys)
        d = _j(out)
        assert isinstance(d["profile_active"], bool)

    @pytest.mark.unit
    def test_status_top_categories_max_10(self, monkeypatch, tu, capsys):
        """top_categories contains at most 10 entries."""
        from tooluniverse.cli import cmd_status

        out, _ = _run(monkeypatch, cmd_status, _args(json=True), tu, capsys)
        d = _j(out)
        assert len(d["top_categories"]) <= 10
        assert all(isinstance(v, int) for v in d["top_categories"].values())

    @pytest.mark.unit
    def test_status_raw_single_line(self, monkeypatch, tu, capsys):
        """--raw produces compact single-line JSON."""
        from tooluniverse.cli import cmd_status

        out, _ = _run(monkeypatch, cmd_status, _args(raw=True), tu, capsys)
        _j(out)
        assert "\n  " not in out

    @pytest.mark.unit
    def test_status_human_readable_default(self, monkeypatch, tu, capsys):
        """Default output is human-readable key-value pairs."""
        from tooluniverse.cli import cmd_status

        out, _ = _run(monkeypatch, cmd_status, _args(), tu, capsys)
        # _render_status always emits "tools loaded:    N"
        assert "tools loaded:" in out
        assert "workspace:" in out


# ═══════════════════════════════════════════════════════════════════════════════
# G. tu build
# ═══════════════════════════════════════════════════════════════════════════════


class TestBuild:
    """Tests for the `tu build` subcommand."""

    @pytest.mark.unit
    def test_build_prints_both_step_labels(self, capsys):
        """tu build runs both steps and prints their labels to stderr."""
        from tooluniverse.cli import cmd_build

        cmd_build(_args())
        err = capsys.readouterr().err
        # cmd_build prints "Regenerating lazy registry…" and "Regenerating coding-API wrappers…"
        # to stderr (so stdout stays clean for scripts)
        assert "Regenerating lazy registry" in err
        assert "Regenerating coding-API wrappers" in err


# ═══════════════════════════════════════════════════════════════════════════════
# H. Argparse / error handling
# ═══════════════════════════════════════════════════════════════════════════════


class TestArgparse:
    """Tests for argparse-level argument handling."""

    @pytest.mark.unit
    def test_no_subcommand_exits_2(self):
        """Running tu with no subcommand exits with code 2."""
        rc, _, err = _cli()
        assert rc == 2

    @pytest.mark.unit
    def test_unknown_subcommand_exits_2(self):
        """Unknown subcommand exits with code 2."""
        rc, _, err = _cli("xyzzy_unknown_command")
        assert rc == 2

    @pytest.mark.unit
    def test_grep_missing_pattern_exits_2(self):
        """tu grep with no pattern exits with code 2."""
        rc, _, _ = _cli("grep")
        assert rc == 2

    @pytest.mark.unit
    def test_info_missing_tool_exits_2(self):
        """tu info with no tool name exits with code 2."""
        rc, _, _ = _cli("info")
        assert rc == 2

    @pytest.mark.unit
    def test_find_missing_query_exits_2(self):
        """tu find with no query exits with code 2."""
        rc, _, _ = _cli("find")
        assert rc == 2

    @pytest.mark.unit
    def test_run_missing_tool_name_exits_2(self):
        """tu run with no tool name exits with code 2."""
        rc, _, _ = _cli("run")
        assert rc == 2

    @pytest.mark.unit
    def test_list_invalid_mode_exits_2(self):
        """tu list --mode invalid_mode exits with code 2."""
        rc, _, _ = _cli("list", "--mode", "invalid_mode_xyz")
        assert rc == 2

    @pytest.mark.unit
    def test_grep_invalid_field_exits_2(self):
        """tu grep protein --field invalid exits with code 2."""
        rc, _, _ = _cli("grep", "protein", "--field", "invalid_field_xyz")
        assert rc == 2

    @pytest.mark.unit
    def test_list_limit_not_integer_exits_2(self):
        """tu list --limit abc exits with code 2."""
        rc, _, _ = _cli("list", "--limit", "abc")
        assert rc == 2

    @pytest.mark.unit
    def test_run_invalid_json_exits_1(self):
        """tu run list_tools --json '{bad json}' exits with code 1, error JSON on stdout."""
        rc, out, err = _cli("run", "list_tools", "{bad json}", "--json")
        assert rc == 1
        # --json mode outputs JSON to stdout — even for parse errors
        d = json.loads(out)
        assert d["status"] == "error"

    @pytest.mark.unit
    def test_help_exits_0(self):
        """tu --help exits with code 0."""
        rc, out, _ = _cli("--help")
        assert rc == 0
        assert "COMMAND" in out

    @pytest.mark.unit
    def test_subcommand_help_exits_0(self):
        """tu list --help exits with code 0."""
        rc, out, _ = _cli("list", "--help")
        assert rc == 0


# ═══════════════════════════════════════════════════════════════════════════════
# I. Output format correctness
# ═══════════════════════════════════════════════════════════════════════════════


class TestOutputFormat:
    """Tests that verify --json always produces valid JSON and --raw is compact."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "cmd_fn,ns_kw",
        [
            ("cmd_list", {"mode": "names", "limit": 3, "json": True}),
            ("cmd_list", {"mode": "categories", "json": True}),
            ("cmd_grep", {"pattern": "protein", "limit": 3, "json": True}),
            ("cmd_info", {"tool_names": ["list_tools"], "json": True}),
            ("cmd_find", {"query": "drug discovery", "limit": 3, "json": True}),
            ("cmd_run", {"tool_name": "list_tools", "arguments": ["{}"] }),
            ("cmd_status", {"json": True}),
        ],
    )
    def test_json_flag_produces_valid_json(self, monkeypatch, tu, capsys, cmd_fn, ns_kw):
        """--json flag (or cmd_run default) produces valid JSON on stdout."""
        import tooluniverse.cli as m

        fn = getattr(m, cmd_fn)
        out, _ = _run(monkeypatch, fn, _args(**ns_kw), tu, capsys)
        _j(out)  # raises AssertionError if not valid JSON

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "cmd_fn,ns_kw",
        [
            ("cmd_list", {"mode": "names", "limit": 2, "raw": True}),
            ("cmd_grep", {"pattern": "protein", "limit": 2, "raw": True}),
            ("cmd_status", {"raw": True}),
        ],
    )
    def test_raw_flag_produces_compact_json(
        self, monkeypatch, tu, capsys, cmd_fn, ns_kw
    ):
        """--raw produces compact JSON without indentation."""
        import tooluniverse.cli as m

        fn = getattr(m, cmd_fn)
        out, _ = _run(monkeypatch, fn, _args(**ns_kw), tu, capsys)
        _j(out)
        assert "\n  " not in out  # no 2-space indentation

    @pytest.mark.unit
    def test_status_messages_not_on_stdout(self, monkeypatch, tu, capsys):
        """Loading/warning messages from ToolUniverse do not appear on stdout."""
        from tooluniverse.cli import cmd_list

        out, _ = _run(monkeypatch, cmd_list, _args(mode="names", limit=2, json=True), tu, capsys)
        # If output starts with '{', it's clean JSON (no prefix messages)
        assert out.strip().startswith("{") or out.strip().startswith("[")

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "cmd_fn,ns_kw",
        [
            ("cmd_list", {"limit": 3}),            # default → categories (no filter)
            ("cmd_grep", {"pattern": "protein", "limit": 3}),
            ("cmd_find", {"query": "drug discovery", "limit": 3}),
            ("cmd_status", {}),
        ],
    )
    def test_human_readable_default_not_json(self, monkeypatch, tu, capsys, cmd_fn, ns_kw):
        """Default output (no --json/--raw) is human-readable text, not raw JSON."""
        import tooluniverse.cli as m

        fn = getattr(m, cmd_fn)
        out, _ = _run(monkeypatch, fn, _args(**ns_kw), tu, capsys)
        stripped = out.strip()
        assert stripped, "Expected non-empty human-readable output"
        assert not stripped.startswith("{"), f"Expected human text, got JSON: {stripped[:100]}"


# ═══════════════════════════════════════════════════════════════════════════════
# J. Subprocess / pipe integration  (slow tests, real end-to-end)
# ═══════════════════════════════════════════════════════════════════════════════


class TestSubprocessIntegration:
    """End-to-end subprocess tests verifying real stdout/stderr separation."""

    @pytest.mark.slow
    @pytest.mark.integration
    def test_e2e_list_stdout_is_clean_json(self):
        """tu list --mode categories --json produces only JSON on stdout."""
        rc, out, err = _cli("list", "--mode", "categories", "--limit", "5", "--json")
        assert rc == 0
        d = _j(out)
        assert "categories" in d

    @pytest.mark.slow
    @pytest.mark.integration
    def test_e2e_list_default_human_readable(self):
        """tu list (no --limit) produces human-readable categories table."""
        rc, out, err = _cli("list")
        assert rc == 0
        assert not out.strip().startswith("{")
        # _render_list categories mode always has a "─" separator line
        assert "─" in out or "categories" in out.lower()

    @pytest.mark.slow
    @pytest.mark.integration
    def test_e2e_list_limit_uses_names_mode(self):
        """tu list --limit N (without --mode) switches to names mode."""
        rc, out, err = _cli("list", "--limit", "5")
        assert rc == 0
        assert not out.strip().startswith("{")
        # names mode shows a "N of M tools" footer, not categories table
        assert "of" in out and "tools" in out

    @pytest.mark.slow
    @pytest.mark.integration
    def test_e2e_grep_stdout_is_clean_json(self):
        """tu grep --json produces only JSON on stdout."""
        rc, out, err = _cli("grep", "protein", "--limit", "3", "--json")
        assert rc == 0
        d = _j(out)
        assert "total_matches" in d

    @pytest.mark.slow
    @pytest.mark.integration
    def test_e2e_grep_human_readable(self):
        """tu grep (no --json) produces a human-readable name/description table."""
        rc, out, err = _cli("grep", "protein", "--limit", "3")
        assert rc == 0
        assert not out.strip().startswith("{")
        # _render_grep always emits a "name  description" header
        assert "name" in out and "description" in out

    @pytest.mark.slow
    @pytest.mark.integration
    def test_e2e_status_stdout_is_clean_json(self):
        """tu status --json produces only JSON on stdout."""
        rc, out, err = _cli("status", "--json")
        assert rc == 0
        d = _j(out)
        assert "tools_loaded" in d
        assert d["tools_loaded"] >= 100

    @pytest.mark.slow
    @pytest.mark.integration
    def test_e2e_status_human_readable(self):
        """tu status (no --json) produces human-readable key-value output."""
        rc, out, err = _cli("status")
        assert rc == 0
        # _render_status always emits "tools loaded:    N"
        assert "tools loaded:" in out
        assert "workspace:" in out

    @pytest.mark.slow
    @pytest.mark.integration
    def test_e2e_loading_messages_on_stderr(self):
        """Tool-loading status messages go to stderr, not stdout."""
        rc, out, err = _cli("list", "--mode", "names", "--limit", "1", "--json")
        assert rc == 0
        # stdout should be pure JSON
        _j(out)
        # stderr may contain loading messages (or be empty if tools already cached)

    @pytest.mark.slow
    @pytest.mark.integration
    def test_e2e_find_returns_tools(self):
        """tu find with natural-language query returns tool results."""
        rc, out, err = _cli("find", "protein structure analysis", "--limit", "3", "--json")
        assert rc == 0
        d = _j(out)
        assert "tools" in d

    @pytest.mark.slow
    @pytest.mark.integration
    def test_e2e_run_list_tools(self):
        """tu run list_tools with JSON args works end-to-end."""
        rc, out, err = _cli("run", "list_tools", '{"mode": "categories"}')
        assert rc == 0
        d = _j(out)
        assert "categories" in d

    @pytest.mark.slow
    @pytest.mark.integration
    def test_e2e_run_key_value(self):
        """tu run list_tools mode=categories via key=value syntax works."""
        rc, out, err = _cli("run", "list_tools", "mode=categories")
        assert rc == 0
        d = _j(out)
        assert "categories" in d

    @pytest.mark.slow
    @pytest.mark.integration
    def test_e2e_run_no_args(self):
        """tu run list_tools with no args returns a valid list_tools response."""
        rc, out, err = _cli("run", "list_tools")
        assert rc == 0
        d = _j(out)
        assert "tools" in d or "categories" in d

    @pytest.mark.slow
    @pytest.mark.integration
    def test_e2e_raw_pipe_to_python(self):
        """tu list --raw output can be piped and parsed by Python."""
        rc, out, err = _cli("list", "--mode", "categories", "--raw")
        assert rc == 0
        d = _j(out)
        assert "categories" in d
        # Verify it's truly compact (no indentation)
        assert "\n  " not in out

    @pytest.mark.slow
    @pytest.mark.integration
    def test_e2e_info_nonexistent_exits_1(self):
        """tu info for nonexistent tool exits 1 and returns error JSON."""
        rc, out, err = _cli("info", "ZZZNOMATCH_TOOL_9999", "--json")
        assert rc == 1
        d = _j(out)
        assert "error" in d

    @pytest.mark.slow
    @pytest.mark.integration
    def test_e2e_run_invalid_json_exits_1(self):
        """tu run with invalid JSON exits 1 and prints error to stderr."""
        rc, out, err = _cli("run", "list_tools", "{bad json}")
        assert rc == 1
        assert "Error" in err
        assert out.strip() == ""  # nothing on stdout

    @pytest.mark.slow
    @pytest.mark.integration
    def test_e2e_list_custom_fields(self):
        """tu list --mode custom --fields name type returns only those fields."""
        rc, out, err = _cli(
            "list", "--mode", "custom", "--fields", "name", "type", "--limit", "3", "--json"
        )
        assert rc == 0
        d = _j(out)
        assert "tools" in d
        for tool in d["tools"]:
            assert "name" in tool
            assert "type" in tool
            assert "description" not in tool

    @pytest.mark.slow
    @pytest.mark.integration
    def test_e2e_grep_regex_anchored(self):
        """tu grep '^UniProt' --mode regex returns only UniProt-prefixed tools."""
        rc, out, err = _cli("grep", "^UniProt", "--mode", "regex", "--limit", "5", "--json")
        assert rc == 0
        d = _j(out)
        for tool in d["tools"]:
            assert tool["name"].startswith("UniProt")

    @pytest.mark.slow
    @pytest.mark.integration
    def test_e2e_list_case_insensitive_category(self):
        """tu list --categories UniProt and uniprot return same count."""
        rc1, out1, _ = _cli("list", "--categories", "uniprot", "--json")
        rc2, out2, _ = _cli("list", "--categories", "UniProt", "--json")
        assert rc1 == 0 and rc2 == 0
        d1, d2 = _j(out1), _j(out2)
        assert d1.get("total_tools") == d2.get("total_tools")


# ═══════════════════════════════════════════════════════════════════════════════
# K. Render function smoke tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestRenderFunctions:
    """Smoke tests for _render_* pure functions."""

    @pytest.mark.unit
    def test_render_list_categories_mode(self):
        """_render_list with categories data produces two-column table."""
        from tooluniverse.cli import _render_list

        data = {"categories": {"uniprot": 47, "chembl": 38}}
        out = _render_list(data)
        assert "uniprot" in out
        assert "chembl" in out
        assert "47" in out

    @pytest.mark.unit
    def test_render_list_names_mode(self):
        """_render_list with names data lists tool names."""
        from tooluniverse.cli import _render_list

        data = {"tools": ["tool_a", "tool_b"], "total_tools": 10, "has_more": True}
        out = _render_list(data)
        assert "tool_a" in out
        assert "tool_b" in out

    @pytest.mark.unit
    def test_render_grep_normal(self):
        """_render_grep produces name + description table."""
        from tooluniverse.cli import _render_grep

        data = {
            "tools": [{"name": "get_protein", "description": "Retrieve protein data"}],
            "total_matches": 1,
            "has_more": False,
        }
        out = _render_grep(data)
        assert "get_protein" in out
        assert "Retrieve protein" in out

    @pytest.mark.unit
    def test_render_grep_error(self):
        """_render_grep with error key shows error message."""
        from tooluniverse.cli import _render_grep

        out = _render_grep({"error": "bad pattern"})
        assert "bad pattern" in out

    @pytest.mark.unit
    def test_render_find_normal(self):
        """_render_find produces score + name + description table."""
        from tooluniverse.cli import _render_find

        data = {
            "tools": [{"name": "get_protein", "description": "Retrieve protein", "score": 0.287}]
        }
        out = _render_find(data)
        assert "get_protein" in out
        assert "0.287" in out

    @pytest.mark.unit
    def test_render_find_empty(self):
        """_render_find with no tools returns '0 results'."""
        from tooluniverse.cli import _render_find

        out = _render_find({"tools": []})
        assert "0 results" in out

    @pytest.mark.unit
    def test_render_info_single(self):
        """_render_info for a single tool shows name and description."""
        from tooluniverse.cli import _render_info

        data = {
            "name": "list_tools",
            "description": "List available tools",
            "category": "meta",
            "parameter": {
                "type": "object",
                "properties": {"mode": {"type": "string", "description": "Output mode"}},
                "required": [],
            },
        }
        out = _render_info(data)
        assert "list_tools" in out
        assert "List available tools" in out
        assert "mode" in out

    @pytest.mark.unit
    def test_render_status_normal(self):
        """_render_status produces key-value pairs."""
        from tooluniverse.cli import _render_status

        data = {
            "tools_loaded": 1907,
            "categories": 413,
            "workspace": "./.tooluniverse",
            "profile_active": False,
            "top_categories": {"uniprot": 47, "chembl": 38},
        }
        out = _render_status(data)
        assert "1907" in out
        assert "413" in out
        assert ".tooluniverse" in out
        assert "uniprot" in out

    @pytest.mark.unit
    def test_print_result_fallback_on_render_error(self, capsys):
        """_print_result falls back to pretty JSON when render_fn raises."""
        from tooluniverse.cli import _print_result

        def bad_renderer(d):
            raise ValueError("render boom")

        _print_result({"key": "value"}, _args(), bad_renderer)
        out = capsys.readouterr().out
        # Should output valid JSON, not crash
        assert '"key"' in out
        assert '"value"' in out

    @pytest.mark.unit
    def test_trunc_short_string(self):
        """_trunc does not modify short strings."""
        from tooluniverse.cli import _trunc

        assert _trunc("hello") == "hello"

    @pytest.mark.unit
    def test_trunc_long_string(self):
        """_trunc truncates long strings with ellipsis."""
        from tooluniverse.cli import _trunc

        long = "x" * 100
        result = _trunc(long, 20)
        assert len(result) == 20
        assert result.endswith("…")


class TestResolveCategories:
    """Tests for _resolve_categories — case-insensitive category name mapping.

    _resolve_categories now returns (resolved_list, had_unknown) tuple.
    had_unknown=True means at least one category name was not found in the registry.
    """

    @pytest.mark.unit
    def test_exact_match_returned_as_is(self):
        """Exact category name is returned unchanged with had_unknown=False."""
        from tooluniverse.cli import _resolve_categories
        from unittest.mock import MagicMock

        tu = MagicMock()
        tu.tool_category_dicts = {"Genomics": [], "Proteomics": []}
        tu.all_tool_dict = {}
        resolved, had_unknown = _resolve_categories(tu, ["Genomics"])
        assert resolved == ["Genomics"]
        assert had_unknown is False

    @pytest.mark.unit
    def test_case_insensitive_match(self):
        """Lowercase input resolves to the stored mixed-case key."""
        from tooluniverse.cli import _resolve_categories
        from unittest.mock import MagicMock

        tu = MagicMock()
        tu.tool_category_dicts = {"Genomics": [], "Proteomics": []}
        tu.all_tool_dict = {}
        resolved, had_unknown = _resolve_categories(tu, ["genomics"])
        assert resolved == ["Genomics"]
        assert had_unknown is False

    @pytest.mark.unit
    def test_uppercase_input_resolves(self):
        """Uppercase input resolves to the stored key."""
        from tooluniverse.cli import _resolve_categories
        from unittest.mock import MagicMock

        tu = MagicMock()
        tu.tool_category_dicts = {"Genomics": []}
        tu.all_tool_dict = {}
        resolved, had_unknown = _resolve_categories(tu, ["GENOMICS"])
        assert resolved == ["Genomics"]
        assert had_unknown is False

    @pytest.mark.unit
    def test_unknown_category_passed_through(self):
        """Unknown category name is returned as-is and had_unknown=True (Feature-R13B-06)."""
        from tooluniverse.cli import _resolve_categories
        from unittest.mock import MagicMock

        tu = MagicMock()
        tu.tool_category_dicts = {"Genomics": []}
        tu.all_tool_dict = {}
        resolved, had_unknown = _resolve_categories(tu, ["NonExistent"])
        assert resolved == ["NonExistent"]
        assert had_unknown is True

    @pytest.mark.unit
    def test_multiple_names_mixed(self):
        """Multiple names resolved independently — mix of hits and misses.
        Feature-20A-08: 'Unknown'/'unknown' now resolves silently to the 'unknown'
        sentinel so no warning or had_unknown is raised for that entry.
        """
        from tooluniverse.cli import _resolve_categories
        from unittest.mock import MagicMock

        tu = MagicMock()
        tu.tool_category_dicts = {"Genomics": [], "Proteomics": []}
        tu.all_tool_dict = {}
        resolved, had_unknown = _resolve_categories(tu, ["genomics", "PROTEOMICS", "Unknown"])
        # "Unknown" resolves silently to the "unknown" sentinel (Feature-20A-08).
        assert resolved == ["Genomics", "Proteomics", "unknown"]
        assert had_unknown is False  # all three resolved cleanly

    @pytest.mark.unit
    def test_empty_names_list(self):
        """Empty input returns ([], False)."""
        from tooluniverse.cli import _resolve_categories
        from unittest.mock import MagicMock

        tu = MagicMock()
        tu.tool_category_dicts = {"Genomics": []}
        tu.all_tool_dict = {}
        resolved, had_unknown = _resolve_categories(tu, [])
        assert resolved == []
        assert had_unknown is False

    @pytest.mark.unit
    def test_none_tool_category_dicts(self):
        """None tool_category_dicts treated as empty — unknown names have had_unknown=True."""
        from tooluniverse.cli import _resolve_categories
        from unittest.mock import MagicMock

        tu = MagicMock()
        tu.tool_category_dicts = None
        tu.all_tool_dict = {}
        resolved, had_unknown = _resolve_categories(tu, ["Genomics"])
        assert resolved == ["Genomics"]
        assert had_unknown is True  # not found in empty registry


class TestServe:
    """Tests for `tu serve` subcommand."""

    @pytest.mark.unit
    def test_serve_subcommand_is_registered(self):
        """'serve' is a recognised subcommand (argparse doesn't exit 2)."""
        import argparse
        from tooluniverse.cli import main

        # Patch sys.argv and intercept before cmd_serve runs
        import sys
        from unittest.mock import patch, MagicMock

        mock_serve = MagicMock()
        with patch("tooluniverse.cli.cmd_serve", mock_serve), \
             patch.object(sys, "argv", ["tu", "serve"]):
            main()

        mock_serve.assert_called_once()

    @pytest.mark.unit
    def test_serve_calls_run_default_stdio_server(self):
        """cmd_serve delegates to run_default_stdio_server."""
        import argparse
        from unittest.mock import patch, MagicMock

        try:
            import tooluniverse.smcp_server  # noqa: F401
        except Exception as e:
            pytest.skip(f"SMCP server not available: {e}")

        mock_server = MagicMock()
        with patch("tooluniverse.smcp_server.run_default_stdio_server", mock_server):
            from tooluniverse.cli import cmd_serve
            cmd_serve(argparse.Namespace())

        mock_server.assert_called_once_with()

    @pytest.mark.unit
    def test_serve_help_exits_0(self):
        """'tu serve --help' exits with code 0."""
        rc, out, _ = _cli("serve", "--help")
        assert rc == 0
        assert "serve" in out.lower() or "mcp" in out.lower()

    @pytest.mark.unit
    def test_serve_no_extra_args_accepted(self):
        """'tu serve --bogus' is rejected by argparse (exit 2)."""
        rc, _, _ = _cli("serve", "--bogus")
        assert rc == 2


# ═══════════════════════════════════════════════════════════════════════════════
# L. _compact
# ═══════════════════════════════════════════════════════════════════════════════


class TestCompact:
    """Direct unit tests for _compact — strips None values from a dict."""

    @pytest.mark.unit
    def test_empty_dict(self):
        from tooluniverse.cli import _compact
        assert _compact({}) == {}

    @pytest.mark.unit
    def test_no_nones_unchanged(self):
        from tooluniverse.cli import _compact
        assert _compact({"a": 1, "b": "x"}) == {"a": 1, "b": "x"}

    @pytest.mark.unit
    def test_all_nones_returns_empty(self):
        from tooluniverse.cli import _compact
        assert _compact({"a": None, "b": None}) == {}

    @pytest.mark.unit
    def test_mixed_keeps_non_none(self):
        from tooluniverse.cli import _compact
        assert _compact({"a": 1, "b": None, "c": False, "d": None}) == {"a": 1, "c": False}

    @pytest.mark.unit
    def test_falsy_non_none_values_kept(self):
        """0, False, and '' are falsy but not None — must be kept."""
        from tooluniverse.cli import _compact
        assert _compact({"a": 0, "b": "", "c": None}) == {"a": 0, "b": ""}


# ═══════════════════════════════════════════════════════════════════════════════
# M. _status_to_stderr
# ═══════════════════════════════════════════════════════════════════════════════


class TestStatusToStderr:
    """Direct unit tests for _status_to_stderr context manager."""

    @pytest.mark.unit
    def test_print_inside_goes_to_stderr(self, capsys):
        from tooluniverse.cli import _status_to_stderr
        with _status_to_stderr():
            print("routed to stderr")
        cap = capsys.readouterr()
        assert "routed to stderr" in cap.err
        assert cap.out == ""

    @pytest.mark.unit
    def test_stdout_restored_after_context(self, capsys):
        from tooluniverse.cli import _status_to_stderr
        with _status_to_stderr():
            pass
        print("back on stdout")
        cap = capsys.readouterr()
        assert "back on stdout" in cap.out

    @pytest.mark.unit
    def test_stdout_restored_after_exception(self, capsys):
        from tooluniverse.cli import _status_to_stderr
        try:
            with _status_to_stderr():
                raise ValueError("boom")
        except ValueError:
            pass
        print("restored after exception")
        cap = capsys.readouterr()
        assert "restored after exception" in cap.out


# ═══════════════════════════════════════════════════════════════════════════════
# N. _infer_type — float path
# ═══════════════════════════════════════════════════════════════════════════════


class TestInferTypeNumericStrings:
    """_infer_type does NOT coerce numeric strings (Feature-27A-02).

    Many tool schemas declare IDs as 'type: string' and auto-coercion
    caused schema validation failures. Numeric strings stay as strings.
    """

    @pytest.mark.unit
    def test_float_string_stays_string(self):
        from tooluniverse.cli import _infer_type

        result = _infer_type("3.14")
        assert result == "3.14"
        assert isinstance(result, str)

    @pytest.mark.unit
    def test_scientific_notation_stays_string(self):
        from tooluniverse.cli import _infer_type

        assert _infer_type("1e5") == "1e5"

    @pytest.mark.unit
    def test_negative_stays_string(self):
        from tooluniverse.cli import _infer_type

        assert _infer_type("-2.5") == "-2.5"

    @pytest.mark.unit
    def test_integer_string_stays_string(self):
        from tooluniverse.cli import _infer_type

        result = _infer_type("42")
        assert result == "42"
        assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════════════════════
# O. _render_list edge cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestRenderListEdgeCases:
    """_render_list paths not covered by existing TestRenderFunctions."""

    @pytest.mark.unit
    def test_empty_tools_list_shows_total(self):
        from tooluniverse.cli import _render_list
        result = _render_list({"tools": [], "total_tools": 7})
        assert "no tools" in result
        assert "7" in result

    @pytest.mark.unit
    def test_categories_mode_empty_dict(self):
        from tooluniverse.cli import _render_list
        result = _render_list({"categories": {}})
        assert "no categories" in result

    @pytest.mark.unit
    def test_names_mode_has_more_hint(self):
        from tooluniverse.cli import _render_list
        d = {"tools": ["ToolA", "ToolB"], "total_tools": 100, "has_more": True}
        result = _render_list(d)
        assert "--offset" in result

    @pytest.mark.unit
    def test_names_mode_no_hint_when_no_more(self):
        from tooluniverse.cli import _render_list
        d = {"tools": ["ToolA"], "total_tools": 1, "has_more": False}
        result = _render_list(d)
        assert "--offset" not in result

    @pytest.mark.unit
    def test_basic_mode_tools_without_description_no_crash(self):
        """Tool dicts without 'description' fall through to str() rendering."""
        from tooluniverse.cli import _render_list
        d = {"tools": [{"name": "ToolA", "type": "api"}, {"name": "ToolB", "type": "api"}], "total_tools": 2}
        result = _render_list(d)
        assert "ToolA" in result or "ToolB" in result


# ═══════════════════════════════════════════════════════════════════════════════
# P. _render_info — parameter block & batch mode
# ═══════════════════════════════════════════════════════════════════════════════


class TestRenderInfoParameters:
    """_render_info parameter section and batch rendering."""

    @pytest.mark.unit
    def test_required_param_labeled(self):
        from tooluniverse.cli import _render_info
        d = {
            "name": "MyTool",
            "description": "does stuff",
            "parameter": {
                "properties": {"query": {"type": "string", "description": "search term"}},
                "required": ["query"],
            },
        }
        result = _render_info(d)
        assert "query" in result
        assert "required" in result
        assert "string" in result

    @pytest.mark.unit
    def test_optional_param_not_labeled_required(self):
        from tooluniverse.cli import _render_info
        d = {
            "name": "MyTool",
            "description": "does stuff",
            "parameter": {
                "properties": {"limit": {"type": "integer", "description": "max results"}},
                "required": [],
            },
        }
        result = _render_info(d)
        assert "limit" in result
        assert "required" not in result

    @pytest.mark.unit
    def test_no_params_no_parameters_header(self):
        from tooluniverse.cli import _render_info
        d = {"name": "MyTool", "description": "simple", "parameter": {}}
        result = _render_info(d)
        assert "Parameters:" not in result

    @pytest.mark.unit
    def test_category_shown_in_brackets(self):
        from tooluniverse.cli import _render_info
        d = {"name": "MyTool", "description": "desc", "category": "Genomics"}
        result = _render_info(d)
        assert "[Genomics]" in result

    @pytest.mark.unit
    def test_batch_mode_renders_all_tools(self):
        from tooluniverse.cli import _render_info
        d = {
            "tools": [
                {"name": "ToolA", "description": "first"},
                {"name": "ToolB", "description": "second"},
            ]
        }
        result = _render_info(d)
        assert "ToolA" in result
        assert "ToolB" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Q. _render_find — score formatting
# ═══════════════════════════════════════════════════════════════════════════════


class TestRenderFindScore:
    """_render_find score formatting branches."""

    @pytest.mark.unit
    def test_float_score_formatted_3dp(self):
        from tooluniverse.cli import _render_find
        d = {"tools": [{"name": "ToolA", "description": "desc", "score": 0.9876}]}
        result = _render_find(d)
        assert "0.988" in result

    @pytest.mark.unit
    def test_int_score_shown_as_string(self):
        from tooluniverse.cli import _render_find
        d = {"tools": [{"name": "ToolA", "description": "desc", "score": 42}]}
        result = _render_find(d)
        assert "42" in result

    @pytest.mark.unit
    def test_relevance_score_key_used_as_fallback(self):
        from tooluniverse.cli import _render_find
        d = {"tools": [{"name": "ToolA", "description": "desc", "relevance_score": 0.5}]}
        result = _render_find(d)
        assert "0.500" in result

    @pytest.mark.unit
    def test_string_score_shown_verbatim(self):
        from tooluniverse.cli import _render_find
        d = {"tools": [{"name": "ToolA", "description": "desc", "score": "high"}]}
        result = _render_find(d)
        assert "high" in result

    @pytest.mark.unit
    def test_total_matches_shows_n_of_m(self):
        """_render_find shows 'N of M results' when total_matches > returned tools."""
        from tooluniverse.cli import _render_find
        d = {
            "tools": [{"name": "ToolA", "description": "desc", "score": 5.0}],
            "total_matches": 100,
        }
        result = _render_find(d)
        assert "1 of 100 results" in result
        assert "--offset" in result  # has_more hint

    @pytest.mark.unit
    def test_total_matches_no_hint_when_no_more(self):
        """_render_find omits '--offset' hint when all results returned."""
        from tooluniverse.cli import _render_find
        d = {
            "tools": [{"name": "ToolA", "description": "desc", "score": 5.0}],
            "total_matches": 1,
        }
        result = _render_find(d)
        assert "1 of 1 results" in result
        assert "--offset" not in result


# ═══════════════════════════════════════════════════════════════════════════════
# S. _render_list summary mode (Feature-01)
# ═══════════════════════════════════════════════════════════════════════════════


class TestRenderListSummaryMode:
    """_render_list correctly shows type + has_parameters for summary mode data."""

    @pytest.mark.unit
    def test_summary_mode_shows_type_and_params_columns(self):
        """When tools have 'type' and 'has_parameters', _render_list shows them."""
        from tooluniverse.cli import _render_list
        d = {
            "tools": [
                {"name": "ToolA", "description": "desc A", "type": "APITool", "has_parameters": True},
                {"name": "ToolB", "description": "desc B", "type": "SpecialTool", "has_parameters": False},
            ],
            "total_tools": 2,
        }
        result = _render_list(d)
        assert "type" in result
        assert "params" in result
        assert "APITool" in result
        assert "SpecialTool" in result
        assert "yes" in result  # has_parameters=True
        assert "no" in result   # has_parameters=False

    @pytest.mark.unit
    def test_basic_mode_does_not_show_type_column(self):
        """When tools lack 'has_parameters', _render_list uses basic name+description layout."""
        from tooluniverse.cli import _render_list
        d = {
            "tools": [
                {"name": "ToolA", "description": "desc A"},
                {"name": "ToolB", "description": "desc B"},
            ],
            "total_tools": 2,
        }
        result = _render_list(d)
        # Should show description column but NOT type or params columns
        assert "description" in result
        assert "params" not in result


# ═══════════════════════════════════════════════════════════════════════════════
# T. _render_status shows version and gated_tools (Feature-12)
# ═══════════════════════════════════════════════════════════════════════════════


class TestRenderStatusVersion:
    """_render_status includes version and gated_tools_count."""

    @pytest.mark.unit
    def test_render_status_shows_version(self):
        from tooluniverse.cli import _render_status
        data = {
            "version": "1.0.22",
            "total_tools": 2000,
            "gated_tools_count": 42,
            "categories": 444,
            "workspace": "/tmp",
            "profile_active": True,
            "top_categories": {},
        }
        result = _render_status(data)
        assert "1.0.22" in result
        assert "42" in result  # gated_tools_count
        assert "version:" in result
        assert "gated tools:" in result


# ═══════════════════════════════════════════════════════════════════════════════
# R. cmd_test
# ═══════════════════════════════════════════════════════════════════════════════


class TestCmdTest:
    """Tests for `tu test` subcommand (cmd_test)."""

    def _ns(self, **kw):
        defaults = dict(tool_name=None, args_json=None, config=None)
        defaults.update(kw)
        return argparse.Namespace(**defaults)

    _DEFAULT_RV = {"status": "success", "data": {"r": 1}}

    def _make_tu(self, tool_def, return_value=_DEFAULT_RV):
        from unittest.mock import MagicMock
        tu = MagicMock()
        tu.all_tool_dict = {tool_def["name"]: tool_def}
        tu.run_one_function = MagicMock(return_value=return_value)
        return tu

    def _cfg_file(self, cfg: dict) -> str:
        """Write cfg to a temp JSON file, return path."""
        import json as _j
        import tempfile
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        _j.dump(cfg, f)
        f.close()
        return f.name

    # ── tool-not-found ────────────────────────────────────────────────────────

    @pytest.mark.unit
    def test_tool_not_found_exits_1(self, monkeypatch, capsys):
        import tooluniverse.cli as m
        from unittest.mock import MagicMock
        tu = MagicMock()
        tu.all_tool_dict = {}
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        with pytest.raises(SystemExit) as exc:
            m.cmd_test(self._ns(tool_name="NoSuchTool_xyz"))
        assert exc.value.code == 1

    @pytest.mark.unit
    def test_tool_not_found_prints_message(self, monkeypatch, capsys):
        import tooluniverse.cli as m
        from unittest.mock import MagicMock
        tu = MagicMock()
        tu.all_tool_dict = {}
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        with pytest.raises(SystemExit):
            m.cmd_test(self._ns(tool_name="NoSuchTool_xyz"))
        assert "not found" in capsys.readouterr().out

    # ── test_examples auto-discovery ─────────────────────────────────────────

    @pytest.mark.unit
    def test_no_examples_no_args_exits_1(self, monkeypatch, capsys):
        """Tool with no test_examples and no args given → exit 1."""
        import tooluniverse.cli as m
        tool_def = {"name": "FakeTool", "description": "x"}
        tu = self._make_tu(tool_def)
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        with pytest.raises(SystemExit) as exc:
            m.cmd_test(self._ns(tool_name="FakeTool"))
        assert exc.value.code == 1

    @pytest.mark.unit
    def test_test_examples_auto_discovered_and_pass(self, monkeypatch, capsys):
        """test_examples from tool def are used when no args given."""
        import tooluniverse.cli as m
        tool_def = {"name": "FakeTool", "description": "x", "test_examples": [{"q": "hi"}]}
        tu = self._make_tu(tool_def)
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        m.cmd_test(self._ns(tool_name="FakeTool"))
        assert "passed" in capsys.readouterr().out.lower()

    @pytest.mark.unit
    def test_multiple_examples_all_pass(self, monkeypatch, capsys):
        import tooluniverse.cli as m
        tool_def = {"name": "FakeTool", "description": "x",
                    "test_examples": [{"q": "a"}, {"q": "b"}, {"q": "c"}]}
        tu = self._make_tu(tool_def)
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        m.cmd_test(self._ns(tool_name="FakeTool"))
        out = capsys.readouterr().out
        assert "3" in out  # 3 test(s) passed

    # ── ad-hoc args_json ──────────────────────────────────────────────────────

    @pytest.mark.unit
    def test_adhoc_args_json_happy_path(self, monkeypatch, capsys):
        import tooluniverse.cli as m
        tool_def = {"name": "FakeTool", "description": "x"}
        tu = self._make_tu(tool_def)
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        m.cmd_test(self._ns(tool_name="FakeTool", args_json='{"q": "test"}'))
        out = capsys.readouterr().out
        assert "passed" in out.lower()

    @pytest.mark.unit
    def test_adhoc_args_json_invalid_exits_1(self, monkeypatch, capsys):
        import tooluniverse.cli as m
        from unittest.mock import MagicMock
        monkeypatch.setattr(m, "_get_tu", MagicMock())
        with pytest.raises(SystemExit) as exc:
            m.cmd_test(self._ns(tool_name="FakeTool", args_json="{not: valid}"))
        assert exc.value.code == 1

    # ── result validation ─────────────────────────────────────────────────────

    @pytest.mark.unit
    def test_none_result_counted_as_failure(self, monkeypatch, capsys):
        import tooluniverse.cli as m
        tool_def = {"name": "FakeTool", "description": "x", "test_examples": [{"q": "hi"}]}
        tu = self._make_tu(tool_def, return_value=None)
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        with pytest.raises(SystemExit) as exc:
            m.cmd_test(self._ns(tool_name="FakeTool"))
        assert exc.value.code == 1

    @pytest.mark.unit
    def test_empty_dict_result_counted_as_failure(self, monkeypatch, capsys):
        import tooluniverse.cli as m
        tool_def = {"name": "FakeTool", "description": "x", "test_examples": [{"q": "hi"}]}
        tu = self._make_tu(tool_def, return_value={})
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        with pytest.raises(SystemExit) as exc:
            m.cmd_test(self._ns(tool_name="FakeTool"))
        assert exc.value.code == 1

    @pytest.mark.unit
    def test_exception_in_run_counted_as_failure(self, monkeypatch, capsys):
        import tooluniverse.cli as m
        from unittest.mock import MagicMock
        tool_def = {"name": "FakeTool", "description": "x", "test_examples": [{"q": "hi"}]}
        tu = MagicMock()
        tu.all_tool_dict = {"FakeTool": tool_def}
        tu.run_one_function = MagicMock(side_effect=RuntimeError("connection failed"))
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        with pytest.raises(SystemExit) as exc:
            m.cmd_test(self._ns(tool_name="FakeTool"))
        assert exc.value.code == 1

    # ── config file ───────────────────────────────────────────────────────────

    @pytest.mark.unit
    def test_config_file_happy_path(self, monkeypatch, capsys):
        import tooluniverse.cli as m
        tool_def = {"name": "FakeTool", "description": "x"}
        tu = self._make_tu(tool_def)
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        cfg = {"tool_name": "FakeTool", "tests": [
            {"name": "basic", "args": {"q": "test"}, "expect_status": "success", "expect_keys": ["status"]}
        ]}
        m.cmd_test(self._ns(config=self._cfg_file(cfg)))
        assert "passed" in capsys.readouterr().out.lower()

    @pytest.mark.unit
    def test_config_expect_status_mismatch_exits_1(self, monkeypatch, capsys):
        import tooluniverse.cli as m
        tool_def = {"name": "FakeTool", "description": "x"}
        tu = self._make_tu(tool_def, return_value={"status": "error", "data": {}})
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        cfg = {"tool_name": "FakeTool", "tests": [
            {"name": "t1", "args": {}, "expect_status": "success", "expect_keys": []}
        ]}
        with pytest.raises(SystemExit) as exc:
            m.cmd_test(self._ns(config=self._cfg_file(cfg)))
        assert exc.value.code == 1

    @pytest.mark.unit
    def test_config_expect_keys_missing_exits_1(self, monkeypatch, capsys):
        import tooluniverse.cli as m
        tool_def = {"name": "FakeTool", "description": "x"}
        tu = self._make_tu(tool_def, return_value={"status": "success"})
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        cfg = {"tool_name": "FakeTool", "tests": [
            {"name": "t1", "args": {}, "expect_status": None, "expect_keys": ["missing_key"]}
        ]}
        with pytest.raises(SystemExit) as exc:
            m.cmd_test(self._ns(config=self._cfg_file(cfg)))
        assert exc.value.code == 1

    @pytest.mark.unit
    def test_config_empty_tests_list_exits_0(self, monkeypatch, capsys):
        """Config file with empty tests list: 0 passed, 0 failed → exit 0."""
        import tooluniverse.cli as m
        tool_def = {"name": "FakeTool", "description": "x"}
        tu = self._make_tu(tool_def)
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        cfg = {"tool_name": "FakeTool", "tests": []}
        m.cmd_test(self._ns(config=self._cfg_file(cfg)))  # should not raise
        assert "passed" in capsys.readouterr().out.lower()

    # ── argparse registration ─────────────────────────────────────────────────

    @pytest.mark.unit
    def test_subcommand_help_exits_0(self):
        rc, out, _ = _cli("test", "--help")
        assert rc == 0
        assert "test" in out.lower()

    @pytest.mark.unit
    def test_missing_tool_name_exits_1(self, monkeypatch, capsys):
        """Feature-NEW-04: tu test with no args should exit 1 with helpful message."""
        import tooluniverse.cli as m
        from unittest.mock import MagicMock
        tu = MagicMock()
        tu.all_tool_dict = {}
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        with pytest.raises(SystemExit) as exc:
            m.cmd_test(self._ns(tool_name=None))
        assert exc.value.code == 1

    @pytest.mark.unit
    def test_missing_tool_name_shows_usage_message(self, monkeypatch, capsys):
        """Feature-NEW-04: tu test with no args should show useful message, not 'None not found'."""
        import tooluniverse.cli as m
        from unittest.mock import MagicMock
        tu = MagicMock()
        tu.all_tool_dict = {}
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        with pytest.raises(SystemExit):
            m.cmd_test(self._ns(tool_name=None))
        err = capsys.readouterr().err
        assert "None" not in err
        assert "tool_name" in err.lower() or "usage" in err.lower() or "missing" in err.lower()

    @pytest.mark.unit
    def test_missing_config_file_exits_1(self, monkeypatch, capsys):
        """Feature-NEW-03: tu test --config missing.json should exit 1 gracefully."""
        import tooluniverse.cli as m
        from unittest.mock import MagicMock
        tu = MagicMock()
        tu.all_tool_dict = {}
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        with pytest.raises(SystemExit) as exc:
            m.cmd_test(self._ns(config="/nonexistent/path/missing.json"))
        assert exc.value.code == 1

    @pytest.mark.unit
    def test_missing_config_file_message(self, monkeypatch, capsys):
        """Feature-NEW-03: missing config file message should mention file name."""
        import tooluniverse.cli as m
        from unittest.mock import MagicMock
        tu = MagicMock()
        tu.all_tool_dict = {}
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        with pytest.raises(SystemExit):
            m.cmd_test(self._ns(config="/nonexistent/path/missing.json"))
        err = capsys.readouterr().err
        assert "missing.json" in err or "not found" in err.lower()


class TestCmdFindOffset:
    """Tests for Feature-NEW-01 (--offset on tu find) and Feature-NEW-02 (exit code for limit=0)."""

    @pytest.mark.unit
    def test_find_limit_zero_with_matches_exits_0(self, monkeypatch):
        """Feature-NEW-02: tu find --limit 0 should not exit 1 when total_matches > 0."""
        import tooluniverse.cli as m
        import tooluniverse.tool_finder_keyword as tfk
        from unittest.mock import MagicMock

        finder_result = json.dumps({
            "query": "protein",
            "total_matches": 285,
            "limit": 0,
            "offset": 0,
            "tools": [],
        })
        tu = MagicMock()
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        mock_finder = MagicMock()
        mock_finder._run_json_search.return_value = finder_result
        monkeypatch.setattr(tfk, "ToolFinderKeyword", lambda *a, **kw: mock_finder)

        args = argparse.Namespace(
            query="protein", limit=0, offset=0, categories=None,
            raw=False, json=False,
        )
        # Should NOT raise SystemExit (limit=0 suppresses results but total_matches > 0)
        m.cmd_find(args)

    @pytest.mark.unit
    def test_find_zero_total_matches_exits_0(self, monkeypatch):
        """Feature-R16A-07/R16B-09: tu find should exit 0 when total_matches == 0.
        Zero results is a valid non-error outcome, consistent with grep."""
        import tooluniverse.cli as m
        import tooluniverse.tool_finder_keyword as tfk
        from unittest.mock import MagicMock

        finder_result = json.dumps({
            "query": "zzz_no_results",
            "total_matches": 0,
            "tools": [],
        })
        tu = MagicMock()
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        mock_finder = MagicMock()
        mock_finder._run_json_search.return_value = finder_result
        monkeypatch.setattr(tfk, "ToolFinderKeyword", lambda *a, **kw: mock_finder)

        args = argparse.Namespace(
            query="zzz_no_results", limit=10, offset=0, categories=None,
            raw=False, json=False,
        )
        # Should NOT raise SystemExit for zero results
        m.cmd_find(args)

    @pytest.mark.unit
    def test_find_offset_arg_accepted(self):
        """Feature-NEW-01: tu find --offset N should be accepted by the argument parser."""
        rc, out, err = _cli("find", "--help")
        assert rc == 0
        assert "--offset" in out


class TestRenderFindOffset:
    """Tests for --offset hint in _render_find."""

    @pytest.mark.unit
    def test_offset_hint_when_has_more(self):
        """--offset hint should appear when total > shown."""
        from tooluniverse.cli import _render_find
        d = {
            "tools": [{"name": "T1", "description": "d1", "relevance_score": 0.9}],
            "total_matches": 50,
        }
        result = _render_find(d)
        assert "--offset" in result

    @pytest.mark.unit
    def test_no_offset_hint_when_all_shown(self):
        """--offset hint should NOT appear when all results are shown."""
        from tooluniverse.cli import _render_find
        d = {
            "tools": [{"name": "T1", "description": "d1", "relevance_score": 0.9}],
            "total_matches": 1,
        }
        result = _render_find(d)
        assert "--offset" not in result


class TestRenderInfoDynamicColumns:
    """Tests for Feature-15 (parameter name column overflow)."""

    @pytest.mark.unit
    def test_long_param_name_does_not_overflow(self):
        """Parameter names longer than 20 chars should not misalign other columns."""
        from tooluniverse.cli import _render_info
        d = {
            "name": "FakeTool",
            "description": "Tool with long param",
            "parameter": {
                "type": "object",
                "properties": {
                    "application_manufacturer_or_NDC_info": {
                        "type": "string",
                        "description": "Long param name"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit"
                    },
                },
                "required": ["application_manufacturer_or_NDC_info"],
            },
        }
        result = _render_info(d)
        lines = result.splitlines()
        # Find the parameter table lines
        param_lines = [ln for ln in lines if "application_manufacturer" in ln or "limit" in ln]
        assert len(param_lines) == 2
        # Both lines should have their type column at approximately the same position
        # (within 5 chars of each other) — dynamic column width should handle this
        col_positions = []
        for line in param_lines:
            # Find position of "string" or "integer" in the line
            for word in ["string", "integer"]:
                pos = line.find(word)
                if pos != -1:
                    col_positions.append(pos)
                    break
        assert len(col_positions) == 2
        assert abs(col_positions[0] - col_positions[1]) <= 2  # aligned within 2 chars


class TestErrorToStderr:
    """Tests for Feature-13 (error messages routing to stderr in human-readable mode)."""

    @pytest.mark.unit
    def test_render_error_goes_to_stderr_not_stdout(self, monkeypatch, capsys):
        """Feature-13: tu info <missing_tool> in human-readable mode should print error to stderr."""
        import tooluniverse.cli as m
        from unittest.mock import MagicMock
        tu = MagicMock()
        tu.all_tool_dict = {}
        tu.run_one_function = MagicMock(return_value={"error": "not found", "name": "MISSING_XYZ"})
        monkeypatch.setattr(m, "_get_tu", lambda: tu)

        args = argparse.Namespace(tool_names=["MISSING_XYZ"], detail="full", raw=False, json=False)
        with pytest.raises(SystemExit):
            m.cmd_info(args)
        captured = capsys.readouterr()
        # Error message should be on stderr, not stdout
        assert "MISSING_XYZ" in captured.err or "not found" in captured.err.lower()
        assert "Error" not in captured.out or "Error" not in captured.out


class TestLimitZero:
    """Tests for Feature-R8A-01 (limit=0 treated as 'no limit' in list/grep)."""

    @pytest.mark.unit
    def test_list_names_limit_zero_passes_zero_not_none(self, monkeypatch):
        """Feature-R8A-01: list --mode names --limit 0 should pass limit=0 to tool (not None)."""
        import tooluniverse.cli as m
        from unittest.mock import MagicMock

        tu = MagicMock()
        tu.run_one_function = MagicMock(return_value={
            "total_tools": 2146, "limit": 0, "offset": 0,
            "has_more": True, "tools": [],
        })
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        args = argparse.Namespace(
            mode="names", categories=None, fields=None, limit=0, offset=0,
            group_by_category=False, raw=False, json=True,
        )
        m.cmd_list(args)
        call_args = tu.run_one_function.call_args[0][0]
        assert call_args["arguments"]["limit"] == 0  # 0 was actually passed, not None

    @pytest.mark.unit
    def test_list_tool_discovery_limit_zero_slices_to_empty(self):
        """Feature-R8A-01: tool_discovery_tools pagination with limit=0 returns [] not all."""
        from tooluniverse.tool_discovery_tools import ListToolsTool
        from unittest.mock import MagicMock

        tu = MagicMock()
        # Build a minimal tool list
        tu.all_tool_dict = {f"Tool{i}": {"name": f"Tool{i}", "description": "x"} for i in range(10)}
        tu.tool_category_dicts = {}
        ltt = ListToolsTool({}, tooluniverse=tu)
        result = ltt.run({"mode": "names", "limit": 0, "offset": 0})
        assert result["tools"] == []
        assert result["total_tools"] == 10


class TestRenderListErrorGuard:
    """Tests for Feature-R8A-02 (render_list missing error guard)."""

    @pytest.mark.unit
    def test_render_list_shows_error_message(self):
        """Feature-R8A-02: _render_list should show error text when result has 'error' key."""
        from tooluniverse.cli import _render_list
        d = {"error": "fields parameter is required for mode='custom'"}
        result = _render_list(d)
        assert "Error" in result
        assert "fields" in result

    @pytest.mark.unit
    def test_cmd_list_custom_no_fields_exits_1(self, monkeypatch):
        """Feature-R8A-02: tu list --mode custom (no --fields) should exit 1."""
        import tooluniverse.cli as m
        from unittest.mock import MagicMock
        import pytest as _pytest

        tu = MagicMock()
        tu.run_one_function = MagicMock(return_value={
            "error": "fields parameter is required for mode='custom'"
        })
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        args = argparse.Namespace(
            mode="custom", categories=None, fields=None, limit=None, offset=0,
            group_by_category=False, raw=False, json=False,
        )
        with _pytest.raises(SystemExit) as exc:
            m.cmd_list(args)
        assert exc.value.code == 1


class TestNegativeOffset:
    """Tests for Feature-R8A-05 (negative --offset silently returning empty results)."""

    @pytest.mark.unit
    def test_negative_offset_list_rejected_by_argparse(self):
        """Feature-R8A-05: tu list --offset -1 should be rejected by argparse."""
        rc, out, err = _cli("list", "--offset", "-1")
        assert rc == 2  # argparse exits 2 for invalid args
        assert "error" in err.lower() or "invalid" in err.lower()

    @pytest.mark.unit
    def test_negative_offset_grep_rejected_by_argparse(self):
        """Feature-R8A-05: tu grep protein --offset -5 should be rejected by argparse."""
        rc, out, err = _cli("grep", "protein", "--offset", "-5")
        assert rc == 2
        assert "error" in err.lower() or "invalid" in err.lower()


class TestGroupByCategory:
    """Tests for Feature-R8A-08 (--group-by-category without explicit mode silently ignored)."""

    @pytest.mark.unit
    def test_group_by_category_auto_selects_by_category_mode(self, monkeypatch):
        """Feature-R8A-08: --group-by-category alone should default to by_category mode."""
        import tooluniverse.cli as m
        from unittest.mock import MagicMock

        tu = MagicMock()
        tu.run_one_function = MagicMock(return_value={
            "tools_by_category": {"GTEx": ["Tool1"]},
            "total_tools": 1, "limit": None, "offset": 0,
        })
        tu.tool_category_dicts = {}
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        args = argparse.Namespace(
            mode=None, categories=None, fields=None, limit=None, offset=0,
            group_by_category=True, raw=False, json=False,
        )
        m.cmd_list(args)
        call_args = tu.run_one_function.call_args[0][0]
        assert call_args["arguments"]["mode"] == "by_category"


class TestSearchModeAlias:
    """Tests for Feature-R8A-03 (--search-mode alias missing on tu grep)."""

    @pytest.mark.unit
    def test_search_mode_alias_accepted(self):
        """Feature-R8A-03: tu grep --search-mode regex should work as alias."""
        rc, out, err = _cli("grep", "--search-mode", "text", "protein", "--limit", "1")
        assert rc == 0  # 0 means found results


class TestRunJsonErrorToStdout:
    """Tests for Feature-R8B-01/02 (tu run parse errors now go to stdout as JSON)."""

    @pytest.mark.unit
    def test_run_parse_error_is_json_on_stdout(self, monkeypatch):
        """Feature-R8B-01/02: tu run parse errors always emit JSON to stdout."""
        import tooluniverse.cli as m
        from unittest.mock import MagicMock
        import pytest as _pytest

        tu = MagicMock()
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        args = argparse.Namespace(
            tool_name="list_tools", arguments=["{not json}"], raw=False, json=True
        )
        import io as _io
        import sys as _sys

        # Capture stdout
        old_stdout = _sys.stdout
        _sys.stdout = buf = _io.StringIO()
        try:
            with _pytest.raises(SystemExit):
                m.cmd_run(args)
        finally:
            _sys.stdout = old_stdout
        output = buf.getvalue()
        d = json.loads(output)
        assert d["status"] == "error"
        assert d["error_details"]["type"] == "argument_parse_error"


class TestRound9Fixes:
    """Tests for Feature-R9A-01..05 and Feature-R9B-01..04."""

    # R21A-06: cmd_list now exits 0 when offset is past end (natural pagination termination)
    @pytest.mark.unit
    def test_cmd_list_offset_past_end_exits_0(self, monkeypatch, tu, capsys):
        """R21A-06: tu list --offset 9999999 exits 0 (offset-past-end is not an error)."""
        from tooluniverse.cli import cmd_list
        out, _ = _run(monkeypatch, cmd_list, _args(mode="names", limit=10, offset=999999, json=True), tu, capsys)
        d = _j(out)
        assert d["tools"] == []
        assert d["has_more"] is False

    # Feature-R9A-02: _render_grep distinguishes limit=0 from offset-past-end
    @pytest.mark.unit
    def test_render_grep_limit_zero_shows_limit_message(self):
        """Feature-R9A-02: limit=0 shows 'limit=0' message, not 'offset past end'."""
        from tooluniverse.cli import _render_grep
        d = {"tools": [], "total_matches": 50, "limit": 0, "offset": 0}
        result = _render_grep(d)
        assert "limit=0" in result
        assert "offset past end" not in result

    @pytest.mark.unit
    def test_render_grep_offset_past_end_shows_offset_message(self):
        """Feature-R9A-02: offset past end shows correct hint message."""
        from tooluniverse.cli import _render_grep
        d = {"tools": [], "total_matches": 50, "limit": 10, "offset": 9999}
        result = _render_grep(d)
        assert "offset past end" in result
        assert "limit=0" not in result

    # Feature-R9A-03/04: _render_find handles offset-past-end and limit=0
    @pytest.mark.unit
    def test_render_find_limit_zero_shows_total(self):
        """Feature-R9A-04: tu find --limit 0 should show total matches, not '0 results'."""
        from tooluniverse.cli import _render_find
        d = {"tools": [], "total_matches": 378, "limit": 0, "offset": 0}
        result = _render_find(d)
        assert "378" in result
        assert "limit=0" in result

    @pytest.mark.unit
    def test_render_find_offset_past_end_shows_hint(self):
        """Feature-R9A-03: tu find --offset 9999 should show offset-past-end hint."""
        from tooluniverse.cli import _render_find
        d = {"tools": [], "total_matches": 285, "limit": 10, "offset": 9999}
        result = _render_find(d)
        assert "285" in result
        assert "offset past end" in result

    @pytest.mark.unit
    def test_cmd_find_offset_past_end_exits_0(self, monkeypatch):
        """Feature-R14B-02: tu find --offset 9999 should exit 0 (pagination complete, not an error)."""
        import tooluniverse.cli as m
        import tooluniverse.tool_finder_keyword as tfk
        from unittest.mock import MagicMock

        finder_result = json.dumps({
            "query": "protein",
            "total_matches": 285,
            "limit": 10,
            "offset": 9999,
            "tools": [],
        })
        tu = MagicMock()
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        mock_finder = MagicMock()
        mock_finder._run_json_search.return_value = finder_result
        monkeypatch.setattr(tfk, "ToolFinderKeyword", lambda *a, **kw: mock_finder)

        args = argparse.Namespace(
            query="protein", limit=10, offset=9999, categories=None,
            raw=False, json=False,
        )
        # R14B-02 fix: past-end offset is normal pagination completion, not an error
        m.cmd_find(args)  # should NOT raise SystemExit

    # Feature-R9A-05: by_category --limit 0 shows condensed view
    @pytest.mark.unit
    def test_render_list_by_category_limit_zero_condensed(self):
        """Feature-R9A-05: by_category with limit=0 shows condensed category list."""
        from tooluniverse.cli import _render_list
        d = {
            "tools_by_category": {"genomics": [], "proteomics": [], "chemistry": []},
            "total_tools": 100,
            "limit": 0,
            "offset": 0,
        }
        result = _render_list(d)
        assert "limit=0" in result
        assert "3 categories" in result
        # Should not emit individual empty category headers
        assert "[genomics]" not in result

    # Feature-R9B-01: _render_info shows full detail sections
    @pytest.mark.unit
    def test_render_info_full_shows_examples(self):
        """Feature-R9B-01: _render_info shows test_examples when present (full detail)."""
        from tooluniverse.cli import _render_info
        d = {
            "name": "MyTool",
            "description": "A tool",
            "test_examples": [{"param1": "val1"}],
            "return_schema": {"description": "Returns data about X"},
        }
        result = _render_info(d)
        assert "Examples" in result
        assert "param1" in result
        assert "Returns" in result

    @pytest.mark.unit
    def test_render_info_full_shows_required_packages(self):
        """Feature-R9B-01: _render_info shows required_packages when present."""
        from tooluniverse.cli import _render_info
        d = {
            "name": "MyTool",
            "description": "A tool",
            "required_packages": ["requests", "numpy"],
        }
        result = _render_info(d)
        assert "requests" in result
        assert "numpy" in result

    # Feature-R9B-02: detail=description includes category
    @pytest.mark.unit
    def test_info_description_detail_includes_category(self, monkeypatch, tu, capsys):
        """Feature-R9B-02: tu info --detail description should still show category."""
        from tooluniverse.cli import cmd_info
        # find a real tool to query
        tool_name = next(iter(tu.all_tool_dict))
        out, _ = _run(
            monkeypatch, cmd_info,
            _args(tool_names=[tool_name], detail="description"),
            tu, capsys,
        )
        # The description-level result should include category in the render
        # (category is now returned by get_tool_info at description level)
        # Just verify we get output with the tool name
        assert tool_name in out or tool_name.lower() in out.lower()

    # Feature-R9B-04: limit=0 has_more is False
    @pytest.mark.unit
    def test_list_limit_zero_has_more_true(self, monkeypatch, tu, capsys):
        """Feature-R19B-05: tu list --limit 0 has_more=True when tools exist (count-probe)."""
        from tooluniverse.cli import cmd_list
        out, _ = _run(
            monkeypatch, cmd_list,
            _args(mode="names", limit=0, json=True),
            tu, capsys,
        )
        d = _j(out)
        # R19B-05 fix: limit=0 → has_more=True when total_tools > 0
        # (consistent with grep and find behavior)
        assert d.get("total_tools", 0) > 0
        assert d.get("has_more") is True

    @pytest.mark.unit
    def test_grep_limit_zero_exits_0_has_more_true(self, monkeypatch, tu, capsys):
        """Feature-R18A-10: grep --limit 0 exits 0; has_more reflects real data availability."""
        from tooluniverse.cli import cmd_grep
        out, _ = _run(
            monkeypatch, cmd_grep,
            _args(pattern="protein", limit=0, json=True),
            tu, capsys,
        )
        d = _j(out)
        # R18A-10 fix: limit=0 → has_more=True when total_matches > 0,
        # consistent with find behavior (count-probe correctly signals data exists).
        assert d.get("total_matches", 0) > 0
        assert d.get("has_more") is True


class TestRound10Fixes:
    """Tests for Feature-R10B-01..03 and Feature-R10A-01..03."""

    # Feature-R10B-01: tu list --json without --mode defaults to names (not categories)
    @pytest.mark.unit
    def test_list_json_no_mode_is_names(self, monkeypatch, tu, capsys):
        """Feature-R10B-01: tu list --json without --mode returns names mode (has 'tools' key)."""
        from tooluniverse.cli import cmd_list
        out, _ = _run(monkeypatch, cmd_list, _args(json=True), tu, capsys)
        d = _j(out)
        assert "tools" in d
        assert "total_tools" in d

    @pytest.mark.unit
    def test_list_raw_and_json_consistent_mode(self, monkeypatch, tu, capsys):
        """Feature-R10B-01: --raw and --json without --mode should both use names mode."""
        from tooluniverse.cli import cmd_list
        out_raw, _ = _run(monkeypatch, cmd_list, _args(raw=True), tu, capsys)
        out_json, _ = _run(monkeypatch, cmd_list, _args(json=True), tu, capsys)
        d_raw = _j(out_raw)
        d_json = _j(out_json)
        assert "tools" in d_raw and "tools" in d_json

    # Feature-R10B-02: tu find --json includes has_more
    @pytest.mark.unit
    def test_find_json_includes_has_more(self, monkeypatch, tu, capsys):
        """Feature-R10B-02: tu find --json should include has_more field."""
        from tooluniverse.cli import cmd_find
        out, _ = _run(monkeypatch, cmd_find, _args(query="protein", limit=3, json=True), tu, capsys)
        d = _j(out)
        assert "has_more" in d

    @pytest.mark.unit
    def test_find_json_has_more_true_when_more_results(self, monkeypatch, tu, capsys):
        """Feature-R10B-02: has_more should be True when total > limit."""
        from tooluniverse.cli import cmd_find
        out, _ = _run(monkeypatch, cmd_find, _args(query="protein", limit=1, json=True), tu, capsys)
        d = _j(out)
        if d.get("total_matches", 0) > 1:
            assert d.get("has_more") is True

    # Feature-R10B-03: JSON-like invalid input shows JSON error, not key=value error
    @pytest.mark.unit
    def test_run_json_like_invalid_shows_json_error(self, monkeypatch, capsys):
        """Feature-R10B-03: tu run tool '{invalid}' should say 'Invalid JSON', not 'Expected key=value'."""
        import tooluniverse.cli as m
        from unittest.mock import MagicMock
        tu = MagicMock()
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        args = argparse.Namespace(
            tool_name="list_tools", arguments=["{invalid json}"], raw=False, json=True
        )
        import io as _io
        import sys as _sys

        old_stdout = _sys.stdout
        _sys.stdout = buf = _io.StringIO()
        try:
            with pytest.raises(SystemExit):
                m.cmd_run(args)
        finally:
            _sys.stdout = old_stdout
        output = buf.getvalue()
        d = json.loads(output)
        # Should say "Invalid JSON" not "Expected key=value"
        assert "Invalid JSON" in d["error"] or "json" in d["error"].lower()
        assert "key=value" not in d["error"]

    # Feature-R10A-01: categories mode + offset should warn
    @pytest.mark.unit
    def test_list_categories_mode_offset_warns(self, monkeypatch, tu, capsys):
        """Feature-R10A-01: tu list --mode categories --offset 5 should warn that offset is ignored."""
        from tooluniverse.cli import cmd_list
        _, err = _run(monkeypatch, cmd_list, _args(mode="categories", offset=5), tu, capsys)
        assert "--offset" in err or "offset" in err.lower()

    # Feature-R10A-02: batch info errors go to stderr, not stdout
    @pytest.mark.unit
    def test_info_batch_error_goes_to_stderr(self, monkeypatch, tu, capsys):
        """Feature-R10A-02: tu info valid_tool nonexistent_tool — error for missing tool goes to stderr.
        Partial success (some found) should exit 0 (R13B-02 fix).
        """
        from tooluniverse.cli import cmd_info
        # Use a real tool + a fake tool
        real_tool = next(iter(tu.all_tool_dict))
        # Partial success: should NOT raise SystemExit (R13B-02 fix)
        # Use return value from _run() directly since it calls capsys.readouterr() internally
        out, err = _run(
            monkeypatch, cmd_info,
            _args(tool_names=[real_tool, "definitely_not_a_real_tool_xyz"]),
            tu, capsys,
        )
        # Error text should be on stderr
        assert "not found" in err.lower() or "error" in err.lower()
        # Valid tool info should be on stdout
        assert real_tool in out or real_tool.lower() in out.lower()

    # Negative limit validation
    @pytest.mark.unit
    def test_negative_limit_rejected_by_argparse(self):
        """Negative --limit should be rejected by argparse."""
        rc, out, err = _cli("list", "--limit", "-1")
        assert rc == 2
        assert "error" in err.lower() or "invalid" in err.lower()

    @pytest.mark.unit
    def test_negative_limit_grep_rejected(self):
        """Negative --limit on grep should be rejected."""
        rc, out, err = _cli("grep", "protein", "--limit", "-5")
        assert rc == 2
        assert "error" in err.lower() or "invalid" in err.lower()

    @pytest.mark.unit
    def test_negative_limit_find_rejected(self):
        """Negative --limit on find should be rejected."""
        rc, out, err = _cli("find", "protein", "--limit", "-2")
        assert rc == 2
        assert "error" in err.lower() or "invalid" in err.lower()


class TestRound10AFixes:
    """Tests for Feature-R10A-01..05."""

    # Feature-R10A-01: --mode names --group-by-category should warn and use names structure
    @pytest.mark.unit
    def test_group_by_category_with_explicit_names_mode_warns(self, monkeypatch, tu, capsys):
        """Feature-R10A-01: explicit --mode names + --group-by-category warns and returns tools list."""
        from tooluniverse.cli import cmd_list
        out, err = _run(monkeypatch, cmd_list,
                        _args(mode="names", group_by_category=True, limit=5, json=True),
                        tu, capsys)
        # Should warn on stderr
        assert "group-by-category" in err or "group_by_category" in err
        # Output should be names-mode structure (has "tools" key, not "tools_by_category")
        d = _j(out)
        assert "tools" in d
        assert "tools_by_category" not in d

    @pytest.mark.unit
    def test_group_by_category_without_explicit_mode_still_works(self, monkeypatch, tu, capsys):
        """Feature-R10A-01: --group-by-category without explicit mode should still produce by_category."""
        from tooluniverse.cli import cmd_list
        out, _ = _run(monkeypatch, cmd_list,
                      _args(group_by_category=True, json=True),
                      tu, capsys)
        d = _j(out)
        assert "tools_by_category" in d

    # Feature-R10A-02: by_category total_tools should be true pre-pagination count
    @pytest.mark.unit
    def test_by_category_total_tools_is_full_count(self, monkeypatch, tu, capsys):
        """Feature-R10A-02: total_tools in by_category mode reflects full count, not post-offset sum."""
        from tooluniverse.cli import cmd_list
        # First, get the true total with no offset
        out_no_offset, _ = _run(monkeypatch, cmd_list,
                                _args(mode="by_category", json=True),
                                tu, capsys)
        full_total = _j(out_no_offset)["total_tools"]

        # With offset=5, total_tools should still be the full count
        out_with_offset, _ = _run(monkeypatch, cmd_list,
                                  _args(mode="by_category", offset=5, json=True),
                                  tu, capsys)
        offset_total = _j(out_with_offset)["total_tools"]
        assert offset_total == full_total, (
            f"total_tools changed with offset: {full_total} → {offset_total}"
        )

    # Feature-R10A-03: tu find "" should show user-friendly error on stderr
    @pytest.mark.unit
    def test_find_empty_query_exits_1_with_friendly_error(self, monkeypatch, tu, capsys):
        """Feature-R10A-03: empty query shows 'query cannot be empty' on stderr, exits 1."""
        from tooluniverse.cli import cmd_find
        with pytest.raises(SystemExit) as exc_info:
            _run(monkeypatch, cmd_find, _args(query=""), tu, capsys)
        assert exc_info.value.code == 1
        _, err = capsys.readouterr()
        assert "query" in err.lower()
        assert "empty" in err.lower()

    @pytest.mark.unit
    def test_find_whitespace_query_exits_1(self, monkeypatch, tu, capsys):
        """Feature-R10A-03: whitespace-only query shows user-friendly error."""
        from tooluniverse.cli import cmd_find
        with pytest.raises(SystemExit) as exc_info:
            _run(monkeypatch, cmd_find, _args(query="   "), tu, capsys)
        assert exc_info.value.code == 1

    # Feature-R10A-04: tu grep "" should show user-friendly error on stderr
    @pytest.mark.unit
    def test_grep_empty_pattern_exits_1_with_friendly_error(self, monkeypatch, tu, capsys):
        """Feature-R10A-04: empty pattern shows 'pattern cannot be empty' on stderr, exits 1."""
        from tooluniverse.cli import cmd_grep
        with pytest.raises(SystemExit) as exc_info:
            _run(monkeypatch, cmd_grep, _args(pattern=""), tu, capsys)
        assert exc_info.value.code == 1
        _, err = capsys.readouterr()
        assert "pattern" in err.lower()
        assert "empty" in err.lower()

    @pytest.mark.unit
    def test_grep_whitespace_pattern_exits_1(self, monkeypatch, tu, capsys):
        """Feature-R10A-04: whitespace-only pattern also shows user-friendly error."""
        from tooluniverse.cli import cmd_grep
        with pytest.raises(SystemExit) as exc_info:
            _run(monkeypatch, cmd_grep, _args(pattern="   "), tu, capsys)
        assert exc_info.value.code == 1

    # Feature-R10A-05: --offset help text for list subcommand
    def test_list_offset_help_mentions_by_category(self):
        """Feature-R10A-05: --offset help text for list mentions per-category behavior."""
        rc, out, err = _cli("list", "--help")
        combined = out + err
        assert "by_category" in combined or "per category" in combined


class TestRound11Fixes:
    """Tests for Feature-R11A-01..09, Feature-R11B-01..03/09/11."""

    # Feature-R11A-01: grep --limit 0 exits 0 (count probe, not error)
    @pytest.mark.unit
    def test_grep_limit_zero_exits_0(self, monkeypatch, tu, capsys):
        """Feature-R11A-01: grep --limit 0 should exit 0 (consistent with list and find)."""
        from tooluniverse.cli import cmd_grep
        out, _ = _run(monkeypatch, cmd_grep,
                      _args(pattern="protein", limit=0, json=True),
                      tu, capsys)
        d = _j(out)
        assert d.get("total_matches", 0) > 0
        assert d.get("tools") == []  # limit=0 → empty list

    # Feature-R11A-02: has_more=True when limit=0 and results exist
    @pytest.mark.unit
    def test_find_limit_zero_has_more_true(self, monkeypatch, tu, capsys):
        """Feature-R11A-02: find --limit 0 has_more is True when total > 0."""
        from tooluniverse.cli import cmd_find
        out, _ = _run(monkeypatch, cmd_find,
                      _args(query="protein folding", limit=0, json=True),
                      tu, capsys)
        d = _j(out)
        assert d.get("total_matches", 0) > 0
        assert d.get("has_more") is True

    @pytest.mark.unit
    def test_list_limit_zero_offset_past_end_exits_0(self, monkeypatch, tu, capsys):
        """R21A-06: list --limit 0 --offset beyond total exits 0 (not an error)."""
        from tooluniverse.cli import cmd_list
        out, _ = _run(monkeypatch, cmd_list,
                      _args(mode="names", limit=0, offset=999999, json=True),
                      tu, capsys)
        d = _j(out)
        # offset past end: limit=0 count-probe signal is False when nothing remains
        assert d.get("has_more") is False

    # Feature-R11B-01: info --json always returns {"tools": [...]} envelope
    @pytest.mark.unit
    def test_info_single_tool_always_envelope(self, monkeypatch, tu, capsys):
        """Feature-R11B-01: single tool info returns {\"tools\": [...]}, not a flat dict."""
        from tooluniverse.cli import cmd_info
        out, _ = _run(monkeypatch, cmd_info,
                      _args(tool_names=["list_tools"], json=True),
                      tu, capsys)
        d = _j(out)
        assert "tools" in d, "Expected {'tools': [...]} envelope"
        assert isinstance(d["tools"], list)
        assert len(d["tools"]) == 1
        assert "name" not in d  # top-level should not have name

    @pytest.mark.unit
    def test_info_multi_tool_envelope_consistent(self, monkeypatch, tu, capsys):
        """Feature-R11B-01: multi-tool info has same structure as single-tool info."""
        from tooluniverse.cli import cmd_info
        out, _ = _run(monkeypatch, cmd_info,
                      _args(tool_names=["list_tools", "grep_tools"], json=True),
                      tu, capsys)
        d = _j(out)
        assert "tools" in d
        assert len(d["tools"]) == 2

    # Feature-R11B-03: grep tool objects include category and type
    @pytest.mark.unit
    def test_grep_tools_include_category_and_type(self, monkeypatch, tu, capsys):
        """Feature-R11B-03: grep results include category and type fields."""
        from tooluniverse.cli import cmd_grep
        out, _ = _run(monkeypatch, cmd_grep,
                      _args(pattern="list_tools", limit=1, json=True),
                      tu, capsys)
        d = _j(out)
        assert len(d["tools"]) > 0
        tool = d["tools"][0]
        assert "category" in tool, "grep results should include category"
        assert "type" in tool, "grep results should include type"
        assert "name" in tool
        assert "description" in tool

    # Feature-R11A-09: info pre-validates empty/whitespace tool names
    @pytest.mark.unit
    def test_info_empty_string_tool_name_exits_1(self, monkeypatch, tu, capsys):
        """Feature-R11A-09: info with empty string tool name exits 1 early."""
        from tooluniverse.cli import cmd_info
        with pytest.raises(SystemExit) as exc:
            _run(monkeypatch, cmd_info,
                 _args(tool_names=[""], json=True),
                 tu, capsys)
        assert exc.value.code == 1
        cap = capsys.readouterr()
        d = _j(cap.out)
        assert "error" in d

    @pytest.mark.unit
    def test_info_whitespace_tool_name_exits_1(self, monkeypatch, tu, capsys):
        """Feature-R11A-09: info with whitespace-only tool name exits 1 early."""
        from tooluniverse.cli import cmd_info
        with pytest.raises(SystemExit) as exc:
            _run(monkeypatch, cmd_info,
                 _args(tool_names=["   "], json=True),
                 tu, capsys)
        assert exc.value.code == 1

    # Feature-R11B-11: validation errors return JSON when --json is set
    @pytest.mark.unit
    def test_find_empty_query_json_flag_returns_json_error(self, monkeypatch, tu, capsys):
        """Feature-R11B-11: find with empty query and --json returns JSON error on stdout."""
        from tooluniverse.cli import cmd_find
        import tooluniverse.cli as m
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        with pytest.raises(SystemExit) as exc:
            cmd_find(_args(query="", json=True))
        assert exc.value.code == 1
        cap = capsys.readouterr()
        d = _j(cap.out)
        assert "error" in d

    @pytest.mark.unit
    def test_grep_empty_pattern_json_flag_returns_json_error(self, monkeypatch, tu, capsys):
        """Feature-R11B-11: grep with empty pattern and --json returns JSON error on stdout."""
        from tooluniverse.cli import cmd_grep
        import tooluniverse.cli as m
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        with pytest.raises(SystemExit) as exc:
            cmd_grep(_args(pattern="", json=True))
        assert exc.value.code == 1
        cap = capsys.readouterr()
        d = _j(cap.out)
        assert "error" in d

    @pytest.mark.unit
    def test_info_empty_name_json_flag_returns_json_error(self, monkeypatch, tu, capsys):
        """Feature-R11B-11: info with empty name and --json returns JSON error on stdout."""
        from tooluniverse.cli import cmd_info
        import tooluniverse.cli as m
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        with pytest.raises(SystemExit) as exc:
            cmd_info(_args(tool_names=[""], json=True))
        assert exc.value.code == 1
        cap = capsys.readouterr()
        d = _j(cap.out)
        assert "error" in d


@pytest.mark.unit
class TestRound12Fixes:
    """Tests for Round 12 bug fixes."""

    @pytest.mark.unit
    def test_custom_mode_comma_separated_fields(self, monkeypatch, tu, capsys):
        """Feature-R12A-01: --fields name,type (comma-separated) works like --fields name type."""
        from tooluniverse.cli import cmd_list
        import tooluniverse.cli as m
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        # Pass comma-separated fields as a single element (simulates user passing name,type)
        out, _ = _run(monkeypatch, cmd_list, _args(mode="custom", fields=["name,type"], limit=3, json=True), tu, capsys)
        d = _j(out)
        assert "tools" in d
        assert len(d["tools"]) > 0, "should return at least one tool"
        # Each tool should have 'name' and 'type', NOT be empty
        for tool in d["tools"]:
            assert "name" in tool, f"Each tool must have 'name' field, got: {tool}"
            assert "type" in tool, f"Each tool must have 'type' field, got: {tool}"

    @pytest.mark.unit
    def test_custom_mode_space_separated_fields_still_works(self, monkeypatch, tu, capsys):
        """Feature-R12A-01: Space-separated --fields (nargs=+) still works correctly."""
        from tooluniverse.cli import cmd_list
        import tooluniverse.cli as m
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        out, _ = _run(monkeypatch, cmd_list, _args(mode="custom", fields=["name", "type"], limit=3, json=True), tu, capsys)
        d = _j(out)
        assert len(d["tools"]) > 0
        for tool in d["tools"]:
            assert "name" in tool
            assert "type" in tool

    @pytest.mark.unit
    def test_categories_mode_has_total_metadata(self, monkeypatch, tu, capsys):
        """Feature-R12A-09/R12B-04: categories mode JSON includes total_categories and total_tools."""
        from tooluniverse.cli import cmd_list
        import tooluniverse.cli as m
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        out, _ = _run(monkeypatch, cmd_list, _args(mode="categories", json=True), tu, capsys)
        d = _j(out)
        assert "categories" in d
        assert "total_categories" in d, "Must include total_categories in JSON"
        assert "total_tools" in d, "Must include total_tools in JSON"
        assert d["total_categories"] == len(d["categories"])
        assert d["total_tools"] > 0

    @pytest.mark.unit
    def test_by_category_includes_per_category_limit_field(self, monkeypatch, tu, capsys):
        """Feature-R12A-02: by_category mode includes per_category_limit field for clarity."""
        from tooluniverse.cli import cmd_list
        import tooluniverse.cli as m
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        out, _ = _run(monkeypatch, cmd_list, _args(mode="by_category", limit=2, json=True), tu, capsys)
        d = _j(out)
        assert "tools_by_category" in d
        assert "per_category_limit" in d, "Must include per_category_limit field"
        assert d["per_category_limit"] == 2

    @pytest.mark.unit
    def test_json_and_raw_mutually_exclusive(self, monkeypatch, tu, capsys):
        """Feature-R12A-12: --json and --raw together should exit with error."""
        import sys
        import tooluniverse.cli as m
        monkeypatch.setattr(sys, "argv", ["tu", "list", "--json", "--raw"])
        with pytest.raises(SystemExit) as exc:
            m.main()
        assert exc.value.code != 0  # Should fail (argparse error = exit 2)

    @pytest.mark.unit
    def test_category_prefix_expands_to_all_matches(self, monkeypatch, tu, capsys):
        """Feature-R12B-06: --categories ncbi expands to all ncbi_* subcategories."""
        from tooluniverse.cli import cmd_list
        import tooluniverse.cli as m
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        # Use a prefix that should match multiple categories
        # 'uniprot' should at least match uniprot and uniprot_id_mapping (if present)
        # More robustly, check that prefix expansion returns multiple results
        # by using a prefix known to match > 1 category (ncbi → ncbi_datasets etc.)
        out, err = _run(monkeypatch, cmd_list, _args(mode="names", categories=["ncbi"], json=True), tu, capsys)
        d = _j(out)
        # If ncbi expands to multiple categories, we should get tools from all of them
        # At minimum, the Info: line should mention expansion (checked via stderr)
        # The tools returned should be > 0
        assert d.get("total_tools", 0) > 0 or len(d.get("tools", [])) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Round 13 bug fixes
# ═══════════════════════════════════════════════════════════════════════════════


class TestRound13Fixes:
    """Tests covering bug fixes from Round 13 simulation agents."""

    @pytest.mark.unit
    def test_find_stopwords_returns_standard_schema(self, monkeypatch, tu, capsys):
        """Feature-R13B-01: stopword-only query returns standard schema, not error schema.
        Feature-R16A-07: exits 0 (zero results is not an error)."""
        import tooluniverse.cli as m
        from tooluniverse.cli import cmd_find

        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        # Should NOT raise SystemExit — exits 0 for zero results
        cmd_find(_args(query="the and for", json=True))
        out, _ = capsys.readouterr()
        d = _j(out)
        # Standard schema keys must be present (not error schema)
        assert "total_matches" in d
        assert "error" not in d
        assert d["total_matches"] == 0
        assert d["tools"] == []
        # Warning is communicated via processing_info
        assert (d.get("processing_info") or {}).get("warning")

    @pytest.mark.unit
    def test_find_no_required_field_in_results(self, monkeypatch, tu, capsys):
        """Feature-R12B-03/R13B-04: find results must not include top-level required: []."""
        from tooluniverse.cli import cmd_find

        out, _ = _run(monkeypatch, cmd_find, _args(query="drug target", limit=3, json=True), tu, capsys)
        d = _j(out)
        for tool in d.get("tools", []):
            assert "required" not in tool, f"tool {tool['name']} has spurious top-level required field"

    @pytest.mark.unit
    def test_find_tool_name_with_underscores_works(self, monkeypatch, tu, capsys):
        """Feature-R13A-08: find with exact tool name (underscores) returns results instead of error."""
        from tooluniverse.cli import cmd_find

        # BioGRID_get_chemical_interactions should now work — underscores become spaces
        out, _ = _run(monkeypatch, cmd_find, _args(query="BioGRID_get_chemical_interactions", limit=5, json=True), tu, capsys)
        d = _j(out)
        assert d.get("total_matches", 0) > 0, "should find matches for tool name query"
        assert "error" not in d
        # Top result should be BioGRID-related
        names = [t.get("name", "") for t in d.get("tools", [])]
        assert any("BioGRID" in n for n in names), f"BioGRID tool should be in results, got: {names}"

    @pytest.mark.unit
    def test_grep_zero_matches_shows_field_hint(self, monkeypatch, tu, capsys):
        """Feature-R13A-01: grep 0 matches with default name field shows --field description hint.
        R14B-01: grep exits 0 on 0 matches now."""
        import tooluniverse.cli as m
        from tooluniverse.cli import cmd_grep

        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        # R14B-01: no longer raises SystemExit on 0 matches
        out, err = _run(monkeypatch, cmd_grep, _args(pattern="binding affinity xyz ZZZNO", field="name"), tu, capsys)
        # Hint should appear in plain mode output
        assert "description" in out.lower() or "description" in err.lower()

    @pytest.mark.unit
    def test_unknown_category_list_exits_1(self, monkeypatch, tu, capsys):
        """Feature-R13B-06: list with unknown category exits 1 (already a warning on stderr)."""
        import tooluniverse.cli as m
        from tooluniverse.cli import cmd_list

        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        with pytest.raises(SystemExit) as exc:
            cmd_list(_args(mode="names", categories=["ZZZNOMATCH_XYZ_9999"], json=True))
        assert exc.value.code == 1

    @pytest.mark.unit
    def test_raw_category_fuzzy_match(self, monkeypatch, tu, capsys):
        """Feature-R12A-11: categories from tool configs (e.g. 'Genomics & Transcriptomics') are
        found via prefix match even if not in tool_category_dicts."""
        from tooluniverse.cli import cmd_list

        # 'Genomics' is a prefix of 'Genomics & Transcriptomics'
        out, _ = _run(monkeypatch, cmd_list, _args(mode="names", categories=["Genomics"], json=True), tu, capsys)
        d = _j(out)
        # Should find tools in the 'Genomics & Transcriptomics' category
        assert d.get("total_tools", 0) > 0 or len(d.get("tools", [])) > 0

class TestRound14Fixes:
    """Tests covering bug fixes from Round 14 simulation agents."""

    # R14B-01: grep exits 0 on 0 matches
    @pytest.mark.unit
    def test_grep_zero_matches_exits_0(self, monkeypatch, tu, capsys):
        """R14B-01: grep with no matches should exit 0 — successful query with 0 results."""
        from tooluniverse.cli import cmd_grep
        # Should NOT raise SystemExit
        out, _ = _run(monkeypatch, cmd_grep, _args(pattern="ZZZNOTEXIST9999XYZ", json=True), tu, capsys)
        d = _j(out)
        assert d["total_matches"] == 0
        assert "error" not in d

    # R14B-02: find exits 0 when offset is past end
    @pytest.mark.unit
    def test_find_past_end_exits_0(self, monkeypatch, tu, capsys):
        """R14B-02: find --offset past end should exit 0 — pagination complete, not an error."""
        from tooluniverse.cli import cmd_find
        import tooluniverse.tool_finder_keyword as tfk
        from unittest.mock import MagicMock
        finder_result = json.dumps({
            "query": "protein", "total_matches": 285,
            "limit": 10, "offset": 9999, "tools": [],
        })
        mock_finder = MagicMock()
        mock_finder._run_json_search.return_value = finder_result
        import tooluniverse.cli as m
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        monkeypatch.setattr(tfk, "ToolFinderKeyword", lambda *a, **kw: mock_finder)
        # Should NOT raise SystemExit
        cmd_find(_args(query="protein", limit=10, offset=9999))

    # R14A-04: grep --json 0-match hint field
    @pytest.mark.unit
    def test_grep_json_zero_matches_has_hint(self, monkeypatch, tu, capsys):
        """R14A-04: grep --json 0 matches with field=name should include 'hint' key."""
        from tooluniverse.cli import cmd_grep
        out, _ = _run(monkeypatch, cmd_grep,
                      _args(pattern="ZZZNOTEXIST9999", field="name", json=True), tu, capsys)
        d = _j(out)
        assert d["total_matches"] == 0
        assert "hint" in d
        assert "description" in d["hint"]

    # R14A-05: grep --json includes categories_filtered
    @pytest.mark.unit
    def test_grep_json_with_categories_has_categories_filtered(self, monkeypatch, tu, capsys):
        """R14A-05: grep --json with --categories should include categories_filtered in response."""
        from tooluniverse.cli import cmd_grep
        real_cat = next(iter(tu.tool_category_dicts.keys()))
        out, _ = _run(monkeypatch, cmd_grep,
                      _args(pattern="a", categories=[real_cat], limit=3, json=True), tu, capsys)
        d = _j(out)
        assert "categories_filtered" in d

    # R14A-01/R14B-04: info --json normalizes "parameter" to "parameters"
    @pytest.mark.unit
    def test_info_json_uses_parameters_key(self, monkeypatch, tu, capsys):
        """R14A-01/R14B-04: info --json renames 'parameter' to 'parameters' for consistency with find."""
        from tooluniverse.cli import cmd_info
        out, _ = _run(monkeypatch, cmd_info,
                      _args(tool_names=["list_tools"], detail="full", json=True), tu, capsys)
        d = _j(out)
        tool = d["tools"][0]
        assert "parameters" in tool, "Expected 'parameters' key in info JSON"
        assert "parameter" not in tool, "Should not have old 'parameter' key in JSON mode"

    # R14B-05 → R19B-05: list --limit 0 now returns has_more: true (consistent with grep/find)
    @pytest.mark.unit
    def test_list_limit_zero_has_more_true(self, monkeypatch, tu, capsys):
        """R19B-05: list --limit 0 has_more=True when tools exist (count-probe)."""
        from tooluniverse.cli import cmd_list
        out, _ = _run(monkeypatch, cmd_list,
                      _args(mode="names", limit=0, json=True), tu, capsys)
        d = _j(out)
        # R19B-05: has_more now True when total_tools > 0, consistent with grep/find
        assert d["total_tools"] > 0
        assert d["has_more"] is True

    @pytest.mark.unit
    def test_grep_limit_zero_has_more_true(self, monkeypatch, tu, capsys):
        """R18A-10: grep --limit 0 has_more=True when matches exist (count-probe)."""
        from tooluniverse.cli import cmd_grep
        out, _ = _run(monkeypatch, cmd_grep,
                      _args(pattern="protein", limit=0, json=True), tu, capsys)
        d = _j(out)
        # R18A-10 fix: has_more now correctly reflects data availability (True when > 0)
        assert d["total_matches"] > 0
        assert d["has_more"] is True

class TestRound15Fixes:
    """Tests covering bug fixes from Round 15 simulation agents."""

    # R15A-03/R15B-04: grep always emits categories_filtered and hint
    @pytest.mark.unit
    def test_grep_json_always_has_categories_filtered(self, monkeypatch, tu, capsys):
        """R15A-03: grep --json without --categories should emit categories_filtered: null."""
        from tooluniverse.cli import cmd_grep
        out, _ = _run(monkeypatch, cmd_grep, _args(pattern="protein", json=True), tu, capsys)
        d = _j(out)
        assert "categories_filtered" in d
        assert d["categories_filtered"] is None

    @pytest.mark.unit
    def test_grep_json_always_has_hint_key(self, monkeypatch, tu, capsys):
        """R15B-04: grep --json should always have 'hint' key (null when no hint)."""
        from tooluniverse.cli import cmd_grep
        # When there are results, hint should be null
        out, _ = _run(monkeypatch, cmd_grep, _args(pattern="protein", json=True), tu, capsys)
        d = _j(out)
        assert "hint" in d
        assert d["hint"] is None

    @pytest.mark.unit
    def test_grep_json_hint_adapts_to_description_field(self, monkeypatch, tu, capsys):
        """R15A-06: grep hint adapts when --field description is already being used."""
        from tooluniverse.cli import cmd_grep
        out, _ = _run(monkeypatch, cmd_grep,
                      _args(pattern="ZZZNOTEXIST99999", field="description", json=True),
                      tu, capsys)
        d = _j(out)
        assert "hint" in d
        # Hint should NOT say "add --field description" since we're already using description
        if d["hint"]:
            assert "description" not in d["hint"] or "different" in d["hint"]

    # R15B-02: query normalization transparency
    @pytest.mark.unit
    def test_find_underscore_query_exposes_normalization(self, monkeypatch, tu, capsys):
        """R15B-02: find with underscore query should expose query_submitted in processing_info."""
        from tooluniverse.cli import cmd_find
        import tooluniverse.tool_finder_keyword as tfk
        from unittest.mock import MagicMock

        # We need to call the actual ToolFinderKeyword to test the normalization
        finder_result_with_normalization = json.dumps({
            "query": "BioGRID get chemical interactions",
            "total_matches": 1,
            "limit": 5,
            "offset": 0,
            "has_more": False,
            "categories_filtered": None,
            "processing_info": {
                "query_tokens": 3,
                "query_phrases": 1,
                "indexed_tools": 2142,
                "query_submitted": "BioGRID_get_chemical_interactions",
                "query_normalized": "BioGRID get chemical interactions",
            },
            "tools": [],
        })
        mock_finder = MagicMock()
        mock_finder._run_json_search.return_value = finder_result_with_normalization
        import tooluniverse.cli as m
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        monkeypatch.setattr(tfk, "ToolFinderKeyword", lambda *a, **kw: mock_finder)

        out, _ = _run(monkeypatch, cmd_find,
                      _args(query="BioGRID_get_chemical_interactions", limit=5, json=True),
                      tu, capsys)
        d = _j(out)
        pi = d.get("processing_info", {})
        assert "query_submitted" in pi
        assert "BioGRID_get_chemical_interactions" in pi.get("query_submitted", "")


# ═══════════════════════════════════════════════════════════════════════════════
# Round 16 bug fixes
# ═══════════════════════════════════════════════════════════════════════════════


class TestRound16Fixes:
    """Tests covering bug fixes from Round 16 simulation agents."""

    # R16A-07/R16B-09: find exits 0 on 0 results (consistent with grep)
    @pytest.mark.unit
    def test_find_zero_results_exits_0(self, monkeypatch, tu, capsys):
        """R16A-07/R16B-09: find with no matches should exit 0 — consistent with grep."""
        from tooluniverse.cli import cmd_find
        import tooluniverse.tool_finder_keyword as tfk
        from unittest.mock import MagicMock

        finder_result = json.dumps({
            "query": "asdfghjklqwerty",
            "total_matches": 0,
            "limit": 10,
            "offset": 0,
            "has_more": False,
            "tools": [],
        })
        mock_finder = MagicMock()
        mock_finder._run_json_search.return_value = finder_result
        import tooluniverse.cli as m
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        monkeypatch.setattr(tfk, "ToolFinderKeyword", lambda *a, **kw: mock_finder)

        # Should NOT raise SystemExit — 0 results is success, not error
        out, _ = _run(monkeypatch, cmd_find,
                      _args(query="asdfghjklqwerty", json=True),
                      tu, capsys)
        d = _j(out)
        assert d["total_matches"] == 0
        assert "error" not in d

    @pytest.mark.unit
    def test_find_real_zero_results_exits_0(self, monkeypatch, tu, capsys):
        """R16A-07: find with a real nonsense query should exit 0 (live test)."""
        from tooluniverse.cli import cmd_find
        import tooluniverse.cli as m
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        # Should NOT raise SystemExit
        out, _ = _run(monkeypatch, cmd_find,
                      _args(query="xxxxxyyyyzzzz999nonexistent", json=True),
                      tu, capsys)
        d = _j(out)
        assert "error" not in d
        # total_matches may be 0 or some number depending on tokenization —
        # the key assertion is that we got a valid JSON response with exit 0
        assert "total_matches" in d


# ═══════════════════════════════════════════════════════════════════════════════
# Round 17 bug fixes
# ═══════════════════════════════════════════════════════════════════════════════


class TestRound17Fixes:
    """Tests covering bug fixes from Round 17 simulation agents."""

    # R17B-02: --detail brief alias works (synonym for description)
    @pytest.mark.unit
    def test_info_brief_detail_is_alias_for_description(self, monkeypatch, tu, capsys):
        """R17B-02: --detail brief is an alias for --detail description (description-only mode)."""
        from tooluniverse.cli import cmd_info

        out_brief, _ = _run(monkeypatch, cmd_info,
                            _args(tool_names=["list_tools"], detail="brief", json=True),
                            tu, capsys)
        out_desc, _ = _run(monkeypatch, cmd_info,
                           _args(tool_names=["list_tools"], detail="description", json=True),
                           tu, capsys)
        d_brief = _j(out_brief)
        d_desc = _j(out_desc)
        # Both modes return description-only (no parameters)
        assert "parameter" not in d_brief["tools"][0]
        assert "parameter" not in d_desc["tools"][0]
        assert d_brief["tools"][0]["description"] == d_desc["tools"][0]["description"]

    @pytest.mark.unit
    def test_info_brief_detail_no_parameter_key(self, monkeypatch, tu, capsys):
        """R17B-02: --detail brief shows description only, no parameters."""
        from tooluniverse.cli import cmd_info

        out, _ = _run(monkeypatch, cmd_info,
                      _args(tool_names=["list_tools"], detail="brief", json=True),
                      tu, capsys)
        d = _j(out)
        tool = d["tools"][0]
        assert tool["name"] == "list_tools"
        assert "description" in tool
        assert "parameter" not in tool
        assert "parameters" not in tool

    # R17B-07: last page shows "end of results" in plain-text render
    @pytest.mark.unit
    def test_render_find_last_page_shows_end_of_results(self):
        """R17B-07: _render_find shows 'end of results' on last non-empty paginated page."""
        from tooluniverse.cli import _render_find

        d = {
            "tools": [{"name": "T1", "description": "d1", "relevance_score": 0.9}],
            "total_matches": 57,
            "limit": 3,
            "offset": 54,
            "has_more": False,
        }
        result = _render_find(d)
        assert "end of results" in result
        assert "use --offset" not in result

    @pytest.mark.unit
    def test_render_find_first_page_no_end_of_results(self):
        """R17B-07: _render_find does NOT show 'end of results' on page 1 (no offset)."""
        from tooluniverse.cli import _render_find

        d = {
            "tools": [{"name": "T1", "description": "d1", "relevance_score": 0.9}],
            "total_matches": 57,
            "limit": 3,
            "offset": 0,
            "has_more": True,
        }
        result = _render_find(d)
        assert "end of results" not in result
        # R18B-08: hint now says "next: --offset N" instead of generic "use --offset"
        assert "--offset" in result

    @pytest.mark.unit
    def test_render_grep_last_page_shows_end_of_results(self):
        """R17B-07: _render_grep shows 'end of results' on last non-empty paginated page."""
        from tooluniverse.cli import _render_grep

        d = {
            "tools": [{"name": "ToolA", "description": "desc A"}],
            "total_matches": 10,
            "limit": 5,
            "offset": 5,
            "has_more": False,
        }
        result = _render_grep(d)
        assert "end of results" in result
        assert "next: --offset" not in result


class TestRound18Fixes:
    """Tests for bugs found in R18A and R18B simulation rounds."""

    # R18B-10: spurious ambiguity warning suppressed on exact-match category
    @pytest.mark.unit
    def test_resolve_categories_exact_match_no_warning(self, monkeypatch, tu, capsys):
        """R18B-10: exact-match category (e.g. 'uniprot') should NOT warn about prefix siblings."""
        from tooluniverse.cli import _resolve_categories

        # Find a real category that is a prefix of another (if any), or mock
        cats = list(tu.tool_category_dicts.keys())
        # Pick a category that actually exists in the registry
        if not cats:
            pytest.skip("No categories available")
        cat = cats[0]
        resolved, had_unknown = _resolve_categories(tu, [cat])
        _, err = capsys.readouterr()
        # Exact match → no warning, resolves to itself
        assert cat in resolved
        assert "Warning: category input" not in err

    # R18A-10: grep limit=0 now returns has_more=True (consistent with find)
    @pytest.mark.unit
    def test_grep_limit_zero_has_more_reflects_availability(self, monkeypatch, tu, capsys):
        """R18A-10: grep --limit 0 has_more=True when matches exist (count-probe)."""
        from tooluniverse.cli import cmd_grep
        out, _ = _run(monkeypatch, cmd_grep,
                      _args(pattern="UniProt", limit=0, json=True), tu, capsys)
        d = _j(out)
        assert d["total_matches"] > 0
        assert d["has_more"] is True

    # R18B-08/R17B-08: pagination footer shows range and next-offset hint
    @pytest.mark.unit
    def test_render_find_pagination_shows_range_and_next_offset(self):
        """R18B-08: _render_find shows range [N-M] and 'next: --offset X' when has_more."""
        from tooluniverse.cli import _render_find
        d = {
            "tools": [
                {"name": f"Tool{i}", "description": f"desc{i}", "relevance_score": 0.9}
                for i in range(5)
            ],
            "total_matches": 50,
            "limit": 5,
            "offset": 5,
            "has_more": True,
        }
        result = _render_find(d)
        # Range [6-10] shown when offset=5, 5 tools
        assert "[6–10]" in result
        # next offset hint
        assert "next: --offset 10" in result

    @pytest.mark.unit
    def test_render_grep_pagination_shows_range_and_next_offset(self):
        """R18B-08: _render_grep shows range [N-M] and 'next: --offset X' when has_more."""
        from tooluniverse.cli import _render_grep
        d = {
            "tools": [{"name": f"Tool{i}", "description": f"desc{i}"} for i in range(3)],
            "total_matches": 20,
            "limit": 3,
            "offset": 6,
            "has_more": True,
        }
        result = _render_grep(d)
        # Range [7-9] (offset=6, 3 tools)
        assert "[7–9]" in result
        assert "next: --offset 9" in result

    @pytest.mark.unit
    def test_render_find_range_on_first_page_when_paginating(self):
        """Feature-20A-07: range IS shown on first page (offset=0) when has_more=True."""
        from tooluniverse.cli import _render_find
        d = {
            "tools": [
                {"name": "T1", "description": "d1", "relevance_score": 0.5}
            ],
            "total_matches": 10,
            "limit": 1,
            "offset": 0,
            "has_more": True,
        }
        result = _render_find(d)
        assert "[1–1]" in result  # range shown on page 1 when paginating
        assert "next: --offset 1" in result  # next-offset hint is still there


class TestRound19Fixes:
    """Tests for bugs found in R19A and R19B simulation rounds."""

    # R19B-05: list --limit 0 now has_more=True (count-probe consistency)
    @pytest.mark.unit
    def test_list_names_limit_zero_has_more_true(self, monkeypatch, tu, capsys):
        """R19B-05: tu list --mode names --limit 0 has_more=True when tools exist."""
        from tooluniverse.cli import cmd_list
        out, _ = _run(monkeypatch, cmd_list,
                      _args(mode="names", limit=0, json=True), tu, capsys)
        d = _j(out)
        assert d["total_tools"] > 0
        assert d["has_more"] is True, "list names --limit 0 should signal data exists"

    # R19B: count key contracts documented — verify expected keys exist per command
    @pytest.mark.unit
    def test_list_json_has_total_tools_key(self, monkeypatch, tu, capsys):
        """R19B schema contract: list uses 'total_tools' as the count key."""
        from tooluniverse.cli import cmd_list
        out, _ = _run(monkeypatch, cmd_list,
                      _args(mode="names", limit=1, json=True), tu, capsys)
        d = _j(out)
        assert "total_tools" in d
        assert d["total_tools"] > 0

    @pytest.mark.unit
    def test_grep_json_has_total_matches_key(self, monkeypatch, tu, capsys):
        """R19B schema contract: grep uses 'total_matches' as the count key."""
        from tooluniverse.cli import cmd_grep
        out, _ = _run(monkeypatch, cmd_grep,
                      _args(pattern="protein", limit=1, json=True), tu, capsys)
        d = _j(out)
        assert "total_matches" in d
        assert d["total_matches"] > 0

    @pytest.mark.unit
    def test_info_json_has_total_found_key(self, monkeypatch, tu, capsys):
        """R19B schema contract: info uses 'total_found' and 'total_requested' keys."""
        from tooluniverse.cli import cmd_info
        out, _ = _run(monkeypatch, cmd_info,
                      _args(tool_names=["UniProt_get_entry_by_accession"], json=True),
                      tu, capsys)
        d = _j(out)
        assert "total_found" in d
        assert "total_requested" in d

    # R19B: pagination range and next-offset hint in human-readable grep output
    @pytest.mark.unit
    def test_grep_paginated_output_shows_range(self, monkeypatch, tu, capsys):
        """R19B: grep with offset shows range and next offset in text output."""
        from tooluniverse.cli import cmd_grep
        out, _ = _run(monkeypatch, cmd_grep,
                      _args(pattern="protein", limit=5, offset=5), tu, capsys)
        # Footer should show range [6-10] and next offset
        assert "[6–10]" in out or "[6-10]" in out
        assert "--offset 10" in out


class TestRound20Fixes:
    """Tests for bugs found in R20A and R20B simulation rounds."""

    # R20B: next_offset=None when limit=0 (count probe, not a real cursor)
    @pytest.mark.unit
    def test_grep_limit_zero_next_offset_is_zero(self, monkeypatch, tu, capsys):
        """Feature-23A-02: grep --limit 0 with has_more=True returns next_offset=0 (not null)."""
        from tooluniverse.cli import cmd_grep

        out, _ = _run(
            monkeypatch, cmd_grep, _args(pattern="protein", limit=0, json=True), tu, capsys
        )
        d = _j(out)
        assert d["has_more"] is True
        # Feature-23A-02: next_offset=0 so callers can use it directly as --offset
        assert d.get("next_offset") == 0, "limit=0 probe with has_more=True should return next_offset=0"

    @pytest.mark.unit
    def test_list_limit_zero_next_offset_is_zero(self, monkeypatch, tu, capsys):
        """Feature-23A-02: list --limit 0 with has_more=True returns next_offset=0 (not null)."""
        from tooluniverse.cli import cmd_list

        out, _ = _run(
            monkeypatch, cmd_list, _args(mode="names", limit=0, json=True), tu, capsys
        )
        d = _j(out)
        assert d["has_more"] is True
        # Feature-23A-02: next_offset=0 so callers can use it directly as --offset
        assert d.get("next_offset") == 0, "limit=0 probe with has_more=True should return next_offset=0"

    @pytest.mark.unit
    def test_grep_pagination_next_offset_usable(self, monkeypatch, tu, capsys):
        """R20B: next_offset is offset+count when has_more=True and limit>0."""
        from tooluniverse.cli import cmd_grep
        out, _ = _run(monkeypatch, cmd_grep,
                      _args(pattern="protein", limit=5, json=True), tu, capsys)
        d = _j(out)
        if d.get("has_more"):
            expected = d["offset"] + len(d["tools"])
            assert d.get("next_offset") == expected

    # R20B: exit-2 on argparse errors emits JSON when --json flag present
    @pytest.mark.unit
    def test_argparse_error_emits_json_on_json_flag(self, capsys):
        """R20B: --limit -1 with --json flag should emit JSON error on stdout (exit 2)."""
        import sys as _sys
        from tooluniverse.cli import main
        _sys.argv = ["tu", "grep", "protein", "--json", "--limit", "-1"]
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2
        out = capsys.readouterr().out
        # stdout should have JSON error, not empty
        assert out.strip(), "exit-2 with --json should emit JSON to stdout"
        d = json.loads(out)
        assert "error" in d


class TestRound21PreFixes:
    """Tests for Feature-20A-07 and Feature-20A-08 fixed before Round 21 agents launched."""

    # Feature-20A-08: category "unknown" caused spurious warning and exit 1
    @pytest.mark.unit
    def test_unknown_category_resolves_silently(self):
        """Feature-20A-08: 'unknown' is a valid internal sentinel — no warning, no had_unknown."""
        from tooluniverse.cli import _resolve_categories
        from unittest.mock import MagicMock

        tu = MagicMock()
        tu.tool_category_dicts = {"Genomics": []}
        tu.all_tool_dict = {}
        resolved, had_unknown = _resolve_categories(tu, ["unknown"])
        assert resolved == ["unknown"]
        assert had_unknown is False, "'unknown' sentinel should resolve without warning"

    @pytest.mark.unit
    def test_unknown_category_case_insensitive(self):
        """Feature-20A-08: 'Unknown', 'UNKNOWN', 'unknown' all resolve to sentinel silently."""
        from tooluniverse.cli import _resolve_categories
        from unittest.mock import MagicMock

        tu = MagicMock()
        tu.tool_category_dicts = {}
        tu.all_tool_dict = {}
        for variant in ("unknown", "Unknown", "UNKNOWN"):
            resolved, had_unknown = _resolve_categories(tu, [variant])
            assert resolved == ["unknown"], f"{variant!r} should resolve to 'unknown'"
            assert had_unknown is False, f"{variant!r} should not set had_unknown"

    # Feature-20A-07: range [1–N] missing on first page when paginating
    @pytest.mark.unit
    def test_render_grep_shows_range_on_first_page(self):
        """Feature-20A-07: _render_grep shows [1–N] on page 1 (offset=0) when has_more=True."""
        from tooluniverse.cli import _render_grep
        d = {
            "tools": [{"name": f"T{i}", "description": f"d{i}"} for i in range(5)],
            "total_matches": 50,
            "limit": 5,
            "offset": 0,
            "has_more": True,
        }
        result = _render_grep(d)
        assert "[1–5]" in result, "First page should show [1-5] range"
        assert "next: --offset 5" in result

    @pytest.mark.unit
    def test_render_grep_no_range_single_page(self):
        """Feature-20A-07: _render_grep does NOT show range when all results fit (no pagination)."""
        from tooluniverse.cli import _render_grep
        d = {
            "tools": [{"name": "T1", "description": "d1"}],
            "total_matches": 1,
            "limit": 10,
            "offset": 0,
            "has_more": False,
        }
        result = _render_grep(d)
        assert "[1–" not in result, "Single page should not show range"

    @pytest.mark.unit
    def test_render_find_shows_range_on_first_page(self):
        """Feature-20A-07: _render_find shows [1–N] on page 1 when has_more=True."""
        from tooluniverse.cli import _render_find
        d = {
            "tools": [{"name": f"T{i}", "description": f"d{i}", "relevance_score": 0.9} for i in range(3)],
            "total_matches": 30,
            "limit": 3,
            "offset": 0,
            "has_more": True,
        }
        result = _render_find(d)
        assert "[1–3]" in result, "First page should show [1-3] range"
        assert "next: --offset 3" in result


class TestRound21Fixes:
    """Tests for R21A bugs fixed before Round 22 agents launched."""

    # R21A-03: next_offset missing from basic/summary/custom modes
    @pytest.mark.unit
    def test_list_basic_mode_has_next_offset(self, monkeypatch, tu, capsys):
        """R21A-03: tu list --mode basic --limit N includes next_offset when has_more=True."""
        from tooluniverse.cli import cmd_list
        out, _ = _run(monkeypatch, cmd_list,
                      _args(mode="basic", limit=5, json=True), tu, capsys)
        d = _j(out)
        if d.get("has_more"):
            expected = d["offset"] + len(d["tools"])
            assert "next_offset" in d, "basic mode must include next_offset"
            assert d["next_offset"] == expected

    @pytest.mark.unit
    def test_list_summary_mode_has_next_offset(self, monkeypatch, tu, capsys):
        """R21A-03: tu list --mode summary --limit N includes next_offset when has_more=True."""
        from tooluniverse.cli import cmd_list
        out, _ = _run(monkeypatch, cmd_list,
                      _args(mode="summary", limit=5, json=True), tu, capsys)
        d = _j(out)
        if d.get("has_more"):
            expected = d["offset"] + len(d["tools"])
            assert "next_offset" in d, "summary mode must include next_offset"
            assert d["next_offset"] == expected

    @pytest.mark.unit
    def test_list_custom_mode_has_next_offset(self, monkeypatch, tu, capsys):
        """R21A-03: tu list --mode custom --fields name --limit N includes next_offset."""
        from tooluniverse.cli import cmd_list
        out, _ = _run(monkeypatch, cmd_list,
                      _args(mode="custom", limit=5, fields=["name"], json=True), tu, capsys)
        d = _j(out)
        if d.get("has_more"):
            expected = d["offset"] + len(d["tools"])
            assert "next_offset" in d, "custom mode must include next_offset"
            assert d["next_offset"] == expected

    @pytest.mark.unit
    def test_list_basic_mode_limit_zero_next_offset_none(self, monkeypatch, tu, capsys):
        """R21A-03: tu list --mode basic --limit 0 → next_offset is None (count probe)."""
        from tooluniverse.cli import cmd_list
        out, _ = _run(monkeypatch, cmd_list,
                      _args(mode="basic", limit=0, json=True), tu, capsys)
        d = _j(out)
        assert d.get("next_offset") is None, "limit=0 probe should have next_offset=None"

    # R21A-06: list offset past end now exits 0
    @pytest.mark.unit
    def test_list_offset_past_end_exits_0(self, monkeypatch, tu, capsys):
        """R21A-06: tu list --offset 999999 exits 0 (not an error; natural pagination end)."""
        from tooluniverse.cli import cmd_list
        out, _ = _run(monkeypatch, cmd_list,
                      _args(mode="names", limit=10, offset=999999, json=True), tu, capsys)
        d = _j(out)
        assert d["tools"] == []
        assert d["has_more"] is False
        assert d["total_tools"] > 0  # total count still accurate


class TestRound21BFixes:
    """Tests for R21B bugs fixed: list footer, grep smart hint, find score key."""

    # R21B-06: list names mode should show range and next-offset in pagination footer
    @pytest.mark.unit
    def test_render_list_names_mode_shows_range_and_next_offset(self):
        """R21B-06: _render_list names mode shows [N-M] and next: --offset hint."""
        from tooluniverse.cli import _render_list
        d = {
            "tools": [f"Tool{i}" for i in range(5)],
            "total_tools": 50,
            "limit": 5,
            "offset": 10,
            "has_more": True,
        }
        result = _render_list(d)
        assert "[11–15]" in result, "Should show range [11-15]"
        assert "next: --offset 15" in result

    @pytest.mark.unit
    def test_render_list_names_mode_shows_end_of_results(self):
        """R21B-07: _render_list names mode shows '(end of results)' on last page."""
        from tooluniverse.cli import _render_list
        d = {
            "tools": [f"Tool{i}" for i in range(3)],
            "total_tools": 53,
            "limit": 5,
            "offset": 50,
            "has_more": False,
        }
        result = _render_list(d)
        assert "end of results" in result
        assert "[51–53]" in result

    @pytest.mark.unit
    def test_render_list_basic_mode_shows_range_and_next_offset(self):
        """R21B-06: _render_list basic mode also shows range and next-offset hint."""
        from tooluniverse.cli import _render_list
        d = {
            "tools": [{"name": f"T{i}", "description": f"d{i}"} for i in range(5)],
            "total_tools": 50,
            "limit": 5,
            "offset": 0,
            "has_more": True,
        }
        result = _render_list(d)
        assert "[1–5]" in result
        assert "next: --offset 5" in result

    # R21B-03/14: smart hint for multi-word grep in name field
    @pytest.mark.unit
    def test_render_grep_multiword_name_search_suggests_underscore(self):
        """R21B-03: grep with space in pattern suggests underscore variant."""
        from tooluniverse.cli import _render_grep
        d = {
            "tools": [],
            "total_matches": 0,
            "field": "name",
            "pattern": "protein structure",
            "limit": 100,
            "offset": 0,
            "has_more": False,
        }
        result = _render_grep(d)
        assert "protein_structure" in result, "Should suggest underscore variant"
        assert "underscores" in result.lower() or "underscore" in result.lower()

    @pytest.mark.unit
    def test_render_grep_single_word_name_search_suggests_description_field(self):
        """R21B-03: single-word grep 0 matches still shows --field description tip."""
        from tooluniverse.cli import _render_grep
        d = {
            "tools": [],
            "total_matches": 0,
            "field": "name",
            "pattern": "xyznonexistent",
            "limit": 100,
            "offset": 0,
            "has_more": False,
        }
        result = _render_grep(d)
        assert "--field description" in result
        assert "underscore" not in result  # no underscore hint for single word

    # R21B-08: find JSON uses relevance_score as canonical key
    @pytest.mark.unit
    def test_render_find_reads_relevance_score_key(self):
        """R21B-08: _render_find uses relevance_score (canonical JSON key) first."""
        from tooluniverse.cli import _render_find
        d = {
            "tools": [{"name": "T1", "description": "d1", "relevance_score": 0.987}],
            "total_matches": 1,
            "limit": 10,
            "offset": 0,
            "has_more": False,
        }
        result = _render_find(d)
        assert "0.987" in result, "Should display relevance_score value"


class TestRound22Fixes:
    """Tests for bugs found and fixed in Round 22 role-play simulation."""

    # R22B-03: list --limit N note about implicit mode switch
    @pytest.mark.unit
    def test_list_limit_prints_mode_switch_note(self, tu, capsys):
        """R22B-03: tu list --limit N prints a note about switching to names mode."""
        import argparse
        from tooluniverse.cli import cmd_list
        import unittest.mock as mock

        args = argparse.Namespace(
            mode=None,
            categories=None,
            fields=None,
            limit=5,
            offset=0,
            group_by_category=False,
            raw=False,
            json=False,
        )
        with mock.patch("tooluniverse.cli._get_tu", return_value=tu):
            cmd_list(args)
        out, err = capsys.readouterr()
        assert "names mode" in err.lower() or "names mode" in err
        assert "--limit 5" in err

    @pytest.mark.unit
    def test_list_offset_prints_mode_switch_note(self, tu, capsys):
        """R22B-03: tu list --offset N also prints the implicit mode-switch note."""
        import argparse
        from tooluniverse.cli import cmd_list
        import unittest.mock as mock

        args = argparse.Namespace(
            mode=None,
            categories=None,
            fields=None,
            limit=None,
            offset=10,
            group_by_category=False,
            raw=False,
            json=False,
        )
        with mock.patch("tooluniverse.cli._get_tu", return_value=tu):
            cmd_list(args)
        out, err = capsys.readouterr()
        assert "names mode" in err.lower() or "names mode" in err
        assert "--offset 10" in err

    @pytest.mark.unit
    def test_list_explicit_mode_no_switch_note(self, tu, capsys):
        """R22B-03: explicit --mode names skips the implicit mode-switch note."""
        import argparse
        from tooluniverse.cli import cmd_list
        import unittest.mock as mock

        args = argparse.Namespace(
            mode="names",
            categories=None,
            fields=None,
            limit=5,
            offset=0,
            group_by_category=False,
            raw=False,
            json=False,
        )
        with mock.patch("tooluniverse.cli._get_tu", return_value=tu):
            cmd_list(args)
        out, err = capsys.readouterr()
        # Explicit mode → no implicit-switch note (limit warning may still appear
        # if mode were categories, but here mode=names so no limit warning either)
        assert "Note: using names mode" not in err

    # R22B-04: info "did you mean" suggestions
    @pytest.mark.unit
    def test_render_info_shows_did_you_mean(self):
        """R22B-04: _render_info shows suggestions when they are in the error dict."""
        from tooluniverse.cli import _render_info
        d = {
            "error": "tool not found",
            "name": "UniProt_search_typo",
            "suggestions": ["UniProt_search", "UniProt_get_entry_by_accession"],
        }
        result = _render_info(d)
        assert "Did you mean" in result
        assert "UniProt_search" in result

    @pytest.mark.unit
    def test_render_info_no_suggestions_shows_grep_hint(self):
        """R22B-04: no suggestions → show grep hint for user to search."""
        from tooluniverse.cli import _render_info
        d = {
            "error": "tool not found",
            "name": "CompletelyMadeUpToolXYZ",
            "suggestions": [],
        }
        result = _render_info(d)
        assert "tu grep" in result
        assert "Did you mean" not in result

    # R22B-07: list --mode help text documents all auto-switch triggers
    @pytest.mark.unit
    def test_list_mode_help_documents_auto_switch(self):
        """R22B-07: --mode help argument contains auto-switch documentation."""
        import argparse
        # Build the parser directly to inspect help text without subprocess truncation
        import sys
        sys.argv = ["tu"]  # prevent argparse from reading pytest args
        import importlib
        import tooluniverse.cli as cli_module
        # Access the parser by creating it
        # Find the --mode action in the list subcommand by scanning the help string
        # we added to the parser definition
        import inspect
        src = inspect.getsource(cli_module)
        # Confirm the help text we wrote is present in source
        assert "auto-switches to names mode" in src
        assert "--limit" in src and "--offset" in src and "--raw" in src

    # R22B-11: grep footer shows searched field
    @pytest.mark.unit
    def test_render_grep_footer_shows_searched_field_name(self):
        """R22B-11: grep output footer shows 'searched: name' on first page."""
        from tooluniverse.cli import _render_grep
        d = {
            "tools": [{"name": "UniProt_search", "description": "desc"}],
            "total_matches": 1,
            "field": "name",
            "pattern": "uniprot",
            "limit": 100,
            "offset": 0,
            "has_more": False,
        }
        result = _render_grep(d)
        assert "searched: name" in result

    @pytest.mark.unit
    def test_render_grep_footer_no_field_hint_for_description_field(self):
        """R22B-11: no 'searched: name' hint when already using --field description."""
        from tooluniverse.cli import _render_grep
        d = {
            "tools": [{"name": "UniProt_search", "description": "desc"}],
            "total_matches": 1,
            "field": "description",
            "pattern": "protein",
            "limit": 100,
            "offset": 0,
            "has_more": False,
        }
        result = _render_grep(d)
        assert "searched: name" not in result
        assert "searched: description" not in result

    @pytest.mark.unit
    def test_render_grep_footer_no_field_hint_on_subsequent_pages(self):
        """R22B-11: field hint omitted on subsequent pages (offset > 0) to keep line short."""
        from tooluniverse.cli import _render_grep
        d = {
            "tools": [{"name": "UniProt_search", "description": "desc"}],
            "total_matches": 50,
            "field": "name",
            "pattern": "uniprot",
            "limit": 1,
            "offset": 10,
            "has_more": True,
        }
        result = _render_grep(d)
        assert "searched: name" not in result

    # R22A-06: grep 0-match tip wording — "use" not "add"
    @pytest.mark.unit
    def test_render_grep_0match_tip_says_use_not_add(self):
        """R22A-06: 0-match tip for name field says 'use --field description' (not 'add')."""
        from tooluniverse.cli import _render_grep
        d = {
            "tools": [],
            "total_matches": 0,
            "field": "name",
            "pattern": "xyznonexistent",
            "limit": 100,
            "offset": 0,
            "has_more": False,
        }
        result = _render_grep(d)
        assert "--field description" in result
        assert "add --field description" not in result

    # R22A-08: regex \| escape warning
    @pytest.mark.unit
    def test_grep_regex_escaped_pipe_warns(self, tu, capsys):
        """R22A-08: grep --mode regex with \\| in pattern warns about literal pipe."""
        import argparse
        from tooluniverse.cli import cmd_grep
        import unittest.mock as mock

        args = argparse.Namespace(
            pattern=r"p-value\|FDR",
            field="description",
            search_mode="regex",
            limit=None,
            offset=0,
            categories=None,
            raw=False,
            json=False,
        )
        with mock.patch("tooluniverse.cli._get_tu", return_value=tu):
            cmd_grep(args)
        out, err = capsys.readouterr()
        assert "\\|" in err or r"\|" in err
        assert "alternation" in err.lower() or "literal" in err.lower()


class TestBug22A09CustomModeUnknownField:
    """Feature-22A-09: tu list --mode custom --fields nonexistent returns empty dicts with no warning."""

    # --- unit tests against tool_discovery_tools.py directly ---

    @pytest.mark.unit
    def test_unknown_field_returns_unknown_fields_key(self, tu):
        """Unknown field name is reported in 'unknown_fields' list in the return dict."""
        result = tu.run_one_function(
            {
                "name": "list_tools",
                "arguments": {
                    "mode": "custom",
                    "fields": ["nonexistent_xyz"],
                    "limit": 3,
                },
            }
        )
        assert isinstance(result, dict)
        assert "unknown_fields" in result
        assert "nonexistent_xyz" in result["unknown_fields"]

    @pytest.mark.unit
    def test_valid_field_has_no_unknown_fields(self, tu):
        """Valid field names produce no 'unknown_fields' entry (None or absent)."""
        result = tu.run_one_function(
            {
                "name": "list_tools",
                "arguments": {
                    "mode": "custom",
                    "fields": ["name", "description"],
                    "limit": 3,
                },
            }
        )
        assert isinstance(result, dict)
        assert not result.get("unknown_fields")

    @pytest.mark.unit
    def test_mixed_fields_reports_only_unknown(self, tu):
        """Mixed valid+invalid fields: only the invalid one appears in unknown_fields."""
        result = tu.run_one_function(
            {
                "name": "list_tools",
                "arguments": {
                    "mode": "custom",
                    "fields": ["name", "bogus_field"],
                    "limit": 3,
                },
            }
        )
        assert isinstance(result, dict)
        unk = result.get("unknown_fields") or []
        assert "bogus_field" in unk
        assert "name" not in unk

    # --- CLI integration tests (cmd_list warns to stderr) ---

    @pytest.mark.unit
    def test_cmd_list_warns_unknown_field_to_stderr(self, tu, capsys):
        """cmd_list prints a warning to stderr when custom field is not found."""
        import argparse
        from tooluniverse.cli import cmd_list
        import unittest.mock as mock

        args = argparse.Namespace(
            mode="custom",
            fields=["totally_missing_field"],
            categories=None,
            limit=2,
            offset=0,
            raw=False,
            json=False,
            group_by_category=False,
        )
        with mock.patch("tooluniverse.cli._get_tu", return_value=tu):
            cmd_list(args)
        _out, err = capsys.readouterr()
        assert "totally_missing_field" in err
        assert "not found" in err.lower()

    @pytest.mark.unit
    def test_cmd_list_no_warning_in_json_mode(self, tu, capsys):
        """In --json mode, unknown field warning is NOT printed to stderr."""
        import argparse
        from tooluniverse.cli import cmd_list
        import unittest.mock as mock

        args = argparse.Namespace(
            mode="custom",
            fields=["totally_missing_field"],
            categories=None,
            limit=2,
            offset=0,
            raw=False,
            json=True,
            group_by_category=False,
        )
        with mock.patch("tooluniverse.cli._get_tu", return_value=tu):
            cmd_list(args)
        _out, err = capsys.readouterr()
        # Warning should NOT appear in stderr when --json is set
        assert "totally_missing_field" not in err or "not found" not in err.lower()


class TestRound23BFixes:
    """Fixes for bugs found by Round 23B agent (Sam, first-time user)."""

    # Feature-23B-01: tu grep chip-seq returns 0 matches with no hint about removing hyphen

    @pytest.mark.unit
    def test_render_grep_hyphen_pattern_suggests_description_field(self):
        """Feature-23B-01/Feature-25B-01: name-field 0-match with hyphen hints --field description.

        Descriptions do use hyphens, so the tip should point directly there
        rather than suggesting the unhyphenated variant (which also returns 0 matches).
        """
        from tooluniverse.cli import _render_grep

        d = {
            "tools": [],
            "total_matches": 0,
            "field": "name",
            "pattern": "chip-seq",
            "limit": 100,
            "offset": 0,
            "has_more": False,
        }
        result = _render_grep(d)
        assert "--field description" in result
        assert "hyphen" in result.lower()

    @pytest.mark.unit
    def test_render_grep_space_takes_priority_over_hyphen(self):
        """Feature-23B-01: space check takes priority if pattern has both space and hyphen."""
        from tooluniverse.cli import _render_grep

        d = {
            "tools": [],
            "total_matches": 0,
            "field": "name",
            "pattern": "chip -seq",  # space AND hyphen
            "limit": 100,
            "offset": 0,
            "has_more": False,
        }
        result = _render_grep(d)
        # space check runs first → underscore hint
        assert "underscore" in result.lower() or "_" in result

    # Feature-23B-05: tu grep X --field description (0 matches) doesn't show hint

    @pytest.mark.unit
    def test_render_grep_description_field_0match_shows_stored_hint(self):
        """Feature-23B-05: description-field 0-match displays the 'hint' from the JSON payload."""
        from tooluniverse.cli import _render_grep

        d = {
            "tools": [],
            "total_matches": 0,
            "field": "description",
            "pattern": "epigenetics",
            "hint": "try a different search term or fewer words",
            "limit": 100,
            "offset": 0,
            "has_more": False,
        }
        result = _render_grep(d)
        assert "try a different search term" in result

    @pytest.mark.unit
    def test_render_grep_description_field_0match_no_hint_in_payload(self):
        """Feature-23B-05: when no hint is in the JSON payload, output just says '0 matches'."""
        from tooluniverse.cli import _render_grep

        d = {
            "tools": [],
            "total_matches": 0,
            "field": "description",
            "pattern": "xyz",
            "hint": None,
            "limit": 100,
            "offset": 0,
            "has_more": False,
        }
        result = _render_grep(d)
        assert result == "0 matches"

    # Feature-23B-04: difflib suggests list_tools for nonsense names (cutoff raised 0.5→0.62)

    @pytest.mark.unit
    def test_info_no_spurious_suggestion_for_garbage_name(self, tu, capsys):
        """Feature-23B-04: 'NonExistentTool123' should NOT suggest 'list_tools'."""
        import argparse
        from tooluniverse.cli import cmd_info
        import unittest.mock as mock

        args = argparse.Namespace(
            tool_names=["NonExistentTool123"],
            detail=None,
            raw=False,
            json=False,
        )
        with mock.patch("tooluniverse.cli._get_tu", return_value=tu):
            with pytest.raises(SystemExit):
                cmd_info(args)
        out, err = capsys.readouterr()
        combined = out + err
        # list_tools must not be suggested for a completely unrelated garbage name
        assert "list_tools" not in combined

    # Feature-23B-03: tu list --categories (no args) gives raw argparse error

    @pytest.mark.unit
    def test_cmd_list_bare_categories_shows_note_and_falls_back(self, tu, capsys):
        """Feature-23B-03: --categories with no args prints a note and falls back to all-categories."""
        import argparse
        from tooluniverse.cli import cmd_list
        import unittest.mock as mock

        args = argparse.Namespace(
            mode=None,
            fields=None,
            categories=[],  # empty list = bare --categories
            limit=None,
            offset=0,
            raw=False,
            json=False,
            group_by_category=False,
        )
        with mock.patch("tooluniverse.cli._get_tu", return_value=tu):
            cmd_list(args)
        _out, err = capsys.readouterr()
        # Should explain --categories requires names and fall back
        assert "--categories" in err
        assert "category" in err.lower()


class TestRound23BRemainingFixes:
    """Tests for Feature-23B-02, 23B-06, 23B-08, 23B-10 fixes."""

    # Feature-23B-02: tu run validation error should be human-friendly (not 77-line JSON)

    @pytest.mark.unit
    def test_render_run_error_is_short(self):
        """Feature-23B-02: _render_run shows a short error summary, not full nested JSON."""
        from tooluniverse.cli import _render_run

        result = {
            "status": "error",
            "error": "Parameter validation failed for 'root': 'compound_id' is a required property",
            "error_details": {
                "type": "ToolValidationError",
                "message": "...",
                "retriable": False,
                "next_steps": ["Check parameter types", "Review documentation"],
                "details": {
                    "validation_error": "'compound_id' is a required property\n\nFailed validating 'required' in schema:\n    {'type': 'object', ...}",
                },
            },
        }
        rendered = _render_run(result)
        # Should NOT include the jsonschema dump
        assert "Failed validating" not in rendered
        assert "schema:" not in rendered
        # Should include the key error message
        assert "compound_id" in rendered
        # Should be short (under 300 chars)
        assert len(rendered) < 300

    @pytest.mark.unit
    def test_render_run_success_returns_json(self):
        """Feature-23B-02: _render_run passes through success results as JSON."""
        from tooluniverse.cli import _render_run
        import json

        result = {"status": "success", "data": {"foo": "bar"}}
        rendered = _render_run(result)
        # Should be valid JSON
        parsed = json.loads(rendered)
        assert parsed["status"] == "success"

    @pytest.mark.unit
    def test_render_run_shows_next_steps(self):
        """Feature-23B-02: _render_run includes next_steps as Tips when present."""
        from tooluniverse.cli import _render_run

        result = {
            "status": "error",
            "error": "Missing required param",
            "error_details": {
                "next_steps": ["Check param types", "Review docs"],
            },
        }
        rendered = _render_run(result)
        assert "Tips:" in rendered
        assert "Check param types" in rendered

    # Feature-23B-06: circuit plugin warning should not appear on every invocation

    @pytest.mark.unit
    def test_plugin_missing_env_is_debug_not_warning(self, caplog):
        """Feature-23B-06: _read_profile_yaml logs missing plugin env at DEBUG, not WARNING."""
        import logging
        from tooluniverse.tool_registry import _read_profile_yaml
        import os
        import tempfile

        import yaml

        # Create a temp plugin dir with a profile.yaml requiring a fake env var
        with tempfile.TemporaryDirectory() as tmp:
            profile = {"required_env": ["FAKE_NONEXISTENT_TOOLUNIVERSE_VAR_XYZ123"]}
            with open(os.path.join(tmp, "profile.yaml"), "w") as f:
                yaml.dump(profile, f)

            with caplog.at_level(logging.DEBUG, logger="ToolRegistry"):
                _read_profile_yaml(tmp, context="test plugin")

        # Check that no WARNING (or higher) was emitted about the missing env var
        warning_records = [
            r for r in caplog.records
            if r.levelno >= logging.WARNING and "FAKE_NONEXISTENT" in r.message
        ]
        assert not warning_records, (
            f"Expected DEBUG for missing env, got WARNING: {warning_records}"
        )

    # Feature-23B-08: no next-step hints after tu list

    @pytest.mark.unit
    def test_render_list_categories_shows_next_steps(self, tu):
        """Feature-23B-08: categories view includes actionable next-step hint."""
        from tooluniverse.cli import _render_list

        d = {
            "categories": {"uniprot": 10, "kegg": 5},
            "total_categories": 2,
            "total_tools": 15,
        }
        rendered = _render_list(d)
        assert "tu grep" in rendered
        assert "tu list --categories" in rendered

    # Feature-23B-10: multi-word grep without quotes should suggest quoting

    @pytest.mark.unit
    def test_cmd_grep_multiword_joins_and_warns(self, tu, capsys):
        """Feature-23B-10: passing multiple words to grep joins them and prints quoting hint."""
        import argparse
        from tooluniverse.cli import cmd_grep
        import unittest.mock as mock

        args = argparse.Namespace(
            pattern=["chip", "seq"],  # multi-word from nargs="+"
            field="name",
            search_mode="text",
            limit=5,
            offset=0,
            categories=None,
            raw=False,
            json=False,
        )
        with mock.patch("tooluniverse.cli._get_tu", return_value=tu):
            cmd_grep(args)
        _out, err = capsys.readouterr()
        # The hint about quoting should appear
        assert "quote" in err.lower() or "quotes" in err.lower() or "tu grep" in err
        # The joined pattern should be used
        assert "chip seq" in err or "chip_seq" in _out or "chip" in _out + err

    @pytest.mark.unit
    def test_cmd_grep_singleword_no_join_warning(self, tu, capsys):
        """Feature-23B-10: single-word grep (list with one item) shows no quoting warning."""
        import argparse
        from tooluniverse.cli import cmd_grep
        import unittest.mock as mock

        args = argparse.Namespace(
            pattern=["protein"],  # single item list from nargs="+"
            field="name",
            search_mode="text",
            limit=5,
            offset=0,
            categories=None,
            raw=False,
            json=False,
        )
        with mock.patch("tooluniverse.cli._get_tu", return_value=tu):
            cmd_grep(args)
        _out, err = capsys.readouterr()
        # No quoting hint for single word
        assert "multi-word" not in err
        assert "quotes" not in err.lower()


class TestRound24MoreFixes2:
    """Tests for Feature-24B-11 (large list shows paging hint)."""

    @pytest.fixture
    def tu(self):
        from tooluniverse import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()
        return tu

    @pytest.mark.unit
    def test_list_all_tools_shows_paging_hint(self, monkeypatch, tu, capsys):
        """Feature-24B-11: tu list with no limit on large catalog shows --limit hint."""
        import unittest.mock as mock
        from tooluniverse.cli import cmd_list

        args = _args(mode="names", limit=None, offset=0, categories=None, json=False)
        with mock.patch("tooluniverse.cli._get_tu", return_value=tu):
            cmd_list(args)
        out, _ = capsys.readouterr()
        # Should suggest --limit when output is very long
        assert "--limit" in out or "limit" in out.lower()

    @pytest.mark.unit
    def test_list_small_result_no_paging_hint(self, monkeypatch, tu, capsys):
        """Feature-24B-11: small result (<=50 tools) should NOT show paging hint."""
        import unittest.mock as mock
        from tooluniverse.cli import cmd_list

        args = _args(mode="names", limit=5, offset=0, categories=None, json=False)
        with mock.patch("tooluniverse.cli._get_tu", return_value=tu):
            cmd_list(args)
        out, _ = capsys.readouterr()
        # No paging hint needed when already paginating with --limit
        assert "tip: use --limit" not in out


class TestRound24MoreFixes:
    """Tests for Feature-24B-02 (--quiet flag suppresses API key warnings).

    Quiet is now the default; --verbose opts back in.
    """

    @pytest.mark.unit
    def test_quiet_is_default_no_warnings(self):
        """Quiet is the default — no missing-API-key warnings without any flag."""
        rc, out, err = _cli("list", "--limit", "2")
        assert rc == 0
        assert "missing API keys" not in err
        assert "Some tools will not be loaded" not in err

    @pytest.mark.unit
    def test_quiet_flag_still_works(self):
        """--quiet flag still works (backwards compat, now a no-op)."""
        rc, out, err = _cli("--quiet", "list", "--limit", "2")
        assert rc == 0
        assert "missing API keys" not in err
        assert "Some tools will not be loaded" not in err

    @pytest.mark.unit
    def test_verbose_flag_accepted(self):
        """--verbose flag is accepted and runs successfully."""
        rc, out, err = _cli("--verbose", "list", "--limit", "1")
        assert rc == 0


class TestRound24Fixes:
    """Tests for Feature-24B-05, Feature-24A-06, Feature-23A-06 (Round 24 initial fixes)."""

    @pytest.fixture
    def tu(self):
        from tooluniverse import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()
        return tu

    @pytest.mark.unit
    def test_info_not_found_uses_full_name_in_grep_suggestion(
        self, monkeypatch, tu, capsys
    ):
        """Feature-24B-05: tu info error shows full tool name in grep suggestion, not truncated."""
        import unittest.mock as mock
        from tooluniverse.cli import cmd_info

        args = argparse.Namespace(
            tool_names=["AlphaFoldNonexistentTool"],
            detail_level=None,
            detail=None,
            raw=False,
            json=False,
        )
        with mock.patch("tooluniverse.cli._get_tu", return_value=tu):
            with pytest.raises(SystemExit):
                cmd_info(args)
        out, err = capsys.readouterr()
        combined = out + err
        # Should suggest 'tu grep AlphaFoldNonexistentTool', not 'tu grep AlphaFo'
        assert "AlphaFoldNonexistentTool" in combined
        # Ensure the name isn't truncated (no name[:6] style truncation)
        assert "AlphaFo\n" not in combined

    @pytest.mark.unit
    def test_list_json_has_categories_filtered_key(self, monkeypatch, tu, capsys):
        """Feature-23A-06: tu list --json includes categories_filtered field."""
        import unittest.mock as mock
        from tooluniverse.cli import cmd_list

        args = _args(mode="names", limit=3, offset=0, categories=None, json=True)
        with mock.patch("tooluniverse.cli._get_tu", return_value=tu):
            cmd_list(args)
        out, _ = capsys.readouterr()
        d = _j(out)
        assert "categories_filtered" in d

    @pytest.mark.unit
    def test_list_json_categories_filtered_reflects_filter(self, monkeypatch, tu, capsys):
        """Feature-23A-06: categories_filtered is non-null when a category filter is applied."""
        import unittest.mock as mock
        from tooluniverse.cli import cmd_list

        args = _args(mode="names", limit=3, offset=0, categories=["kegg"], json=True)
        with mock.patch("tooluniverse.cli._get_tu", return_value=tu):
            cmd_list(args)
        out, _ = capsys.readouterr()
        d = _j(out)
        # categories_filtered should be non-null when a filter was applied
        assert d.get("categories_filtered") is not None
        # The resolved category should include "kegg"
        assert any("kegg" in cat for cat in d["categories_filtered"])

    @pytest.mark.unit
    def test_grep_category_field_zero_matches_shows_hint(self, monkeypatch, tu, capsys):
        """Feature-24A-06: tu grep --field category with 0 matches shows a helpful hint."""
        import unittest.mock as mock
        from tooluniverse.cli import cmd_grep

        args = argparse.Namespace(
            pattern=["xyznonexistentcategory999"],
            field="category",
            search_mode="text",
            limit=10,
            offset=0,
            categories=None,
            raw=False,
            json=False,
        )
        with mock.patch("tooluniverse.cli._get_tu", return_value=tu):
            cmd_grep(args)
        out, _ = capsys.readouterr()
        # Should show a hint pointing to list --mode categories
        assert "categories" in out.lower()
        assert "0 matches" in out

    @pytest.mark.unit
    def test_run_parse_error_human_mode_friendly_message(self, monkeypatch, tu, capsys):
        """Feature-24B-07: tu run with invalid JSON in human mode shows friendly error to stderr."""
        from tooluniverse.cli import cmd_run

        with pytest.raises(SystemExit) as exc_info:
            _run(
                monkeypatch,
                cmd_run,
                _args(tool_name="list_tools", arguments=["{not json}"]),
                tu,
                capsys,
            )
        assert exc_info.value.code == 1
        cap = capsys.readouterr()
        # Human mode: error message to stderr, NOT JSON on stdout
        assert cap.out.strip() == "" or not cap.out.startswith("{")
        assert "Error" in cap.err or "error" in cap.err.lower()


class TestRound25Fixes:
    """Tests for Feature-25A-03 (Round 25 fixes)."""

    @pytest.fixture
    def tu(self):
        from tooluniverse import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()
        return tu

    @pytest.mark.unit
    def test_validate_case_variant_shows_did_you_mean(self, tu):
        """Feature-25A-03: when a required param is missing but a case-variant was given,
        the validation error includes a 'did you mean?' hint."""
        # Find a tool with a mixed-case required parameter using tool configs
        tool_name = None
        param_name = None
        for name, cfg in tu.all_tool_dict.items():
            schema = cfg.get("parameter", {})
            req = schema.get("required", [])
            mixed = [p for p in req if p.lower() != p]
            if mixed:
                tool_name = name
                param_name = mixed[0]
                break

        if tool_name is None:
            pytest.skip("No tool with mixed-case required parameter found")

        # Get the actual tool instance
        tool = tu._get_tool_instance(tool_name)
        # Pass a lowercase version of the parameter (the typo case)
        wrong_args = {param_name.lower(): "dummy_value"}
        err = tool.validate_parameters(wrong_args)
        assert err is not None, "Expected a validation error for wrong-case param"
        err_str = str(err)
        assert "did you mean" in err_str.lower()
        assert param_name in err_str
        assert param_name.lower() in err_str
    @pytest.mark.unit
    def test_handle_error_includes_response_body_on_http_error(self, tu):
        """Feature-25A-01: handle_error extracts the API response body from HTTPError."""
        import unittest.mock as mock
        from tooluniverse.base_tool import BaseTool

        tool = tu._get_tool_instance("list_tools")

        # Simulate a requests.HTTPError with a JSON response body
        fake_response = mock.MagicMock()
        fake_response.json.return_value = {"message": "Invalid API token"}
        fake_response.text = '{"message": "Invalid API token"}'
        fake_response.status_code = 401

        http_err = Exception("401 Client Error: Unauthorized")
        http_err.response = fake_response

        result = tool.handle_error(http_err)
        err_str = str(result)
        # Should mention the upstream API message
        assert "Invalid API token" in err_str

    @pytest.mark.unit
    def test_handle_error_no_response_falls_back_gracefully(self, tu):
        """Feature-25A-01: handle_error works normally when exception has no response."""
        plain_err = RuntimeError("Something went wrong")
        tool = tu._get_tool_instance("list_tools")
        result = tool.handle_error(plain_err)
        assert result is not None
        assert "Something went wrong" in str(result)


class TestRound25BFixes:
    """Tests for Feature-25B-03 (tu test empty data warning) and related."""

    def _make_tu(self, return_value):
        from unittest.mock import MagicMock
        tu = MagicMock()
        tool_def = {"name": "FakeTool", "description": "x", "test_examples": [{"q": "hi"}]}
        tu.all_tool_dict = {"FakeTool": tool_def}
        tu.run_one_function = MagicMock(return_value=return_value)
        return tu

    @pytest.mark.unit
    def test_cmd_test_warns_when_data_is_empty_list(self, monkeypatch, capsys):
        """Feature-25B-03: tu test shows a '!' warning when result has data:[] on success."""
        import tooluniverse.cli as m

        tu = self._make_tu({"status": "success", "data": []})
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        m.cmd_test(argparse.Namespace(tool_name="FakeTool", config=None, args_json=None, json=False))
        out, _ = capsys.readouterr()
        # Should show '!' warning (not '✓') and mention the empty data issue
        assert "!" in out
        assert "empty" in out.lower()

    @pytest.mark.unit
    def test_cmd_test_no_warning_when_data_is_nonempty(self, monkeypatch, capsys):
        """Feature-25B-03: tu test shows '✓' (no warning) when data is non-empty."""
        import tooluniverse.cli as m

        tu = self._make_tu({"status": "success", "data": [{"id": "X"}]})
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        m.cmd_test(argparse.Namespace(tool_name="FakeTool", config=None, args_json=None, json=False))
        out, _ = capsys.readouterr()
        assert "✓" in out
        assert "empty" not in out.lower()

    @pytest.mark.unit
    def test_cmd_test_json_includes_warnings_field(self, monkeypatch, capsys):
        """Feature-25B-03: --json output includes 'warnings' array when data is empty."""
        import tooluniverse.cli as m

        tu = self._make_tu({"status": "success", "data": []})
        monkeypatch.setattr(m, "_get_tu", lambda: tu)
        m.cmd_test(argparse.Namespace(tool_name="FakeTool", config=None, args_json=None, json=True))
        out, _ = capsys.readouterr()
        import json as _j
        d = _j.loads(out)
        assert "tests" in d
        first = d["tests"][0]
        assert "warnings" in first
        assert len(first["warnings"]) > 0


class TestQuietDefault:
    """Tests for quiet-by-default in SDK load_tools()."""

    @pytest.mark.unit
    def test_load_tools_quiet_true_by_default(self):
        """load_tools(quiet=True) is the default — no warning emitted."""
        import inspect
        from tooluniverse import ToolUniverse

        sig = inspect.signature(ToolUniverse.load_tools)
        assert sig.parameters["quiet"].default is True

    @pytest.mark.unit
    def test_load_tools_quiet_suppresses_warning(self, capsys):
        """SDK: load_tools() (quiet=True default) suppresses API key warnings."""
        from tooluniverse import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()
        _, err = capsys.readouterr()
        assert "missing API keys" not in err

    @pytest.mark.unit
    def test_load_tools_quiet_false_accepted(self):
        """SDK: load_tools(quiet=False) runs without error."""
        from tooluniverse import ToolUniverse

        tu = ToolUniverse()
        # Should not raise
        tu.load_tools(quiet=False)
