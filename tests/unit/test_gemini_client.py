"""Unit tests for the migrated GeminiClient (google-generativeai → google-genai)."""

from __future__ import annotations

import logging
import os
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
    cfg = client._build_config(temperature=0.7, max_tokens=128)
    assert cfg.temperature == 0.7
    assert cfg.max_output_tokens == 128


def test_build_config_omits_max_tokens_when_none(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    client = GeminiClient("gemini-2.5-flash", logging.getLogger("test"))
    cfg = client._build_config(temperature=0.0, max_tokens=None)
    assert cfg.temperature == 0.0
    assert cfg.max_output_tokens is None


def test_no_dependency_on_deprecated_google_generativeai():
    """Regression guard: the migration removes google.generativeai. If a
    future edit re-introduces it, this test should catch the import sneaking back."""
    import tooluniverse.llm_clients as mod
    src = open(mod.__file__).read()
    assert "google.generativeai" not in src, (
        "google.generativeai was reintroduced into llm_clients.py — "
        "the deprecated package should remain absent; use google.genai (the new SDK)."
    )
