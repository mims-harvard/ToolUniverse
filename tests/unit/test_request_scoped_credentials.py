"""Tests for native request-scoped ToolUniverse credentials."""

import asyncio
import json
from concurrent.futures import as_completed
from pathlib import Path

import pytest

from tooluniverse import ToolUniverse, credential_context
from tooluniverse.base_tool import BaseTool
from tooluniverse.base_rest_tool import BaseRESTTool
from tooluniverse.credentials import (
    ContextThreadPoolExecutor,
    current_credentials,
    get_credential,
    has_credential_context,
)
from tooluniverse.semantic_scholar_tool import SemanticScholarTool


class _FakeResponse:
    status_code = 200
    reason = "OK"
    headers = {}

    def json(self):
        return {"data": []}


class _CredentialEchoTool(BaseTool):
    calls = 0

    def run(self, arguments=None, **kwargs):
        type(self).calls += 1
        return {
            "credential": self.credential("TEST_API_KEY", "process-fallback"),
            "calls": type(self).calls,
        }


_ECHO_CONFIG = {
    "name": "CredentialEchoTest",
    "type": "_CredentialEchoTool",
    "description": "Echo a request-scoped test credential",
    "parameter": {"type": "object", "properties": {}},
}


def _make_tooluniverse():
    tu = ToolUniverse(tool_files={}, keep_default_tools=False)
    tu.register_custom_tool(_CredentialEchoTool, tool_config=_ECHO_CONFIG)
    return tu


@pytest.mark.unit
def test_credential_context_is_fail_closed_and_restores_parent():
    assert get_credential("KEY", "environment") == "environment"
    assert current_credentials() is None
    assert has_credential_context() is False

    source = {"KEY": "outer"}
    with credential_context(source) as scoped:
        source["KEY"] = "mutated-after-entry"
        assert scoped["KEY"] == "outer"
        assert get_credential("KEY", "environment") == "outer"
        assert get_credential("MISSING", "environment") is None
        assert has_credential_context() is True

        with credential_context({"KEY": "inner"}):
            assert get_credential("KEY", "environment") == "inner"

        assert get_credential("KEY", "environment") == "outer"

    assert current_credentials() is None
    assert get_credential("KEY", "environment") == "environment"

    with credential_context({}):
        assert get_credential("KEY", "environment") is None


@pytest.mark.unit
@pytest.mark.parametrize(
    "credentials",
    [None, [], {"": "value"}, {1: "value"}, {"KEY": 1}],
)
def test_credential_context_rejects_invalid_mappings(credentials):
    with pytest.raises(TypeError):
        with credential_context(credentials):
            pass


@pytest.mark.unit
def test_context_thread_pool_executor_isolates_concurrent_credentials():
    futures = {}
    with ContextThreadPoolExecutor(max_workers=12) as executor:
        for index in range(100):
            expected = f"tenant-{index}"
            with credential_context({"TEST_API_KEY": expected}):
                future = executor.submit(get_credential, "TEST_API_KEY")
            futures[future] = expected

        for future in as_completed(futures):
            assert future.result() == futures[future]

    assert current_credentials() is None


@pytest.mark.unit
def test_semantic_scholar_resolves_api_key_per_call(monkeypatch):
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "process-key")
    tool = SemanticScholarTool({"name": "SemanticScholar_search_papers"})
    monkeypatch.setattr(tool, "_enforce_rate_limit", lambda has_api_key: None)

    captured_headers = []

    def fake_request(*args, **kwargs):
        captured_headers.append(kwargs.get("headers", {}))
        return _FakeResponse()

    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.request_with_retry", fake_request
    )

    tool.run({"query": "fallback", "limit": 1})
    with credential_context({"SEMANTIC_SCHOLAR_API_KEY": "tenant-a"}):
        tool.run({"query": "first", "limit": 1})
    with credential_context({"SEMANTIC_SCHOLAR_API_KEY": "tenant-b"}):
        tool.run({"query": "second", "limit": 1})
    with credential_context({}):
        tool.run({"query": "anonymous", "limit": 1})

    assert captured_headers == [
        {"x-api-key": "process-key"},
        {"x-api-key": "tenant-a"},
        {"x-api-key": "tenant-b"},
        {},
    ]


@pytest.mark.unit
def test_semantic_scholar_does_not_serialize_authenticated_tenants(monkeypatch):
    tool = SemanticScholarTool({"name": "SemanticScholar_search_papers"})
    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.time.sleep",
        lambda seconds: pytest.fail("authenticated request was process-throttled"),
    )

    tool._enforce_rate_limit(has_api_key=True)


@pytest.mark.unit
def test_semantic_scholar_abstract_enrichment_uses_same_scoped_key(monkeypatch):
    tool = SemanticScholarTool({"name": "SemanticScholar_search_papers"})
    monkeypatch.setattr(tool, "_enforce_rate_limit", lambda has_api_key: None)

    captured_headers = []

    def fake_request(session, method, url, **kwargs):
        captured_headers.append(kwargs.get("headers", {}))
        if url.endswith("/paper/search"):
            response = _FakeResponse()
            response.json = lambda: {
                "data": [{"paperId": "paper-1", "title": "Test", "abstract": None}]
            }
            return response
        response = _FakeResponse()
        response.json = lambda: {"abstract": "Enriched"}
        return response

    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.request_with_retry", fake_request
    )

    with credential_context({"SEMANTIC_SCHOLAR_API_KEY": "tenant-key"}):
        result = tool.run({"query": "test", "limit": 1, "include_abstract": True})

    assert result["status"] == "success"
    assert result["data"][0]["abstract"] == "Enriched"
    assert captured_headers == [
        {"x-api-key": "tenant-key"},
        {"x-api-key": "tenant-key"},
    ]


@pytest.mark.unit
def test_base_rest_optional_auth_header_uses_request_credential(monkeypatch):
    config = {
        "name": "OptionalAuthTest",
        "type": "BaseRESTTool",
        "fields": {
            "endpoint": "https://example.test/items",
            "auth_header": {
                "env_var": "TEST_API_KEY",
                "header": "x-api-key",
                "required": False,
            },
        },
        "parameter": {"type": "object", "properties": {}},
    }
    tool = BaseRESTTool(config)
    captured_headers = []

    def fake_request(*args, **kwargs):
        captured_headers.append(kwargs["headers"])
        response = _FakeResponse()
        response.json = lambda: {"ok": True}
        return response

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", fake_request)

    with credential_context({"TEST_API_KEY": "tenant-key"}):
        assert tool.run({})["data"]["ok"] is True
    with credential_context({}):
        assert tool.run({})["data"]["ok"] is True

    assert captured_headers == [{"x-api-key": "tenant-key"}, {}]


@pytest.mark.unit
def test_all_semantic_scholar_rest_tools_declare_optional_scoped_auth():
    config_path = (
        Path(__file__).parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "semantic_scholar_ext_tools.json"
    )
    configs = json.loads(config_path.read_text())

    assert configs
    for config in configs:
        assert config["fields"]["auth_header"] == {
            "env_var": "SEMANTIC_SCHOLAR_API_KEY",
            "header": "x-api-key",
            "required": False,
        }


@pytest.mark.unit
def test_run_one_function_accepts_credentials_and_disables_shared_cache():
    _CredentialEchoTool.calls = 0
    tu = _make_tooluniverse()

    class _FailIfUsedCache:
        enabled = True

        def __getattr__(self, name):
            raise AssertionError(
                f"credential-scoped execution used shared cache: {name}"
            )

    tu.cache_manager = _FailIfUsedCache()
    function_call = {"name": "CredentialEchoTest", "arguments": {}}

    first = tu.run_one_function(
        function_call.copy(),
        use_cache=True,
        validate=False,
        credentials={"TEST_API_KEY": "tenant-a"},
    )
    second = tu.run_one_function(
        function_call.copy(),
        use_cache=True,
        validate=False,
        credentials={"TEST_API_KEY": "tenant-b"},
    )

    assert first == {"credential": "tenant-a", "calls": 1}
    assert second == {"credential": "tenant-b", "calls": 2}
    assert current_credentials() is None


@pytest.mark.unit
def test_run_one_function_async_accepts_credentials():
    _CredentialEchoTool.calls = 0
    tu = _make_tooluniverse()

    result = asyncio.run(
        tu.run_one_function_async(
            {"name": "CredentialEchoTest", "arguments": {}},
            validate=False,
            credentials={"TEST_API_KEY": "async-tenant"},
        )
    )

    assert result == {"credential": "async-tenant", "calls": 1}
    assert current_credentials() is None
