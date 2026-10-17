#!/usr/bin/env python3
"""Emit `data/remote_tools/<slug>_tools.json` from a provider's own decorators.

A published entry is a DISCOVERY record, not a claim that anything is hosted:
`RemoteTool.run()` always answers "not available for local execution" and
points at `code_url`. Without one, an operation does not appear in
ToolUniverse's catalogue at all, so an agent cannot find out that the model
exists -- which is how 26 of the 31 providers on the resident standard ended
up invisible while 28 of the 31 older remote directories were listed.

The entry is GENERATED rather than written because `test_remote_schema_parity`
requires the published `parameter` and the decorator's `parameter_schema` to
be structurally identical. Two hand-maintained copies of one schema is the
drift this repository has already paid for elsewhere.

Usage:
    python scripts/remote_validation/generate_catalogue_entries.py [--check] [slug ...]

`--check` writes nothing and exits 1 if any file would change.
"""

from __future__ import annotations

import argparse
import contextlib
import glob
import importlib.util
import io
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
REMOTE = SRC / "tooluniverse" / "remote"
PUBLISHED = SRC / "tooluniverse" / "data" / "remote_tools"
SKILLS = ROOT / "skills"
DOCS_URL = "https://zitniklab.hms.harvard.edu/ToolUniverse/expand_tooluniverse/remote/{slug}.html"
CODE_URL = "https://github.com/mims-harvard/ToolUniverse/tree/main/src/tooluniverse/remote/{slug}"


def _capture(slug: str) -> dict:
    """Import a provider's tool modules with `register_mcp_tool` spied on."""
    sys.path.insert(0, str(SRC))
    import tooluniverse.mcp_tool_registry as reg

    found: dict = {}
    original = reg.register_mcp_tool

    def spy(*args, **kwargs):
        name = kwargs.get("tool_type_name")
        config = kwargs.get("config") or {}
        inner = original(*args, **kwargs)

        def wrapper(cls):
            found[name] = (config, cls.__name__)
            return inner(cls)

        return wrapper

    reg.register_mcp_tool = spy
    try:
        for path in sorted((REMOTE / slug).glob("*.py")):
            if "launch" in path.name:
                continue
            spec = importlib.util.spec_from_file_location(f"_gen_{slug}_{path.stem}", path)
            module = importlib.util.module_from_spec(spec)
            with contextlib.redirect_stdout(io.StringIO()):
                spec.loader.exec_module(module)
    finally:
        reg.register_mcp_tool = original
    return found


def _skill_example(slug: str) -> tuple[str | None, dict | None]:
    """The operation the setup skill demonstrates, and its example."""
    path = SKILLS / f"setup-{slug}-remote-tool" / "SKILL.md"
    if not path.is_file():
        return None, None
    text = path.read_text(encoding="utf-8")
    op = re.search(r"^Operation: (\S+)", text, re.MULTILINE)
    ex = re.search(r"~~~json\n(.*?)\n~~~", text, re.DOTALL)
    if op is None or ex is None:
        return None, None
    try:
        return op.group(1), json.loads(ex.group(1))
    except json.JSONDecodeError:
        return op.group(1), None


def _url(slug: str) -> str:
    """The provider's own upstream when it pins one; the docs page otherwise."""
    data = tomllib.loads((REMOTE / slug / "provider.toml").read_text(encoding="utf-8"))
    upstream = (data.get("kit") or {}).get("upstream")
    return upstream or DOCS_URL.format(slug=slug)


def build(slug: str) -> list:
    captured = _capture(slug)
    if not captured:
        raise SystemExit(f"{slug}: no @register_mcp_tool found")
    data = tomllib.loads((REMOTE / slug / "provider.toml").read_text(encoding="utf-8"))
    order = data["provider"].get("operations") or sorted(captured)
    demo_op, demo = _skill_example(slug)
    url = _url(slug)

    entries = []
    for name in order:
        if name not in captured:
            raise SystemExit(
                f"{slug}: provider.toml names {name}, no decorator registers it"
            )
        config, cls_name = captured[name]
        schema = dict(config.get("parameter_schema") or {})
        # Mirrors `_decorated_parameter_schemas`, which defaults this before
        # comparing -- so the published copy has to default it the same way or
        # the parity test sees a difference that is not one.
        if schema.get("type") == "object":
            schema.setdefault("additionalProperties", False)
        entry = {
            "type": "RemoteTool",
            "name": name,
            "description": config.get("description", ""),
            "parameter": schema,
            "remote_info": {
                "server_type": "MCP",
                "transport": "http",
                "original_type": cls_name,
                "url": url,
                "code_url": CODE_URL.format(slug=slug),
                "mcp_tool_name": name,
            },
        }
        if config.get("return_schema"):
            entry["return_schema"] = config["return_schema"]
            entry = {
                k: entry[k]
                for k in (
                    "type",
                    "name",
                    "description",
                    "parameter",
                    "return_schema",
                    "remote_info",
                )
            }
        if name == demo_op and demo is not None:
            entry["test_examples"] = [demo]
        entries.append(entry)
    return entries


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="*")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    # Default to the providers that have NO entry yet. The ones that do were
    # written by hand before this script existed, and regenerating them would
    # rewrite text nobody asked to change -- and boltz cannot even be imported
    # without its interpreter on the environment, because its tool module
    # constructs a client at import time. Name a slug explicitly to force it.
    slugs = args.slugs or [
        Path(p).parent.name
        for p in sorted(glob.glob(str(REMOTE / "*" / "provider.toml")))
        if not (PUBLISHED / f"{Path(p).parent.name}_tools.json").is_file()
    ]
    changed = []
    for slug in slugs:
        target = PUBLISHED / f"{slug}_tools.json"
        text = json.dumps(build(slug), indent=2) + "\n"
        if target.is_file() and target.read_text(encoding="utf-8") == text:
            continue
        changed.append(slug)
        if not args.check:
            target.write_text(text, encoding="utf-8")
    if args.check:
        if changed:
            print("would change:", " ".join(changed))
            return 1
        print("catalogue entries are current")
        return 0
    print(f"wrote {len(changed)} file(s): {' '.join(changed) or '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
