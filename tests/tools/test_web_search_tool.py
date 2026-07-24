#!/usr/bin/env python3
"""
Unit tests for WebSearchTool failure and fallback behavior.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse import web_search_tool
from tooluniverse.mcp_client_tool import BaseMCPClient
from tooluniverse.web_search_tool import WebSearchTool


def _new_tool():
    return WebSearchTool({"name": "web_search", "parameter": {"type": "object"}})


@pytest.mark.unit
@pytest.mark.parametrize(
    ("server_url", "expected_endpoint"),
    [
        ("https://search.parallel.ai/mcp", "https://search.parallel.ai/mcp"),
        ("https://example.com/mcp/", "https://example.com/mcp/"),
        ("https://example.com", "https://example.com/mcp/"),
    ],
)
def test_mcp_endpoint_preserves_configured_slash_shape(server_url, expected_endpoint):
    client = BaseMCPClient(server_url)

    assert client._get_mcp_endpoint("") == expected_endpoint


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


@pytest.mark.unit
def test_parallel_search_uses_mcp_and_normalizes_structured_results(monkeypatch):
    calls = {}

    class FakeMCPClient:
        def __init__(self, server_url, transport, timeout):
            calls["init"] = {
                "server_url": server_url,
                "transport": transport,
                "timeout": timeout,
            }

        async def _make_mcp_request(self, method, params):
            calls["request"] = {"method": method, "params": params}
            return {
                "isError": False,
                "structuredContent": {
                    "results": [
                        {
                            "title": "First result",
                            "url": "https://example.com/first",
                            "excerpts": ["First excerpt.", "Second excerpt."],
                        },
                        {
                            "title": None,
                            "url": "https://example.com/second",
                            "excerpts": ["Unused because of max_results."],
                        },
                    ]
                },
            }

        def _run_with_cleanup(self, async_func):
            import asyncio

            return asyncio.run(async_func())

    monkeypatch.setattr(web_search_tool, "BaseMCPClient", FakeMCPClient)

    results = _new_tool()._search_with_parallel("test query", max_results=1)

    assert calls["init"] == {
        "server_url": "https://search.parallel.ai/mcp",
        "transport": "http",
        "timeout": 30,
    }
    assert calls["request"] == {
        "method": "tools/call",
        "params": {
            "name": "web_search",
            "arguments": {
                "objective": "test query",
                "search_queries": ["test query"],
            },
        },
    }
    assert results == [
        {
            "title": "First result",
            "url": "https://example.com/first",
            "snippet": "First excerpt.\n\nSecond excerpt.",
            "rank": 1,
        }
    ]


@pytest.mark.unit
def test_parallel_backend_reports_success(monkeypatch):
    tool = _new_tool()
    monkeypatch.setattr(
        tool,
        "_search_with_parallel",
        lambda **kwargs: [
            {
                "title": "Parallel result",
                "url": "https://example.com",
                "snippet": "excerpt",
                "rank": 1,
            }
        ],
    )

    result = tool.run({"query": "test query", "backend": "parallel"})

    assert result["status"] == "success"
    assert result["data"]["backend_used"] == "parallel"
    assert result["data"]["attempted_backends"] == ["parallel"]


@pytest.mark.unit
def test_parallel_backend_failure_falls_back_to_auto(monkeypatch):
    tool = _new_tool()

    def parallel_fail(**kwargs):
        raise RuntimeError("parallel failed")

    monkeypatch.setattr(tool, "_search_with_parallel", parallel_fail)
    monkeypatch.setattr(
        tool,
        "_search_with_ddgs",
        lambda **kwargs: [
            {
                "title": "Fallback result",
                "url": "https://fallback.example",
                "snippet": "from DDGS",
                "rank": 1,
            }
        ],
    )

    result = tool.run({"query": "test query", "backend": "parallel"})

    assert result["status"] == "success"
    assert result["data"]["backend_used"] == "auto"
    assert result["data"]["attempted_backends"] == ["parallel", "auto"]
    assert result["data"]["provider_errors"]["parallel"] == "parallel failed"


@pytest.mark.unit
def test_auto_backend_does_not_call_parallel(monkeypatch):
    tool = _new_tool()

    def unexpected_parallel_call(**kwargs):
        raise AssertionError("Parallel must remain opt-in")

    monkeypatch.setattr(tool, "_search_with_parallel", unexpected_parallel_call)
    monkeypatch.setattr(
        tool,
        "_search_with_ddgs",
        lambda **kwargs: [
            {
                "title": "Default result",
                "url": "https://default.example",
                "snippet": "from default chain",
                "rank": 1,
            }
        ],
    )

    result = tool.run({"query": "test query", "backend": "auto"})

    assert result["status"] == "success"
    assert result["data"]["backend_used"] == "duckduckgo"
    assert "parallel" not in result["data"]["attempted_backends"]
