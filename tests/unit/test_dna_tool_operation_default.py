"""Each DNA_* tool is registered as one operation, but `operation` was a
required parameter with no default, so the natural call implied by the tool's
own name -- DNA_find_orfs(sequence=...) -- failed parameter validation before
reaching the handler. An agent that hit that error had no way to tell the tool
was usable, and fell back to doing the sequence work by hand.

Fixed the same way MSigDBTool was: the tool config names its operation
(`fields.operation`, falling back to the DNA_<operation> tool name) and
`run()` uses it when the caller does not pass one.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.dna_tools import DNATool

pytestmark = pytest.mark.unit

CONFIG_PATH = (
    Path(__file__).parent.parent.parent
    / "src"
    / "tooluniverse"
    / "data"
    / "dna_tools.json"
)


def _dna_configs():
    raw = json.loads(CONFIG_PATH.read_text())
    tools = raw if isinstance(raw, list) else raw.get("tools", [])
    return [t for t in tools if t.get("type") == "DNATool" and t.get("test_examples")]


@pytest.mark.parametrize("cfg", _dna_configs(), ids=lambda c: c["name"])
def test_documented_example_works_without_operation(cfg):
    """The tool's own example must run when `operation` is omitted."""
    example = dict(cfg["test_examples"][0])
    example.pop("operation", None)
    result = DNATool(cfg).run(example)
    assert result.get("status") == "success", result.get("error")


@pytest.mark.parametrize("cfg", _dna_configs(), ids=lambda c: c["name"])
def test_explicit_operation_still_honoured(cfg):
    """Passing `operation` explicitly must keep working (back-compat)."""
    result = DNATool(cfg).run(dict(cfg["test_examples"][0]))
    assert result.get("status") == "success", result.get("error")


def test_operation_is_not_required_in_schema():
    for cfg in _dna_configs():
        required = (cfg.get("parameter") or {}).get("required", [])
        assert "operation" not in required, f"{cfg['name']} still requires operation"


def test_explicit_operation_overrides_config_default():
    """An explicit operation must win over the tool's configured default."""
    cfg = next(c for c in _dna_configs() if c["name"] == "DNA_find_orfs")
    result = DNATool(cfg).run(
        {"operation": "calculate_gc_content", "sequence": "GCGCATAT"}
    )
    assert result["status"] == "success"
    assert "gc_content_percent" in result["data"]
