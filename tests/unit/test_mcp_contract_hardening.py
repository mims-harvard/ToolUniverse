import copy
from unittest.mock import AsyncMock, patch

import pytest

from tooluniverse.mcp_client_tool import (
    BaseMCPClient,
    MCPAutoLoaderTool,
    MCPClientTool,
    MCPProxyTool,
)


CONTRACT = {
    "name": "reviewed_tool",
    "description": "Locally reviewed description.",
    "inputSchema": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
    "outputSchema": {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
        "additionalProperties": False,
    },
    "annotations": {
        "readOnlyHint": True,
        "destructiveHint": False,
    },
}


def _proxy_config(**overrides):
    config = {
        "name": "reviewed_reviewed_tool",
        "description": "A reviewed MCP proxy.",
        "type": "MCPProxyTool",
        "server_url": "https://example.test/mcp",
        "target_tool_name": "reviewed_tool",
        "return_schema": copy.deepcopy(CONTRACT["outputSchema"]),
        "normalize_mcp_result": True,
        "require_structured_content": True,
        "mcp_structured_error_field": "error",
        "mcp_contract_sha256": "abc123",
    }
    config.update(overrides)
    return config


def _loader_config(**overrides):
    reviewed_manifest = {
        "name": CONTRACT["name"],
        "description": CONTRACT["description"],
        "contract_sha256": MCPAutoLoaderTool._contract_sha256(CONTRACT),
        "annotations": copy.deepcopy(CONTRACT["annotations"]),
    }
    config = {
        "name": "reviewed_loader",
        "description": "A reviewed MCP loader.",
        "type": "MCPAutoLoaderTool",
        "server_url": "https://example.test/mcp",
        "selected_tools": ["reviewed_tool"],
        "tool_contracts": [reviewed_manifest],
        "strict_tool_contracts": True,
        "normalize_mcp_result": True,
        "require_structured_content": True,
        "mcp_structured_error_field": "error",
        "http_headers_from_env": {
            "Authorization": {
                "env": "TEST_MCP_TOKEN",
                "prefix": "Bearer ",
            }
        },
    }
    config.update(overrides)
    return config


def test_http_headers_are_resolved_from_environment_without_storing_secret(
    monkeypatch,
):
    monkeypatch.setenv("TEST_MCP_TOKEN", "secret-value")
    client = BaseMCPClient(
        "https://example.test/mcp",
        http_headers_from_env={
            "Authorization": {
                "env": "TEST_MCP_TOKEN",
                "prefix": "Bearer ",
            }
        },
    )

    assert client._resolve_http_headers() == {"Authorization": "Bearer secret-value"}
    assert "secret-value" not in repr(client.http_headers_from_env)


@pytest.mark.parametrize(
    "mapping",
    [
        {"Bad\nHeader": "TEST_MCP_TOKEN"},
        {"Authorization": "../NOT_AN_ENV"},
        {"Authorization": {"env": "TEST_MCP_TOKEN", "prefix": "Bad\rPrefix"}},
    ],
)
def test_http_header_configuration_rejects_injection(monkeypatch, mapping):
    monkeypatch.setenv("TEST_MCP_TOKEN", "secret-value")
    client = BaseMCPClient(
        "https://example.test/mcp",
        http_headers_from_env=mapping,
    )

    with pytest.raises(ValueError):
        client._resolve_http_headers()


@pytest.mark.asyncio
async def test_resolved_auth_header_is_passed_to_streamable_http(
    monkeypatch,
):
    monkeypatch.setenv("TEST_MCP_TOKEN", "secret-value")
    client = MCPClientTool(
        {
            "name": "authenticated_client",
            "description": "Authenticated MCP client.",
            "server_url": "https://example.test/mcp",
            "http_headers_from_env": {"X-GI-Key": {"env": "TEST_MCP_TOKEN"}},
        }
    )
    mock_session = AsyncMock()
    mock_session.list_tools.return_value = {"tools": []}
    mock_read_stream = AsyncMock()
    mock_write_stream = AsyncMock()

    with (
        patch("tooluniverse.mcp_client_tool.streamablehttp_client") as mock_stream,
        patch("tooluniverse.mcp_client_tool.ClientSession") as mock_session_class,
    ):
        mock_stream.return_value.__aenter__.return_value = (
            mock_read_stream,
            mock_write_stream,
            None,
        )
        mock_session_class.return_value.__aenter__.return_value = mock_session

        assert await client.list_tools() == []

    mock_stream.assert_called_once_with(
        "https://example.test/mcp",
        headers={"X-GI-Key": "secret-value"},
        timeout=600,
    )


def test_proxy_normalizes_and_validates_structured_content():
    proxy = MCPProxyTool(_proxy_config())

    result = proxy._normalize_result(
        {
            "content": [{"type": "text", "text": "answer"}],
            "structuredContent": {"answer": "ok"},
            "isError": False,
        }
    )

    assert result == {
        "status": "success",
        "data": {"answer": "ok"},
        "provenance": {
            "protocol": "mcp",
            "tool": "reviewed_tool",
            "contract_sha256": "abc123",
        },
    }


def test_proxy_maps_mcp_errors_and_rejects_invalid_or_missing_output():
    proxy = MCPProxyTool(_proxy_config())

    remote_error = proxy._normalize_result(
        {
            "content": [{"type": "text", "text": "quota exhausted"}],
            "isError": True,
        }
    )
    invalid = proxy._normalize_result(
        {
            "structuredContent": {"answer": 42},
            "isError": False,
        }
    )
    missing = proxy._normalize_result({"content": [], "isError": False})

    assert remote_error == {"status": "error", "error": "quota exhausted"}
    assert invalid["status"] == "error"
    assert "invalid structuredContent" in invalid["error"]
    assert missing["status"] == "error"
    assert "required structuredContent" in missing["error"]


def test_proxy_maps_structured_business_error_to_tooluniverse_error():
    proxy = MCPProxyTool(_proxy_config())

    result = proxy._normalize_result(
        {
            "structuredContent": {
                "error": {
                    "code": "unavailable",
                    "message": "Private key required",
                }
            },
            "isError": False,
        }
    )

    assert result == {
        "status": "error",
        "error": "Private key required",
        "error_details": {
            "code": "unavailable",
            "message": "Private key required",
        },
    }


@pytest.mark.asyncio
async def test_strict_loader_uses_reviewed_contract_and_ignores_unknown_tools(
    monkeypatch,
):
    loader = MCPAutoLoaderTool(_loader_config())
    remote_contract = copy.deepcopy(CONTRACT)
    remote_contract["description"] = "Untrusted remote description."

    async def fake_request(method, params=None):
        assert method == "tools/list"
        return {
            "tools": [
                remote_contract,
                {
                    "name": "new_unreviewed_tool",
                    "description": "Must not be registered.",
                    "inputSchema": {"type": "object"},
                    "outputSchema": {"type": "object"},
                },
            ]
        }

    monkeypatch.setattr(loader, "_make_mcp_request", fake_request)
    discovered = await loader.discover_tools()
    configs = loader.generate_proxy_tool_configs()

    assert list(discovered) == ["reviewed_tool"]
    assert discovered["reviewed_tool"]["description"] == (
        "Locally reviewed description."
    )
    assert len(configs) == 1
    assert configs[0]["parameter"] == CONTRACT["inputSchema"]
    assert configs[0]["return_schema"] == CONTRACT["outputSchema"]
    assert configs[0]["annotations"] == CONTRACT["annotations"]
    assert configs[0]["http_headers_from_env"] == {
        "Authorization": {
            "env": "TEST_MCP_TOKEN",
            "prefix": "Bearer ",
        }
    }
    assert configs[0]["normalize_mcp_result"] is True
    assert configs[0]["require_structured_content"] is True
    assert configs[0]["mcp_structured_error_field"] == "error"
    assert "mcp_contract_sha256" in configs[0]


@pytest.mark.asyncio
async def test_strict_loader_fails_closed_on_contract_drift(monkeypatch):
    loader = MCPAutoLoaderTool(_loader_config())
    changed_contract = copy.deepcopy(CONTRACT)
    changed_contract["inputSchema"]["properties"]["query"]["type"] = "integer"

    async def fake_request(method, params=None):
        return {"tools": [changed_contract]}

    monkeypatch.setattr(loader, "_make_mcp_request", fake_request)

    with pytest.raises(Exception, match="contract changed"):
        await loader.discover_tools()


SECOND_CONTRACT = {
    "name": "second_reviewed_tool",
    "description": "Second locally reviewed description.",
    "inputSchema": {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    },
    "outputSchema": {
        "type": "object",
        "properties": {"content": {"type": "string"}},
        "required": ["content"],
        "additionalProperties": False,
    },
    "annotations": {
        "readOnlyHint": True,
        "destructiveHint": False,
    },
}


def _two_tool_loader_config():
    """A loader reviewing two tools, as the real Exa/Folklore loaders do."""
    return _loader_config(
        selected_tools=[CONTRACT["name"], SECOND_CONTRACT["name"]],
        tool_contracts=[
            {
                "name": CONTRACT["name"],
                "description": CONTRACT["description"],
                "contract_sha256": MCPAutoLoaderTool._contract_sha256(CONTRACT),
                "annotations": copy.deepcopy(CONTRACT["annotations"]),
            },
            {
                "name": SECOND_CONTRACT["name"],
                "description": SECOND_CONTRACT["description"],
                "contract_sha256": MCPAutoLoaderTool._contract_sha256(SECOND_CONTRACT),
                "annotations": copy.deepcopy(SECOND_CONTRACT["annotations"]),
            },
        ],
    )


@pytest.mark.asyncio
async def test_one_drifted_tool_does_not_take_down_its_unaffected_siblings(
    monkeypatch, caplog
):
    """Upstream changing one tool must not deregister every other reviewed tool.

    Exa added a required `objective` field to `web_search_exa`, which under
    abort-all behavior also took `web_fetch_exa` offline even though its
    contract still matched exactly.
    """
    loader = MCPAutoLoaderTool(_two_tool_loader_config())
    drifted = copy.deepcopy(CONTRACT)
    drifted["inputSchema"]["properties"]["objective"] = {"type": "string"}
    drifted["inputSchema"]["required"] = ["query", "objective"]

    async def fake_request(method, params=None):
        return {"tools": [drifted, copy.deepcopy(SECOND_CONTRACT)]}

    monkeypatch.setattr(loader, "_make_mcp_request", fake_request)
    discovered = await loader.discover_tools()

    assert list(discovered) == ["second_reviewed_tool"]
    assert "reviewed_tool (contract changed" in caplog.text


@pytest.mark.asyncio
async def test_a_missing_reviewed_tool_still_fails_the_whole_category(monkeypatch):
    """Presence of every reviewed tool checks the server's identity.

    A server offering only a subset may be stale, rolled back, or the wrong
    host, so -- unlike drift in a single tool -- this stays fail-closed even
    when the remaining reviewed tools match byte-for-byte.
    """
    loader = MCPAutoLoaderTool(_two_tool_loader_config())

    async def fake_request(method, params=None):
        return {"tools": [copy.deepcopy(SECOND_CONTRACT)]}

    monkeypatch.setattr(loader, "_make_mcp_request", fake_request)

    with pytest.raises(Exception, match="missing from server"):
        await loader.discover_tools()


@pytest.mark.asyncio
async def test_a_selected_tool_without_a_reviewed_contract_fails_loudly(monkeypatch):
    """A typo in selected_tools is a local config error, not upstream drift."""
    config = _two_tool_loader_config()
    config["selected_tools"] = ["reviewed_tool", "typoo_tool"]
    loader = MCPAutoLoaderTool(config)

    async def fake_request(method, params=None):
        return {
            "tools": [
                copy.deepcopy(CONTRACT),
                {"name": "typoo_tool", "inputSchema": {}, "outputSchema": {}},
            ]
        }

    monkeypatch.setattr(loader, "_make_mcp_request", fake_request)

    with pytest.raises(Exception, match="No reviewed MCP contract"):
        await loader.discover_tools()


@pytest.mark.asyncio
async def test_drifted_tool_is_never_exposed_even_when_siblings_load(monkeypatch):
    """The pin still holds: a drifted tool is excluded, never silently accepted."""
    loader = MCPAutoLoaderTool(_two_tool_loader_config())
    drifted = copy.deepcopy(CONTRACT)
    drifted["inputSchema"]["properties"]["query"]["type"] = "integer"

    async def fake_request(method, params=None):
        return {"tools": [drifted, copy.deepcopy(SECOND_CONTRACT)]}

    monkeypatch.setattr(loader, "_make_mcp_request", fake_request)
    await loader.discover_tools()
    configs = loader.generate_proxy_tool_configs()

    assert [config["target_tool_name"] for config in configs] == [
        "second_reviewed_tool"
    ]


@pytest.mark.asyncio
async def test_strict_loader_fails_closed_when_reviewed_tool_is_missing(
    monkeypatch,
):
    loader = MCPAutoLoaderTool(_loader_config())

    async def fake_request(method, params=None):
        return {"tools": []}

    monkeypatch.setattr(loader, "_make_mcp_request", fake_request)

    with pytest.raises(Exception, match="missing from server"):
        await loader.discover_tools()


def test_legacy_loader_keeps_raw_discovery_behavior():
    loader = MCPAutoLoaderTool(
        {
            "name": "legacy_loader",
            "description": "Legacy-compatible loader.",
            "server_url": "https://example.test/mcp",
        }
    )
    loader._discovered_tools = {
        "legacy_tool": {
            "name": "legacy_tool",
            "inputSchema": {"type": "object"},
        }
    }

    config = loader.generate_proxy_tool_configs()[0]

    assert "normalize_mcp_result" not in config
    assert "require_structured_content" not in config
    assert "return_schema" not in config
