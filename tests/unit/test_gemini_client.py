"""Unit tests for the migrated GeminiClient (google-generativeai → google-genai)."""

from __future__ import annotations

import logging
import os
from types import SimpleNamespace
from unittest import mock

import pytest

from tooluniverse.llm_clients import GeminiClient


def test_missing_api_key_raises_value_error(monkeypatch):
    """Constructor must raise ValueError (not ImportError) when key is absent."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY not found"):
        GeminiClient("gemini-2.5-flash", logging.getLogger("test"))


def test_constructs_with_api_key(monkeypatch):
    """With key present, constructor should produce a google.genai.Client."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-not-validated-at-construction")
    client = GeminiClient("gemini-2.5-flash", logging.getLogger("test"))
    # google.genai.Client is the documented type for the new SDK
    assert type(client._client).__name__ == "Client"
    assert client.model_name == "gemini-2.5-flash"


def test_build_config_passes_temperature_and_max_tokens(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    client = GeminiClient("gemini-2.5-flash", logging.getLogger("test"))
    cfg = client._build_config(0.7, 128)
    assert cfg.temperature == 0.7
    assert cfg.max_output_tokens == 128


@pytest.mark.parametrize(
    "model_name",
    [
        "gemini-3.6-flash",
        "models/gemini-3.6-flash",
        "gemini-3.5-flash-lite",
        "gemini-flash-latest",
        "gemini-4.0-flash",
    ],
)
def test_build_config_omits_deprecated_sampling_parameters(monkeypatch, model_name):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    client = GeminiClient(model_name, logging.getLogger("test"))

    cfg = client._build_config(temperature=0.7, max_tokens=128)

    assert cfg.temperature is None
    assert cfg.top_p is None
    assert cfg.top_k is None
    assert cfg.max_output_tokens == 128


def test_gemini_35_flash_keeps_supported_temperature(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    client = GeminiClient("gemini-3.5-flash", logging.getLogger("test"))

    cfg = client._build_config(temperature=0.7, max_tokens=None)

    assert cfg.temperature == 0.7


def test_build_config_enables_json_mime_type(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    client = GeminiClient("gemini-2.5-flash", logging.getLogger("test"))
    cfg = client._build_config(temperature=0.0, max_tokens=None, return_json=True)
    assert cfg.response_mime_type == "application/json"


def test_build_config_leaves_json_mime_type_unset_by_default(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    client = GeminiClient("gemini-2.5-flash", logging.getLogger("test"))
    cfg = client._build_config(temperature=0.0, max_tokens=None, return_json=False)
    assert cfg.response_mime_type is None


def test_build_config_omits_max_tokens_when_none(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    client = GeminiClient("gemini-2.5-flash", logging.getLogger("test"))
    cfg = client._build_config(temperature=0.0, max_tokens=None)
    assert cfg.temperature == 0.0
    assert cfg.max_output_tokens is None


def test_gemini_json_mode_guard_removed():
    """Regression guard: the old hard raise that broke return_json agentic
    tools on Gemini must stay gone now that JSON mode is honored."""
    import tooluniverse.llm_clients as mod

    src = open(mod.__file__).read()
    assert "Gemini JSON mode not supported here" not in src


def test_infer_returns_dumped_custom_format():
    client = GeminiClient.__new__(GeminiClient)
    client.model_name = "gemini-2.5-flash"
    client._build_config = mock.Mock(return_value=None)
    parsed = mock.Mock()
    parsed.model_dump.return_value = {"field": "value"}
    client._client = mock.Mock()
    client._client.models.generate_content.return_value = mock.Mock(parsed=parsed)

    result = client.infer([], 0.0, None, False, custom_format={"type": "object"})

    assert result == {"field": "value"}


def test_infer_extracts_text_without_accessing_response_text_property():
    class ResponseWithGuardedText:
        def __init__(self, candidates):
            self.candidates = candidates

        @property
        def text(self):
            raise AssertionError(
                "response.text must not be read when parts are present"
            )

    client = GeminiClient.__new__(GeminiClient)
    client.model_name = "gemini-3.6-flash"
    client._build_config = mock.Mock(return_value=None)
    response = ResponseWithGuardedText(
        [
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[
                        SimpleNamespace(thought_signature=b"signature"),
                        SimpleNamespace(text='{"field": "value"}'),
                    ]
                )
            )
        ]
    )
    client._client = mock.Mock()
    client._client.models.generate_content.return_value = response

    result = client.infer([], 0.0, None, True)

    assert result == '{"field": "value"}'


def test_infer_stream_buffers_custom_format():
    client = GeminiClient.__new__(GeminiClient)
    client._client = mock.Mock()
    client.infer = mock.Mock(return_value={"field": "value"})

    chunks = list(client.infer_stream([], 0.0, None, False, custom_format=object()))

    assert chunks == [{"field": "value"}]
    client._client.models.generate_content_stream.assert_not_called()


def test_no_dependency_on_deprecated_google_generativeai():
    """Regression guard: the migration removes google.generativeai. If a
    future edit re-introduces it, this test should catch the import sneaking back."""
    import tooluniverse.llm_clients as mod

    src = open(mod.__file__).read()
    assert "google.generativeai" not in src, (
        "google.generativeai was reintroduced into llm_clients.py — "
        "the deprecated package should remain absent; use google.genai (the new SDK)."
    )
