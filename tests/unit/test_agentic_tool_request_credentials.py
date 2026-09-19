"""AgenticTool resolves OpenAI keys from request-scoped credentials.

A hosted application passes each user's ``OPENAI_API_KEY`` through
``run_one_function(credentials=...)``. The key must reach the OpenAI client for that
request only, must never be copied into ``os.environ``, and must not be served to a
request that carries a different key or none. The ``openai`` module is replaced by a
fake, so no network call is made.
"""

import json
import logging
import os
import sys
from types import SimpleNamespace

import pytest

from tooluniverse import ToolUniverse, credential_context
from tooluniverse.agentic_tool import AgenticTool

_LLM_ENV_VARS = (
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENROUTER_API_KEY",
    "GEMINI_API_KEY",
    "VLLM_SERVER_URL",
    "TOOLUNIVERSE_LLM_DEFAULT_PROVIDER",
    "TOOLUNIVERSE_LLM_MODEL_DEFAULT",
    "TOOLUNIVERSE_LLM_CONFIG_MODE",
    "AGENTIC_TOOL_FALLBACK_CHAIN",
)

_AGENTIC_CONFIG = {
    "name": "HostedOpenAIAgentTest",
    "type": "AgenticTool",
    "description": "Summarize text with an OpenAI model",
    "prompt": "Summarize: {text}",
    "input_arguments": ["text"],
    "parameter": {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
    "configs": {
        "api_type": "OPENAI",
        "model_id": "gpt-4o-mini",
        "validate_api_key": False,
        "use_global_fallback": False,
        "return_metadata": False,
        "max_retries": 1,
        "retry_delay": 0,
    },
}


class _FakeOpenAIClient:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = []
        completions = SimpleNamespace(create=self._create, parse=self._create)
        self.chat = SimpleNamespace(completions=completions)
        type(self).instances.append(self)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="summary"))]
        )


class _FakeRateLimitError(Exception):
    pass


@pytest.fixture
def fake_openai(monkeypatch):
    for name in _LLM_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    _FakeOpenAIClient.instances = []
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(OpenAI=_FakeOpenAIClient, RateLimitError=_FakeRateLimitError),
    )
    return _FakeOpenAIClient


def _tooluniverse_with_agentic_tool(tmp_path):
    config_path = tmp_path / "agentic_tools.json"
    config_path.write_text(json.dumps([_AGENTIC_CONFIG]))
    tu = ToolUniverse(
        tool_files={"agentic": str(config_path)}, keep_default_tools=False
    )
    tu.load_tools()
    return tu


def _call(tu, credentials):
    return tu.run_one_function(
        {"name": "HostedOpenAIAgentTest", "arguments": {"text": "hello"}},
        validate=False,
        credentials=credentials,
    )


@pytest.mark.unit
def test_request_openai_key_constructs_openai_client(
    fake_openai, tmp_path, caplog, capsys
):
    caplog.set_level(logging.DEBUG)
    tu = _tooluniverse_with_agentic_tool(tmp_path)
    # Without any process-level LLM key the tool is gated at startup.
    assert "HostedOpenAIAgentTest" not in tu.all_tool_dict

    result = _call(tu, {"OPENAI_API_KEY": "sk-tenant-a"})

    assert result == "summary"
    assert len(fake_openai.instances) == 1
    client = fake_openai.instances[0]
    assert client.kwargs["api_key"] == "sk-tenant-a"
    assert client.calls[0]["model"] == "gpt-4o-mini"
    assert "OPENAI_API_KEY" not in os.environ
    captured = capsys.readouterr()
    assert "sk-tenant-a" not in caplog.text + captured.out + captured.err


@pytest.mark.unit
def test_request_openai_keys_are_isolated_between_tenants(fake_openai, tmp_path):
    tu = _tooluniverse_with_agentic_tool(tmp_path)

    assert _call(tu, {"OPENAI_API_KEY": "sk-tenant-a"}) == "summary"
    assert _call(tu, {"OPENAI_API_KEY": "sk-tenant-b"}) == "summary"
    assert _call(tu, {"OPENAI_API_KEY": "sk-tenant-a"}) == "summary"

    keys = [client.kwargs["api_key"] for client in fake_openai.instances]
    # One client per distinct tenant key; tenant A's client is reused for tenant A only.
    assert keys == ["sk-tenant-a", "sk-tenant-b"]
    assert len(fake_openai.instances[0].calls) == 2
    assert len(fake_openai.instances[1].calls) == 1

    # An empty request scope fails closed: no client is built from any other key.
    missing = _call(tu, {})
    assert "OPENAI_API_KEY not set" in str(missing)
    assert len(fake_openai.instances) == 2


@pytest.mark.unit
def test_request_scope_overrides_and_masks_process_openai_key(fake_openai, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-process")
    config = {key: value for key, value in _AGENTIC_CONFIG.items() if key != "type"}

    with credential_context({"OPENAI_API_KEY": "sk-tenant"}):
        tenant_tool = AgenticTool(config)
    assert tenant_tool._is_available
    assert fake_openai.instances[-1].kwargs["api_key"] == "sk-tenant"

    with credential_context({}):
        masked_tool = AgenticTool(config)
        assert AgenticTool.has_any_api_keys() is False
    assert not masked_tool._is_available
    assert len(fake_openai.instances) == 1

    local_tool = AgenticTool(config)
    assert local_tool._is_available
    assert fake_openai.instances[-1].kwargs["api_key"] == "sk-process"
    assert os.environ["OPENAI_API_KEY"] == "sk-process"
