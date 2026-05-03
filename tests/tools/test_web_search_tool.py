#!/usr/bin/env python3
"""
Unit tests for WebSearchTool failure and fallback behavior.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.web_search_tool import WebSearchTool


def _new_tool():
    return WebSearchTool({"name": "web_search", "parameter": {"type": "object"}})


@pytest.mark.unit
def test_web_search_success_includes_backend_metadata(monkeypatch):
    tool = _new_tool()

    def fake_search(*args, **kwargs):
        return [
            {
                "title": "Result A",
                "url": "https://example.org",
                "snippet": "snippet",
                "rank": 1,
            }
        ]

    monkeypatch.setattr(tool, "_search_with_ddgs", fake_search)
    result = tool.run({"query": "test query", "backend": "auto"})

    assert result["status"] == "success"
    assert result["data"]["status"] == "success"
    assert result["data"]["total_results"] == 1
    assert result["data"]["backend_used"] in result["data"]["attempted_backends"]


@pytest.mark.unit
def test_web_search_returns_clean_empty_results_on_backend_failure(monkeypatch):
    tool = _new_tool()

    def always_fail(*args, **kwargs):
        raise RuntimeError("simulated search failure")

    monkeypatch.setattr(tool, "_search_with_duckduckgo_html", always_fail)
    monkeypatch.setattr(tool, "_search_with_wikipedia_api", always_fail)
    monkeypatch.setattr(tool, "_search_with_ddgs", always_fail)
    result = tool.run({"query": "test query", "backend": "auto"})

    assert result["status"] == "success"
    assert result["data"]["status"] == "success"
    assert result["data"]["total_results"] == 0
    assert result["data"]["results"] == []
    assert result["data"]["backend_used"] == "none"
    assert result["data"]["all_providers_failed"] is True
    assert "auto" in result["data"]["provider_errors"]
    assert "simulated search failure" in result["data"]["provider_errors"]["auto"]


@pytest.mark.unit
def test_web_search_empty_result_without_provider_error(monkeypatch):
    tool = _new_tool()

    monkeypatch.setattr(tool, "_search_with_ddgs", lambda **kwargs: [])
    monkeypatch.setattr(tool, "_search_with_duckduckgo_html", lambda **kwargs: [])
    monkeypatch.setattr(tool, "_search_with_wikipedia_api", lambda **kwargs: [])

    result = tool.run({"query": "test query", "backend": "auto"})

    assert result["status"] == "success"
    assert result["data"]["status"] == "success"
    assert result["data"]["backend_used"] == "empty"
    assert result["data"]["total_results"] == 0
    assert (
        "provider_errors" not in result["data"] or not result["data"]["provider_errors"]
    )


@pytest.mark.unit
def test_web_search_falls_back_to_http_provider(monkeypatch):
    tool = _new_tool()

    def ddgs_fail(*args, **kwargs):
        raise RuntimeError("ddgs failed")

    def duck_success(*args, **kwargs):
        return [
            {
                "title": "Fallback Result",
                "url": "https://fallback.example",
                "snippet": "from fallback",
                "rank": 1,
            }
        ]

    monkeypatch.setattr(tool, "_search_with_ddgs", ddgs_fail)
    monkeypatch.setattr(tool, "_search_with_duckduckgo_html", duck_success)
    monkeypatch.setattr(tool, "_search_with_wikipedia_api", lambda **kwargs: [])

    result = tool.run({"query": "test query", "backend": "auto"})

    assert result["status"] == "success"
    assert result["data"]["status"] == "success"
    assert result["data"]["total_results"] == 1
    assert result["data"]["backend_used"] == "duckduckgo_html"
    assert "provider_errors" in result["data"]
    assert "auto" in result["data"]["provider_errors"]
