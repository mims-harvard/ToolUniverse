"""
Guards against tools whose success path can never be reached.

A ComposeTool declares the tools it needs in ``required_tools``. When one of those
names does not exist anywhere in the tool configs it is a dangling reference: the
composition attempts an auto-load that can never succeed, and because
``fail_on_missing_tools`` defaults to false the tool keeps going and returns a
success-shaped payload built from nothing.

That failure mode is invisible to every other gate -- the tool "runs", exits zero
and produces output -- so it is checked here statically instead.

The check is against names *declared* in the configs, not names registered at
runtime, so a tool skipped for want of an API key (every AgenticTool, when no LLM
key is set) still counts as resolvable.
"""

import json
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"


DEPENDENCY_FIELDS = ("required_tools", "available_tools")


def _load_configs():
    """
    Return (declared_names, dependency_cases) across every tool config.

    Cases are collected during the sweep so the parsed configs (~12MB) can be
    freed as we go rather than retained for the whole pytest session.
    """
    declared = set()
    cases = []
    for path in sorted(DATA_DIR.rglob("*.json")):
        try:
            content = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict) or "name" not in item:
                continue
            declared.add(item["name"])
            for field in DEPENDENCY_FIELDS:
                if isinstance(item.get(field), list) and item[field]:
                    cases.append((path.name, item["name"], field, item[field]))
    return declared, cases


DECLARED, CASES = _load_configs()


def test_configs_were_discovered():
    """Positive control: the sweep below is meaningless if nothing was loaded."""
    assert len(DECLARED) > 1000, f"only {len(DECLARED)} tool names found in {DATA_DIR}"
    assert CASES, "no dependency declarations found to check"


@pytest.mark.parametrize(
    "config_file,tool_name,field,dependencies",
    CASES,
    ids=[f"{c}::{n}::{f}" for c, n, f, _ in CASES],
)
def test_declared_dependencies_exist(config_file, tool_name, field, dependencies):
    """Every declared dependency must name a tool that actually exists."""
    dangling = [dep for dep in dependencies if dep not in DECLARED]
    assert not dangling, (
        f"{tool_name} ({config_file}) lists {field} entries that are not declared "
        f"in any tool config: {dangling}. A dangling dependency cannot ever load, "
        f"so the tool silently degrades and still reports success."
    )
