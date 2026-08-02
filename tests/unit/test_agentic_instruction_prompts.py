import asyncio
import json
from unittest.mock import patch

import pytest

from tooluniverse.agentic_tool import (
    API_KEY_ENV_VARS,
    AgenticTool,
    render_agentic_instruction,
)
from tooluniverse.execute_function import ToolUniverse
from tooluniverse.smcp import SMCP

pytestmark = pytest.mark.unit


def _agentic_config(name="HostReview"):
    return {
        "name": name,
        "type": "AgenticTool",
        "description": "Review text using a configurable rubric.",
        "prompt": "Review {text}\nRubric: {rubric}\nLabels: {labels}",
        "input_arguments": ["text", "rubric", "labels"],
        "parameter": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to review"},
                "rubric": {
                    "type": "string",
                    "description": "Review rubric",
                    "default": "rigorous",
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Labels to apply",
                    "default": [],
                },
            },
            "required": ["text"],
        },
    }


def _clear_llm_credentials(monkeypatch):
    for variables in API_KEY_ENV_VARS.values():
        for variable in variables:
            monkeypatch.delenv(variable, raising=False)


def _make_server(tmp_path, monkeypatch, configs, **kwargs):
    _clear_llm_credentials(monkeypatch)
    # ToolUniverse may generate an API-key template when credentials are absent.
    # Keep that expected side effect inside pytest's temporary directory.
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "agentic_tools.json"
    config_path.write_text(json.dumps(configs), encoding="utf-8")
    tooluniverse = ToolUniverse(
        tool_files={"agentic_test": str(config_path)},
        keep_default_tools=False,
        enable_name_shortening=True,
    )
    server = SMCP(
        tooluniverse_config=tooluniverse,
        auto_expose_tools=False,
        search_enabled=False,
        **kwargs,
    )
    return server, tooluniverse


def test_render_agentic_instruction_is_side_effect_free_and_applies_defaults():
    """Render configured defaults without constructing or invoking an LLM client."""
    config = _agentic_config()

    rendered = render_agentic_instruction(config, {"text": "A result"})

    assert rendered == "Review A result\nRubric: rigorous\nLabels: []"
    with pytest.raises(ValueError, match="Missing required input arguments"):
        render_agentic_instruction(config, {})
    with pytest.raises(ValueError, match="cannot be empty"):
        render_agentic_instruction(config, {"text": "  "})


def test_agentic_tool_preview_uses_shared_renderer_without_changing_class():
    """Keep the legacy AgenticTool preview API on the shared rendering path."""
    config = _agentic_config()
    with patch.object(AgenticTool, "_try_initialize_api"):
        tool = AgenticTool(config)

    assert tool.get_prompt_preview({"text": "A result"}).endswith(
        "Rubric: rigorous\nLabels: []"
    )


def test_smcp_exposes_agentic_config_as_prompt_without_llm_credentials(
    tmp_path, monkeypatch
):
    """Expose and render an MCP prompt when no backend LLM key is configured."""
    server, tooluniverse = _make_server(
        tmp_path,
        monkeypatch,
        [_agentic_config()],
        expose_agentic_prompts=True,
    )

    async def exercise_prompt():
        prompts = await server.get_prompts()
        assert set(prompts) == {"HostReview"}
        prompt = prompts["HostReview"]
        assert prompt.meta["tooluniverse"] == {
            "source_type": "AgenticTool",
            "execution": "host",
        }
        messages = await prompt.render(
            {"text": "A result", "labels": '["major", "minor"]'}
        )
        return messages[0].content.text

    try:
        rendered = asyncio.run(exercise_prompt())
    finally:
        asyncio.run(server.close())

    assert "Review A result" in rendered
    assert "Rubric: rigorous" in rendered
    assert "Labels: ['major', 'minor']" in rendered
    assert not any(
        config.get("type") == "AgenticTool" for config in tooluniverse.all_tools
    )


def test_agentic_prompt_exposure_is_opt_in_and_respects_filters(tmp_path, monkeypatch):
    """Keep prompt exposure disabled by default and honor include filters."""
    configs = [_agentic_config("IncludedReview"), _agentic_config("ExcludedReview")]
    disabled, _ = _make_server(tmp_path, monkeypatch, configs)
    try:
        assert asyncio.run(disabled.get_prompts()) == {}
    finally:
        asyncio.run(disabled.close())

    enabled, _ = _make_server(
        tmp_path,
        monkeypatch,
        configs,
        expose_agentic_prompts=True,
        include_tools=["IncludedReview"],
    )
    try:
        assert set(asyncio.run(enabled.get_prompts())) == {"IncludedReview"}
    finally:
        asyncio.run(enabled.close())
