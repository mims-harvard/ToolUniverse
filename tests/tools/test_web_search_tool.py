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
from tooluniverse.web_search_tool import (
    WebAPIDocumentationSearchTool,
    WebSearchTool,
)


def _new_tool():
    return WebSearchTool({"name": "web_search", "parameter": {"type": "object"}})


def _new_api_docs_tool():
    return WebAPIDocumentationSearchTool(
        {
            "name": "web_api_documentation_search",
            "parameter": {"type": "object"},
        }
    )


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
@pytest.mark.parametrize(
    "response",
    [
        {"isError": True},
        {"isError": False},
        {"isError": False, "structuredContent": {"results": {}}},
    ],
)
def test_parallel_search_rejects_error_or_malformed_mcp_responses(
    monkeypatch, response
):
    class FakeMCPClient:
        def __init__(self, *args, **kwargs):
            pass

        async def _make_mcp_request(self, method, params):
            return response

        def _run_with_cleanup(self, async_func):
            import asyncio

            return asyncio.run(async_func())

    monkeypatch.setattr(web_search_tool, "BaseMCPClient", FakeMCPClient)

    with pytest.raises(RuntimeError):
        _new_tool()._search_with_parallel("test query", max_results=2)


@pytest.mark.unit
def test_parallel_search_skips_malformed_items_and_reassigns_ranks(monkeypatch):
    class FakeMCPClient:
        def __init__(self, *args, **kwargs):
            pass

        async def _make_mcp_request(self, method, params):
            return {
                "isError": False,
                "structured_content": {
                    "results": [
                        None,
                        {},
                        {"url": ""},
                        {
                            "title": None,
                            "url": "https://example.com/valid",
                            "excerpts": ["Valid excerpt.", 7],
                        },
                        {
                            "title": 12,
                            "url": "https://example.com/second",
                            "excerpts": "not a list",
                        },
                    ]
                },
            }

        def _run_with_cleanup(self, async_func):
            import asyncio

            return asyncio.run(async_func())

    monkeypatch.setattr(web_search_tool, "BaseMCPClient", FakeMCPClient)

    results = _new_tool()._search_with_parallel("test query", max_results=2)

    assert results == [
        {
            "title": "",
            "url": "https://example.com/valid",
            "snippet": "Valid excerpt.",
            "rank": 1,
        },
        {
            "title": "",
            "url": "https://example.com/second",
            "snippet": "",
            "rank": 2,
        },
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

    result = tool.run(
        {
            "query": "test query",
            "backend": "parallel",
            "region": "us-en",
            "safesearch": "moderate",
        }
    )

    assert result["status"] == "success"
    assert result["data"]["backend_used"] == "parallel"
    assert result["data"]["attempted_backends"] == ["parallel"]
    assert "search.parallel.ai/mcp" in result["data"]["provider_notice"]
    assert "patient-identifying" in result["data"]["provider_notice"]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("control", "value"),
    [("region", "cn-zh"), ("safesearch", "off")],
)
def test_parallel_backend_rejects_unsupported_controls(monkeypatch, control, value):
    tool = _new_tool()

    def unexpected_parallel_call(**kwargs):
        raise AssertionError("Unsupported controls must fail before transmission")

    monkeypatch.setattr(tool, "_search_with_parallel", unexpected_parallel_call)

    result = tool.run(
        {"query": "sensitive query", "backend": "parallel", control: value}
    )

    assert result["status"] == "error"
    assert control in result["error"]
    assert "does not support" in result["error"]


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
    assert "search.parallel.ai/mcp" in result["data"]["provider_notice"]


@pytest.mark.unit
def test_parallel_all_provider_failure_keeps_disclosure(monkeypatch):
    tool = _new_tool()

    def always_fail(**kwargs):
        raise RuntimeError("simulated provider failure")

    monkeypatch.setattr(tool, "_search_with_parallel", always_fail)
    monkeypatch.setattr(tool, "_search_with_ddgs", always_fail)
    monkeypatch.setattr(tool, "_search_with_duckduckgo_html", always_fail)
    monkeypatch.setattr(tool, "_search_with_wikipedia_api", always_fail)

    result = tool.run({"query": "test query", "backend": "parallel"})

    assert result["status"] == "success"
    assert result["data"]["backend_used"] == "none"
    assert result["data"]["all_providers_failed"] is True
    assert result["data"]["attempted_backends"][0] == "parallel"
    assert "search.parallel.ai/mcp" in result["data"]["provider_notice"]


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
    assert "provider_notice" not in result["data"]


@pytest.mark.unit
def test_api_documentation_search_enhances_query_once_without_mutating_input(
    monkeypatch,
):
    tool = _new_api_docs_tool()
    captured = {}

    def fake_search(**kwargs):
        captured.update(kwargs)
        return (
            [
                {
                    "title": "FastMCP Client",
                    "url": "https://gofastmcp.com/clients/client",
                    "snippet": "Client documentation",
                    "rank": 1,
                }
            ],
            "parallel",
            ["parallel"],
            None,
            {},
        )

    monkeypatch.setattr(tool, "_search_with_fallback", fake_search)
    monkeypatch.setattr(web_search_tool.time, "sleep", lambda _: None)
    arguments = {
        "query": "FastMCP Client",
        "focus": "api_docs",
        "backend": "parallel",
        "max_results": 4,
    }
    original_arguments = dict(arguments)

    result = tool.run(arguments)

    expected_query = '"FastMCP Client" API documentation official docs'
    assert captured["query"] == expected_query
    assert result["status"] == "success"
    assert result["data"]["query"] == expected_query
    assert result["data"]["enhanced_query"] == expected_query
    assert result["data"]["search_type"] == "api_documentation"
    assert result["data"]["focus"] == "api_docs"
    assert arguments == original_arguments


# --------------------------------------------------------------------------- #
# SerpBase backend
# --------------------------------------------------------------------------- #

# Fixture shape from SerpBase's own documented example response
# (https://serpbase.dev/docs), verified live against the real endpoint's
# auth-error shape (200 OK + "error" field, not a 401) but not against a
# real successful response -- no API key was available to confirm this.
_SERPBASE_DOCUMENTED_RESPONSE = {
    "status": 1000,
    "request_id": "test-request-id",
    "elapsed_ms": 120,
    "credits_charged": 1,
    "search_type": "search",
    "query": "python asyncio",
    "page": 1,
    "organic": [
        {
            "rank": 1,
            "title": "asyncio — Asynchronous I/O",
            "link": "https://docs.python.org/3/library/asyncio.html",
            "snippet": "asyncio is a library to write concurrent code.",
        }
    ],
}


class _FakeSerpBaseResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@pytest.mark.unit
def test_serpbase_search_requires_api_key(monkeypatch):
    monkeypatch.delenv("SERPBASE_API_KEY", raising=False)
    tool = _new_tool()

    with pytest.raises(RuntimeError, match="SERPBASE_API_KEY"):
        tool._search_with_serpbase(query="test", max_results=5)


@pytest.mark.unit
def test_serpbase_search_parses_documented_response_shape(monkeypatch):
    monkeypatch.setenv("SERPBASE_API_KEY", "test-key")
    captured = {}

    def fake_post(url, *, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _FakeSerpBaseResponse(_SERPBASE_DOCUMENTED_RESPONSE)

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)

    results = _new_tool()._search_with_serpbase(
        query="python asyncio", max_results=5, region="us-en"
    )

    assert captured["url"] == "https://api.serpbase.dev/google/search"
    assert captured["json"] == {"q": "python asyncio", "gl": "us", "hl": "en"}
    assert captured["headers"] == {"X-API-Key": "test-key"}
    assert results == [
        {
            "title": "asyncio — Asynchronous I/O",
            "url": "https://docs.python.org/3/library/asyncio.html",
            "snippet": "asyncio is a library to write concurrent code.",
            "rank": 1,
        }
    ]


@pytest.mark.unit
def test_serpbase_search_splits_region_into_gl_and_hl(monkeypatch):
    monkeypatch.setenv("SERPBASE_API_KEY", "test-key")
    captured = {}

    def fake_post(url, *, json=None, headers=None, timeout=None):
        captured["json"] = json
        return _FakeSerpBaseResponse({"organic": []})

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)

    _new_tool()._search_with_serpbase(query="x", max_results=1, region="cn-zh")

    assert captured["json"]["gl"] == "cn"
    assert captured["json"]["hl"] == "zh"


@pytest.mark.unit
def test_serpbase_search_raises_on_error_field_even_with_200(monkeypatch):
    """SerpBase returns HTTP 200 even for auth failures, with the failure in
    the JSON body's `error` field -- confirmed live against the real API."""
    monkeypatch.setenv("SERPBASE_API_KEY", "wrong-key")

    def fake_post(*args, **kwargs):
        return _FakeSerpBaseResponse({"error": "unauthorized", "status": 1001})

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)

    with pytest.raises(RuntimeError, match="unauthorized"):
        _new_tool()._search_with_serpbase(query="x", max_results=1)


@pytest.mark.unit
def test_serpbase_search_raises_on_missing_organic_key(monkeypatch):
    monkeypatch.setenv("SERPBASE_API_KEY", "test-key")

    def fake_post(*args, **kwargs):
        return _FakeSerpBaseResponse({"status": 1000, "query": "x"})

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)

    with pytest.raises(RuntimeError, match="organic"):
        _new_tool()._search_with_serpbase(query="x", max_results=1)


@pytest.mark.unit
def test_serpbase_search_skips_malformed_items_and_falls_back_to_url_field(
    monkeypatch,
):
    monkeypatch.setenv("SERPBASE_API_KEY", "test-key")

    def fake_post(*args, **kwargs):
        return _FakeSerpBaseResponse(
            {
                "organic": [
                    "not a dict",
                    {"title": "No link at all"},
                    {"title": "Uses url not link", "url": "https://example.com/u"},
                    {"title": "Real result", "link": "https://example.com/real"},
                ]
            }
        )

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)

    results = _new_tool()._search_with_serpbase(query="x", max_results=10)

    assert [r["url"] for r in results] == [
        "https://example.com/u",
        "https://example.com/real",
    ]
    assert [r["rank"] for r in results] == [1, 2]


@pytest.mark.unit
def test_serpbase_search_truncates_to_max_results(monkeypatch):
    monkeypatch.setenv("SERPBASE_API_KEY", "test-key")

    def fake_post(*args, **kwargs):
        return _FakeSerpBaseResponse(
            {
                "organic": [
                    {"title": f"Result {i}", "link": f"https://example.com/{i}"}
                    for i in range(10)
                ]
            }
        )

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)

    results = _new_tool()._search_with_serpbase(query="x", max_results=3)

    assert len(results) == 3


@pytest.mark.unit
def test_serpbase_backend_reports_success(monkeypatch):
    tool = _new_tool()
    monkeypatch.setattr(
        tool,
        "_search_with_serpbase",
        lambda **kwargs: [
            {
                "title": "SerpBase result",
                "url": "https://example.com",
                "snippet": "excerpt",
                "rank": 1,
            }
        ],
    )

    result = tool.run(
        {
            "query": "test query",
            "backend": "serpbase",
            "region": "us-en",
            "safesearch": "moderate",
        }
    )

    assert result["status"] == "success"
    assert result["data"]["backend_used"] == "serpbase"
    assert result["data"]["attempted_backends"] == ["serpbase"]
    assert "api.serpbase.dev" in result["data"]["provider_notice"]
    assert "patient-identifying" in result["data"]["provider_notice"]


@pytest.mark.unit
def test_serpbase_backend_rejects_unsupported_safesearch_control(monkeypatch):
    tool = _new_tool()

    def unexpected_call(**kwargs):
        raise AssertionError("Unsupported controls must fail before transmission")

    monkeypatch.setattr(tool, "_search_with_serpbase", unexpected_call)

    result = tool.run(
        {"query": "sensitive query", "backend": "serpbase", "safesearch": "off"}
    )

    assert result["status"] == "error"
    assert "safesearch" in result["error"]
    assert "does not support" in result["error"]


@pytest.mark.unit
def test_serpbase_backend_accepts_non_default_region(monkeypatch):
    """Unlike Parallel, SerpBase supports region -- only safesearch is rejected."""
    tool = _new_tool()
    monkeypatch.setattr(
        tool,
        "_search_with_serpbase",
        lambda **kwargs: [
            {"title": "R", "url": "https://example.com", "snippet": "", "rank": 1}
        ],
    )

    result = tool.run({"query": "test query", "backend": "serpbase", "region": "cn-zh"})

    assert result["status"] == "success"
    assert result["data"]["backend_used"] == "serpbase"


@pytest.mark.unit
def test_serpbase_backend_failure_falls_back_to_auto(monkeypatch):
    tool = _new_tool()

    def serpbase_fail(**kwargs):
        raise RuntimeError("serpbase failed")

    monkeypatch.setattr(tool, "_search_with_serpbase", serpbase_fail)
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

    result = tool.run({"query": "test query", "backend": "serpbase"})

    assert result["status"] == "success"
    assert result["data"]["backend_used"] == "auto"
    assert result["data"]["attempted_backends"] == ["serpbase", "auto"]
    assert result["data"]["provider_errors"]["serpbase"] == "serpbase failed"
    assert "api.serpbase.dev" in result["data"]["provider_notice"]


@pytest.mark.unit
def test_serpbase_all_provider_failure_keeps_disclosure(monkeypatch):
    tool = _new_tool()

    def always_fail(**kwargs):
        raise RuntimeError("simulated provider failure")

    monkeypatch.setattr(tool, "_search_with_serpbase", always_fail)
    monkeypatch.setattr(tool, "_search_with_ddgs", always_fail)
    monkeypatch.setattr(tool, "_search_with_duckduckgo_html", always_fail)
    monkeypatch.setattr(tool, "_search_with_wikipedia_api", always_fail)

    result = tool.run({"query": "test query", "backend": "serpbase"})

    assert result["status"] == "success"
    assert result["data"]["backend_used"] == "none"
    assert result["data"]["all_providers_failed"] is True
    assert result["data"]["attempted_backends"][0] == "serpbase"
    assert "api.serpbase.dev" in result["data"]["provider_notice"]


@pytest.mark.unit
def test_auto_backend_does_not_call_serpbase(monkeypatch):
    tool = _new_tool()

    def unexpected_call(**kwargs):
        raise AssertionError("SerpBase must remain opt-in")

    monkeypatch.setattr(tool, "_search_with_serpbase", unexpected_call)
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
    assert "serpbase" not in result["data"]["attempted_backends"]
    assert "provider_notice" not in result["data"]
