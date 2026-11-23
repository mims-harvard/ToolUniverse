"""
A config may not name a tool type that no class implements.

``special_tools.json`` declared ``"type": "SpecialTool"`` for ``Finish`` and
``CallAgent`` while no class was ever registered under that name, so both
failed at construction with ``ToolConfigError: Tool type 'SpecialTool' not
found in registry``. Nothing caught it, because nothing checked the declared
types against the registry -- and the two tools stayed fully visible
meanwhile: shipped as typed SDK wrappers in ``tooluniverse.tools.__all__``,
carried in ``.tool_metadata.json``, and documented in
``docs/tools/special_tools.rst`` with a copy-pasteable ``tu.run(query)``
example that could only error.

The first test is the general guard: measured over the shipped configs, 734
distinct types across 2996 entries, of which ``SpecialTool`` was the only one
with no class. The second pins what the two entries now do, since "resolves to
a class" alone would be satisfied by a class that lies about doing work.
"""

import collections
import json
import pathlib

import jsonschema
import pytest

from tooluniverse import ToolUniverse
from tooluniverse.default_config import default_tool_files
from tooluniverse.tool_registry import auto_discover_tools


def _declared_types():
    """Map each declared tool type to the categories that declare it."""
    declared = collections.defaultdict(set)
    for category, path in default_tool_files.items():
        config = pathlib.Path(path)
        if config.suffix != ".json" or not config.exists():
            continue
        data = json.loads(config.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            continue
        for entry in data:
            if isinstance(entry, dict) and entry.get("type"):
                declared[entry["type"]].add(category)
    return declared


def test_every_declared_tool_type_resolves_to_a_registered_class():
    declared = _declared_types()
    assert len(declared) > 500, (
        f"only {len(declared)} types found; config discovery broke"
    )

    registered = set(auto_discover_tools(lazy=True))
    assert registered, "the lazy tool registry is empty"

    missing = {t: sorted(cats) for t, cats in declared.items() if t not in registered}
    assert not missing, (
        "these tool types are declared in a shipped config but no class is "
        f"registered under them, so every tool using one fails at "
        f"construction: {json.dumps(missing, indent=2, sort_keys=True)}"
    )


def _special_tool_configs():
    path = pathlib.Path(default_tool_files["special_tools"])
    return {
        c["name"]: c
        for c in json.loads(path.read_text(encoding="utf-8"))
        if c.get("type") == "SpecialTool"
    }


@pytest.fixture(scope="module")
def engine():
    tu = ToolUniverse()
    tu.load_tools(categories=["special_tools"])
    try:
        yield tu
    finally:
        tu.close()


@pytest.mark.parametrize(
    "name,arguments",
    [
        ("Finish", {}),
        ("CallAgent", {"solution": "Check each implicated gene for a known drug."}),
    ],
)
def test_a_special_tool_echoes_its_signal_instead_of_failing(engine, name, arguments):
    configs = _special_tool_configs()
    assert name in configs, f"{name} is no longer a SpecialTool in special_tools.json"

    result = engine.run_one_function({"name": name, "arguments": arguments})

    assert isinstance(result, dict), f"{name} returned {type(result).__name__}"
    assert "error" not in result, (
        f"{name} still fails instead of returning its signal: {result.get('error')}"
    )
    jsonschema.validate(result, configs[name]["return_schema"])

    assert result["control_signal"] == name
    assert result["performed_work"] is False, (
        f"{name} reports that it performed work. It is a control signal: "
        "ToolUniverse runs no agent loop, so claiming work would be the "
        "same kind of untruth as the registry error it replaced."
    )
    assert result["arguments"] == arguments, (
        "the caller's arguments must come back unchanged so a loop can read "
        f"the plan it sent: {result['arguments']!r} != {arguments!r}"
    )
    assert "not an executable tool" in result["message"]
