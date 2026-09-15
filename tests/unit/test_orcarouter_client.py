"""Tests for the OrcaRouter LLM client integration."""

import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from tooluniverse.agentic_tool import AgenticTool
from tooluniverse.llm_clients import OrcaRouterClient

pytestmark = pytest.mark.unit


class FakeRateLimitError(Exception):
    pass


class FakeCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
        )


class FakeOpenAIClient:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(
                create=self.completions.create,
                parse=self.completions.create,
            )
        )
        FakeOpenAIClient.instances.append(self)


@pytest.fixture(autouse=True)
def fake_openai(monkeypatch):
    FakeOpenAIClient.instances = []
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(OpenAI=FakeOpenAIClient, RateLimitError=FakeRateLimitError),
    )
    monkeypatch.setenv("ORCAROUTER_API_KEY", "test-key")
    monkeypatch.delenv("ORCAROUTER_BASE_URL", raising=False)
    monkeypatch.delenv("ORCAROUTER_DEFAULT_MODEL_LIMITS", raising=False)
    monkeypatch.delenv("ORCAROUTER_MAX_TOKENS_BY_MODEL", raising=False)


def test_client_default_base_url(monkeypatch):
    client = OrcaRouterClient(
        "orcarouter/auto",
        logger=SimpleNamespace(warning=lambda *_: None, error=lambda *_: None),
    )
    assert FakeOpenAIClient.instances[0].kwargs["base_url"] == (
        "https://api.orcarouter.ai/v1"
    )
    assert FakeOpenAIClient.instances[0].kwargs["api_key"] == "test-key"
    assert client.model_name == "orcarouter/auto"


def test_client_custom_base_url(monkeypatch):
    monkeypatch.setenv("ORCAROUTER_BASE_URL", "https://custom.example/v1")
    OrcaRouterClient(
        "orcarouter/auto",
        logger=SimpleNamespace(warning=lambda *_: None, error=lambda *_: None),
    )
    assert FakeOpenAIClient.instances[0].kwargs["base_url"] == "https://custom.example/v1"


def test_client_missing_api_key(monkeypatch):
    monkeypatch.delenv("ORCAROUTER_API_KEY")
    with pytest.raises(ValueError, match="ORCAROUTER_API_KEY not set"):
        OrcaRouterClient(
            "orcarouter/auto",
            logger=SimpleNamespace(warning=lambda *_: None, error=lambda *_: None),
        )


def test_infer_json_object(monkeypatch):
    client = OrcaRouterClient(
        "orcarouter/auto",
        logger=SimpleNamespace(warning=lambda *_: None, error=lambda *_: None),
    )
    result = client.infer(
        messages=[{"role": "user", "content": "ping"}],
        temperature=0,
        max_tokens=16,
        return_json=True,
        max_retries=1,
        retry_delay=0,
    )
    assert result == "ok"
    call_kwargs = FakeOpenAIClient.instances[0].completions.calls[0]
    assert call_kwargs["model"] == "orcarouter/auto"
    assert call_kwargs["response_format"] == {"type": "json_object"}


def test_infer_default_max_tokens(monkeypatch):
    monkeypatch.setenv("ORCAROUTER_MAX_TOKENS_BY_MODEL", '{"orcarouter/auto": 4096}')
    client = OrcaRouterClient(
        "orcarouter/auto",
        logger=SimpleNamespace(warning=lambda *_: None, error=lambda *_: None),
    )
    result = client.infer(
        messages=[{"role": "user", "content": "ping"}],
        temperature=None,
        max_tokens=None,
        return_json=False,
        max_retries=1,
        retry_delay=0,
    )
    assert result == "ok"
    assert FakeOpenAIClient.instances[0].completions.calls[0]["max_tokens"] == 4096


def test_agentic_tool_orcarouter_in_supported_types():
    """ORCAROUTER should be a supported API type and route to OrcaRouterClient."""
    tool_config = {
        "name": "Test_Tool",
        "prompt": "Test: {x}",
        "input_arguments": ["x"],
        "parameter": {
            "type": "object",
            "properties": {"x": {"type": "string"}},
            "required": ["x"],
        },
        "configs": {
            "api_type": "ORCAROUTER",
            "model_id": "orcarouter/auto",
            "validate_api_key": False,
        },
    }
    with patch("tooluniverse.agentic_tool.OrcaRouterClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.test_api = Mock()
        mock_client.infer = Mock(return_value="Test result")
        tool = AgenticTool(tool_config)
        assert tool._is_available
        assert tool._current_api_type == "ORCAROUTER"
        assert tool._current_model_id == "orcarouter/auto"


def test_agentic_tool_requires_key_in_env_vars():
    """ORCAROUTER_API_KEY should be listed in API_KEY_ENV_VARS."""
    from tooluniverse.agentic_tool import API_KEY_ENV_VARS

    assert "ORCAROUTER" in API_KEY_ENV_VARS
    assert API_KEY_ENV_VARS["ORCAROUTER"] == ["ORCAROUTER_API_KEY"]
