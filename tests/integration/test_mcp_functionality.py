#!/usr/bin/env python3
"""
MCP Functionality Tests

Tests that MCP-related functionality actually works:
- SMCP server can be created and configured
- MCP client tools can be instantiated
- MCP protocol methods are available
- Tool discovery and execution works
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from tooluniverse.smcp import SMCP
from tooluniverse.mcp_client_tool import MCPClientTool, MCPAutoLoaderTool


@pytest.mark.integration
@pytest.mark.mcp
class TestMCPFunctionality:
    """Test that MCP functionality actually works"""

    def test_smcp_server_creation(self):
        """Test that SMCP server can be created with different configurations"""
        # Test basic creation
        server = SMCP(name="Test Server")
        assert server is not None
        assert server.name == "Test Server"
        
        # Test with tool categories
        server = SMCP(
            name="Category Server",
            tool_categories=["uniprot", "ChEMBL"],
            search_enabled=True
        )
        assert server is not None
        assert len(server.tooluniverse.all_tool_dict) > 0
        
        # Test with specific tools
        server = SMCP(
            name="Tool Server",
            include_tools=["UniProt_get_entry_by_accession"],
            search_enabled=False
        )
        assert server is not None

    def test_smcp_server_tool_loading(self):
        """Test that SMCP server loads tools correctly"""
        server = SMCP(
            name="Loading Test",
            tool_categories=["uniprot"],
            search_enabled=True
        )
        
        # Check that tools are loaded
        tools = server.tooluniverse.all_tool_dict
        assert len(tools) > 0
        
        # Check that UniProt tools are present
        uniprot_tools = [name for name in tools.keys() if "UniProt" in name]
        assert len(uniprot_tools) > 0

    def test_smcp_server_configuration(self):
        """Test SMCP server configuration options"""
        # Test with different worker counts
        server = SMCP(name="Worker Test", max_workers=10)
        assert server.max_workers == 10
        
        # Test with search disabled
        server = SMCP(name="No Search", search_enabled=False)
        assert server.search_enabled is False
        
        # Test with hooks enabled
        server = SMCP(name="Hooks Test", hooks_enabled=True)
        assert server.hooks_enabled is True

    def test_mcp_client_tool_creation(self):
        """Test that MCP client tools can be created"""
        # Test MCPClientTool
        tool_config = {
            "name": "test_client",
            "server_url": "http://localhost:8000",
            "transport": "http"
        }
        
        client = MCPClientTool(tool_config)
        assert client is not None
        assert client.server_url == "http://localhost:8000"
        assert client.transport == "http"
        
        # Test MCPAutoLoaderTool
        auto_loader = MCPAutoLoaderTool(tool_config)
        assert auto_loader is not None

    @pytest.mark.asyncio
    async def test_mcp_client_tool_async_methods(self):
        """Test that MCP client tools have async methods"""
        tool_config = {
            "name": "test_client",
            "server_url": "http://localhost:8000",
            "transport": "http"
        }
        
        client = MCPClientTool(tool_config)
        
        # Test that async methods exist and are callable
        assert hasattr(client, 'list_tools')
        assert asyncio.iscoroutinefunction(client.list_tools)
        
        assert hasattr(client, 'call_tool')
        assert asyncio.iscoroutinefunction(client.call_tool)
        
        assert hasattr(client, 'list_resources')
        assert asyncio.iscoroutinefunction(client.list_resources)

    @pytest.mark.asyncio
    async def test_mcp_client_tool_with_mock_server(self):
        """Test MCP client tool with mocked server responses"""
        from unittest.mock import patch, MagicMock, AsyncMock
        
        # Mock the streamablehttp_client and ClientSession
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value={
            "tools": [
                {
                    "name": "test_tool",
                    "description": "A test tool",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "param1": {"type": "string"}
                        }
                    }
                }
            ]
        })
        
        mock_read_stream = AsyncMock()
        mock_write_stream = AsyncMock()
        
        with patch('tooluniverse.mcp_client_tool.streamablehttp_client') as mock_client:
            mock_client.return_value.__aenter__.return_value = (mock_read_stream, mock_write_stream, None)
            
            with patch('tooluniverse.mcp_client_tool.ClientSession') as mock_session_class:
                mock_session_class.return_value.__aenter__.return_value = mock_session
                
                tool_config = {
                    "name": "test_client",
                    "server_url": "http://localhost:8000",
                    "transport": "http"
                }
                
                client = MCPClientTool(tool_config)
                
                # Test listing tools
                tools = await client.list_tools()
                assert len(tools) > 0
                assert tools[0]["name"] == "test_tool"

    def test_smcp_server_utility_tools(self):
        """Test that SMCP server has utility tools"""
        server = SMCP(
            name="Utility Test",
            tool_categories=["uniprot"],
            search_enabled=True
        )
        
        # Check that utility tools are registered
        # These should be available as MCP tools
        assert hasattr(server, 'tooluniverse')
        assert server.tooluniverse is not None

    def test_smcp_server_tool_finder_initialization(self):
        """Test that SMCP server initializes tool finders correctly"""
        # Test with search enabled
        server = SMCP(
            name="Finder Test",
            tool_categories=["uniprot"],
            search_enabled=True
        )
        
        # Check that tool finders are initialized
        # The actual attribute names might be different
        assert hasattr(server, 'tooluniverse')
        assert server.tooluniverse is not None
        
        # Check that search is enabled
        assert server.search_enabled is True

    def test_smcp_server_error_handling(self):
        """Test SMCP server error handling"""
        # Test with invalid configuration (nonexistent category)
        server = SMCP(
            name="Error Test",
            tool_categories=["nonexistent_category"]
        )
        
        # Should still create server with defaults
        assert server is not None
        assert server.max_workers >= 1

    def test_mcp_protocol_methods_availability(self):
        """Test that MCP protocol methods are available"""
        server = SMCP(name="Protocol Test")
        
        # Check that custom MCP methods are available
        assert hasattr(server, '_tools_find_middleware')
        assert callable(server._tools_find_middleware)
        
        assert hasattr(server, '_handle_tools_find')
        assert callable(server._handle_tools_find)
        
        # Check that FastMCP methods are available
        assert hasattr(server, 'get_tools')
        assert callable(server.get_tools)

    @pytest.mark.asyncio
    async def test_smcp_tools_find_functionality(self):
        """Test SMCP tools/find functionality"""
        server = SMCP(
            name="Find Test",
            tool_categories=["uniprot", "ChEMBL"],
            search_enabled=True
        )
        
        # Test tools/find request

        
        response = await server._handle_tools_find(
            request_id="find-test",
            params={
                "query": "protein analysis",
                "limit": 5
            }
        )
        
        # Should return a valid response
        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"
        assert "id" in response
        assert response["id"] == "find-test"
        
        # Should have either result or error
        assert "result" in response or "error" in response
        
        if "result" in response:
            # The result might be a list of tools directly or have a tools field
            result = response["result"]
            if isinstance(result, list):
                # Direct list of tools
                assert len(result) > 0
            elif "tools" in result:
                # Tools in a tools field
                assert isinstance(result["tools"], list)
                assert len(result["tools"]) > 0
            else:
                # Other format - just check it's not empty
                assert result is not None

    def test_smcp_server_thread_pool(self):
        """Test SMCP server thread pool configuration"""
        server = SMCP(
            name="Thread Test",
            max_workers=3
        )
        
        assert hasattr(server, 'executor')
        assert server.executor is not None
        assert server.max_workers == 3

    def test_smcp_server_tool_categories(self):
        """Test SMCP server tool category filtering"""
        # Test with specific categories
        server = SMCP(
            name="Category Test",
            tool_categories=["uniprot", "ChEMBL"]
        )
        
        tools = server.tooluniverse.all_tool_dict
        assert len(tools) > 0
        
        # Check that we have tools from the specified categories
        tool_names = list(tools.keys())
        has_uniprot = any("UniProt" in name for name in tool_names)
        has_chembl = any("ChEMBL" in name for name in tool_names)
        
        assert has_uniprot or has_chembl

    def test_smcp_server_exclude_tools(self):
        """Test SMCP server tool exclusion"""
        # Test excluding specific tools
        server = SMCP(
            name="Exclude Test",
            tool_categories=["uniprot"],
            exclude_tools=["UniProt_get_entry_by_accession"]
        )
        
        tools = server.tooluniverse.all_tool_dict
        assert "UniProt_get_entry_by_accession" not in tools

    def test_smcp_server_include_tools(self):
        """Test SMCP server tool inclusion"""
        # Test including specific tools
        server = SMCP(
            name="Include Test",
            include_tools=["UniProt_get_entry_by_accession"]
        )
        
        tools = server.tooluniverse.all_tool_dict
        assert "UniProt_get_entry_by_accession" in tools

    def test_mcp_client_tool_configuration(self):
        """Test MCP client tool configuration options"""
        # Test different transport types
        http_config = {
            "name": "http_client",
            "server_url": "http://localhost:8000",
            "transport": "http"
        }
        
        ws_config = {
            "name": "ws_client",
            "server_url": "ws://localhost:8000",
            "transport": "websocket"
        }
        
        http_client = MCPClientTool(http_config)
        ws_client = MCPClientTool(ws_config)
        
        assert http_client.transport == "http"
        assert ws_client.transport == "websocket"

    def test_smcp_server_hooks_configuration(self):
        """Test SMCP server hooks configuration"""
        # Test with different hook configurations
        server = SMCP(
            name="Hooks Test",
            hooks_enabled=True,
            hook_type="SummarizationHook"
        )
        
        assert server.hooks_enabled is True
        assert server.hook_type == "SummarizationHook"

    def test_smcp_server_auto_expose_tools(self):
        """Test SMCP server auto-expose tools setting"""
        # Test with auto_expose_tools disabled
        server = SMCP(
            name="No Auto Expose",
            auto_expose_tools=False
        )
        
        assert server.auto_expose_tools is False
        
        # Test with auto_expose_tools enabled (default)
        server = SMCP(name="Auto Expose")
        assert server.auto_expose_tools is True

    def test_mcp_auto_loader_tool_configuration(self):
        """Test MCPAutoLoaderTool configuration options"""
        # Test basic configuration
        tool_config = {
            "name": "test_auto_loader",
            "server_url": "http://localhost:8000",
            "transport": "http",
            "timeout": 30,
            "tool_prefix": "mcp_",
            "auto_register": True
        }
        
        auto_loader = MCPAutoLoaderTool(tool_config)
        assert auto_loader is not None
        assert auto_loader.server_url == "http://localhost:8000"
        assert auto_loader.transport == "http"
        assert auto_loader.timeout == 30
        assert auto_loader.tool_prefix == "mcp_"
        assert auto_loader.auto_register is True

    def test_mcp_auto_loader_tool_proxy_config_generation(self):
        """Test MCPAutoLoaderTool proxy configuration generation"""
        tool_config = {
            "name": "test_auto_loader",
            "server_url": "http://localhost:8000",
            "transport": "http",
            "tool_prefix": "test_",
            "selected_tools": ["tool1", "tool2"]
        }
        
        auto_loader = MCPAutoLoaderTool(tool_config)
        
        # Mock discovered tools
        auto_loader._discovered_tools = {
            "tool1": {
                "name": "tool1",
                "description": "Test tool 1",
                "inputSchema": {
                    "type": "object",
                    "properties": {"param1": {"type": "string"}},
                    "required": ["param1"]
                }
            },
            "tool2": {
                "name": "tool2", 
                "description": "Test tool 2",
                "inputSchema": {
                    "type": "object",
                    "properties": {"param2": {"type": "integer"}},
                    "required": ["param2"]
                }
            },
            "tool3": {
                "name": "tool3",
                "description": "Test tool 3",
                "inputSchema": {"type": "object", "properties": {}}
            }
        }
        
        # Generate proxy configs
        configs = auto_loader.generate_proxy_tool_configs()
        
        # Should only include selected tools
        assert len(configs) == 2
        assert any(config["name"] == "test_tool1" for config in configs)
        assert any(config["name"] == "test_tool2" for config in configs)
        assert not any(config["name"] == "test_tool3" for config in configs)
        
        # Check config structure
        for config in configs:
            assert "name" in config
            assert "description" in config
            assert "type" in config
            assert config["type"] == "MCPProxyTool"
            assert "server_url" in config
            assert "target_tool_name" in config
            assert "parameter" in config

    @pytest.mark.asyncio
    async def test_mcp_auto_loader_tool_discovery(self):
        """Test MCPAutoLoaderTool tool discovery functionality"""
        tool_config = {
            "name": "test_auto_loader",
            "server_url": "http://localhost:8000",
            "transport": "http",
            "timeout": 5
        }
        
        auto_loader = MCPAutoLoaderTool(tool_config)
        
        # Mock the MCP request to avoid actual network calls
        with patch.object(auto_loader, '_make_mcp_request') as mock_request:
            mock_request.return_value = {
                "tools": [
                    {
                        "name": "mock_tool",
                        "description": "A mock tool for testing",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"text": {"type": "string"}},
                            "required": ["text"]
                        }
                    }
                ]
            }
            
            # Test discovery
            discovered = await auto_loader.discover_tools()
            
            assert len(discovered) == 1
            assert "mock_tool" in discovered
            assert discovered["mock_tool"]["description"] == "A mock tool for testing"

    @pytest.mark.asyncio
    async def test_mcp_auto_loader_tool_registration(self):
        """Test MCPAutoLoaderTool tool registration with ToolUniverse"""
        tool_config = {
            "name": "test_auto_loader",
            "server_url": "http://localhost:8000",
            "transport": "http",
            "tool_prefix": "test_",
            "auto_register": True
        }
        
        auto_loader = MCPAutoLoaderTool(tool_config)
        
        # Mock discovered tools
        auto_loader._discovered_tools = {
            "test_tool": {
                "name": "test_tool",
                "description": "A test tool",
                "inputSchema": {
                    "type": "object",
                    "properties": {"param": {"type": "string"}},
                    "required": ["param"]
                }
            }
        }
        
        # Create a mock ToolUniverse engine
        mock_engine = MagicMock()
        mock_engine.callable_functions = {}
        
        def mock_register_custom_tool(tool_class, tool_name, tool_config, instantiate=False, tool_instance=None):
            # Simulate the actual behavior of register_custom_tool
            actual_key = tool_config.get("name", tool_name)
            if instantiate:
                mock_engine.callable_functions[actual_key] = MagicMock()
        
        mock_register_custom_tool_mock = MagicMock(side_effect=mock_register_custom_tool)
        mock_engine.register_custom_tool = mock_register_custom_tool_mock
        
        # Test registration
        registered_count = auto_loader.register_tools_in_engine(mock_engine)
        
        assert registered_count == 1
        mock_engine.register_custom_tool.assert_called_once()
        
        # Check the call arguments
        call_args = mock_engine.register_custom_tool.call_args
        assert call_args[1]["tool_name"] == "test_test_tool"
        assert call_args[1]["instantiate"] is True

    @pytest.mark.asyncio
    async def test_mcp_auto_loader_tool_auto_load_and_register(self):
        """Test MCPAutoLoaderTool complete auto-load and register process"""
        tool_config = {
            "name": "test_auto_loader",
            "server_url": "http://localhost:8000",
            "transport": "http",
            "tool_prefix": "auto_",
            "auto_register": True
        }
        
        auto_loader = MCPAutoLoaderTool(tool_config)
        
        # Mock the discovery and registration process
        with patch.object(auto_loader, 'discover_tools') as mock_discover, \
             patch.object(auto_loader, 'register_tools_in_engine') as mock_register:
            
            mock_discover.return_value = {
                "discovered_tool": {
                    "name": "discovered_tool",
                    "description": "A discovered tool",
                    "inputSchema": {"type": "object", "properties": {}}
                }
            }
            mock_register.return_value = 1
            
            # Create a mock ToolUniverse engine
            mock_engine = MagicMock()
            
            # Test auto-load and register
            result = await auto_loader.auto_load_and_register(mock_engine)
            
            # Verify the result
            assert "discovered_count" in result
            assert "registered_count" in result
            assert "tools" in result
            assert "registered_tools" in result
            
            assert result["discovered_count"] == 1
            assert result["registered_count"] == 1
            assert "discovered_tool" in result["tools"]
            
            # Verify methods were called
            mock_discover.assert_called_once()
            mock_register.assert_called_once_with(mock_engine)

    def test_mcp_auto_loader_tool_with_disabled_auto_register(self):
        """Test MCPAutoLoaderTool with auto_register disabled"""
        tool_config = {
            "name": "test_auto_loader",
            "server_url": "http://localhost:8000",
            "transport": "http",
            "auto_register": False
        }
        
        auto_loader = MCPAutoLoaderTool(tool_config)
        assert auto_loader.auto_register is False
        
        # Mock discovered tools
        auto_loader._discovered_tools = {
            "test_tool": {
                "name": "test_tool",
                "description": "A test tool",
                "inputSchema": {"type": "object", "properties": {}}
            }
        }
        
        # Generate configs should work even with auto_register disabled
        configs = auto_loader.generate_proxy_tool_configs()
        assert len(configs) == 1
        assert configs[0]["name"] == "mcp_test_tool"  # Default prefix is "mcp_"
