"""Regression guard: ToolGraphComposer's output_path, analysis_depth,
min_compatibility_score, exclude_categories, max_tools_per_category, and
force_rebuild were all wrongly marked required in tool_composition_tools.json
even though each has a schema default that compose_scripts/tool_graph_
composer.py's compose() already reads correctly via arguments.get(x, default).
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tooluniverse.agentic_tool import AgenticTool
from tooluniverse.compose_scripts.tool_graph_composer import compose

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _tool_config(name):
    configs = json.loads((_DATA_DIR / "tool_composition_tools.json").read_text())
    for cfg in configs:
        if cfg["name"] == name:
            return cfg
    raise AssertionError(f"{name} not found")


def test_tool_graph_composer_requires_nothing():
    cfg = _tool_config("ToolGraphComposer")
    assert cfg["parameter"]["required"] == []


def test_tool_compatibility_analyzer_requires_only_source_and_target():
    cfg = _tool_config("ToolCompatibilityAnalyzer")
    assert cfg["parameter"]["required"] == ["source_tool", "target_tool"]


def test_compose_uses_defaults_when_all_args_omitted():
    tooluniverse = MagicMock()
    tooluniverse.all_tool_dict = {}  # no tools -> clean early return, no LLM calls

    with tempfile.TemporaryDirectory() as tmp:
        output_path = str(Path(tmp) / "graph")
        result = compose({"output_path": output_path}, tooluniverse, call_tool=MagicMock())

    assert result["status"] == "error"
    assert result["message"] == "No tools available for analysis after filtering"
    assert result["tools_analyzed"] == 0


def test_tool_compatibility_analyzer_fills_analysis_depth_default():
    """AgenticTool has its own generic default-filling mechanism (fills
    missing input_arguments from each property's schema "default" before
    formatting the prompt) -- confirmed here via get_prompt_preview(), which
    exercises that exact logic without needing a working LLM API key."""
    cfg = _tool_config("ToolCompatibilityAnalyzer")
    tool = AgenticTool(cfg)

    preview = tool.get_prompt_preview(
        {"source_tool": '{"name": "a"}', "target_tool": '{"name": "b"}'}
    )

    assert "Analysis Depth: detailed" in preview
