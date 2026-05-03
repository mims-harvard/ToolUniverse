"""
tu — ToolUniverse CLI

Human-friendly command-line interface covering the same functionality as the
compact mode available in the ToolUniverse MCP server.

Subcommands:
    list    List available tools (mirrors list_tools)
    grep    Search by text/regex pattern (mirrors grep_tools)
    info    Get tool details (mirrors get_tool_info)
    find    Find tools by natural-language query (mirrors find_tools)
    run     Execute a tool (mirrors execute_tool, same interface)
    test    Test a tool with example inputs and report pass/fail
    status  Show current ToolUniverse status
    build   Regenerate the static lazy registry
    serve   Start the MCP stdio server (same as `tooluniverse`)
"""

import contextlib
import difflib
import json
import os
import sys
import argparse
from typing import Any

try:
    from importlib.metadata import version as _pkg_version

    _TU_VERSION = _pkg_version("tooluniverse")
except Exception:
    _TU_VERSION = "unknown"

# Redirect ToolUniverse logger to stderr so JSON output on stdout stays clean.
# Set env var early so it takes effect even if logging_config is imported
# before _get_tu() is called (e.g., by pytest or other imports).
os.environ.setdefault("TOOLUNIVERSE_STDIO_MODE", "1")

# Skip the heavy MCP/fastmcp/http-client imports that tooluniverse/__init__.py
# pulls in unconditionally — the CLI never needs them (tu serve loads smcp
# explicitly inside cmd_serve).  This saves ~480 ms on every invocation.
# Users can opt out with: TOOLUNIVERSE_LIGHT_IMPORT=0 tu <command>
os.environ.setdefault("TOOLUNIVERSE_LIGHT_IMPORT", "1")

_TRUNC = 60  # max description chars in table output


def _non_neg_int(value: str) -> int:
    """Argparse type that rejects negative integers (used for --offset and --limit)."""
    try:
        n = int(value)
    except (ValueError, TypeError):
        raise argparse.ArgumentTypeError(f"invalid int value: '{value}'")
    if n < 0:
        raise argparse.ArgumentTypeError(f"value must be >= 0, got {n}")
    return n


def _get_tu():
    """Lazy-initialize a ToolUniverse instance."""
    # Reconfigure logger to stderr and suppress INFO messages in CLI mode.
    # The CLI has its own status output; library-level info logs are noise.
    try:
        import logging
        from tooluniverse.logging_config import reconfigure_for_stdio

        reconfigure_for_stdio()
        logging.getLogger("tooluniverse").setLevel(logging.WARNING)
    except Exception:
        pass

    from tooluniverse import ToolUniverse

    tu = ToolUniverse()
    if not tu.all_tool_dict:
        tu._auto_load_tools_if_empty()
    return tu


@contextlib.contextmanager
def _status_to_stderr():
    """Route print() status messages to stderr so stdout stays pure JSON."""
    old_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        yield
    finally:
        sys.stdout = old_stdout


def _compact(d: dict) -> dict:
    """Remove keys whose value is None so optional params are truly omitted."""
    return {k: v for k, v in d.items() if v is not None}


# ── render functions ────────────────────────────────────────────────────────────


def _trunc(s: str, n: int = _TRUNC) -> str:
    """Truncate string to n chars, appending '…' if truncated."""
    if not s:
        return ""
    s = s.replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def _render_list(d: dict) -> str:
    """Render list_tools result as human-readable text."""
    if "error" in d:
        return f"Error: {d['error']}"
    lines = []

    # categories mode: two-column table sorted by count
    # Identify by "categories" dict key (absent in names/basic/summary which use "tools")
    if "categories" in d and "tools" not in d:
        cats = d["categories"]
        sorted_cats = sorted(cats.items(), key=lambda x: -x[1])
        if not sorted_cats:
            return "(no categories)"
        col1 = max(len(k) for k, _ in sorted_cats)
        col1 = max(col1, 8)
        lines.append(f"{'category':<{col1}}  {'tools':>5}")
        lines.append("─" * (col1 + 8))
        for cat, cnt in sorted_cats:
            lines.append(f"{cat:<{col1}}  {cnt:>5}")
        total = sum(cats.values())
        lines.append(f"\n{len(cats)} categories · {total} tools")
        # Feature-23B-08: add actionable next-step hints after the categories overview
        lines.append(
            "Next: `tu grep <term>` to search, `tu list --categories <name>` to filter, "
            "`tu find '<query>'` for natural-language search"
        )
        return "\n".join(lines)

    # by_category mode: section per category with indented tool names
    if "tools_by_category" in d:
        by_cat = d["tools_by_category"]
        if not by_cat:
            return "(no categories)"
        total = d.get("total_tools", 0)
        limit_val = d.get("limit")
        # When limit=0, all per-category slices are empty — show just the category names
        if limit_val == 0:
            cats = sorted(by_cat.keys())
            lines.append(f"{len(cats)} categories  (limit=0, tool names suppressed)")
            for cat in cats:
                lines.append(f"  {cat}")
            return "\n".join(lines)
        for cat, cat_tools in sorted(by_cat.items()):
            n = len(cat_tools)
            lines.append(f"\n[{cat}]  ({n} {'tool' if n == 1 else 'tools'})")
            for t in cat_tools:
                name = t.get("name", t) if isinstance(t, dict) else t
                desc = _trunc(t.get("description", "")) if isinstance(t, dict) else ""
                lines.append(f"  {name}  {desc}" if desc else f"  {name}")
        limit_note = (
            f"  (limit={limit_val} tools per category)" if limit_val is not None else ""
        )
        lines.append(f"\n{len(by_cat)} categories · {total} tools{limit_note}")
        return "\n".join(lines)

    # names mode: plain list with summary
    tools = d.get("tools", [])
    if not tools:
        total = d.get("total_tools", 0)
        offset = d.get("offset", 0)
        limit_val = d.get("limit")
        if limit_val == 0 and total:
            return f"0 of {total} tools (limit=0, no results shown)"
        if offset and total:
            return f"0 of {total} tools (offset past end — use --offset < {total})"
        return f"(no tools)  total={total}"

    # R21B-06/07: build pagination footer consistent with grep/find.
    def _list_footer(count, total, offset, has_more):
        first = offset + 1
        last = offset + count
        range_str = f"  [{first}–{last}]" if (offset or has_more) else ""
        if has_more:
            next_off = offset + count
            more_hint = f"  (more — next: --offset {next_off})"
        elif offset and count:
            more_hint = "  (end of results)"
        elif count == total and total > 50:
            # Feature-24B-11: large unfiltered list — suggest paginating with --limit
            more_hint = (
                "  (tip: use --limit N to paginate, or --categories <name> to filter)"
            )
        else:
            more_hint = ""
        return f"\n{count} of {total} tools{range_str}{more_hint}"

    if isinstance(tools[0], str):
        for name in tools:
            lines.append(name)
        total = d.get("total_tools", len(tools))
        has_more = d.get("has_more", False)
        offset = d.get("offset", 0)
        lines.append(_list_footer(len(tools), total, offset, has_more))
        return "\n".join(lines)

    # basic/summary/custom mode: name + optional description
    col1 = max((len(t.get("name", "")) for t in tools), default=8)
    col1 = max(col1, 8)
    if any("type" in t and "has_parameters" in t for t in tools):
        # summary mode: name + type + has_parameters + description
        col_type = max((len(str(t.get("type", ""))) for t in tools), default=4)
        col_type = max(col_type, 4)
        lines.append(
            f"{'name':<{col1}}  {'type':<{col_type}}  {'params':<5}  description"
        )
        lines.append("─" * (col1 + 2 + col_type + 2 + 5 + 2 + _TRUNC))
        for t in tools:
            has_p = "yes" if t.get("has_parameters") else "no"
            lines.append(
                f"{t.get('name', ''):<{col1}}  {str(t.get('type', '')):<{col_type}}  {has_p:<5}  {_trunc(t.get('description', ''))}"
            )
    elif any("description" in t for t in tools):
        lines.append(f"{'name':<{col1}}  description")
        lines.append("─" * (col1 + 2 + _TRUNC))
        for t in tools:
            lines.append(
                f"{t.get('name', ''):<{col1}}  {_trunc(t.get('description', ''))}"
            )
    else:
        # custom mode with no description: build a table from the actual keys present
        all_keys = list(dict.fromkeys(k for t in tools for k in t)) if tools else []
        if all_keys:
            col_widths = {
                k: max(len(k), max((len(str(t.get(k, ""))) for t in tools), default=0))
                for k in all_keys
            }
            header = "  ".join(f"{k:<{col_widths[k]}}" for k in all_keys)
            lines.append(header)
            lines.append("─" * len(header))
            for t in tools:
                lines.append(
                    "  ".join(f"{str(t.get(k, '')):<{col_widths[k]}}" for k in all_keys)
                )
        else:
            for t in tools:
                lines.append(str(t))
    total = d.get("total_tools", len(tools))
    has_more = d.get("has_more", False)
    offset = d.get("offset", 0)
    lines.append(_list_footer(len(tools), total, offset, has_more))
    return "\n".join(lines)


def _render_grep(d: dict) -> str:
    """Render grep_tools result as two-column name + description table."""
    if "error" in d:
        return f"Error: {d['error']}"
    tools = d.get("tools", [])
    total = d.get("total_matches", 0)
    if not tools:
        if total > 0:
            if d.get("limit") == 0:
                return f"0 of {total} matches (limit=0, no results shown)"
            return f"0 of {total} matches (offset past end — use --offset < {total})"
        # Feature-R13A-01 / R21B-03: context-sensitive hints for 0 name-field matches.
        if d.get("field") == "name":
            pattern = d.get("pattern", "")
            if " " in pattern:
                # R21B-03: multi-word name search always fails — names use underscores.
                underscore_hint = pattern.replace(" ", "_")
                return (
                    f"0 matches  (tip: tool names use underscores — try "
                    f"'{underscore_hint}', or use --field description)"
                )
            if "-" in pattern:
                # Feature-23B-01/Feature-25B-01: tool names don't use hyphens, but descriptions
                # do. Point directly to --field description rather than the unhyphenated
                # name variant (which often also returns 0 matches in the name field).
                return (
                    f"0 matches  (tip: tool names don't use hyphens, but descriptions do "
                    f"— try `tu grep '{pattern}' --field description`)"
                )
            return (
                "0 matches in tool names.\n"
                "  → Try: tu grep '" + pattern + "' --field description"
            )
        # Feature-23B-05: show the stored hint for non-name-field 0-match results too
        hint = d.get("hint")
        if hint:
            return f"0 matches  (tip: {hint})"
        return "0 matches"
    col1 = max((len(t.get("name", "")) for t in tools), default=8)
    col1 = max(col1, 8)
    lines = [f"{'name':<{col1}}  description", "─" * (col1 + 2 + _TRUNC)]
    for t in tools:
        lines.append(f"{t.get('name', ''):<{col1}}  {_trunc(t.get('description', ''))}")
    has_more = d.get("has_more", False)
    offset = d.get("offset", 0)
    # Feature-R18B-08/R17B-08: show range (e.g. "11–20 of 59") when paginating.
    first = offset + 1
    last = offset + len(tools)
    # Feature-20A-07: show range on page 1 too when results span multiple pages.
    range_str = f"  [{first}–{last}]" if (offset or has_more) else ""
    if has_more:
        next_offset = offset + len(tools)
        more_hint = f"  (more — next: --offset {next_offset})"
    elif offset and tools:
        # Feature-R17B-07: signal "end of results" when paging lands on the last page
        more_hint = "  (end of results)"
    else:
        more_hint = ""
    # R22B-11: show which field was searched on the first page so users discover
    # --field description.  Skip on subsequent pages to keep the line short.
    field = d.get("field", "name")
    field_hint = (
        "  (searched: name — use --field description to search descriptions)"
        if field == "name" and offset == 0
        else ""
    )
    lines.append(f"\n{len(tools)} of {total} matches{range_str}{more_hint}{field_hint}")
    return "\n".join(lines)


def _render_find(d: dict) -> str:
    """Render find_tools result as score + name + description table."""
    if "error" in d:
        return f"Error: {d['error']}"
    tools = d.get("tools", [])
    total = d.get("total_matches", 0)
    if not tools:
        if total > 0:
            if d.get("limit") == 0:
                return f"0 of {total} results (limit=0, no results shown)"
            offset = d.get("offset", 0)
            if offset:
                return (
                    f"0 of {total} results (offset past end — use --offset < {total})"
                )
        # Feature-R13B-01: "no meaningful terms" now uses standard schema with warning in processing_info.
        warning = (d.get("processing_info") or {}).get("warning", "")
        if warning:
            return f"0 results  (note: {warning})"
        return "0 results"
    col1 = max((len(t.get("name", "")) for t in tools), default=8)
    col1 = max(col1, 8)
    # R21B-08: use "relevance_score" key (canonical in find_tools JSON output).
    lines = [
        f"{'score':>7}  {'name':<{col1}}  description",
        "─" * (7 + 2 + col1 + 2 + _TRUNC),
    ]
    for t in tools:
        score = t.get("relevance_score", t.get("score", ""))
        if isinstance(score, float):
            score_str = f"{score:.3f}"
        else:
            score_str = str(score)
        lines.append(
            f"{score_str:>7}  {t.get('name', ''):<{col1}}  {_trunc(t.get('description', ''))}"
        )
    total = d.get("total_matches", len(tools))
    has_more = d.get("has_more", total > len(tools))
    offset = d.get("offset", 0)
    # Feature-R18B-08/R17B-08: show range (e.g. "11–20 of 285") when paginating.
    first = offset + 1
    last = offset + len(tools)
    # Feature-20A-07: show range on page 1 too when results span multiple pages.
    range_str = f"  [{first}–{last}]" if (offset or has_more) else ""
    if has_more:
        next_offset = offset + len(tools)
        more_hint = f"  (more — next: --offset {next_offset})"
    elif offset and tools:
        # Feature-R17B-07: signal "end of results" when paging lands on the last page
        more_hint = "  (end of results)"
    else:
        more_hint = ""
    lines.append(f"\n{len(tools)} of {total} results{range_str}{more_hint}")
    return "\n".join(lines)


def _render_info(d: dict) -> str:
    """Render get_tool_info result as human-readable tool card."""
    if "error" in d:
        name = d.get("name", "")
        suggestions = d.get("suggestions", [])
        # R22B-04: append "Did you mean?" hint when suggestions are available.
        if name:
            hint = ""
            if suggestions:
                hint = f"\n  Did you mean: {', '.join(suggestions)}?"
            else:
                # Feature-24B-05: use full name (not truncated) so suggestion is useful.
                # Split on underscore and take the first meaningful segment so that
                # e.g. 'AlphaFold' → 'tu grep AlphaFold' (finds alphafold_* tools).
                hint = f"\n  Run `tu grep {name}` to search for similar tools."
            return f"Error: Tool '{name}' not found.{hint}"
        return f"Error: {d['error']}"
    # batch result
    if "tools" in d:
        parts = []
        for t in d["tools"]:
            parts.append(_render_info(t))
        return "\n\n".join(parts)

    name = d.get("name", "?")
    category = d.get("category", "")
    desc = d.get("description", "")
    cat_str = f"  [{category}]" if category else ""
    lines = [f"{name}{cat_str}", f"  {desc}"]

    params = d.get("parameter", {})
    if params and isinstance(params, dict):
        props = params.get("properties", {})
        required = set(params.get("required", []))
        if props:
            lines.append("\n  Parameters:")
            # Pre-compute type strings and dynamic column widths
            type_strs = {}
            for pname, pdef in props.items():
                ptype = pdef.get("type", "")
                if not ptype and "oneOf" in pdef:
                    ptype = "|".join(
                        b.get("type", "?") for b in pdef["oneOf"] if isinstance(b, dict)
                    )
                type_strs[pname] = (
                    "/".join(ptype) if isinstance(ptype, list) else str(ptype)
                )
            type_col = max((len(v) for v in type_strs.values()), default=4)
            type_col = max(type_col, 6)  # minimum width
            name_col = max((len(p) for p in props), default=8)
            name_col = max(name_col, 8)  # minimum width
            for pname, pdef in props.items():
                ptype_str = type_strs[pname]
                req = "required" if pname in required else ""
                pdesc = _trunc(pdef.get("description", ""), 50)
                # Fixed-width req column so description always starts at same position
                lines.append(
                    f"    {pname:<{name_col}} {ptype_str:<{type_col}}  {req:<8}  {pdesc}"
                )

    # Full-detail sections: shown when get_tool_info returns the complete tool config
    pkgs = d.get("required_packages") or d.get("required_api_keys")
    if pkgs and isinstance(pkgs, list):
        lines.append(f"\n  Required: {', '.join(str(p) for p in pkgs)}")

    examples = d.get("test_examples")
    if examples and isinstance(examples, list):
        lines.append("\n  Examples:")
        for ex in examples[:2]:
            lines.append(f"    {json.dumps(ex, separators=(',', ':'))}")

    ret = d.get("return_schema")
    if ret and isinstance(ret, dict):
        ret_desc = ret.get("description", "")
        if ret_desc:
            lines.append(f"\n  Returns: {ret_desc}")

    return "\n".join(lines)


def _render_run(d: dict) -> str:
    """Feature-23B-02: human-friendly renderer for `tu run` errors.

    For error results, emits a short summary instead of the full 77-line JSON
    dump (which buries the actionable message in jsonschema noise).
    For success, falls back to pretty JSON (tool data has no fixed schema).
    """
    if not isinstance(d, dict):
        return str(d)
    if d.get("status") != "error" and "error" not in d:
        return json.dumps(d, indent=2, ensure_ascii=False)
    # Short, actionable error summary
    short_err = d.get("error", "unknown error")
    lines = [f"Error: {short_err}"]
    details = d.get("error_details") or {}

    # Feature-25B-02: for "tool not found" errors, replace generic network tips
    # with tool-discovery tips and include fuzzy suggestions when available.
    is_not_found = "not found" in short_err.lower()
    is_api_key_error = "requires api key" in short_err.lower()
    suggestions = d.get("suggestions") or details.get("suggestions") or []
    if is_api_key_error:
        lines.append("Tips:")
        lines.append(
            "  • Set the required environment variable(s) in your shell or .tooluniverse/.env"
        )
        lines.append("  • Run `tu status` to check which API keys are configured")
    elif is_not_found:
        if suggestions:
            lines.append(f"  Did you mean: {', '.join(suggestions[:3])}?")
        lines.append("Tips:")
        lines.append("  • Check tool name spelling (names are case-sensitive)")
        # Feature-27B-09: tu find is always available; list it first
        lines.append("  • Run `tu find '<description>'` for natural-language search")
        lines.append("  • Run `tu grep <name>` to search by pattern")
    else:
        next_steps = details.get("next_steps") or []
        # Feature-25B-07: filter out Python SDK-specific tips not relevant to CLI users
        cli_steps = [s for s in next_steps if "tu.tools.refresh()" not in s]
        if cli_steps:
            lines.append("Tips:")
            for step in cli_steps:
                lines.append(f"  • {step}")

    return "\n".join(lines)


def _render_status(d: dict) -> str:
    """Render status as key-value pairs + top categories list."""
    lines = [
        f"version:         {d.get('version', '?')}",
        f"tools loaded:    {d.get('total_tools', d.get('tools_loaded', '?'))}",
        f"gated tools:     {d.get('gated_tools_count', '?')}",
        f"categories:      {d.get('categories', '?')}",
        f"workspace:       {d.get('workspace', '?')}",
        f"profile active:  {'yes' if d.get('profile_active') else 'no'}",
    ]
    top = d.get("top_categories", {})
    if top:
        lines.append("\ntop categories:")
        for cat, cnt in top.items():
            lines.append(f"  {cat:<20} {cnt}")
    return "\n".join(lines)


# ── output helper ───────────────────────────────────────────────────────────────


def _print_result(result: Any, args: argparse.Namespace, render_fn=None) -> None:
    """Print result. Respects --raw / --json / human-readable default."""
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except (json.JSONDecodeError, TypeError):
            print(result)
            return
    if args.raw:
        print(json.dumps(result, ensure_ascii=False))
    elif args.json or render_fn is None:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        try:
            rendered = render_fn(result)
            # Route error messages to stderr so stdout stays clean for piping.
            # In --json/--raw mode, errors go to stdout intentionally (machine-parseable).
            is_error = isinstance(result, dict) and "error" in result
            out = sys.stderr if is_error else sys.stdout
            print(rendered, file=out)
        except Exception:
            print(json.dumps(result, indent=2, ensure_ascii=False))


# ── category helpers ────────────────────────────────────────────────────────────


def _resolve_categories(tu, names: list) -> tuple:
    """Map user-supplied names to actual stored category keys (case-insensitive).

    Resolution order:
    1. Exact match (case-insensitive) → found, but also check whether the exact
       match key is a strict prefix of other categories (e.g. 'gtex' vs 'gtex_v2').
       If so, emit a warning and pick the category with the most tools.
    2. No exact match → find all categories whose lowercase key starts with the
       lowercase input (prefix matches).
       - If exactly one prefix match exists, use it silently.
       - If multiple prefix matches exist, warn on stderr listing all candidates
         with their tool counts, then include ALL of them.
    3. No match at all → warn on stderr with suggestions, pass through unchanged.

    Returns:
        (resolved_names, had_unknown) where had_unknown=True means at least one
        input category was not found in the registry (callers should exit 1).
    """
    category_dicts = tu.tool_category_dicts or {}
    actual = set(category_dicts.keys())

    # Feature-R12A-11: tool_category_dicts uses loader keys (e.g. "cellmarker"), but some
    # tool configs declare a different "category" field (e.g. "Genomics & Transcriptomics").
    # Build a supplemental map of those raw categories so prefix matching can find them.
    raw_cats: dict = {}  # cat_name -> [tool_names]
    _all_tool_dict = getattr(tu, "all_tool_dict", None)
    if not isinstance(_all_tool_dict, dict):
        _all_tool_dict = {}
    for tool_name, tool in _all_tool_dict.items():
        cat = tool.get("category") if isinstance(tool, dict) else None
        if cat and cat not in actual:
            raw_cats.setdefault(cat, []).append(tool_name)
    # Merge raw_cats into the searchable universe (don't mutate actual category_dicts).
    # Feature-20A-08: "unknown" is an internal sentinel returned by _get_tool_category for
    # tools without any category assignment.  It is never stored in category_dicts or
    # raw_cats, so add it explicitly so `--categories unknown` resolves silently.
    full_actual = actual | set(raw_cats.keys()) | {"unknown"}

    # Build a mapping from lowercased key → original key for exact lookup.
    lower_map = {k.lower(): k for k in full_actual}

    def _tool_count(cat_key):
        tools = category_dicts.get(cat_key, raw_cats.get(cat_key, []))
        return len(tools) if isinstance(tools, list) else 0

    resolved = []
    had_unknown = False
    for name in names:
        name_lower = name.lower()

        # 1. Exact case-insensitive match.
        if name_lower in lower_map:
            exact_key = lower_map[name_lower]
            # Feature-R18B-10: If there is an exact (case-insensitive) match, use it
            # silently.  Do NOT warn about categories that merely share this as a
            # prefix (e.g. user typed "uniprot" → use "uniprot", ignore "uniprot_ref").
            # The spurious warning was confusing and caused users to doubt their input.
            resolved.append(exact_key)
            continue

        # 2. Prefix matches.
        prefix_matches = [k for k in full_actual if k.lower().startswith(name_lower)]

        if not prefix_matches:
            # 3. No match at all — warn with suggestions.
            # Feature-R13B-06: set had_unknown so callers can exit 1.
            suggestions = [k for k in full_actual if name_lower[:4] in k.lower()][:3]
            hint = (
                f" Did you mean: {', '.join(suggestions[:3])!r}?" if suggestions else ""
            )
            print(
                f"Warning: category {name!r} not found.{hint}",
                file=sys.stderr,
            )
            had_unknown = True
            resolved.append(name)
            continue

        if len(prefix_matches) == 1:
            resolved.append(prefix_matches[0])
            continue

        # Multiple prefix matches — include ALL matching categories.
        prefix_matches_sorted = sorted(prefix_matches, key=_tool_count, reverse=True)
        candidates_info = ", ".join(
            f"{c!r} ({_tool_count(c)} tools)" for c in prefix_matches_sorted
        )
        print(
            f"Info: category input {name!r} expands to {len(prefix_matches_sorted)} "
            f"categories: {candidates_info}.",
            file=sys.stderr,
        )
        resolved.extend(prefix_matches_sorted)

    return resolved, had_unknown


# ── run argument parsing ────────────────────────────────────────────────────────


def _infer_type(s: str):
    """Coerce a key=value string to an appropriate Python type.

    Conversions: 'true'→True, 'false'→False,
    '[...]'→list, '{...}'→dict (JSON arrays/objects only).
    'null' is left as the string 'null'; to pass a JSON null use JSON format.

    Feature-27A-02: Numeric-looking strings (e.g. species_id=9606, orpha_code=558)
    are NOT coerced to int/float. Many tool schemas declare these as 'type: string'
    and auto-coercion caused schema validation failures. ToolUniverse's validation
    layer accepts string values for integer schema fields, so this is safe.
    """
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    # JSON arrays and objects: parse so key=value supports list/dict params
    if (s.startswith("[") and s.endswith("]")) or (
        s.startswith("{") and s.endswith("}")
    ):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
    return s


def _parse_run_args(argv: list) -> "dict | None":
    """Parse ['{"k":"v"}'] or ['k1=v1', 'k2=v2'] → dict, or [] → None."""
    if not argv:
        return None
    if len(argv) == 1:
        # Try JSON parse first for any single token (handles objects and arrays)
        try:
            return json.loads(argv[0])
        except json.JSONDecodeError as exc:
            # If the token looks like attempted JSON (starts with { or [), report
            # the JSON parse error directly rather than falling into key=value path
            # with a misleading "Expected key=value" message.
            token = argv[0].strip()
            if token.startswith(("{", "[")):
                raise ValueError(f"Invalid JSON: {exc}") from exc
        # Not JSON and not JSON-like: fall through to key=value path
    else:
        # Multiple tokens: if the first looks like JSON, user is mixing formats
        try:
            json.loads(argv[0])
            raise ValueError(
                "Cannot mix JSON and key=value arguments. "
                "Use one format only: either a single JSON string "
                "or key=value pairs."
            )
        except json.JSONDecodeError:
            pass
    # key=value path
    result = {}
    for token in argv:
        if "=" not in token:
            raise ValueError(f"Expected key=value, got: {token!r}")
        k, _, v = token.partition("=")
        k = k.strip()
        if not k:
            raise ValueError(f"Invalid argument: empty parameter name in {token!r}")
        val = _infer_type(v)
        if v.lower() == "null":
            raise ValueError(
                f"Passing '{k}=null' in key=value format sends Python None to the tool "
                f"and usually causes unexpected errors. "
                f"To pass a null JSON value, use JSON format: '{{\""
                + k
                + f"\": null}}'. "
                f"To omit the parameter, simply remove '{k}=null' from the command."
            )
        result[k] = val
    return result


# ── subcommand handlers ────────────────────────────────────────────────────────


def cmd_list(args: argparse.Namespace) -> None:
    # Determine mode: smart default when user didn't set it explicitly.
    # When piping (--raw/--json) without an explicit --mode, default to "names"
    # so the output always has a "tools" key and is pipeable.
    # For interactive use without any flags, default to "categories" overview.
    mode = args.mode
    # Feature-23B-03: bare --categories (no args) → show the categories overview as-is
    if args.categories is not None and len(args.categories) == 0:
        print(
            "Note: --categories requires category names to filter "
            "(e.g., --categories uniprot). Showing all categories instead.",
            file=sys.stderr,
        )
        args.categories = None
    if mode is None:
        if args.group_by_category:
            # --group-by-category without explicit mode → by_category output
            mode = "by_category"
        elif args.categories:
            mode = "names"
        elif args.raw or args.json:
            # --raw/--json without an explicit mode means the user is piping or
            # wants machine-readable output; return a tools list (has "tools" key)
            # rather than the categories overview (which only has "categories" key)
            mode = "names"
        elif args.limit is not None or args.offset:
            # user specified pagination flags → they want a browsable list, not a
            # category overview (which ignores limit/offset)
            # R22B-03: tell the user about the implicit mode switch so it's not silent.
            mode = "names"
            _pagination_flags = []
            if args.limit is not None:
                _pagination_flags.append(f"--limit {args.limit}")
            if args.offset:
                _pagination_flags.append(f"--offset {args.offset}")
            print(
                f"Note: using names mode ({', '.join(_pagination_flags)} specified; "
                "use --mode categories for the category overview).",
                file=sys.stderr,
            )
        else:
            mode = "categories"

    # Feature-R10A-01: --group-by-category with an explicit non-by_category mode is
    # contradictory — warn and ignore the flag so the output matches the stated mode.
    if args.group_by_category and mode != "by_category" and args.mode is not None:
        print(
            f"Warning: --group-by-category ignored in --mode {mode}; "
            "use --mode by_category to get grouped output.",
            file=sys.stderr,
        )
        args.group_by_category = False

    if mode == "categories" and (args.limit is not None or args.offset):
        ignored = []
        if args.limit is not None:
            ignored.append(f"--limit {args.limit}")
        if args.offset:
            ignored.append(f"--offset {args.offset}")
        print(
            f"Warning: {' and '.join(ignored)} ignored in categories mode (categories mode shows all categories).\n"
            "  Use --mode names or --mode basic to paginate individual tools.",
            file=sys.stderr,
        )
    with _status_to_stderr():
        tu = _get_tu()
        _cat_unknown = False
        if args.categories:
            args.categories, _cat_unknown = _resolve_categories(tu, args.categories)
        result = tu.run_one_function(
            {
                "name": "list_tools",
                "arguments": _compact(
                    {
                        "mode": mode,
                        "categories": args.categories,
                        "fields": args.fields,
                        "limit": args.limit,
                        "offset": args.offset,
                        "group_by_category": args.group_by_category,
                    }
                ),
            }
        )
    # Feature-22A-09: warn when custom mode fields didn't match any tool attribute
    if (
        isinstance(result, dict)
        and result.get("unknown_fields")
        and not (args.json or args.raw)
    ):
        unk = result["unknown_fields"]
        valid = (
            "name, description, type, category, parameters, "
            "return_schema, is_async, test_examples"
        )
        print(
            f"Warning: field(s) {unk!r} not found in any tool.\n"
            f"  Valid fields include: {valid}",
            file=sys.stderr,
        )
    # Feature-23A-06: inject categories_filtered so list JSON schema is consistent
    # with grep and find (which always emit "categories_filtered").
    if isinstance(result, dict) and "error" not in result:
        result["categories_filtered"] = args.categories or None
    _print_result(result, args, _render_list)
    # Feature-R13B-06: exit 1 when an unknown category was passed.
    if _cat_unknown:
        sys.exit(1)
    if isinstance(result, dict):
        if "error" in result:
            sys.exit(1)
        # R21A-06: do NOT exit 1 when offset is past end of results. An empty
        # page at a high offset is normal pagination termination, not an error.
        # This is consistent with `find` (Feature-R14B-02) and `grep` behavior.


def cmd_grep(args: argparse.Namespace) -> None:
    # Feature-23B-10: pattern is now nargs="+" so it may be a list of words.
    # Join them and warn the user so they learn the quoting idiom.
    if isinstance(args.pattern, list):
        if len(args.pattern) > 1:
            joined = " ".join(args.pattern)
            print(
                f"Note: multi-word grep — treating as '{joined}'. "
                f"Use quotes to avoid this message: tu grep '{joined}'",
                file=sys.stderr,
            )
        args.pattern = " ".join(args.pattern)
    # Feature-R10A-04: validate non-empty pattern before hitting the internal API
    if not args.pattern or not args.pattern.strip():
        if args.json or args.raw:
            print(json.dumps({"error": "pattern cannot be empty"}))
        else:
            print("Error: pattern cannot be empty", file=sys.stderr)
        sys.exit(1)
    # Feature-22A-08: warn when a regex pattern contains \| — in Python re, \| is a literal
    # pipe character, not alternation.  Users familiar with grep -E syntax often expect
    # \| to mean OR, but in Python re the unescaped | is the alternation operator.
    if getattr(args, "search_mode", None) == "regex" and r"\|" in args.pattern:
        print(
            "Note: in Python regex, \\| matches a literal '|' character, not alternation. "
            "Use | (unescaped) for OR — e.g., 'A|B' not 'A\\|B'.",
            file=sys.stderr,
        )
    with _status_to_stderr():
        tu = _get_tu()
        _cat_unknown = False
        if args.categories:
            args.categories, _cat_unknown = _resolve_categories(tu, args.categories)
        result = tu.run_one_function(
            {
                "name": "grep_tools",
                "arguments": _compact(
                    {
                        "pattern": args.pattern,
                        "field": args.field,
                        "search_mode": args.search_mode,
                        "limit": args.limit,
                        "offset": args.offset,
                        "categories": args.categories,
                    }
                ),
            }
        )
    # Feature-R14A-05/R15A-03: always inject categories_filtered so grep JSON schema
    # matches find (which always emits "categories_filtered": null when not filtered).
    if isinstance(result, dict) and "error" not in result:
        result["categories_filtered"] = args.categories or None
    # Feature-R14A-04/R15B-04: always include "hint" key in grep JSON (null when no hint).
    # When 0 matches and field is "name", adapt hint to the actual field being searched.
    if isinstance(result, dict) and "error" not in result:
        field = result.get("field", "name")
        if (
            not result.get("tools")
            and result.get("total_matches", 0) == 0
            and field == "name"
        ):
            result["hint"] = "use --field description to search tool descriptions"
        elif (
            not result.get("tools")
            and result.get("total_matches", 0) == 0
            and field == "description"
        ):
            # R15A-06: adapt hint when already searching description
            result["hint"] = "try a different search term or fewer words"
        elif (
            not result.get("tools")
            and result.get("total_matches", 0) == 0
            and field == "category"
        ):
            # Feature-24A-06: add hint for --field category 0 matches (consistency with other fields)
            result["hint"] = (
                "try `tu list --mode categories` to browse available categories"
            )
        else:
            result["hint"] = None
    _print_result(result, args, _render_grep)
    if _cat_unknown:
        sys.exit(1)
    if isinstance(result, dict):
        if "error" in result:
            sys.exit(1)
        # Feature-R14B-01: exit 0 on zero matches — the command ran successfully.
        # 0 matches is a valid, non-error outcome for a search command.
        # (Previous behaviour exited 1 like Unix grep, but that breaks scripting pipelines
        # that treat any non-zero exit as a failure rather than "no results".)
        # Only exit 1 on actual errors (the "error" key check above).


def cmd_info(args: argparse.Namespace) -> None:
    # Feature-R11A-09: pre-validate tool names (empty / whitespace-only)
    valid_names = [n for n in args.tool_names if n and n.strip()]
    if not valid_names:
        msg = "tool name cannot be empty"
        if args.json or args.raw:
            print(json.dumps({"error": msg}))
        else:
            print(f"Error: {msg}", file=sys.stderr)
        sys.exit(1)
    args.tool_names = valid_names

    with _status_to_stderr():
        tu = _get_tu()
        # Feature-R11B-01: always pass as list so JSON response is always {"tools": [...]}
        # rather than a flat dict for single-tool requests.
        # Feature-R17B-02: "brief" is the user-facing alias for the API's "description" level.
        detail_level = "description" if args.detail == "brief" else args.detail
        result = tu.run_one_function(
            {
                "name": "get_tool_info",
                "arguments": {
                    "tool_names": args.tool_names,
                    "detail_level": detail_level,
                },
            }
        )
    # R22B-04: inject "did you mean" suggestions into each not-found error entry so
    # _render_info can display them without needing direct access to `tu`.
    if isinstance(result, dict) and "tools" in result:
        all_names = list(tu.all_tool_dict.keys())
        for tool in result["tools"]:
            if isinstance(tool, dict) and "error" in tool:
                name = tool.get("name", "")
                if name:
                    # Feature-23B-04: raised cutoff from 0.5 → 0.62 to avoid spurious
                    # suggestions when difflib matches by coincidence (e.g.
                    # "NonExistentTool123" → "list_tools" both contain "tool").
                    tool["suggestions"] = difflib.get_close_matches(
                        name, all_names, n=3, cutoff=0.62
                    )
    # Feature-R14A-01/R14B-04: normalize "parameter" (singular, raw tool config format) to
    # "parameters" (plural, consistent with find output) in each tool entry.
    # Human-readable mode uses _render_info which reads "parameter" directly; only rename
    # for JSON/raw consumers that compare find and info results programmatically.
    if (args.json or args.raw) and isinstance(result, dict):
        for tool in result.get("tools", []):
            if (
                isinstance(tool, dict)
                and "parameter" in tool
                and "parameters" not in tool
            ):
                tool["parameters"] = tool.pop("parameter")
    # In human-readable mode, route per-tool errors to stderr and valid tools to stdout
    if (
        not args.raw
        and not args.json
        and isinstance(result, dict)
        and "tools" in result
        and "error" not in result
    ):
        has_good = False
        for tool in result.get("tools", []):
            if "error" in tool:
                print(_render_info(tool), file=sys.stderr)
            else:
                print(_render_info(tool))
                has_good = True
        # Feature-R13B-02: exit 1 only when ALL tools were missing (total failure).
        if not has_good:
            sys.exit(1)
        return
    _print_result(result, args, _render_info)
    if isinstance(result, dict):
        if "error" in result:
            sys.exit(1)
        # Feature-R13B-02: exit 1 only when ALL requested tools were not found.
        # Partial success (some found, some missing) exits 0 so callers can
        # distinguish "nothing found" from "some found" without parsing JSON.
        tools_in_result = result.get("tools", [])
        if tools_in_result and all("error" in t for t in tools_in_result):
            sys.exit(1)


def cmd_find(args: argparse.Namespace) -> None:
    """Find tools with keyword-based search (no LLM/API keys required)."""
    # Feature-R10A-03: validate non-empty query before hitting the internal API
    if not args.query or not args.query.strip():
        if args.json or args.raw:
            print(json.dumps({"error": "query cannot be empty"}))
        else:
            print("Error: query cannot be empty", file=sys.stderr)
        sys.exit(1)
    with _status_to_stderr():
        tu = _get_tu()
        _cat_unknown = False
        if args.categories:
            args.categories, _cat_unknown = _resolve_categories(tu, args.categories)
        from tooluniverse.tool_finder_keyword import ToolFinderKeyword

        finder = ToolFinderKeyword({}, tooluniverse=tu)
        raw_result = finder._run_json_search(
            _compact(
                {
                    "description": args.query,
                    "limit": args.limit,
                    "offset": getattr(args, "offset", 0) or 0,
                    "categories": args.categories,
                }
            )
        )
    try:
        result = json.loads(raw_result)
    except (json.JSONDecodeError, TypeError):
        result = {"raw": raw_result}
    _print_result(result, args, _render_find)
    if _cat_unknown:
        sys.exit(1)
    if isinstance(result, dict):
        if "error" in result:
            sys.exit(1)
        tools_list = (
            result.get("tools") if isinstance(result.get("tools"), list) else []
        )
        result.get("total_matches", len(tools_list))
        # Feature-R16A-07/R16B-09: exit 0 on zero matches — consistent with grep.
        # 0 results is a valid non-error outcome; the command ran successfully.
        # Feature-R14B-02: do NOT exit 1 when offset is past end. An empty page with
        # total_matches > 0 is normal pagination completion, not an error.


def cmd_run(args: argparse.Namespace) -> None:
    """Execute a tool.

    Interface mirrors execute_tool:
      tool_name  — name of the tool to run (required)
      arguments  — key=value pairs OR JSON string (optional)
    """
    arguments = None
    try:
        arguments = _parse_run_args(args.arguments)
    except (json.JSONDecodeError, ValueError) as exc:
        err_payload = {
            "status": "error",
            "error": str(exc),
            "error_details": {
                "retriable": False,
                "type": "argument_parse_error",
            },
        }
        # Feature-24B-07: human mode shows a friendly hint; --json/--raw gets JSON on stdout.
        if getattr(args, "json", False) or getattr(args, "raw", False):
            print(json.dumps(err_payload))
        else:
            print(
                f"Error: {exc}\n"
                f"  Tip: use key=value syntax, e.g. `tu run {args.tool_name} param=value`",
                file=sys.stderr,
            )
        sys.exit(1)

    with _status_to_stderr():
        tu = _get_tu()
        result = tu.run_one_function(
            {
                "name": "execute_tool",
                # Omit `arguments` key entirely when None so the tool sees its
                # own default rather than a None that fails JSON schema validation.
                "arguments": _compact(
                    {"tool_name": args.tool_name, "arguments": arguments}
                ),
            }
        )
    # Feature-23B-02: use _render_run so human mode gets a concise error summary;
    # --json / --raw still get the full JSON blob.
    _print_result(result, args, render_fn=_render_run)
    # Exit non-zero when the tool reported an error (check both status field and
    # the presence of an "error" key to catch tool-layer errors that lack "status")
    if isinstance(result, dict) and (
        result.get("status") == "error" or "error" in result
    ):
        sys.exit(1)


def _count_gated_tools(tu) -> int:
    """Count tools not loaded because of missing required API keys.

    Reads each tool-config JSON file referenced by ``tu.tool_files`` and
    counts tool entries that have ``required_api_keys`` where at least one
    key is absent from the environment *and* whose name is not in
    ``tu.all_tool_dict`` (i.e. the tool was filtered out during loading).
    """
    loaded_names = set(tu.all_tool_dict.keys())
    gated = 0
    for _cat, file_path in (tu.tool_files or {}).items():
        if not file_path or not os.path.isfile(file_path):
            continue
        try:
            with open(file_path, encoding="utf-8") as fh:
                raw = json.load(fh)
        except Exception:
            continue
        # JSON files may contain a list of configs or a single dict
        configs = raw if isinstance(raw, list) else [raw]
        for cfg in configs:
            if not isinstance(cfg, dict):
                continue
            name = cfg.get("name", "")
            if name in loaded_names:
                continue
            req_keys = cfg.get("required_api_keys", [])
            if req_keys and any(not os.environ.get(k) for k in req_keys):
                gated += 1
    return gated


def cmd_status(args: argparse.Namespace) -> None:
    with _status_to_stderr():
        tu = _get_tu()
        tu._auto_load_tools_if_empty()
        # Count categories the same way list_tools does (via _get_tool_category)
        # so that `tu status` and `tu list --mode categories` agree.
        from tooluniverse.tool_discovery_tools import _get_tool_category

        category_counts: dict[str, int] = {}
        for tool_name, tool in (tu.all_tool_dict or {}).items():
            cat = _get_tool_category(tool, tool_name, tu)
            category_counts[cat] = category_counts.get(cat, 0) + 1
        gated_count = _count_gated_tools(tu)
    status = {
        "total_tools": len(tu.all_tools),
        "categories": len(category_counts),
        "workspace": str(tu._workspace_dir),
        "profile_active": tu._workspace_profile_config is not None,
        "top_categories": dict(
            sorted(category_counts.items(), key=lambda x: -x[1])[:10]
        ),
        "version": _TU_VERSION,
        "gated_tools_count": gated_count,
    }
    _print_result(status, args, _render_status)


def cmd_test(args: argparse.Namespace) -> None:
    """Test a tool against example inputs and report pass/fail."""
    import time

    use_json = getattr(args, "json", False)
    use_color = (sys.stderr.isatty() or sys.stdout.isatty()) and not use_json
    green = "\033[32m" if use_color else ""
    red = "\033[31m" if use_color else ""
    yellow = "\033[33m" if use_color else ""
    bold = "\033[1m" if use_color else ""
    reset = "\033[0m" if use_color else ""

    def _ok(msg):
        return f"{green}✓{reset} {msg}"

    def _fail(msg):
        return f"{red}✗{reset} {msg}"

    def _warn(msg):
        return f"{yellow}!{reset} {msg}"

    # ── resolve test list ─────────────────────────────────────────────────────
    if args.config:
        import json as _json

        try:
            with open(args.config) as f:
                cfg = _json.load(f)
        except FileNotFoundError:
            msg = f"Config file not found: {args.config}"
            if use_json:
                print(json.dumps({"status": "error", "error": msg}))
            else:
                print(_fail(msg), file=sys.stderr)
            sys.exit(1)
        except (OSError, _json.JSONDecodeError) as exc:
            msg = f"Cannot read config file: {exc}"
            if use_json:
                print(json.dumps({"status": "error", "error": msg}))
            else:
                print(_fail(msg), file=sys.stderr)
            sys.exit(1)
        tool_name = cfg["tool_name"]
        tests = [
            {
                "name": t.get("name", ""),
                "args": t["args"],
                "expect_status": t.get("expect_status"),
                "expect_keys": t.get("expect_keys", []),
            }
            for t in cfg.get("tests", [])
        ]
    else:
        tool_name = args.tool_name
        if tool_name is None:
            msg = "Missing required argument: tool_name\n  Usage: tu test <tool_name> [args_json]\n  Or:    tu test --config FILE"
            if use_json:
                print(
                    json.dumps(
                        {
                            "status": "error",
                            "error": "Missing required argument: tool_name",
                        }
                    )
                )
            else:
                print(_fail(msg), file=sys.stderr)
            sys.exit(1)
        if args.args_json:
            import json as _json

            try:
                parsed = _json.loads(args.args_json)
            except _json.JSONDecodeError as exc:
                print(f"Error: invalid JSON arguments — {exc}", file=sys.stderr)
                sys.exit(1)
            tests = [
                {"name": "", "args": parsed, "expect_status": None, "expect_keys": []}
            ]
        else:
            tests = None  # resolve from test_examples after loading

    # ── load ──────────────────────────────────────────────────────────────────
    with _status_to_stderr():
        tu = _get_tu()

    if tool_name not in tu.all_tool_dict:
        msg = f"Tool '{tool_name}' not found. Run `tu list` to see available tools."
        if use_json:
            print(json.dumps({"status": "error", "error": msg}))
        else:
            print(_fail(msg))
        sys.exit(1)

    tool_def = tu.all_tool_dict[tool_name]

    # ── resolve test_examples if no tests provided ────────────────────────────
    if tests is None:
        examples = (
            tool_def.get("test_examples", []) if isinstance(tool_def, dict) else []
        )
        if not examples:
            msg = (
                f"No test_examples found for '{tool_name}' and no arguments given.\n"
                f'  Pass explicit args:  tu test {tool_name} \'{{"q": "test"}}\'\n'
                f"  Or add test_examples to the tool's JSON config.\n"
                f"  Note: 'examples' and 'test_examples' are different fields — only\n"
                f"  'test_examples' is used by 'tu test'. Each entry must be a flat\n"
                f'  dict of arguments (not {{"description": ..., "arguments": ...}}).'
            )
            if use_json:
                print(
                    json.dumps(
                        {
                            "status": "error",
                            "error": f"No test_examples found for '{tool_name}' and no arguments given.",
                        }
                    )
                )
            else:
                print(_warn(msg))
            sys.exit(1)
        tests = [
            {
                "name": f"example {i + 1}",
                "args": ex,
                "expect_status": None,
                "expect_keys": [],
            }
            for i, ex in enumerate(examples)
        ]

    # ── run tests ─────────────────────────────────────────────────────────────
    import json as _json

    if not use_json:
        print(
            f"\n{bold}Testing: {tool_name}{reset}  ({len(tests)} test{'s' if len(tests) != 1 else ''})\n"
        )
    passed = 0
    json_test_results = []
    for t in tests:
        label = t["name"] or _json.dumps(t["args"])
        t0 = time.time()
        try:
            result = tu.run_one_function({"name": tool_name, "arguments": t["args"]})
        except Exception as exc:
            elapsed = time.time() - t0
            if not use_json:
                print(f"  {_fail(label)}  [{elapsed:.2f}s]")
                print(f"    Exception: {exc}")
            else:
                json_test_results.append(
                    {
                        "name": label,
                        "passed": False,
                        "elapsed": round(elapsed, 3),
                        "failures": [f"Exception: {exc}"],
                        "result": None,
                    }
                )
            continue

        elapsed = time.time() - t0
        failures = []

        if t["expect_status"] and isinstance(result, dict):
            got = result.get("status")
            got_display = repr(got) if got is not None else "<missing>"
            if got != t["expect_status"]:
                failures.append(
                    f"status: expected '{t['expect_status']}', got {got_display}"
                )
        elif (
            isinstance(result, dict)
            and "error" in result
            and result.get("status") != "success"
        ):
            # Implicit failure: tool returned an error without explicit expect_status check
            err_msg = result.get("error", "")
            failures.append(f"tool returned error: {str(err_msg)[:200]}")

        for key in t["expect_keys"]:
            if isinstance(result, dict) and key not in result:
                failures.append(f"missing key '{key}' in result")

        if result is None:
            failures.append("result is None")
        elif isinstance(result, dict) and not result:
            failures.append("result is an empty dict")

        # return_schema validation (auto, from tool definition)
        if (
            not failures
            and isinstance(result, dict)
            and result.get("status") == "success"
        ):
            return_schema = (
                tool_def.get("return_schema") if isinstance(tool_def, dict) else None
            )
            if return_schema:
                try:
                    import jsonschema

                    jsonschema.validate(result.get("data"), return_schema)
                except ImportError:
                    pass  # jsonschema not installed — skip silently
                except jsonschema.ValidationError as exc:
                    failures.append(
                        f"return_schema mismatch: {exc.message} (at {list(exc.absolute_path)})"
                    )

        # Feature-25B-01: warn when data is empty on success — test example may be stale
        warnings = []
        if (
            not failures
            and isinstance(result, dict)
            and result.get("status") == "success"
        ):
            data_val = result.get("data")
            if (
                data_val is not None
                and isinstance(data_val, list)
                and len(data_val) == 0
            ):
                warnings.append(
                    "data is empty [] — test example may use a stale/invalid ID "
                    "or the query legitimately returns no results"
                )

        if failures:
            if not use_json:
                print(f"  {_fail(label)}  [{elapsed:.2f}s]")
                for f in failures:
                    print(f"    {f}")
                print(f"    result: {_json.dumps(result, default=str)[:300]}")
            else:
                json_test_results.append(
                    {
                        "name": label,
                        "passed": False,
                        "elapsed": round(elapsed, 3),
                        "failures": failures,
                        "warnings": warnings,
                        "result": result,
                    }
                )
        else:
            if not use_json:
                preview = _json.dumps(result, default=str)[:120]
                if warnings:
                    print(f"  {_warn(label)}  [{elapsed:.2f}s]  {preview}…")
                    for w in warnings:
                        print(f"    ! {w}")
                else:
                    print(f"  {_ok(label)}  [{elapsed:.2f}s]  {preview}…")
            else:
                json_test_results.append(
                    {
                        "name": label,
                        "passed": True,
                        "elapsed": round(elapsed, 3),
                        "failures": [],
                        "warnings": warnings,
                        "result": result,
                    }
                )
            passed += 1

    # ── summary ───────────────────────────────────────────────────────────────
    failed = len(tests) - passed
    if use_json:
        summary = {
            "status": "success" if failed == 0 else "error",
            "tool_name": tool_name,
            "total": len(tests),
            "passed": passed,
            "failed": failed,
            "tests": json_test_results,
        }
        print(_json.dumps(summary, default=str))
        if failed > 0:
            sys.exit(1)
        return

    print(f"\n{'─' * 50}")
    if failed == 0:
        print(f"{green}{bold}All {len(tests)} test(s) passed.{reset}")
    else:
        print(f"{red}{bold}{failed}/{len(tests)} test(s) failed.{reset}")
        sys.exit(1)


def cmd_build(args: argparse.Namespace) -> None:
    """Regenerate the static lazy registry and coding-API wrapper files."""
    from pathlib import Path

    # Resolve output directory.
    # Default: .tooluniverse/coding_api/ next to the current workspace —
    # never touches the installed package in site-packages.
    output_dir = (
        Path(args.output)
        if args.output
        else Path.cwd() / ".tooluniverse" / "coding_api"
    )

    # Step 1 — lazy registry (always writes back into the installed package;
    # this is a small internal optimisation file and is harmless to update).
    try:
        print("Regenerating lazy registry…", file=sys.stderr)
        mod = __import__("tooluniverse.generate_lazy_registry", fromlist=["main"])
        mod.main()
    except SystemExit as exc:
        if exc.code not in (None, 0):
            sys.exit(exc.code)
    except Exception as exc:
        print(f"Error in generate_lazy_registry: {exc}", file=sys.stderr)
        sys.exit(1)

    # Step 2 — coding-API wrappers → user-specified or local workspace dir.
    try:
        print("Regenerating coding-API wrappers…", file=sys.stderr)
        mod = __import__("tooluniverse.generate_tools", fromlist=["main"])
        mod.main(output_dir=output_dir)
    except SystemExit as exc:
        if exc.code not in (None, 0):
            sys.exit(exc.code)
    except Exception as exc:
        print(f"Error in generate_tools: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_serve(_args: argparse.Namespace) -> None:
    """Start the MCP stdio server — identical to running `tooluniverse`."""
    from tooluniverse.smcp_server import run_default_stdio_server

    run_default_stdio_server()


# ── argument parser ────────────────────────────────────────────────────────────


def main() -> None:
    # Shared output flags
    _out = argparse.ArgumentParser(add_help=False)
    _out.add_argument(
        "--json",
        action="store_true",
        help="Output as pretty JSON",
    )
    _out.add_argument(
        "--raw",
        action="store_true",
        help="Output compact JSON (suitable for piping)",
    )

    parser = argparse.ArgumentParser(
        prog="tu",
        description="ToolUniverse CLI — discover and run scientific tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  tu list\n"
            "  tu list --categories uniprot\n"
            "  tu grep protein --field description\n"
            "  tu find 'protein structure analysis' --limit 5\n"
            "  tu info UniProt_get_entry_by_accession\n"
            "  tu run UniProt_get_entry_by_accession accession=P12345\n"
            '  tu run UniProt_get_entry_by_accession \'{"accession": "P12345"}\'\n'
            "  tu test Dryad_search_datasets\n"
            '  tu test MyAPI_search \'{"q": "test"}\'\n'
            "  tu status\n"
            "  tu build\n"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_TU_VERSION}",
    )
    # Feature-24B-02: quiet mode suppresses the missing-API-key warning.
    # Now quiet is the default; kept for backwards compatibility.
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        default=True,
        help="Suppress informational warnings (default: on, kept for backwards compat)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show informational warnings (e.g. missing API key notices)",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ── list ──────────────────────────────────────────────────────────────────
    p = sub.add_parser(
        "list",
        help="List available tools",
        parents=[_out],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  tu list\n"
            "  tu list --mode categories\n"
            "  tu list --categories ChEMBL UniProt --limit 20\n"
            "  tu list --mode by_category --group-by-category\n"
            "  tu list --mode custom --fields name type category\n"
        ),
    )
    p.add_argument(
        "--mode",
        default=None,
        choices=["names", "categories", "basic", "by_category", "summary", "custom"],
        help=(
            "Output mode (default: categories overview; auto-switches to names mode "
            "when --categories, --limit, --offset, --raw, or --json are given without "
            "an explicit --mode)"
        ),
    )
    p.add_argument(
        # Feature-23B-03: nargs="*" so bare --categories (no args) is parseable;
        # cmd_list treats the empty-list case as a redirect to the categories overview.
        # Feature-25B-08: --category (singular) accepted as alias for --categories.
        "--categories",
        "--category",
        nargs="*",
        metavar="CAT",
        help="Filter by category names (omit names to see the full category overview)",
        dest="categories",
    )
    p.add_argument(
        "--fields",
        nargs="+",
        metavar="FIELD",
        help="Fields to include (required for --mode custom, e.g. name type category)",
    )
    p.add_argument(
        "--limit",
        type=_non_neg_int,
        default=None,
        help="Max tools to return (0 = count-probe: returns total without fetching results; "
        "in by_category mode: max tools per category)",
    )
    p.add_argument(
        "--offset",
        type=_non_neg_int,
        default=0,
        help="Skip first N tools (in by_category mode: skip first N tools per category)",
    )
    p.add_argument(
        "--group-by-category",
        dest="group_by_category",
        action="store_true",
        help="Group results by category",
    )
    p.set_defaults(func=cmd_list)

    # ── grep ──────────────────────────────────────────────────────────────────
    p = sub.add_parser(
        "grep",
        help="Search tools by text or regex pattern",
        parents=[_out],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  tu grep protein\n"
            "  tu grep protein --field description\n"
            "  tu grep '^UniProt' --mode regex\n"
            "  tu grep drug --field description --limit 20\n"
        ),
    )
    # Feature-23B-10: nargs="+" captures multi-word input (e.g. `tu grep chip seq`).
    # cmd_grep joins the words and shows a quoting hint so the user learns the idiom.
    p.add_argument(
        "pattern",
        nargs="+",
        help="Search pattern (quote multi-word: tu grep 'chip seq')",
    )
    p.add_argument(
        "--field",
        default="name",
        choices=["name", "description", "type", "category"],
        help="Field to search in (default: name)",
    )
    p.add_argument(
        "--mode",
        "--search-mode",
        dest="search_mode",
        default="text",
        choices=["text", "regex"],
        help="text = case-insensitive substring; regex = regular expression (default: text)",
    )
    p.add_argument(
        "--limit",
        type=_non_neg_int,
        default=100,
        help="Max results (default: 100; use 0 as a count-probe to get total without fetching results)",
    )
    p.add_argument(
        "--offset", type=_non_neg_int, default=0, help="Skip first N results"
    )
    p.add_argument(
        "--categories", nargs="+", metavar="CAT", help="Filter by category names"
    )
    p.set_defaults(func=cmd_grep)

    # ── info ──────────────────────────────────────────────────────────────────
    p = sub.add_parser(
        "info",
        help="Get tool details",
        parents=[_out],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  tu info UniProt_get_entry_by_accession\n"
            "  tu info UniProt_get_entry_by_accession --detail brief\n"
            "  tu info UniProt_get_entry_by_accession ChEMBL_get_molecule\n"
        ),
    )
    p.add_argument("tool_names", nargs="+", metavar="TOOL", help="Tool name(s)")
    p.add_argument(
        "--detail",
        default="full",
        choices=["brief", "description", "full"],
        # Feature-R17B-02: 'description' is confusingly named — it means "description only"
        # (strips parameters/examples). 'brief' is an alias added as the clearer name.
        # 'full' (default) returns everything: description, parameters, examples.
        help=(
            "'full' (default) shows all info: description, parameters, examples; "
            "'brief' (or 'description') shows description text only — no parameters"
        ),
    )
    p.set_defaults(func=cmd_info)

    # ── find ──────────────────────────────────────────────────────────────────
    p = sub.add_parser(
        "find",
        help="Find tools by natural-language query",
        parents=[_out],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  tu find 'protein structure analysis'\n"
            "  tu find 'search for drug targets' --limit 5\n"
            "  tu find 'gene expression' --categories GTEx ENCODE\n"
        ),
    )
    p.add_argument("query", help="Natural-language search query")
    p.add_argument(
        "--limit",
        type=_non_neg_int,
        default=10,
        help="Max results (default: 10; use 0 as a count-probe to get total without fetching results)",
    )
    p.add_argument(
        "--offset",
        type=_non_neg_int,
        default=0,
        help="Skip first N results (default: 0)",
    )
    p.add_argument(
        "--categories", nargs="+", metavar="CAT", help="Filter by category names"
    )
    p.set_defaults(func=cmd_find)

    # ── run ───────────────────────────────────────────────────────────────────
    p = sub.add_parser(
        "run",
        help="Execute a tool",
        parents=[_out],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Arguments can be key=value pairs or a single JSON string.\n\n"
            "Examples:\n"
            "  tu run UniProt_get_entry_by_accession accession=P12345\n"
            "  tu run list_tools mode=categories\n"
            '  tu run UniProt_get_entry_by_accession \'{"accession": "P12345"}\'\n'
            '  tu run grep_tools \'{"pattern": "protein", "field": "name"}\'\n'
        ),
    )
    p.add_argument("tool_name", help="Name of the tool to execute")
    p.add_argument(
        "arguments",
        nargs="*",
        default=[],
        metavar="ARG",
        help="Tool arguments: JSON string OR key=value pairs",
    )
    p.set_defaults(func=cmd_run)

    # ── test ──────────────────────────────────────────────────────────────────
    p = sub.add_parser(
        "test",
        help="Test a tool with example inputs and report pass/fail",
        parents=[_out],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  tu test Dryad_search_datasets              # uses test_examples from the tool's JSON config\n"
            '  tu test MyAPI_search \'{"q": "test"}\'  # single ad-hoc call\n'
            "  tu test --config my_tool_tests.json        # full config with assertions\n\n"
            "Config file format (my_tool_tests.json):\n"
            "  {\n"
            '    "tool_name": "MyAPI_search",\n'
            '    "tests": [\n'
            '      {"name": "basic", "args": {"q": "test"}, "expect_status": "success", "expect_keys": ["data"]}\n'
            "    ]\n"
            "  }\n"
        ),
    )
    p.add_argument("tool_name", nargs="?", help="Tool name to test")
    p.add_argument(
        "args_json",
        nargs="?",
        metavar="ARGS",
        help="JSON arguments for a single ad-hoc test",
    )
    p.add_argument(
        "--config", "-c", metavar="FILE", help="Path to a JSON test config file"
    )
    p.set_defaults(func=cmd_test)

    # ── status ────────────────────────────────────────────────────────────────
    p = sub.add_parser(
        "status",
        help="Show ToolUniverse status",
        parents=[_out],
    )
    p.set_defaults(func=cmd_status)

    # ── build ─────────────────────────────────────────────────────────────────
    p = sub.add_parser(
        "build",
        help="Rebuild the static tool registry (run after adding new built-in tools)",
    )
    p.add_argument(
        "--output",
        metavar="DIR",
        default=None,
        help=(
            "Directory to write coding-API wrapper files into "
            "(default: .tooluniverse/coding_api/)"
        ),
    )
    p.set_defaults(func=cmd_build)

    # ── serve ─────────────────────────────────────────────────────────────────
    p = sub.add_parser(
        "serve",
        help="Start the MCP stdio server (identical to `tooluniverse`)",
    )
    p.set_defaults(func=cmd_serve)

    # Quiet is now the default. --verbose/-v opts back in to warnings.
    # We check argv directly because argparse hasn't run yet.
    if "--verbose" in sys.argv or "-v" in sys.argv:
        os.environ.pop("TOOLUNIVERSE_QUIET", None)
    else:
        os.environ["TOOLUNIVERSE_QUIET"] = "1"
        # Feature-26A-03: logger singleton may already exist; raise its level to WARNING
        # so that ℹ️ info lines (e.g. "Number of tools", "Auto-loaded workspace
        # profile.yaml") are suppressed.
        try:
            from tooluniverse.logging_config import reconfigure_for_quiet

            reconfigure_for_quiet()
        except Exception:
            pass

    # Feature-R20B: argparse exits with code 2 and empty stdout on bad args (e.g. --limit -1).
    # Callers that do json.loads(stdout) crash on empty string.
    # Override: if --json or --raw is in argv, emit a JSON error before exiting.
    _json_mode = "--json" in sys.argv or "--raw" in sys.argv
    try:
        args = parser.parse_args()
    except SystemExit as _exc:
        if _exc.code == 2 and _json_mode:
            # argparse already printed its error message to stderr; add JSON to stdout.
            print(
                json.dumps(
                    {"error": "invalid arguments — check --help for usage"}, indent=2
                )
            )
        raise
    # Feature-R12A-12: --json and --raw are mutually exclusive; --raw is a strict subset
    if getattr(args, "json", False) and getattr(args, "raw", False):
        parser.error("--json and --raw are mutually exclusive; use one or the other")
    args.func(args)


if __name__ == "__main__":
    main()
