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

import argparse
import contextlib
import difflib
import json
import os
import sys
from pathlib import Path
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


def _bounded_int(minimum: int, maximum: int):
    def parse(value: str) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise argparse.ArgumentTypeError(f"invalid int value: '{value}'") from exc
        if not minimum <= number <= maximum:
            raise argparse.ArgumentTypeError(
                f"value must be between {minimum} and {maximum}, got {number}"
            )
        return number

    return parse


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

    from tooluniverse.execute_function import ToolUniverse

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
        # Fix-R13D-1: surface tools that exist but are hidden because a
        # required API key is unset -- without this, `tu grep uspto` looked
        # identical to "no such tools exist" (confirmed live), when in fact
        # the tools are real and just need a key set.
        gated = d.get("gated_matches")
        if gated:
            lines = [
                f"0 loaded matches, but {len(gated)} gated tool(s) matched by name:"
            ]
            for g in gated:
                lines.append(
                    f"  {g['name']}  (requires: {', '.join(g['missing_api_keys'])})"
                )
            lines.append("  Set the API key(s) as environment variables, then retry.")
            return "\n".join(lines)
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
        description = _trunc(t.get("description", ""))
        missing_keys = t.get("missing_api_keys") or []
        if t.get("available") is False and missing_keys:
            description = f"[requires: {', '.join(missing_keys)}] {description}"
        lines.append(f"{score_str:>7}  {t.get('name', ''):<{col1}}  {description}")
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
        error_msg = d.get("error", "")
        suggestions = d.get("suggestions", [])
        # Fix-R13D-1: this used to hardcode "not found" for every error here,
        # discarding a more specific message like "requires API key(s) not
        # set: X" (confirmed live this contradicted `tu run`'s own error for
        # the exact same tool name, which does surface the real reason).
        # Only fall back to the generic not-found/"did you mean" framing when
        # the tool is genuinely absent from the registry.
        if name and error_msg and "not found" not in error_msg:
            return f"Error: Tool '{name}' {error_msg}"
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


def _extract_detail_hint(raw_detail: Any) -> str | None:
    """Pull a human-readable hint out of an error envelope's `detail` field.

    Different tools populate `detail` inconsistently: a dict with hint/
    message keys, or (very commonly, since many tools just pass through
    `resp.text`) a raw response-body string that is often itself a
    JSON-encoded object, e.g. '{"code": "404", "status": "The Uniprot code
    p00698 does not exist in the SASBDB"}'. The default (non---json) CLI
    output previously dropped this entirely, showing only the generic
    top-level error string and leaving the actually-useful upstream
    message discoverable only via --json (confirmed live for SASBDB 404s
    and AlphaFold 400s).
    """
    if isinstance(raw_detail, dict):
        return raw_detail.get("hint") or raw_detail.get("message")
    if isinstance(raw_detail, str) and raw_detail.strip():
        try:
            parsed = json.loads(raw_detail)
        except (json.JSONDecodeError, TypeError):
            parsed = None
        if isinstance(parsed, dict):
            for key in ("message", "error", "status", "detail", "reason"):
                val = parsed.get(key)
                if isinstance(val, str) and val.strip():
                    return val
        # Not JSON, or no usable field inside it -- fall back to the raw
        # string, capped so a huge HTML error page doesn't flood the
        # terminal.
        return raw_detail if len(raw_detail) <= 300 else raw_detail[:297] + "..."
    return None


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
    # Short, actionable error summary. The project's standard envelope nests
    # the error message under d["data"]["error"]; older tools put it at the
    # top level. Check both so the CLI never falls back to "unknown error"
    # when the message is actually present.
    nested = d.get("data") or {}
    short_err = (
        d.get("error")
        or (nested.get("error") if isinstance(nested, dict) else None)
        or "unknown error"
    )
    lines = [f"Error: {short_err}"]
    # Fix-R3B-007/R3E-002: BaseRESTTool-backed tools (openFDA, EPA, etc.) put
    # the raw upstream HTTP response body in `detail` on non-2xx responses.
    # That's often the only place the *actionable* explanation lives (e.g.
    # openFDA's "use a .exact keyword field" hint) — short_err is usually
    # just a generic "<Tool> API error". Surface it instead of dropping it.
    detail = d.get("detail")
    detail_already_shown = False
    if isinstance(detail, str) and detail.strip() and detail.strip() not in short_err:
        lines.append(f"Detail: {detail.strip()[:300]}")
        detail_already_shown = True
    details = d.get("error_details") or {}

    # Feature-25B-02: for "tool not found" errors, replace generic network tips
    # with tool-discovery tips and include fuzzy suggestions when available.
    # Fix-R18A-2/R18C-6: a plain "not found" substring match also fires on a
    # tool's own HTTP-404-shaped error message (e.g. "PDBe API error: 404
    # Client Error: Not Found for url: ..." or CTD's "'cadmium' was not found
    # in the RENCI CTD mirror") -- confirmed live these produced misleading
    # "check tool name spelling" tips for a perfectly valid tool call with a
    # bad parameter VALUE, not a bad tool name. A genuine unknown-tool-name
    # error is reliably tagged error_details.type == "ToolUnavailableError"
    # (confirmed live); use that structured signal instead of the message text.
    is_not_found = details.get("type") == "ToolUnavailableError"
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
        # Surface a tool-provided hint (top-level or nested under data) so
        # actionable auth/usage guidance reaches CLI users, not just JSON consumers.
        hint = d.get("hint") or (
            nested.get("hint") if isinstance(nested, dict) else None
        )
        if hint:
            cli_steps = [*cli_steps, hint]
        # Fix-R18C-1: some tools put a single actionable redirect at the
        # top-level "suggestion" key (e.g. CTD_get_gene_diseases pointing
        # callers at OpenTargets) -- confirmed live this was silently
        # dropped since only the plural "suggestions" (fuzzy tool-name
        # matches) and error_details.next_steps were ever surfaced.
        suggestion = d.get("suggestion")
        if suggestion:
            cli_steps = [*cli_steps, suggestion]
        # Fix-R18D-3/R20: BaseRESTTool-backed tools put the actionable
        # upstream error in a top-level (or nested) "detail" field, distinct
        # from error_details -- confirmed live this was silently dropped,
        # leaving only the generic "Error: HTTP request failed" with no
        # indication of the real cause.
        raw_detail = d.get("detail") or (
            nested.get("detail") if isinstance(nested, dict) else None
        )
        detail_hint = _extract_detail_hint(raw_detail)
        # When `detail` is a plain (non-JSON) string, _extract_detail_hint's
        # fallback returns that exact string (capped the same way), which
        # would just repeat the "Detail: ..." line above -- both come from
        # the same d["detail"] value. Skip in that case; still show it when
        # extraction actually pulled a more specific sub-field out of JSON.
        is_raw_passthrough_of_shown_detail = detail_already_shown and detail_hint == (
            detail if len(detail) <= 300 else detail[:297] + "..."
        )
        if (
            detail_hint
            and detail_hint != hint
            and not is_raw_passthrough_of_shown_detail
        ):
            cli_steps = [*cli_steps, f"Upstream detail: {detail_hint}"]
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
    # "tools loaded" counts registered configs, not runnable tools. Flag any
    # optional dependency group that is missing so a partial install is visible.
    gaps = d.get("missing_extras") or {}
    if gaps:
        lines.append(
            f"\noptional deps:   {len(gaps)} group(s) not installed "
            "(tools needing them will fail at runtime)"
        )
        for extra, packages in gaps.items():
            lines.append(
                f"  [{extra}]{'':<{max(0, 14 - len(extra))}} missing: {', '.join(packages)}"
            )
        lines.append("  run `tooluniverse-doctor` for details")
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
    # Fix-R13D-1: skip this for a gated tool (error != "not found") -- the
    # tool name is already exact, so suggesting near-miss alternatives is
    # noise, not help.
    if isinstance(result, dict) and "tools" in result:
        all_names = list(tu.all_tool_dict.keys())
        for tool in result["tools"]:
            if isinstance(tool, dict) and tool.get("error") == "not found":
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
        # Preserve the stable batch envelope while restoring the top-level error
        # contract used by shell clients.  Per-tool details remain available in
        # ``tools``; the alias only appears when the request was a total failure.
        tools_in_result = result.get("tools", [])
        if tools_in_result and all(
            isinstance(tool, dict) and "error" in tool for tool in tools_in_result
        ):
            if len(tools_in_result) == 1:
                result.setdefault("error", tools_in_result[0]["error"])
            else:
                result.setdefault("error", "no requested tools are available")
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
    # Fix-R3-02: `tu info <typo>` already offers "Did you mean: ...", but the
    # far more common `tu run <typo>` did not -- _render_run_error knows how to
    # display suggestions, yet nothing on the run path ever populated them, so
    # a one-character tool-name typo produced only generic spelling tips.
    # Populate them here exactly as cmd_info does. Skip API-key-gated tools:
    # their name is already correct, so near-miss alternatives are noise.
    if isinstance(result, dict) and result.get("status") == "error":
        details = result.get("error_details") or {}
        is_api_key_error = "requires api key" in str(result.get("error", "")).lower()
        if details.get("type") == "ToolUnavailableError" and not is_api_key_error:
            # Same cutoff as cmd_info (Feature-23B-04) to avoid coincidental matches.
            suggestions = difflib.get_close_matches(
                args.tool_name, list(tu.all_tool_dict.keys()), n=3, cutoff=0.62
            )
            if suggestions:
                result["suggestions"] = suggestions
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
        from tooluniverse.extras import runtime_readiness

        readiness = runtime_readiness(tu.all_tools)
    status = {
        "total_tools": len(tu.all_tools),
        # Backward-compatible alias retained for existing CLI JSON consumers.
        "tools_loaded": len(tu.all_tools),
        "categories": len(category_counts),
        "workspace": str(tu._workspace_dir),
        "profile_active": tu._workspace_profile_config is not None,
        "top_categories": dict(
            sorted(category_counts.items(), key=lambda x: -x[1])[:10]
        ),
        "version": _TU_VERSION,
        "gated_tools_count": gated_count,
        "missing_extras": readiness["missing_extras"],
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


def _remote_tool_install_hint() -> str:
    return (
        "tuplatform-connect is not published on PyPI; install its reviewed "
        "public wheel with the pinned SHA-256:\n  "
        'pip install "tuplatform-connect @ '
        "https://connect.aiscientist.tools/downloads/"
        "tuplatform_connect-0.3.0-py3-none-any.whl"
        "#sha256=3fad5eee5ecf7887a693d93ccd1aa112dc0955617a885d1fc3daded0030f9ae0"
        '"'
    )


def _resolve_private_connection_key(
    service: str = "", *, auto_login: bool = False, no_browser: bool = False
) -> str:
    import getpass

    key = os.getenv("TOOLUNIVERSE_SERVICE_KEY", "").strip()
    if key:
        return key
    try:
        key = _read_stored_remote_key()
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Stored remote login is unusable: {exc}") from exc
    if key:
        return key
    if not sys.stdin.isatty():
        return ""
    if auto_login and service:
        key = _device_authorization_login(service, no_browser=no_browser)
        _write_stored_remote_key(key)
        return key
    try:
        return getpass.getpass("Private connection key: ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def _private_connection_key_available() -> bool:
    """Check key availability for preflight without prompting or exposing it."""

    environment_key = os.getenv("TOOLUNIVERSE_SERVICE_KEY", "").strip()
    if environment_key and not _valid_remote_key(environment_key):
        raise SystemExit(
            "TOOLUNIVERSE_SERVICE_KEY has an invalid format; unset it or replace "
            "it with `tu remote login`."
        )
    if environment_key:
        return True
    try:
        return bool(_read_stored_remote_key())
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Stored remote login is unusable: {exc}") from exc


def _remote_auth_path() -> Path:
    """Return the private per-user credential path without resolving symlinks."""

    override = os.getenv("TOOLUNIVERSE_REMOTE_AUTH_FILE", "").strip()
    if override:
        return Path(os.path.abspath(os.path.expanduser(override)))
    xdg = os.getenv("XDG_CONFIG_HOME", "").strip()
    base = (
        Path(os.path.abspath(os.path.expanduser(xdg)))
        if xdg
        else Path.home() / ".config"
    )
    return base / "tooluniverse" / "remote-auth.json"


def _read_private_bytes(path: Path, *, maximum: int = 1 << 16) -> bytes:
    """Read one small regular 0600 file without following its final symlink."""

    import stat

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"{path} is not a regular file")
        if metadata.st_mode & 0o077:
            raise ValueError(f"{path} permissions must be 0600")
        if metadata.st_size > maximum:
            raise ValueError(f"{path} is unexpectedly large")
        chunks = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(descriptor, min(remaining, 8192))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        if len(content) > maximum:
            raise ValueError(f"{path} is unexpectedly large")
        return content
    finally:
        os.close(descriptor)


def _valid_remote_key(key: str) -> bool:
    import re

    return re.fullmatch(r"tu-sk-(?:[0-9a-f]{60}|[A-Za-z0-9_-]{54})", key) is not None


def _read_stored_remote_key() -> str:
    """Load a locally stored key while preserving its secrecy."""

    path = _remote_auth_path()
    if not path.exists():
        return ""
    try:
        document = json.loads(_read_private_bytes(path).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path} does not contain valid login data") from exc
    if not isinstance(document, dict):
        raise ValueError(f"{path} does not contain valid login data")
    key = str(document.get("service_key", "")).strip()
    if not _valid_remote_key(key):
        raise ValueError(f"{path} contains an invalid connection key")
    return key


def _write_stored_remote_key(key: str) -> Path:
    """Write the verified key to a no-follow 0600 config file."""

    path = _remote_auth_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        payload = json.dumps(
            {"version": 1, "service_key": key}, separators=(",", ":")
        ).encode("utf-8")
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if not written:
                raise OSError("could not finish writing the stored remote login")
            view = view[written:]
    finally:
        os.close(descriptor)
    return path


def _key_from_protected_env_file(path_value: str) -> str:
    """Read TOOLUNIVERSE_SERVICE_KEY from a protected dotenv-style file."""

    import shlex

    path = Path(os.path.abspath(os.path.expanduser(path_value)))
    text = _read_private_bytes(path).decode("utf-8")
    found = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, value = line.partition("=")
        if separator and name.strip() == "TOOLUNIVERSE_SERVICE_KEY":
            parsed = shlex.split(value, comments=True, posix=True)
            if len(parsed) != 1:
                raise ValueError("protected env file has an invalid service-key value")
            found.append(parsed[0].strip())
    if len(found) != 1 or not _valid_remote_key(found[0]):
        raise ValueError(
            "protected env file must contain one valid TOOLUNIVERSE_SERVICE_KEY"
        )
    return found[0]


class _PlatformHTTPError(RuntimeError):
    """Structured platform failure used by the short-lived device polling loop."""

    def __init__(
        self,
        message: str,
        *,
        status: int,
        error_code: str = "",
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.error_code = error_code
        self.retry_after = retry_after


class _DeviceAuthorizationExpired(RuntimeError):
    """Internal signal used to replace one expired browser request."""


def _validate_remote_connection_key(service: str, key: str) -> dict:
    """Validate both least-privilege relay keys and legacy full-access keys safely."""

    return _platform_request(
        service, "/remote-servers/preflight", api_key=key, payload={}
    )


def _connection_key_for_share(service: str, *, no_browser: bool = False) -> str:
    """Resolve, validate, and interactively repair the key before starting a provider."""

    key = _resolve_private_connection_key(
        service, auto_login=True, no_browser=no_browser
    )
    if not key or not _valid_remote_key(key):
        return key
    try:
        _validate_remote_connection_key(service, key)
        return key
    except RuntimeError as exc:
        # Explicit environment configuration wins: silently replacing it would leave the next
        # process broken again. Non-interactive jobs also fail fast instead of waiting on a browser.
        if not sys.stdin.isatty() or os.getenv("TOOLUNIVERSE_SERVICE_KEY", "").strip():
            raise RuntimeError(
                "TU Platform connection-key validation failed before provider "
                f"startup: {exc}. Run `tu remote login` to replace an expired or "
                "revoked key."
            ) from exc
        print("Stored connection expired or was revoked; re-authorizing...")
        key = _device_authorization_login(service, no_browser=no_browser)
        _write_stored_remote_key(key)
        return key


def _device_authorization_login(service: str, *, no_browser: bool = False) -> str:
    """Authorize interactively, automatically replacing one expired request."""

    for attempt in range(2):
        try:
            return _device_authorization_attempt(service, no_browser=no_browser)
        except _DeviceAuthorizationExpired:
            if attempt:
                raise RuntimeError(
                    "browser authorization expired twice; run the command again when ready"
                ) from None
            print(
                "Authorization expired; creating one fresh link automatically...",
                flush=True,
            )
    raise AssertionError("unreachable")


def _device_authorization_attempt(service: str, *, no_browser: bool = False) -> str:
    """Run one short-lived browser authorization request."""

    import platform
    import time
    import urllib.parse
    import webbrowser

    host = platform.node().strip() or "this computer"
    started = _platform_request(
        service,
        "/auth/device/start",
        payload={"client_name": f"ToolUniverse CLI on {host}", "expires_in_days": 30},
    )
    device_code = str(started.get("device_code", ""))
    user_code = str(started.get("user_code", ""))
    verification_url = str(
        started.get("verification_uri_complete")
        or started.get("verification_uri")
        or ""
    )
    try:
        expires_in = int(started.get("expires_in", 0))
        interval = int(started.get("interval", 5))
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "platform returned invalid device authorization timing"
        ) from exc
    parsed_url = urllib.parse.urlsplit(verification_url)
    if (
        not _valid_device_code(device_code)
        or not _valid_device_user_code(user_code)
        or expires_in < 1
        or expires_in > 15 * 60
        or interval < 1
        or interval > 30
        or parsed_url.scheme not in {"http", "https"}
        or not parsed_url.hostname
        or parsed_url.username is not None
        or parsed_url.password is not None
        or any(ord(character) < 32 for character in verification_url)
    ):
        raise RuntimeError("platform returned an invalid device authorization response")

    print("Authorize this computer in your browser:")
    print(f"  {verification_url}")
    print(f"Code: {user_code}")
    print("Waiting for approval (Ctrl-C to cancel)...", flush=True)
    if not no_browser:
        try:
            if not webbrowser.open(verification_url, new=2):
                print("The browser did not open automatically; use the link above.")
        except Exception:
            print("The browser did not open automatically; use the link above.")

    deadline = time.monotonic() + expires_in
    poll_interval = interval
    while time.monotonic() < deadline:
        time.sleep(poll_interval)
        try:
            token = _platform_request(
                service,
                "/auth/device/token",
                payload={"device_code": device_code},
            )
        except _PlatformHTTPError as exc:
            if exc.error_code == "authorization_pending":
                continue
            if exc.error_code == "slow_down":
                poll_interval = min(30, max(poll_interval + 5, exc.retry_after or 0))
                continue
            if exc.error_code == "access_denied":
                raise RuntimeError("browser authorization was denied") from exc
            if exc.error_code == "expired_token":
                raise _DeviceAuthorizationExpired(
                    "browser authorization expired"
                ) from exc
            if exc.error_code == "key_limit_reached":
                raise RuntimeError(
                    "the account has 20 connection keys; revoke one in TU Platform and retry"
                ) from exc
            raise

        key = str(token.get("access_token", ""))
        if token.get("purpose") != "relay" or not _valid_remote_key(key):
            raise RuntimeError("platform returned an invalid computer-only connection")
        _validate_remote_connection_key(service, key)
        return key
    raise _DeviceAuthorizationExpired("browser authorization expired")


def _valid_device_code(code: str) -> bool:
    import re

    return re.fullmatch(r"[0-9a-f]{64}", code) is not None


def _valid_device_user_code(code: str) -> bool:
    import re

    return (
        re.fullmatch(
            r"[BCDFGHJKLMNPQRSTVWXYZ23456789]{4}-[BCDFGHJKLMNPQRSTVWXYZ23456789]{4}",
            code,
        )
        is not None
    )


def cmd_remote_login(args: argparse.Namespace) -> None:
    """Authorize in a browser or import and securely remember one connection key."""

    import getpass

    try:
        if args.env_file:
            key = _key_from_protected_env_file(args.env_file)
        else:
            key = os.getenv("TOOLUNIVERSE_SERVICE_KEY", "").strip()
            if not key and getattr(args, "manual_key", False) and sys.stdin.isatty():
                key = getpass.getpass("Computer-only connection key: ").strip()
            if not key and not getattr(args, "manual_key", False):
                key = _device_authorization_login(
                    args.service, no_browser=getattr(args, "no_browser", False)
                )
        if not _valid_remote_key(key):
            raise ValueError("a valid computer-only connection key is required")
        _validate_remote_connection_key(args.service, key)
        path = _write_stored_remote_key(key)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Error: remote login failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    print(f"Remote login verified and stored securely at {path} (0600).")
    print("The connection key was not displayed.")


def cmd_remote_logout(args: argparse.Namespace) -> None:
    """Remove the local login and optionally revoke its platform credential."""

    path = _remote_auth_path()
    try:
        if getattr(args, "revoke", False):
            key = _read_stored_remote_key()
            if not key:
                raise ValueError("no stored connection key is available to revoke")
            _platform_request(
                getattr(
                    args,
                    "service",
                    "https://tooluniverse-backend.onrender.com",
                ),
                "/remote-servers/connection-key",
                api_key=key,
                method="DELETE",
            )
        path.unlink(missing_ok=True)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Error: could not remove stored remote login: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if getattr(args, "revoke", False):
        print(f"Revoked the platform connection and removed its local login at {path}.")
    else:
        print(f"Removed stored remote login at {path}.")


def _local_mcp_endpoint(host: str, port: int) -> tuple[str, str]:
    """Return a connectable host and correctly formatted local MCP URL."""
    connect_host = {"0.0.0.0": "127.0.0.1", "::": "::1"}.get(host, host)
    url_host = f"[{connect_host}]" if ":" in connect_host else connect_host
    return connect_host, f"http://{url_host}:{port}/mcp"


def _start_remote_tool_server(args: argparse.Namespace) -> None:
    import hashlib
    import importlib.util
    import socket
    import threading
    import time
    from pathlib import Path

    from tooluniverse.mcp_tool_registry import (
        _mcp_tool_registry,
        _start_server_for_port,
        collect_tools_for_serve,
    )

    for raw_path in args.files:
        path = Path(raw_path).expanduser().resolve()
        if not path.is_file() or path.suffix != ".py":
            raise ValueError(f"remote tool file not found or not Python: {raw_path}")
        module_name = (
            "_tooluniverse_remote_"
            + hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]
        )
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ValueError(f"could not import remote tool file: {raw_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(module_name, None)
            raise

    server_name = args.name or Path(args.files[0]).stem.replace("_", " ").title()
    selected = collect_tools_for_serve(
        args.port,
        host=args.host,
        server_name=server_name,
        max_workers=args.workers,
    )
    if not selected or not _mcp_tool_registry:
        raise ValueError(
            "no remote tools found; decorate a function with @remote_tool or "
            "a class with @register_remote_tool"
        )

    local_host, local_url = _local_mcp_endpoint(args.host, args.port)
    print(f"Remote tool server: {server_name}", flush=True)
    print(f"Tools: {', '.join(item['name'] for item in selected)}", flush=True)
    print(f"Local MCP: {local_url}", flush=True)

    if not args.share:
        _start_server_for_port(args.port)
        return

    try:
        from tuplatform_connect.relay import RelayAgent, RelayError
    except ImportError as exc:
        raise RuntimeError(
            "--share requires the maintained tuplatform-connect relay.\n"
            + _remote_tool_install_hint()
        ) from exc

    api_key = _connection_key_for_share(
        args.service,
        no_browser=getattr(args, "no_browser", False),
    )
    if not api_key:
        raise RuntimeError(
            "--share requires a computer-only connection key. Set "
            "TOOLUNIVERSE_SERVICE_KEY or run interactively to enter it securely."
        )

    server_errors = []

    def run_server():
        try:
            _start_server_for_port(args.port)
        except BaseException as exc:  # surface failures from the daemon thread
            server_errors.append(exc)

    thread = threading.Thread(
        target=run_server, name="tooluniverse-remote-mcp", daemon=True
    )
    thread.start()
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if server_errors:
            raise RuntimeError(f"local MCP server failed: {server_errors[0]}")
        try:
            with socket.create_connection((local_host, args.port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.1)
    else:
        raise RuntimeError("local MCP server did not start within 20 seconds")

    print("Sharing through ToolUniverse Platform; press Ctrl-C to stop.")
    print(
        "Manage the computer and publish one selected tool at: "
        "https://connect.aiscientist.tools/remote-servers"
    )
    try:
        RelayAgent(
            args.service,
            api_key,
            local_url,
            server_name,
            workers=args.workers,
        ).run_forever()
    except RelayError as exc:
        raise RuntimeError(str(exc)) from exc


def _forward_remote_tool_server(args: argparse.Namespace) -> None:
    try:
        from tuplatform_connect.relay import RelayAgent, RelayError
    except ImportError as exc:
        raise RuntimeError(
            "--forward requires tuplatform-connect.\n" + _remote_tool_install_hint()
        ) from exc
    key = _connection_key_for_share(
        args.service,
        no_browser=getattr(args, "no_browser", False),
    )
    if not key:
        raise RuntimeError("a computer-only connection key is required")
    try:
        RelayAgent(
            args.service,
            key,
            args.forward,
            args.name or "Remote MCP Server",
            workers=args.workers,
        ).run_forever()
    except RelayError as exc:
        raise RuntimeError(str(exc)) from exc


def cmd_doctor(args: argparse.Namespace) -> None:
    """Run local SDK diagnostics or a joined local-MCP/platform preflight."""
    if not args.forward:
        from tooluniverse.doctor import main as doctor_main

        raise SystemExit(doctor_main())
    try:
        from tuplatform_connect.doctor import run_checks
    except ImportError as exc:
        raise SystemExit(
            "Remote diagnostics require tuplatform-connect.\n"
            + _remote_tool_install_hint()
        ) from exc
    result = run_checks(
        args.service,
        _resolve_private_connection_key(args.service),
        args.forward,
    )
    if args.json:
        print(json.dumps(result, separators=(",", ":")))
    else:
        for check in result["checks"]:
            marker = "✓" if check["ok"] else "✗"
            print(f"{marker} {check['name']}: {check['detail']}")
        print(
            "Ready to share."
            if result["ok"]
            else "Fix the failed checks and run this command again."
        )
    if not result["ok"]:
        raise SystemExit(1)


def cmd_serve(args: argparse.Namespace) -> None:
    """Start the normal MCP server or expose provider-owned remote tools."""
    try:
        forward = getattr(args, "forward", None)
        files = getattr(args, "files", [])
        share = getattr(args, "share", False)
        if forward and files:
            raise ValueError("use either TOOL.py files or --forward, not both")
        if share and not files and not forward:
            raise ValueError("--share requires TOOL.py files or --forward URL")
        if forward:
            _forward_remote_tool_server(args)
        elif files:
            _start_remote_tool_server(args)
        else:
            from tooluniverse.smcp_server import run_default_stdio_server

            run_default_stdio_server()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def _print_remote_check(result: dict, *, as_json: bool) -> None:
    """Render remote preflight without ever including secret values."""
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    marker = "✓" if result.get("ok") else "✗"
    print(f"{marker} implementation: {result.get('implementation', 'unknown')}")
    if result.get("error"):
        print(f"  error: {result['error']}")
    if result.get("python"):
        print(f"  provider Python: {result['python']}")
    provider = result.get("provider") or {}
    if provider.get("error"):
        print(f"  provider error: {provider['error']}")
    python_supported = result.get("python_supported_3_12")
    python_label = (
        "unknown" if python_supported is None else ("yes" if python_supported else "no")
    )
    print(f"  Python 3.12: {python_label}")
    module_available = provider.get("module_available")
    module_label = (
        "unknown"
        if module_available is None
        else ("yes" if module_available else "no")
    )
    print(f"  provider module: {module_label}")
    for command, available in (provider.get("commands") or {}).items():
        print(f"  command {command}: {'yes' if available else 'no'}")
    for variable in result.get("provider_environment") or []:
        ready = variable.get("set") and variable.get("path_exists", True)
        print(f"  environment {variable['name']}: {'ready' if ready else 'missing'}")
    credentials = result.get("provider_credentials") or {}
    if credentials:
        state = "ready" if credentials.get("ready") else "blocked"
        status = credentials.get("http_status")
        suffix = f" (HTTP {status})" if status else ""
        print(f"  provider credential {credentials['name']}: {state}{suffix}")
        if credentials.get("detail"):
            print(f"    {credentials['detail']}")
    gpu = provider.get("gpu") or {}
    gpu_policy = result.get("gpu_policy")
    if gpu_policy != "none":
        passed = gpu.get("tensor_sum") == 28.0
        label = (
            "passed"
            if passed
            else ("unavailable (optional)" if gpu_policy == "recommended" else "failed")
        )
        print(f"  CUDA tensor check: {label}")
        if gpu.get("device"):
            print(f"  GPU: {gpu['device']}")
    share = result.get("share_prerequisites") or {}
    if share.get("requested"):
        print(f"  relay SDK: {'yes' if share.get('sdk_available') else 'no'}")
        print(
            f"  connection key set: {'yes' if share.get('service_key_set') else 'no'}"
        )


def cmd_remote_list(args: argparse.Namespace) -> None:
    """List reviewed provider entry points."""
    from tooluniverse.remote_runtime import REMOTE_DEPLOYMENTS

    rows = [
        {
            "implementation": deployment.slug,
            "endpoint": deployment.endpoint,
            "operations": list(deployment.operations),
            "gpu_policy": deployment.gpu_policy,
            "relay_workers": deployment.relay_workers,
        }
        for deployment in REMOTE_DEPLOYMENTS
    ]
    if args.json:
        print(json.dumps({"implementations": rows}, indent=2))
        return
    for row in rows:
        print(
            f"{row['implementation']:<22} {row['endpoint']:<32} gpu={row['gpu_policy']}"
        )


def cmd_remote_check(args: argparse.Namespace) -> None:
    """Check a reviewed provider environment and current endpoint."""
    from tooluniverse.remote_runtime import (
        REMOTE_BY_SLUG,
        check_environment,
        discover_endpoint,
    )

    deployment = REMOTE_BY_SLUG[args.implementation]
    result = check_environment(
        deployment,
        python=args.python,
        share=args.share,
        service_key_available=(
            _private_connection_key_available() if args.share else None
        ),
        allow_cpu=args.allow_cpu,
        timeout=args.timeout,
    )
    local_mcp = discover_endpoint(deployment, timeout=2)
    result["local_mcp"] = local_mcp
    # An absent endpoint is expected before first launch. A reachable endpoint
    # with the wrong tool set is a hard conflict and must never appear healthy.
    if local_mcp.get("reachable") and not local_mcp.get("ok"):
        result["ok"] = False
    _print_remote_check(result, as_json=args.json)
    if not result.get("ok"):
        raise SystemExit(1)


def cmd_remote_run(args: argparse.Namespace) -> None:
    """Start/reuse one reviewed provider and optionally share it privately."""
    from tooluniverse.remote_runtime import (
        REMOTE_BY_SLUG,
        check_environment,
        ensure_provider,
        resolve_python,
        stop_provider,
    )

    deployment = REMOTE_BY_SLUG[args.implementation]
    try:
        key = (
            _connection_key_for_share(
                getattr(args, "service", ""),
                no_browser=getattr(args, "no_browser", False),
            )
            if args.share
            else ""
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if args.share and not key:
        print(
            "Error: no private connection key is configured. "
            "Run `tu remote login` once, then retry this command.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if args.share and not _valid_remote_key(key):
        print(
            "Error: the private connection key has an invalid format. "
            "Unset TOOLUNIVERSE_SERVICE_KEY if it is overriding a stored login, "
            "then run `tu remote login`.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    check = check_environment(
        deployment,
        python=args.python,
        share=args.share,
        service_key_available=bool(key),
        allow_cpu=args.allow_cpu,
        timeout=args.timeout,
    )
    _print_remote_check(check, as_json=False)
    if not check.get("ok"):
        raise SystemExit(1)

    managed = None
    try:
        if args.share:
            print("TU Platform connection key verified.")

        provider_python = resolve_python(args.python, deployment)
        managed, ready = ensure_provider(
            deployment,
            python=provider_python,
            log_dir=args.log_dir,
            startup_timeout=args.startup_timeout,
        )
        action = "Started" if managed is not None else "Reused"
        print(f"{action} exact local MCP: {ready['endpoint']}")
        print(f"Tools: {', '.join(ready['discovered_operations'])}")
        if managed is not None:
            print(f"Provider log: {managed.log_path}")

        if not args.share:
            if managed is None:
                return
            print("Remote tool is ready; press Ctrl-C to stop.")
            try:
                exit_code = managed.process.wait()
            except KeyboardInterrupt:
                return
            if exit_code:
                raise RuntimeError(f"provider exited with code {exit_code}")
            return

        from tuplatform_connect.doctor import run_checks
        from tuplatform_connect.relay import RelayAgent, RelayError

        doctor = run_checks(args.service, key, deployment.endpoint)
        if not doctor.get("ok"):
            details = "; ".join(
                check_item.get("detail", check_item.get("name", "failed"))
                for check_item in doctor.get("checks", [])
                if not check_item.get("ok")
            )
            raise RuntimeError(f"TU Platform preflight failed: {details}")
        print("TU Platform preflight passed.")
        print("Sharing privately; press Ctrl-C to stop the relay.")
        try:
            workers = args.workers or deployment.relay_workers
            RelayAgent(
                args.service,
                key,
                deployment.endpoint,
                args.name or f"{deployment.slug}-remote",
                workers=workers,
            ).run_forever()
        except RelayError as exc:
            raise RuntimeError(str(exc)) from exc
    except KeyboardInterrupt:
        print("Stopping remote tool.")
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    finally:
        stop_provider(managed)


def _platform_request(
    base_url: str,
    path: str,
    *,
    api_key: str = "",
    payload: dict | None = None,
    method: str | None = None,
) -> dict:
    import urllib.error
    import urllib.request

    from tooluniverse.platform_remote_tool import _NoRedirect, _validated_base_url

    body = None
    headers = {"Accept": "application/json", "User-Agent": "tooluniverse-cli/1"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if payload is not None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        _validated_base_url(base_url) + path,
        data=body,
        method=method or ("POST" if payload is not None else "GET"),
        headers=headers,
    )
    try:
        with urllib.request.build_opener(_NoRedirect).open(
            request, timeout=15
        ) as response:
            raw = response.read((16 << 20) + 1)
        if len(raw) > 16 << 20:
            raise ValueError("platform response exceeded 16 MiB")
        result = json.loads(raw.decode("utf-8"))
        if not isinstance(result, dict):
            raise ValueError("platform returned an unexpected response")
        return result
    except urllib.error.HTTPError as exc:
        detail = f"platform returned HTTP {exc.code}"
        error_code = ""
        try:
            parsed = json.loads(exc.read(1 << 20).decode("utf-8"))
            if isinstance(parsed, dict):
                detail = str(
                    parsed.get("error_description") or parsed.get("detail") or detail
                )
                error_code = str(parsed.get("error") or "")
        except Exception:
            pass
        retry_after = None
        try:
            retry_after = int(exc.headers.get("Retry-After", ""))
        except (TypeError, ValueError):
            pass
        raise _PlatformHTTPError(
            detail,
            status=exc.code,
            error_code=error_code,
            retry_after=retry_after,
        ) from exc


def cmd_connect(args: argparse.Namespace) -> None:
    """Persist one explicit MCP server, shared server, or marketplace tool."""
    from tooluniverse.remote_connections import (
        extract_resource_id,
        mcp_connection,
        platform_connection,
        save_connection,
    )

    target = args.target.strip()
    base_url = args.service.rstrip("/")
    try:
        if target.upper().startswith("TU-SHARE-"):
            env_name = (
                "TU_API_KEY" if os.getenv("TU_API_KEY") else "TOOLUNIVERSE_SERVICE_KEY"
            )
            api_key = os.getenv(env_name, "").strip()
            if not api_key:
                raise RuntimeError(
                    "joining a share code requires TU_API_KEY or TOOLUNIVERSE_SERVICE_KEY"
                )
            joined = _platform_request(
                base_url,
                "/remote-servers/join",
                api_key=api_key,
                payload={"share_code": target},
            )
            server_id = joined.get("server_id")
            if not server_id:
                raise RuntimeError("platform did not return the joined server")
            server = _platform_request(
                base_url, f"/remote-servers/{server_id}", api_key=api_key
            )
            connection = mcp_connection(
                server["relay_url"], args.name or server.get("name", "remote"), env_name
            )
        else:
            resource_id = extract_resource_id(target)
            looks_like_marketplace = args.platform or resource_id == target.lower()
            if resource_id and (
                looks_like_marketplace
                or "connect.aiscientist.tools" in target
                or "/discover/" in target
            ):
                metadata = _platform_request(
                    base_url, f"/expert-sessions/public/{resource_id}"
                )
                if metadata.get("tool_type") not in {"remote-mcp", "hosted-sdk"}:
                    raise ValueError("only automated published tools can be connected")
                raw_schema = metadata.get("input_schema") or "{}"
                schema = (
                    json.loads(raw_schema)
                    if isinstance(raw_schema, str)
                    else raw_schema
                )
                if not isinstance(schema, dict):
                    schema = {"type": "object"}
                connection = platform_connection(
                    resource_id,
                    name=args.name or metadata.get("name", "Remote tool"),
                    description=metadata.get("description", ""),
                    input_schema=schema,
                    base_url=base_url,
                )
            else:
                connection = mcp_connection(target, args.name, args.auth_env)
        changed = save_connection(connection)
    except (KeyError, OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    tool_hint = (
        connection.get("tool_name") or connection.get("prefix", "remote_") + "<tool>"
    )
    action = "Connected" if changed else "Already connected"
    print(f"{action}: {connection['name']}")
    print(f"Tool name: {tool_hint}")
    print("It will load on the next ToolUniverse.load_tools() or `tu serve` start.")


def cmd_connections(args: argparse.Namespace) -> None:
    """List explicit remote connections without resolving or contacting them."""
    from tooluniverse.remote_connections import read_connections

    connections = read_connections()
    if args.json:
        print(json.dumps(connections, indent=2, ensure_ascii=False))
        return
    if not connections:
        print("No remote tool connections saved.")
        print("Add one with: tu connect <MCP-URL> --name <unique-name>")
        return
    for connection in connections:
        kind = connection.get("kind", "remote")
        target = connection.get("url") or connection.get("resource_id") or "unknown"
        namespace = connection.get("tool_name") or connection.get("prefix") or ""
        auth = (
            f" (token from {connection['auth_env']})"
            if connection.get("auth_env")
            else ""
        )
        print(f"{connection.get('name', 'Remote tool')} [{kind}]")
        print(f"  target: {target}{auth}")
        print(f"  tool namespace: {namespace}")


def cmd_disconnect(args: argparse.Namespace) -> None:
    """Remove one explicit remote connection without contacting the server."""
    from tooluniverse.remote_connections import remove_connection

    try:
        removed = remove_connection(args.target)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if removed is None:
        print(f"No saved connection matched: {args.target}", file=sys.stderr)
        raise SystemExit(1)
    print(f"Disconnected: {removed.get('name', 'Remote tool')}")
    print(
        "It will be absent after the next ToolUniverse.load_tools() or `tu serve` start."
    )


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
    # Fix-R4E-2: users reflexively type grep's -i flag; accept it instead of
    # an unrecognized-arguments error. text mode (the default) already does
    # case-insensitive matching, so this is a no-op rather than a real toggle.
    p.add_argument(
        "-i",
        "--ignore-case",
        action="store_true",
        help="No-op: text mode (the default) is already case-insensitive",
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
        help=(
            "Rebuild the static tool registry and regenerate coding-API "
            "wrapper files (run after adding new built-in tools)"
        ),
    )
    p.add_argument(
        "--output",
        metavar="DIR",
        default=None,
        help=(
            "Directory to write coding-API wrapper files into "
            "(default: .tooluniverse/coding_api/). Only affects the wrapper "
            "files — the static lazy registry is always regenerated in "
            "place inside the installed package, regardless of --output."
        ),
    )
    p.set_defaults(func=cmd_build)

    # ── remote ────────────────────────────────────────────────────────────────
    from tooluniverse.remote_runtime import REMOTE_BY_SLUG

    remote = sub.add_parser(
        "remote",
        help="Check, start, and privately share reviewed remote-tool providers",
    )
    remote_sub = remote.add_subparsers(dest="remote_command", required=True)

    p = remote_sub.add_parser("list", help="List reviewed remote-tool providers")
    p.add_argument("--json", action="store_true", help="output machine-readable JSON")
    p.set_defaults(func=cmd_remote_list)

    p = remote_sub.add_parser(
        "login",
        help="authorize this computer in a browser and remember it securely",
    )
    p.add_argument(
        "--env-file",
        metavar="PATH",
        help="import TOOLUNIVERSE_SERVICE_KEY from an existing 0600 env file",
    )
    p.add_argument(
        "--manual-key",
        action="store_true",
        help="read a connection key from a hidden terminal prompt instead of opening a browser",
    )
    p.add_argument(
        "--no-browser",
        action="store_true",
        help="print the authorization link without trying to open a browser",
    )
    p.add_argument(
        "--service",
        default=os.getenv(
            "TOOLUNIVERSE_SERVICE_URL",
            os.getenv("TU_BASE_URL", "https://tooluniverse-backend.onrender.com"),
        ),
        help="ToolUniverse Platform API base URL",
    )
    p.set_defaults(func=cmd_remote_login)

    p = remote_sub.add_parser(
        "logout", help="remove the locally stored private connection key"
    )
    p.add_argument(
        "--revoke",
        action="store_true",
        help="also revoke this computer-only connection on TU Platform",
    )
    p.add_argument(
        "--service",
        default=os.getenv(
            "TOOLUNIVERSE_SERVICE_URL",
            os.getenv("TU_BASE_URL", "https://tooluniverse-backend.onrender.com"),
        ),
        help="ToolUniverse Platform API base URL",
    )
    p.set_defaults(func=cmd_remote_logout)

    def _add_remote_common(
        remote_parser: argparse.ArgumentParser, *, include_share: bool = True
    ) -> None:
        remote_parser.add_argument(
            "implementation",
            choices=sorted(REMOTE_BY_SLUG),
            help="reviewed remote-tool implementation",
        )
        remote_parser.add_argument(
            "--python",
            metavar="PATH",
            help="Python executable from the provider environment",
        )
        if include_share:
            remote_parser.add_argument(
                "--share",
                action="store_true",
                help="also require TU Platform relay credentials",
            )
        remote_parser.add_argument(
            "--no-browser",
            action="store_true",
            help="print login links without trying to open a browser",
        )
        remote_parser.add_argument(
            "--allow-cpu",
            action="store_true",
            help="allow CPU execution when the provider normally requires CUDA",
        )
        remote_parser.add_argument(
            "--timeout",
            type=float,
            default=30,
            help="provider-environment check timeout in seconds (default: 30)",
        )

    p = remote_sub.add_parser(
        "check",
        help="validate one provider environment and probe its local endpoint",
    )
    _add_remote_common(p)
    p.add_argument("--json", action="store_true", help="output machine-readable JSON")
    p.set_defaults(func=cmd_remote_check)

    def _add_remote_run_options(remote_parser: argparse.ArgumentParser) -> None:
        remote_parser.add_argument(
            "--name", help="private connection name shown on TU Platform"
        )
        remote_parser.add_argument(
            "--workers",
            type=_bounded_int(1, 2),
            default=None,
            help=(
                "maximum concurrent relayed calls "
                "(default: reviewed provider value; maximum: 2)"
            ),
        )
        remote_parser.add_argument(
            "--startup-timeout",
            type=float,
            default=120,
            help="local provider startup timeout in seconds (default: 120)",
        )
        remote_parser.add_argument(
            "--log-dir",
            default=os.getenv(
                "TOOLUNIVERSE_REMOTE_LOG_DIR", ".tooluniverse/remote-logs"
            ),
            help="provider log directory (default: .tooluniverse/remote-logs)",
        )
        remote_parser.add_argument(
            "--service",
            default=os.getenv(
                "TOOLUNIVERSE_SERVICE_URL",
                os.getenv("TU_BASE_URL", "https://tooluniverse-backend.onrender.com"),
            ),
            help="ToolUniverse Platform API base URL",
        )

    p = remote_sub.add_parser(
        "run",
        help="start or reuse one provider and optionally share it privately",
    )
    _add_remote_common(p)
    _add_remote_run_options(p)
    p.set_defaults(func=cmd_remote_run)

    p = remote_sub.add_parser(
        "share",
        help="start or reuse one provider and share it privately",
    )
    _add_remote_common(p, include_share=False)
    _add_remote_run_options(p)
    p.set_defaults(func=cmd_remote_run, share=True)

    # ── doctor ────────────────────────────────────────────────────────────────
    p = sub.add_parser(
        "doctor",
        help="Check local ToolUniverse, or validate a remote MCP server and platform connection",
    )
    p.add_argument(
        "--forward",
        metavar="URL",
        help="local Streamable HTTP MCP endpoint to validate",
    )
    p.add_argument(
        "--service",
        default=os.getenv(
            "TOOLUNIVERSE_SERVICE_URL",
            os.getenv("TU_BASE_URL", "https://tooluniverse-backend.onrender.com"),
        ),
        help="ToolUniverse Platform API base URL",
    )
    p.add_argument("--json", action="store_true", help="output machine-readable JSON")
    p.set_defaults(func=cmd_doctor)

    # ── serve ─────────────────────────────────────────────────────────────────
    p = sub.add_parser(
        "serve",
        help="Start ToolUniverse MCP or launch/share provider-owned remote tools",
    )
    p.add_argument(
        "files",
        nargs="*",
        metavar="TOOL.py",
        help="Python files containing @remote_tool or @register_remote_tool",
    )
    p.add_argument(
        "--share",
        action="store_true",
        help="share the remote tool server through ToolUniverse Platform",
    )
    p.add_argument(
        "--forward",
        metavar="URL",
        help="share an already-running Streamable HTTP MCP server",
    )
    p.add_argument("--name", help="server name shown to users")
    p.add_argument(
        "--host",
        default="127.0.0.1",
        help="local bind host for file mode (default: 127.0.0.1)",
    )
    p.add_argument(
        "--port",
        type=_bounded_int(1, 65535),
        default=8080,
        help="local MCP port for file mode (default: 8080)",
    )
    p.add_argument(
        "--workers",
        type=_bounded_int(1, 32),
        default=8,
        help="maximum concurrent local requests (default: 8)",
    )
    p.add_argument(
        "--service",
        default=os.getenv(
            "TOOLUNIVERSE_SERVICE_URL",
            os.getenv("TU_BASE_URL", "https://tooluniverse-backend.onrender.com"),
        ),
        help="ToolUniverse Platform API base URL",
    )
    p.add_argument(
        "--no-browser",
        action="store_true",
        help="print login links without trying to open a browser",
    )
    p.set_defaults(func=cmd_serve)

    # ── connect ───────────────────────────────────────────────────────────────
    p = sub.add_parser(
        "connect",
        help="connect one explicit MCP server, shared server, or published tool",
    )
    p.add_argument(
        "target", help="MCP URL, TU-SHARE code, marketplace URL, or tool UUID"
    )
    p.add_argument("--name", help="local display name and tool prefix")
    p.add_argument(
        "--auth-env",
        default="",
        help="environment variable containing a direct MCP server bearer token",
    )
    p.add_argument(
        "--platform",
        action="store_true",
        help="treat a UUID-containing target as a published platform tool",
    )
    p.add_argument(
        "--service",
        default=os.getenv("TU_BASE_URL", "https://tooluniverse-backend.onrender.com"),
        help="ToolUniverse Platform API base URL",
    )
    p.set_defaults(func=cmd_connect)

    p = sub.add_parser(
        "connections",
        help="list saved remote tool connections without contacting them",
    )
    p.add_argument("--json", action="store_true", help="output JSON")
    p.set_defaults(func=cmd_connections)

    p = sub.add_parser(
        "disconnect",
        help="remove one saved remote tool connection",
    )
    p.add_argument(
        "target", help="exact MCP URL, UUID, display name, or tool namespace"
    )
    p.set_defaults(func=cmd_disconnect)

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
