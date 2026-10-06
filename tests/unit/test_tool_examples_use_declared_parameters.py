"""A tool's own test_examples must not be rejected by its own validator.

`ChEMBL_search_assays` and `ChEMBL_search_activities` shipped examples passing
`target_chembl_id__exact`, which neither tool declares. BaseTool's argument
check fuzzy-matched the key against the declared `target_chembl_id` and refused
the call, so 20 of the 21 failures the weekly health check reported for the
`chembl` category were the tool rejecting its own documentation.

The check below replays BaseTool's rule with BaseTool's own helpers rather than
a copy of it, so it cannot drift from the behaviour it is guarding. It stays
static: no tool is instantiated and no network is touched, which is what lets
it run over every shipped config in the unit suite.

An undeclared key is NOT automatically a defect. BaseTool deliberately accepts
unknown keys that look nothing like a declared property as forward-compatible
pass-through, which is why `web_search` ships `description` and
`expected_output_type`, and `TDC_list_datasets` ships `operation`, without
failing. Only the two rejection paths are errors, and only those are asserted.
"""

import json
from pathlib import Path

import pytest

from tooluniverse.base_tool import BaseTool

pytestmark = pytest.mark.unit

DATA_DIR = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"


def _shipped_tools():
    for path in sorted(DATA_DIR.rglob("*.json")):
        try:
            configs = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError):
            continue
        if not isinstance(configs, list):
            continue
        for config in configs:
            if isinstance(config, dict) and config.get("name"):
                yield path.name, config


def _rejection(config, example):
    """Why BaseTool would refuse this example, or None if it would not.

    Mirrors the two refusing branches of `BaseTool._validate_arguments`: a
    misspelling hint, and every supplied key being unknown.
    """
    parameter = config.get("parameter") or {}
    properties = parameter.get("properties") or {}
    if not properties or not example:
        return None
    if parameter.get("additionalProperties") is True:
        return None

    # ToolUniverse injects `operation` from the config before validation, and
    # BaseTool drops it again before blaming the caller.
    checked = {
        k: v
        for k, v in example.items()
        if not (k == "operation" and v == config.get("operation"))
    }
    unknown = BaseTool._unknown_keys(checked, properties)
    if not unknown:
        return None

    unset = [p for p in properties if p not in checked]
    for key in unknown:
        match = BaseTool._best_property_match(key, unset)
        if match is not None:
            return f"{key!r} is not declared and reads as a misspelling of {match!r}"
    if len(unknown) == len(checked):
        return f"every supplied key is undeclared: {unknown}"
    return None


def test_no_shipped_example_is_rejected_by_its_own_tool():
    offenders = []
    for file_name, config in _shipped_tools():
        for index, example in enumerate(config.get("test_examples") or []):
            if not isinstance(example, dict):
                continue
            reason = _rejection(config, example)
            if reason:
                offenders.append(
                    f"{file_name}::{config['name']} example {index + 1}: {reason}"
                )

    assert not offenders, (
        "These test_examples would be refused by the tool's own argument "
        "validation, so the tool fails its own documented call:\n  "
        + "\n  ".join(offenders)
    )
