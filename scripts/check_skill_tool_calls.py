#!/usr/bin/env python3
"""Statically check that tool calls shown in skill markdown match the real tool schemas.

For every call written as ``tools.NAME(kw=...)``, ``tu run NAME '{json}'`` or
``{"name": "NAME", "arguments": {...}}`` it reports:

* an argument the tool does not declare (ToolUniverse rejects these, or silently
  drops them when they are mixed with valid ones);
* a required argument that is missing;
* a tool name that does not exist (only when its prefix is shared by other real
  tools, so made-up example names and ordinary identifiers are not flagged).

Nothing is instantiated or executed: schemas are read from
``src/tooluniverse/data/*.json``. Do not replace this with a live run over many
tools -- some tool classes load multi-GB datasets when constructed.

A call is skipped when its own line or one of the four lines above it contains
``WRONG``, ``❌`` or ``noqa: skill-call`` (deliberate "wrong usage" examples).

Usage:
    python scripts/check_skill_tool_calls.py            # all skills
    python scripts/check_skill_tool_calls.py skills/tooluniverse-toxicology
Exit status is 1 when any problem is found.
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "src" / "tooluniverse" / "data"

# Options of the tools.NAME(...) wrapper itself, not tool arguments.
WRAPPER_KWARGS = {"use_cache", "stream_callback", "validate"}
# Skills that document how to write tools use made-up names on purpose.
SKIP_DIR_PARTS = ("devtu-", "custom-tool", "create-tooluniverse-skill")
SUPPRESS = re.compile(r"WRONG|❌|noqa: skill-call")

_FENCE = re.compile(r"^```[A-Za-z0-9_+-]*[ \t]*\n(.*?)^```", re.S | re.M)
_PY_CALL = re.compile(r"tools\.([A-Za-z0-9_]+)\(")
_CLI = re.compile(r"tu run\s+([A-Za-z0-9_]+)\s+'(\{.*?\})'", re.S)
_DICT = re.compile(
    r"""["']name["']\s*:\s*["']([A-Za-z0-9_]+)["']\s*,\s*["']arguments["']\s*:\s*"""
    r"""(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})""",
    re.S,
)


def load_schemas(data_dir=DATA_DIR):
    """Return {tool name: (declared properties, required properties)}."""
    schemas = {}
    for path in sorted(Path(data_dir).glob("*.json")):
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        for entry in entries if isinstance(entries, list) else []:
            if isinstance(entry, dict) and "name" in entry:
                params = entry.get("parameter") or {}
                schemas.setdefault(
                    entry["name"],
                    (
                        set(params.get("properties", {})),
                        set(params.get("required", [])),
                    ),
                )
    return schemas


def _suppressed(text, pos):
    before = text[:pos].splitlines()[-4:]
    rest_of_line = text[pos:].split("\n", 1)[0]
    return any(SUPPRESS.search(line) for line in before + [rest_of_line])


def _balanced(text, start):
    depth, i = 1, start
    while i < len(text) and depth:
        depth += (text[i] == "(") - (text[i] == ")")
        i += 1
    return text[start : i - 1]


def _literal_keys(source):
    try:
        value = json.loads(source)
    except ValueError:
        try:
            value = ast.literal_eval(source)
        except (ValueError, SyntaxError):
            return None
    return set(value) if isinstance(value, dict) else None


def iter_calls(markdown):
    """Yield (tool name, set of argument names or None, has_splat, position)."""
    for block in _FENCE.finditer(markdown):
        text, base = block.group(1), block.start(1)
        for m in _PY_CALL.finditer(text):
            try:
                call = ast.parse(
                    "f(" + _balanced(text, m.end()) + ")", mode="eval"
                ).body
            except SyntaxError:
                continue
            if call.args:
                continue
            names = {k.arg for k in call.keywords if k.arg} - WRAPPER_KWARGS
            splat = any(k.arg is None for k in call.keywords)
            yield m.group(1), names, splat, base + m.start(), text, m.start(), True
        for rx in (_CLI, _DICT):
            for m in rx.finditer(text):
                keys = _literal_keys(m.group(2))
                if keys is not None:
                    yield (
                        m.group(1),
                        keys,
                        False,
                        base + m.start(),
                        text,
                        m.start(),
                        False,
                    )


def check_markdown(markdown, schemas):
    """Return a list of human-readable problems for one markdown document."""
    prefixes = {}
    for name in schemas:
        prefixes[name.split("_")[0]] = prefixes.get(name.split("_")[0], 0) + 1
    problems = []
    for name, args, splat, _, text, pos, is_py in iter_calls(markdown):
        if _suppressed(text, pos):
            continue
        if name not in schemas:
            if "_" in name and prefixes.get(name.split("_")[0], 0) >= 2:
                problems.append(f"{name}: no such tool")
            continue
        props, required = schemas[name]
        unknown = sorted(a for a in args if props and a not in props)
        missing = [] if splat else sorted(r for r in required if r not in args)
        if unknown or missing:
            problems.append(f"{name}: unknown={unknown} missing_required={missing}")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("paths", nargs="*", default=[str(ROOT / "skills")])
    args = parser.parse_args(argv)
    schemas = load_schemas()
    total = 0
    for base in args.paths:
        for md in sorted(Path(base).rglob("*.md")):
            if any(part in str(md) for part in SKIP_DIR_PARTS):
                continue
            for problem in check_markdown(md.read_text(encoding="utf-8"), schemas):
                total += 1
                print(
                    f"{md.relative_to(ROOT) if md.is_relative_to(ROOT) else md}: {problem}"
                )
    print(f"{total} problem(s)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
