"""The `get_<package>_info` family must be callable the same way throughout.

166 tools share this naming convention, so an agent that learns the call from
one member applies it to the next. They used to disagree on required
parameters -- 62 required none, 51 required `include_examples`, 50 required
`info_type` -- so that generalisation failed about 63% of the time, which is
what agent transcripts showed: a tool call, a validation error, a retry with
different arguments, another error.

Both offending parameters are optional knobs, not identifiers: `include_examples`
already declared `"default": true` while also being listed as required, which is
self-contradictory. Reading the config files directly keeps this fast and free of
tool loading.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

PACKAGES_DIR = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data" / "packages"
FAMILY = re.compile(r"^get_\w+_info$")

#: Members that legitimately need an identifier -- they cannot default it.
IDENTIFIER_PARAMS = frozenset({"pdb_id", "tool_names"})


def _package_tools():
    for path in sorted(PACKAGES_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if not isinstance(payload, list):
            continue
        for tool in payload:
            if isinstance(tool, dict) and isinstance(tool.get("name"), str):
                yield path.name, tool


@pytest.fixture(scope="module")
def family():
    tools = [(f, t) for f, t in _package_tools() if FAMILY.match(t["name"])]
    if not tools:
        pytest.skip("no package-info tools found")
    return tools


def test_family_is_large_enough_to_be_a_convention(family):
    assert len(family) >= 100


def test_no_member_requires_an_optional_knob(family):
    offenders = [
        (tool["name"], param)
        for _, tool in family
        for param in (tool.get("parameter", {}).get("required") or [])
        if param not in IDENTIFIER_PARAMS
    ]
    assert not offenders, (
        f"{len(offenders)} member(s) require a parameter that should have a default: "
        f"{offenders[:5]}"
    )


def test_every_optional_knob_declares_a_default(family):
    missing = [
        (tool["name"], param)
        for _, tool in family
        for param, spec in (tool.get("parameter", {}).get("properties") or {}).items()
        if param not in IDENTIFIER_PARAMS
        and isinstance(spec, dict)
        and "default" not in spec
    ]
    assert not missing, f"{len(missing)} knob(s) have no default: {missing[:5]}"


def test_declared_defaults_are_valid_choices(family):
    """A default outside its own enum would fail the moment it is used."""
    bad = [
        (tool["name"], param, spec.get("default"))
        for _, tool in family
        for param, spec in (tool.get("parameter", {}).get("properties") or {}).items()
        if isinstance(spec, dict)
        and isinstance(spec.get("enum"), list)
        and "default" in spec
        and spec["default"] not in spec["enum"]
    ]
    assert not bad, f"default not in enum: {bad[:5]}"


def test_generated_wrappers_match_the_optional_configs(family):
    """The config and the generated Python signature must agree, or the tool is
    reachable through MCP and not through the coding API."""
    tools_dir = PACKAGES_DIR.parents[1] / "tools"
    if not tools_dir.exists():
        pytest.skip("generated wrappers not present")

    mismatched = []
    for _, tool in family:
        wrapper = tools_dir / f"{tool['name']}.py"
        if not wrapper.exists():
            continue
        source = wrapper.read_text()
        for param, spec in (tool.get("parameter", {}).get("properties") or {}).items():
            if param in IDENTIFIER_PARAMS or not isinstance(spec, dict):
                continue
            if "default" not in spec:
                continue
            # `\s+`, not `\s*`: a zero-width match would let the negative
            # lookahead fire on the space right after the colon and report every
            # correctly-annotated wrapper as broken.
            if re.search(rf"^\s+{param}:\s+(?!Optional)", source, re.M):
                mismatched.append((tool["name"], param))
    assert not mismatched, f"wrapper still requires: {mismatched[:5]}"
