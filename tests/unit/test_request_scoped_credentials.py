"""Tests for native request-scoped ToolUniverse credentials."""

import asyncio
import ast
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
from tooluniverse.provider_rate_limit import ProviderRateLimiter
from tooluniverse.disgenet_tool import DisGeNETTool
from tooluniverse.omim_tool import OMIMTool
from tooluniverse.pubmed_tool import PubMedRESTTool
from tooluniverse.semantic_scholar_tool import SemanticScholarTool
from tooluniverse.umls_tool import UMLSRESTTool


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


class _ConstructorCredentialTool(BaseTool):
    instances = 0

    def __init__(self, tool_config):
        super().__init__(tool_config)
        type(self).instances += 1
        self.instance_number = type(self).instances
        self.bound_credential = self.credential("TEST_API_KEY", "process-fallback")

    def run(self, arguments=None, **kwargs):
        return {
            "credential": self.bound_credential,
            "instance_number": self.instance_number,
        }


_ECHO_CONFIG = {
    "name": "CredentialEchoTest",
    "type": "_CredentialEchoTool",
    "description": "Echo a request-scoped test credential",
    "parameter": {
        "type": "object",
        "properties": {"value": {"type": "integer"}},
    },
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
def test_request_scope_masks_credentials_but_not_infrastructure_config(monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "process-secret")
    monkeypatch.setenv("BOLTZ_MCP_SERVER_HOST", "https://internal.example")
    tu = ToolUniverse(tool_files={}, keep_default_tools=False)

    with credential_context({}):
        assert tu._get_api_key("TEST_API_KEY") is None
        assert tu._get_api_key("BOLTZ_MCP_SERVER_HOST") == "https://internal.example"


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
def test_semantic_scholar_uses_credential_partitioned_rate_limit(monkeypatch):
    tool = SemanticScholarTool({"name": "SemanticScholar_search_papers"})
    calls = []
    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.enforce_provider_rate_limit",
        lambda provider, credential, rps: calls.append((provider, credential, rps)),
    )

    tool._enforce_rate_limit("tenant-a")
    tool._enforce_rate_limit("")

    assert calls == [
        ("semantic_scholar", "tenant-a", 1.0),
        ("semantic_scholar", "", None),
    ]


@pytest.mark.unit
def test_provider_rate_limiter_isolates_credentials_without_retaining_secrets():
    now = [0.0]
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    limiter = ProviderRateLimiter(
        max_buckets=2,
        clock=lambda: now[0],
        sleep=sleep,
        digest_secret=b"x" * 32,
    )

    limiter.wait("semantic_scholar", "tenant-a-secret", 1.0)
    limiter.wait("semantic_scholar", "tenant-a-secret", 1.0)
    limiter.wait("semantic_scholar", "tenant-b-secret", 1.0)
    limiter.wait("semantic_scholar", "tenant-c-secret", 1.0)

    assert sleeps == [1.0]
    assert len(limiter._next_slots) == 2
    assert all(
        b"tenant" not in credential_digest
        for _, credential_digest in limiter._next_slots
    )


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
            "rate_limit": {
                "provider": "example",
                "credential": "TEST_API_KEY",
                "authenticated_rps": 2.0,
                "anonymous_rps": None,
            },
        },
        "parameter": {"type": "object", "properties": {}},
    }
    tool = BaseRESTTool(config)
    captured_headers = []
    rate_limit_calls = []

    def fake_request(*args, **kwargs):
        captured_headers.append(kwargs["headers"])
        response = _FakeResponse()
        response.json = lambda: {"ok": True}
        return response

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", fake_request)
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.enforce_provider_rate_limit",
        lambda provider, credential, rps: rate_limit_calls.append(
            (provider, credential, rps)
        ),
    )

    with credential_context({"TEST_API_KEY": "tenant-key"}):
        assert tool.run({})["data"]["ok"] is True
    with credential_context({}):
        assert tool.run({})["data"]["ok"] is True

    assert captured_headers == [{"x-api-key": "tenant-key"}, {}]
    assert rate_limit_calls == [
        ("example", "tenant-key", 2.0),
        ("example", "", None),
    ]


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
        assert config["fields"]["rate_limit"] == {
            "provider": "semantic_scholar",
            "credential": "SEMANTIC_SCHOLAR_API_KEY",
            "authenticated_rps": 1.0,
            "anonymous_rps": None,
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


@pytest.mark.unit
def test_parallel_batch_preserves_request_credentials():
    _CredentialEchoTool.calls = 0
    tu = _make_tooluniverse()

    with credential_context({"TEST_API_KEY": "batch-tenant"}):
        results = tu.run(
            [
                {"name": "CredentialEchoTest", "arguments": {"value": 1}},
                {"name": "CredentialEchoTest", "arguments": {"value": 2}},
            ],
            verbose=False,
            max_workers=2,
        )

    assert [result["credential"] for result in results] == [
        "batch-tenant",
        "batch-tenant",
    ]
    assert current_credentials() is None


@pytest.mark.unit
def test_batch_bypasses_shared_cache_inside_credential_context():
    _CredentialEchoTool.calls = 0
    tu = _make_tooluniverse()

    class _FailIfUsedCache:
        enabled = True

        def __getattr__(self, name):
            raise AssertionError(f"credential-scoped batch used shared cache: {name}")

    tu.cache_manager = _FailIfUsedCache()

    with credential_context({"TEST_API_KEY": "batch-tenant"}):
        results = tu.run(
            [{"name": "CredentialEchoTest", "arguments": {"value": 1}}],
            verbose=False,
            use_cache=True,
            max_workers=2,
        )

    assert results == [{"credential": "batch-tenant", "calls": 1}]


@pytest.mark.unit
def test_required_key_tool_can_be_activated_by_request_credentials(tmp_path):
    config = {
        **_ECHO_CONFIG,
        "name": "CredentialGatedEchoTest",
        "required_api_keys": ["TEST_API_KEY"],
    }
    config_path = tmp_path / "gated_tools.json"
    config_path.write_text(json.dumps([config]))

    tu = ToolUniverse(
        tool_files={"gated": str(config_path)},
        keep_default_tools=False,
    )
    tu.register_custom_tool(_CredentialEchoTool)
    tu.load_tools()

    assert "CredentialGatedEchoTest" not in tu.all_tool_dict
    assert tu._excluded_api_key_tools["CredentialGatedEchoTest"] == ["TEST_API_KEY"]

    result = tu.run_one_function(
        {"name": "CredentialGatedEchoTest", "arguments": {}},
        validate=False,
        credentials={"TEST_API_KEY": "tenant-key"},
    )

    assert result["credential"] == "tenant-key"
    assert "CredentialGatedEchoTest" in tu.all_tool_dict

    missing_result = tu.run_one_function(
        {"name": "CredentialGatedEchoTest", "arguments": {}},
        validate=False,
        credentials={},
    )
    assert missing_result["status"] == "error"
    assert "TEST_API_KEY" in missing_result["error"]


@pytest.mark.unit
def test_any_of_key_tool_can_be_activated_by_one_request_credential(tmp_path):
    config = {**_ECHO_CONFIG, "name": "CredentialAnyOfEchoTest"}
    config_path = tmp_path / "alternative_tools.json"
    config_path.write_text(json.dumps([config]))
    tu = ToolUniverse(
        tool_files={"alternative": str(config_path)},
        keep_default_tools=False,
    )
    tu.register_custom_tool(_CredentialEchoTool)
    tu._excluded_any_api_key_tools["CredentialAnyOfEchoTest"] = [
        "TEST_API_KEY",
        "ALTERNATIVE_API_KEY",
    ]

    result = tu.run_one_function(
        {"name": "CredentialAnyOfEchoTest", "arguments": {}},
        validate=False,
        credentials={"ALTERNATIVE_API_KEY": "available"},
    )

    assert result["credential"] is None
    assert "CredentialAnyOfEchoTest" in tu.all_tool_dict


@pytest.mark.unit
def test_clear_tools_clears_credential_activation_metadata():
    tu = _make_tooluniverse()
    tu._excluded_api_key_tools["required"] = ["REQUIRED_KEY"]
    tu._excluded_any_api_key_tools["alternative"] = ["ONE_KEY", "TWO_KEY"]

    tu.clear_tools()

    assert tu._excluded_api_key_tools == {}
    assert tu._excluded_any_api_key_tools == {}


@pytest.mark.unit
def test_request_credentials_do_not_reuse_constructor_bound_tool_instances():
    _ConstructorCredentialTool.instances = 0
    config = {
        "name": "ConstructorCredentialTest",
        "type": "_ConstructorCredentialTool",
        "description": "Bind a credential in the constructor",
        "parameter": {"type": "object", "properties": {}},
    }
    tu = ToolUniverse(tool_files={}, keep_default_tools=False)
    tu.register_custom_tool(_ConstructorCredentialTool, tool_config=config)

    process_result = tu.run_one_function(
        {"name": "ConstructorCredentialTest", "arguments": {}},
        validate=False,
    )
    tenant_a = tu.run_one_function(
        {"name": "ConstructorCredentialTest", "arguments": {}},
        validate=False,
        credentials={"TEST_API_KEY": "tenant-a"},
    )
    tenant_b = tu.run_one_function(
        {"name": "ConstructorCredentialTest", "arguments": {}},
        validate=False,
        credentials={"TEST_API_KEY": "tenant-b"},
    )

    assert process_result["credential"] == "process-fallback"
    assert tenant_a["credential"] == "tenant-a"
    assert tenant_b["credential"] == "tenant-b"
    assert (
        len(
            {
                process_result["instance_number"],
                tenant_a["instance_number"],
                tenant_b["instance_number"],
            }
        )
        == 3
    )


@pytest.mark.unit
def test_runtime_tools_do_not_read_credentials_directly_from_environment():
    source_root = Path(__file__).parents[2] / "src" / "tooluniverse"
    excluded_paths = {
        "http_client.py",  # ToolUniverse service-to-service authentication
        "server_security.py",  # MCP server ingress authentication
    }
    findings = []

    for path in source_root.rglob("*.py"):
        relative = path.relative_to(source_root)
        if (
            relative.parts[0] in {"database_setup", "remote"}
            or str(relative) in excluded_paths
        ):
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            first_arg = node.args[0]
            if not isinstance(first_arg, ast.Constant) or not isinstance(
                first_arg.value, str
            ):
                continue
            credential_name = first_arg.value
            if not credential_name.endswith(
                (
                    "KEY",
                    "TOKEN",
                    "SECRET",
                    "PASSWORD",
                    "USERNAME",
                    "EMAIL",
                    "JWT",
                )
            ):
                continue
            function_name = ast.unparse(node.func)
            if "os.getenv" in function_name or "os.environ" in function_name:
                findings.append(f"{relative}:{node.lineno}:{credential_name}")

    assert findings == [], (
        "Runtime tools must use BaseTool.credential()/get_credential() so hosted BYOK "
        f"stays request-scoped; direct environment reads found: {findings}"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("tool", "credential_name", "arguments", "expected_location"),
    [
        (
            OMIMTool({"name": "OMIM", "parameter": {}}),
            "OMIM_API_KEY",
            {"operation": "search", "query": "BRCA1"},
            ("params", "apiKey"),
        ),
        (
            DisGeNETTool({"name": "DisGeNET", "parameter": {}}),
            "DISGENET_API_KEY",
            {"operation": "get_gda", "gene": "BRCA1"},
            ("headers", "Authorization"),
        ),
        (
            UMLSRESTTool(
                {
                    "name": "UMLS",
                    "fields": {"endpoint": "/search/current"},
                }
            ),
            "UMLS_API_KEY",
            {"query": "diabetes"},
            ("params", "apiKey"),
        ),
    ],
)
def test_provider_tools_resolve_credentials_per_request(
    monkeypatch, tool, credential_name, arguments, expected_location
):
    captured = []

    class Response(_FakeResponse):
        def raise_for_status(self):
            return None

        def json(self):
            if isinstance(tool, DisGeNETTool):
                return {"payload": [], "warnings": []}
            if isinstance(tool, OMIMTool):
                return {"omim": {"searchResponse": {"entryList": []}}}
            return {"result": {"results": []}}

    def fake_get(*args, **kwargs):
        captured.append(kwargs)
        return Response()

    module_name = tool.__class__.__module__
    monkeypatch.setattr(f"{module_name}.requests.get", fake_get)

    with credential_context({credential_name: "tenant-one"}):
        assert tool.run(dict(arguments))["status"] == "success"
    with credential_context({credential_name: "tenant-two"}):
        assert tool.run(dict(arguments))["status"] == "success"

    container, key = expected_location
    assert [call[container][key] for call in captured] == [
        "tenant-one",
        "tenant-two",
    ]


@pytest.mark.unit
def test_pubmed_resolves_ncbi_key_per_request(monkeypatch):
    tool = PubMedRESTTool(
        {
            "name": "PubMedTest",
            "fields": {"endpoint": "https://example.test/esearch.fcgi"},
            "parameter": {"type": "object", "properties": {}},
        }
    )
    captured = []
    monkeypatch.setattr(tool, "_enforce_rate_limit", lambda api_key: None)

    def fake_request(*args, **kwargs):
        captured.append(kwargs["params"].get("api_key"))
        response = _FakeResponse()
        response.url = "https://example.test"
        response.json = lambda: {"result": {}}
        return response

    monkeypatch.setattr("tooluniverse.pubmed_tool.request_with_retry", fake_request)

    with credential_context({"NCBI_API_KEY": "ncbi-one"}):
        tool.run({})
    with credential_context({"NCBI_API_KEY": "ncbi-two"}):
        tool.run({})
    with credential_context({}):
        tool.run({})

    assert captured == ["ncbi-one", "ncbi-two", None]
