#!/usr/bin/env python3
"""
Unit tests for WebSearchTool failure and fallback behavior.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse import credential_context, web_search_tool
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
def test_duckduckgo_redirect_preserves_percent_encoded_destination_query(monkeypatch):
    """parse_qs decodes uddg once; a second decode changes the destination."""
    tool = _new_tool()

    class FakeResponse:
        text = (
            '<a class="result__a" '
            'href="/l/?uddg=https%3A%2F%2Fexample.org%2Fsearch%3Fq%3Da%252Bb">'
            "Result</a>"
        )

        def raise_for_status(self):
            return None

    monkeypatch.setattr(
        web_search_tool.requests, "get", lambda *args, **kwargs: FakeResponse()
    )

    results = tool._search_with_duckduckgo_html("query", max_results=1)

    assert results[0]["url"] == "https://example.org/search?q=a%2Bb"


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


# Fixture shape from a live keyless call to https://api.firecrawl.dev/v2/search
# on 2026-09-21 (success envelope, `data.web` items, `creditsUsed`, `id`).
# The `id` below is a placeholder, not a real request id.
_FIRECRAWL_LIVE_RESPONSE = {
    "success": True,
    "data": {
        "web": [
            {
                "url": "https://docs.python.org/3/library/asyncio-eventloop.html",
                "title": "Event Loop — Python 3 documentation",
                "description": "The event loop is the core of every asyncio application.",
                "position": 1,
            }
        ]
    },
    "creditsUsed": 2,
    "id": "00000000-0000-7000-8000-000000000000",
}


class _FakeFirecrawlResponse:
    def __init__(self, payload, status_code=200, reason=""):
        self._payload = payload
        self.status_code = status_code
        self.reason = reason

    def json(self):
        return self._payload


@pytest.mark.unit
def test_firecrawl_search_works_without_api_key(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    captured = {}

    def fake_post(url, *, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _FakeFirecrawlResponse(_FIRECRAWL_LIVE_RESPONSE)

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)

    results = _new_tool()._search_with_firecrawl(
        query="python asyncio event loop", max_results=5
    )

    assert captured["url"] == "https://api.firecrawl.dev/v2/search"
    assert captured["json"] == {
        "query": "python asyncio event loop",
        "limit": 5,
        "sources": ["web"],
        "country": "US",
        "highlights": False,
        "safe": True,
    }
    assert captured["headers"] == {}
    assert captured["timeout"] == 30
    assert results == [
        {
            "title": "Event Loop — Python 3 documentation",
            "url": "https://docs.python.org/3/library/asyncio-eventloop.html",
            "snippet": "The event loop is the core of every asyncio application.",
            "rank": 1,
        }
    ]


@pytest.mark.unit
def test_firecrawl_search_sends_bearer_header_when_key_is_set(monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test-key")
    captured = {}

    def fake_post(url, *, json=None, headers=None, timeout=None):
        captured["headers"] = headers
        return _FakeFirecrawlResponse(_FIRECRAWL_LIVE_RESPONSE)

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)

    _new_tool()._search_with_firecrawl(query="x", max_results=1)

    assert captured["headers"] == {"Authorization": "Bearer fc-test-key"}


@pytest.mark.unit
def test_firecrawl_search_strips_whitespace_from_api_key(monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "  fc-test-key\n")
    captured = {}

    def fake_post(url, *, json=None, headers=None, timeout=None):
        captured["headers"] = headers
        return _FakeFirecrawlResponse(_FIRECRAWL_LIVE_RESPONSE)

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)

    _new_tool()._search_with_firecrawl(query="x", max_results=1)

    assert captured["headers"]["Authorization"] == "Bearer fc-test-key"


@pytest.mark.unit
def test_firecrawl_search_prefers_the_request_scoped_key(monkeypatch):
    """A hosted process serves each request with that request's own key."""
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-operator-key")
    captured = {}

    def fake_post(url, *, json=None, headers=None, timeout=None):
        captured["headers"] = headers
        return _FakeFirecrawlResponse(_FIRECRAWL_LIVE_RESPONSE)

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)
    tool = _new_tool()

    with credential_context({"FIRECRAWL_API_KEY": "fc-request-key"}):
        tool._search_with_firecrawl(query="x", max_results=1)

    assert captured["headers"] == {"Authorization": "Bearer fc-request-key"}


@pytest.mark.unit
def test_firecrawl_search_in_a_scope_without_the_key_stays_keyless(monkeypatch):
    """Fail closed: a request that carries no Firecrawl key must not spend the
    operator's environment key. Keyless is the documented tier, so the search
    still runs, just without the Authorization header."""
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-operator-key")
    captured = {}

    def fake_post(url, *, json=None, headers=None, timeout=None):
        captured["headers"] = headers
        return _FakeFirecrawlResponse(_FIRECRAWL_LIVE_RESPONSE)

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)
    tool = _new_tool()

    with credential_context({"SOME_OTHER_KEY": "unrelated"}):
        results = tool._search_with_firecrawl(query="x", max_results=1)

    assert captured["headers"] == {}
    assert len(results) == 1


@pytest.mark.unit
@pytest.mark.parametrize(
    ("region", "expected_country"),
    [
        ("us-en", "US"),
        ("uk-en", "GB"),
        ("de-de", "DE"),
        ("cn-zh", "CN"),
        ("fr-fr", "FR"),
        ("ja-jp", "JP"),
        ("", "US"),
    ],
)
def test_firecrawl_search_maps_region_country_half_to_iso_code(
    monkeypatch, region, expected_country
):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    captured = {}

    def fake_post(url, *, json=None, headers=None, timeout=None):
        captured["json"] = json
        return _FakeFirecrawlResponse({"success": True, "data": {"web": []}})

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)

    _new_tool()._search_with_firecrawl(query="x", max_results=1, region=region)

    assert captured["json"]["country"] == expected_country
    # The language half has no Firecrawl equivalent and must not leak through.
    assert "location" not in captured["json"]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("safesearch", "expected_safe"),
    [("on", True), ("moderate", True), ("off", None)],
)
def test_firecrawl_search_maps_safesearch_to_two_state_filter(
    monkeypatch, safesearch, expected_safe
):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    captured = {}

    def fake_post(url, *, json=None, headers=None, timeout=None):
        captured["json"] = json
        return _FakeFirecrawlResponse({"success": True, "data": {"web": []}})

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)

    _new_tool()._search_with_firecrawl(query="x", max_results=1, safesearch=safesearch)

    assert captured["json"].get("safe") == expected_safe


@pytest.mark.unit
def test_firecrawl_search_rate_limit_keyless_points_at_ip_cap(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

    def fake_post(*args, **kwargs):
        return _FakeFirecrawlResponse(
            {"success": False, "error": "Rate limit exceeded"}, status_code=429
        )

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)

    with pytest.raises(RuntimeError) as excinfo:
        _new_tool()._search_with_firecrawl(query="x", max_results=1)

    message = str(excinfo.value)
    assert "429" in message
    assert "Rate limit exceeded" in message
    assert "per IP" in message
    assert "FIRECRAWL_API_KEY" in message


@pytest.mark.unit
def test_firecrawl_search_surfaces_402_out_of_credits(monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test-key")

    def fake_post(*args, **kwargs):
        return _FakeFirecrawlResponse(
            {"success": False, "error": "Payment Required: Insufficient credits"},
            status_code=402,
        )

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)

    with pytest.raises(RuntimeError) as excinfo:
        _new_tool()._search_with_firecrawl(query="x", max_results=1)

    message = str(excinfo.value)
    assert "402" in message
    assert "Insufficient credits" in message
    assert "unset FIRECRAWL_API_KEY" not in message


@pytest.mark.unit
def test_firecrawl_search_rate_limit_with_key_does_not_blame_keyless_cap(
    monkeypatch,
):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test-key")

    def fake_post(*args, **kwargs):
        return _FakeFirecrawlResponse(
            {"success": False, "error": "Rate limit exceeded"}, status_code=429
        )

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)

    with pytest.raises(RuntimeError) as excinfo:
        _new_tool()._search_with_firecrawl(query="x", max_results=1)

    message = str(excinfo.value)
    assert "429" in message
    assert "per IP" not in message
    assert "set FIRECRAWL_API_KEY" not in message


@pytest.mark.unit
def test_firecrawl_search_raises_on_http_error_status(monkeypatch):
    """Firecrawl reports auth failures via the status code (401 + success:false),
    confirmed live on 2026-09-21. The body's error text must survive into the
    RuntimeError so provider_errors shows the real reason."""
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-wrong")

    def fake_post(*args, **kwargs):
        return _FakeFirecrawlResponse(
            {"success": False, "error": "Unauthorized: Invalid token"},
            status_code=401,
        )

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)

    with pytest.raises(RuntimeError, match="401.*Unauthorized: Invalid token"):
        _new_tool()._search_with_firecrawl(query="x", max_results=1)


@pytest.mark.unit
def test_firecrawl_search_surfaces_validation_details_on_400(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

    def fake_post(*args, **kwargs):
        return _FakeFirecrawlResponse(
            {
                "success": False,
                "error": "Invalid request body",
                "details": [{"code": "unrecognized_keys", "keys": ["foo"]}],
            },
            status_code=400,
        )

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)

    with pytest.raises(
        RuntimeError, match="400.*Invalid request body.*unrecognized_keys"
    ):
        _new_tool()._search_with_firecrawl(query="x", max_results=1)


@pytest.mark.unit
def test_firecrawl_search_raises_on_non_json_error_body(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

    class _HtmlErrorResponse(_FakeFirecrawlResponse):
        def json(self):
            raise ValueError("not json")

    monkeypatch.setattr(
        web_search_tool.requests,
        "post",
        lambda *a, **k: _HtmlErrorResponse(None, status_code=502, reason="Bad Gateway"),
    )

    with pytest.raises(RuntimeError, match="502.*Bad Gateway"):
        _new_tool()._search_with_firecrawl(query="x", max_results=1)


@pytest.mark.unit
@pytest.mark.parametrize(
    "payload",
    [
        {"success": False, "error": "something went wrong"},
        {"success": True},
        {"success": True, "data": {"web": {}}},
        {"success": True, "data": []},
        "not a dict",
    ],
)
def test_firecrawl_search_rejects_error_or_malformed_bodies(monkeypatch, payload):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

    def fake_post(*args, **kwargs):
        return _FakeFirecrawlResponse(payload)

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)

    with pytest.raises(RuntimeError):
        _new_tool()._search_with_firecrawl(query="x", max_results=1)


@pytest.mark.unit
def test_firecrawl_search_skips_malformed_items_and_reassigns_ranks(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

    def fake_post(*args, **kwargs):
        return _FakeFirecrawlResponse(
            {
                "success": True,
                "data": {
                    "web": [
                        None,
                        {},
                        {"url": ""},
                        {"title": None, "url": "https://example.com/a", "position": 7},
                        {"title": 12, "url": "https://example.com/b", "description": 3},
                    ]
                },
            }
        )

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)

    results = _new_tool()._search_with_firecrawl(query="x", max_results=10)

    assert results == [
        {"title": "", "url": "https://example.com/a", "snippet": "", "rank": 1},
        {"title": "", "url": "https://example.com/b", "snippet": "", "rank": 2},
    ]


@pytest.mark.unit
def test_firecrawl_search_truncates_to_max_results(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

    def fake_post(*args, **kwargs):
        return _FakeFirecrawlResponse(
            {
                "success": True,
                "data": {
                    "web": [
                        {"title": f"R{i}", "url": f"https://example.com/{i}"}
                        for i in range(10)
                    ]
                },
            }
        )

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)

    results = _new_tool()._search_with_firecrawl(query="x", max_results=3)

    assert len(results) == 3


@pytest.mark.unit
def test_firecrawl_backend_reports_success(monkeypatch):
    tool = _new_tool()
    monkeypatch.setattr(
        tool,
        "_search_with_firecrawl",
        lambda **kwargs: [
            {
                "title": "Firecrawl result",
                "url": "https://example.com",
                "snippet": "excerpt",
                "rank": 1,
            }
        ],
    )

    result = tool.run(
        {
            "query": "test query",
            "backend": "firecrawl",
            "region": "us-en",
            "safesearch": "moderate",
        }
    )

    assert result["status"] == "success"
    assert result["data"]["backend_used"] == "firecrawl"
    assert result["data"]["attempted_backends"] == ["firecrawl"]
    assert "api.firecrawl.dev" in result["data"]["provider_notice"]
    assert "patient-identifying" in result["data"]["provider_notice"]


@pytest.mark.unit
def test_firecrawl_backend_receives_clamped_max_results(monkeypatch):
    tool = _new_tool()
    captured = {}

    def fake_firecrawl(**kwargs):
        captured.update(kwargs)
        return [{"title": "R", "url": "https://example.com", "snippet": "", "rank": 1}]

    monkeypatch.setattr(tool, "_search_with_firecrawl", fake_firecrawl)

    result = tool.run(
        {"query": "test query", "backend": "firecrawl", "max_results": 80}
    )

    assert result["status"] == "success"
    assert captured["max_results"] == 50


@pytest.mark.unit
def test_firecrawl_backend_accepts_non_default_region_and_safesearch(monkeypatch):
    """Unlike Parallel and SerpBase, Firecrawl takes both controls, so neither
    is rejected up front; they are forwarded to the provider method."""
    tool = _new_tool()
    captured = {}

    def fake_firecrawl(**kwargs):
        captured.update(kwargs)
        return [{"title": "R", "url": "https://example.com", "snippet": "", "rank": 1}]

    monkeypatch.setattr(tool, "_search_with_firecrawl", fake_firecrawl)

    result = tool.run(
        {
            "query": "test query",
            "backend": "firecrawl",
            "region": "uk-en",
            "safesearch": "on",
        }
    )

    assert result["status"] == "success"
    assert result["data"]["backend_used"] == "firecrawl"
    assert captured["region"] == "uk-en"
    assert captured["safesearch"] == "on"


@pytest.mark.unit
def test_firecrawl_run_forwards_controls_to_request_body(monkeypatch):
    """End-to-end through run(): only requests.post is faked, so the clamp,
    region mapping, and safesearch handling are exercised together."""
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    captured = {}

    def fake_post(url, *, json=None, headers=None, timeout=None):
        captured["json"] = json
        return _FakeFirecrawlResponse(_FIRECRAWL_LIVE_RESPONSE)

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)

    result = _new_tool().run(
        {
            "query": "x",
            "backend": "firecrawl",
            "region": "uk-en",
            "safesearch": "off",
            "max_results": 80,
        }
    )

    body = captured["json"]
    assert body["country"] == "GB"
    assert body["limit"] == 50
    assert "safe" not in body
    assert body["highlights"] is False
    assert body["sources"] == ["web"]
    assert result["status"] == "success"
    assert result["data"]["backend_used"] == "firecrawl"


@pytest.mark.unit
def test_firecrawl_run_empty_results_fall_back_without_provider_error(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    tool = _new_tool()

    def fake_post(url, *, json=None, headers=None, timeout=None):
        assert url == "https://api.firecrawl.dev/v2/search"
        return _FakeFirecrawlResponse({"success": True, "data": {"web": []}})

    monkeypatch.setattr(web_search_tool.requests, "post", fake_post)
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

    result = tool.run({"query": "x", "backend": "firecrawl"})

    data = result["data"]
    assert result["status"] == "success"
    assert data["attempted_backends"][0] == "firecrawl"
    assert data["backend_used"] != "firecrawl"
    assert "firecrawl" not in data.get("provider_errors", {})
    assert data["provider_notice"] == web_search_tool.FIRECRAWL_PROVIDER_NOTICE


@pytest.mark.unit
def test_firecrawl_backend_failure_falls_back_to_auto(monkeypatch):
    tool = _new_tool()

    def firecrawl_fail(**kwargs):
        raise RuntimeError("firecrawl failed")

    monkeypatch.setattr(tool, "_search_with_firecrawl", firecrawl_fail)
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

    result = tool.run({"query": "test query", "backend": "firecrawl"})

    assert result["status"] == "success"
    assert result["data"]["backend_used"] == "auto"
    assert result["data"]["attempted_backends"] == ["firecrawl", "auto"]
    assert result["data"]["provider_errors"]["firecrawl"] == "firecrawl failed"
    assert "api.firecrawl.dev" in result["data"]["provider_notice"]


@pytest.mark.unit
def test_firecrawl_all_provider_failure_keeps_disclosure(monkeypatch):
    tool = _new_tool()

    def always_fail(**kwargs):
        raise RuntimeError("simulated provider failure")

    monkeypatch.setattr(tool, "_search_with_firecrawl", always_fail)
    monkeypatch.setattr(tool, "_search_with_ddgs", always_fail)
    monkeypatch.setattr(tool, "_search_with_duckduckgo_html", always_fail)
    monkeypatch.setattr(tool, "_search_with_wikipedia_api", always_fail)

    result = tool.run({"query": "test query", "backend": "firecrawl"})

    assert result["status"] == "success"
    assert result["data"]["backend_used"] == "none"
    assert result["data"]["all_providers_failed"] is True
    assert result["data"]["attempted_backends"][0] == "firecrawl"
    assert "api.firecrawl.dev" in result["data"]["provider_notice"]


@pytest.mark.unit
def test_auto_backend_does_not_call_firecrawl(monkeypatch):
    tool = _new_tool()

    def unexpected_call(**kwargs):
        raise AssertionError("Firecrawl must remain opt-in")

    monkeypatch.setattr(tool, "_search_with_firecrawl", unexpected_call)
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
    assert "firecrawl" not in result["data"]["attempted_backends"]
    assert "provider_notice" not in result["data"]


@pytest.mark.unit
def test_api_documentation_search_forwards_firecrawl_backend(monkeypatch):
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
            "firecrawl",
            ["firecrawl"],
            None,
            {},
        )

    monkeypatch.setattr(tool, "_search_with_fallback", fake_search)
    monkeypatch.setattr(web_search_tool.time, "sleep", lambda _: None)

    result = tool.run(
        {"query": "FastMCP Client", "focus": "api_docs", "backend": "firecrawl"}
    )

    assert captured["backend"] == "firecrawl"
    assert result["status"] == "success"
    assert result["data"]["backend_used"] == "firecrawl"
    assert "api.firecrawl.dev" in result["data"]["provider_notice"]


@pytest.mark.integration
@pytest.mark.network
def test_firecrawl_backend_live_keyless_call(monkeypatch):
    """Opt-in live check against the real endpoint (excluded by default via the
    `network` marker). Always runs keyless so a developer's real key is never
    spent by this test; the authenticated path is covered by unit tests.

    Skips whenever Firecrawl did not serve the search, whatever the reason:
    the keyless per-IP cap (429), an exhausted account (402), a blocked or
    shared runner IP, or a provider outage. The backend falls back to DDGS in
    all of those cases, which is correct behaviour and not something this test
    should report as a failure."""
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    tool = _new_tool()

    result = tool.run(
        {"query": "python asyncio event loop", "backend": "firecrawl", "max_results": 3}
    )

    data = result["data"]
    if data["backend_used"] != "firecrawl":
        reason = data.get("provider_errors", {}).get(
            "firecrawl", "no provider error reported"
        )
        pytest.skip(f"Firecrawl did not serve this search: {reason}")

    assert result["status"] == "success"
    assert 1 <= data["total_results"] <= 3
    first = data["results"][0]
    assert first["url"].startswith("http")
    assert first["rank"] == 1
    assert "api.firecrawl.dev" in data["provider_notice"]
