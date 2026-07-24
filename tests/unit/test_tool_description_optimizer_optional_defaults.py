"""Regression guard for the round-37 backlog's ToolDescriptionOptimizer fix,
plus a genuine behavior bug found while fixing it:

- save_to_file, output_file, max_iterations, satisfaction_threshold were all
  wrongly marked required in optimizer_tools.json even though max_iterations/
  satisfaction_threshold have schema defaults the compose() function already
  reads correctly, and output_file/save_to_file are handled gracefully when
  omitted (output_file falls back to "<tool_name>_optimized_description.txt";
  save_to_file previously had no schema default at all despite promising one
  implicitly via its boolean type).
- Separately: compose()'s own code read save_to_file into a throwaway
  expression (`arguments.get("save_to_file", False)` with no assignment) and
  a comment literally said "always save, regardless of save_to_file flag" --
  the file was written to disk unconditionally, ignoring the flag entirely,
  contradicting the schema's own description ("If true, save..."). Fixed to
  actually gate the file write on save_to_file, restoring the tool's
  documented contract.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tooluniverse.compose_scripts.tool_description_optimizer import compose

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _tool_config():
    configs = json.loads((_DATA_DIR / "optimizer_tools.json").read_text())
    for cfg in configs:
        if cfg["name"] == "ToolDescriptionOptimizer":
            return cfg
    raise AssertionError("ToolDescriptionOptimizer not found")


def test_requires_only_tool_config():
    cfg = _tool_config()
    assert cfg["parameter"]["required"] == ["tool_config"]


def _fake_call_tool(name, args):
    if name == "TestCaseGenerator":
        return [{"query": "test"}]
    if name == "DescriptionAnalyzer":
        return {"optimized_description": "A better description.", "rationale": "why"}
    if name == "DescriptionQualityEvaluator":
        return {"overall_score": 9, "is_satisfactory": True, "feedback": "great"}
    raise AssertionError(f"unexpected call_tool: {name}")


def _run_compose(tmp_path, save_to_file):
    tooluniverse = MagicMock()
    tooluniverse.run_one_function.return_value = {"status": "success"}
    output_file = str(tmp_path / "report.txt")

    result = compose(
        {
            "tool_config": {"name": "SomeTool", "description": "original desc"},
            "save_to_file": save_to_file,
            "output_file": output_file,
            "max_iterations": 1,
            "satisfaction_threshold": 8,
        },
        tooluniverse=tooluniverse,
        call_tool=_fake_call_tool,
    )
    return result, output_file


def test_save_to_file_false_does_not_write_a_file():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        result, output_file = _run_compose(tmp_path, save_to_file=False)

        assert result["saved_to"] is None
        assert not Path(output_file).exists()


def test_save_to_file_true_writes_a_file():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        result, output_file = _run_compose(tmp_path, save_to_file=True)

        assert result["saved_to"] == output_file
        assert Path(output_file).exists()
