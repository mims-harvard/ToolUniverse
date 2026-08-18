"""Tests for opt-in Bearer authentication on remote MCP clients."""

from unittest.mock import AsyncMock, patch

import pytest

from tooluniverse.mcp_client_tool import MCPAutoLoaderTool, MCPProxyTool


@pytest.mark.asyncio
async def test_auto_loader_sends_configured_bearer_token(monkeypatch):
    monkeypatch.setenv("TEST_MCP_TOKEN", "secret-token")
    session = AsyncMock()
    session.initialize = AsyncMock()
    session.list_tools = AsyncMock(return_value={"tools": []})

    with patch("tooluniverse.mcp_client_tool.streamablehttp_client") as transport:
        transport.return_value.__aenter__.return_value = (
            AsyncMock(),
            AsyncMock(),
            None,
        )
        with patch("tooluniverse.mcp_client_tool.ClientSession") as session_class:
            session_class.return_value.__aenter__.return_value = session
            loader = MCPAutoLoaderTool(
                {
                    "name": "authenticated_loader",
                    "server_url": "http://localhost:8081/mcp",
                    "bearer_token_env": "TEST_MCP_TOKEN",
                }
            )

            assert await loader.discover_tools() == {}

    transport.assert_called_once_with(
        "http://localhost:8081/mcp",
        headers={"Authorization": "Bearer secret-token"},
        timeout=5,
    )


def test_auto_loader_passes_auth_configuration_to_proxy_tools(monkeypatch):
    monkeypatch.setenv("TEST_MCP_TOKEN", "secret-token")
    loader = MCPAutoLoaderTool(
        {
            "name": "authenticated_loader",
            "server_url": "http://localhost:8081/mcp",
            "bearer_token_env": "TEST_MCP_TOKEN",
        }
    )
    loader._discovered_tools = {
        "remote_tool": {
            "name": "remote_tool",
            "description": "Remote tool",
            "inputSchema": {"type": "object", "properties": {}},
        }
    }

    proxy_config = loader.generate_proxy_tool_configs()[0]
    proxy = MCPProxyTool(proxy_config)

    assert proxy_config["bearer_token_env"] == "TEST_MCP_TOKEN"
    assert proxy.http_headers == {"Authorization": "Bearer secret-token"}


def test_unconfigured_client_does_not_send_global_token(monkeypatch):
    monkeypatch.setenv("TOOLUNIVERSE_API_TOKEN", "must-not-leak")

    loader = MCPAutoLoaderTool(
        {"name": "public_loader", "server_url": "https://public.example/mcp"}
    )

    assert loader.bearer_token_env is None
    assert loader.http_headers == {}
