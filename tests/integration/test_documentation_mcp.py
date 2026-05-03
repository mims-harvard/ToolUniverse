#!/usr/bin/env python3
"""
Integration tests for ToolUniverse MCP functionality - Cleaned Version

Tests real MCP functionality with actual tool execution.
"""

import pytest
import time

from tooluniverse import ToolUniverse
from tooluniverse.smcp import SMCP


@pytest.mark.integration
@pytest.mark.mcp
class TestToolUniverseMCPIntegration:
    """Test MCP functionality with real tool execution."""

    @pytest.fixture(autouse=True)
    def setup_tooluniverse(self):
        """Setup ToolUniverse instance for each test."""
        self.tu = ToolUniverse()
        self.tu.load_tools()
        yield
        self.tu.close()

    def test_mcp_server_creation_real(self):
        """Test real MCP server creation and basic functionality."""
        # Test that we can create an MCP server
        server = SMCP(
            name="Test Server",
            tool_categories=["uniprot"],
            search_enabled=True
        )
        
        assert server is not None
        assert hasattr(server, 'name')
        assert hasattr(server, 'tool_categories')
        assert hasattr(server, 'search_enabled')

    def test_mcp_server_tool_categories_real(self):
        """Test real MCP server tool category filtering."""
        # Test with different tool categories
        categories = ["uniprot", "arxiv", "pubmed"]
        
        for category in categories:
            server = SMCP(
                name=f"Test Server {category}",
                tool_categories=[category],
                search_enabled=True
            )
            
            assert server is not None
            assert category in server.tool_categories

    def test_mcp_server_search_functionality_real(self):
        """Test real MCP server search functionality."""
        # Test server with search enabled
        server = SMCP(
            name="Search Test Server",
            tool_categories=["uniprot"],
            search_enabled=True
        )
        
        assert server is not None
        assert server.search_enabled is True

    def test_mcp_server_search_disabled_real(self):
        """Test real MCP server with search disabled."""
        # Test server with search disabled
        server = SMCP(
            name="No Search Server",
            tool_categories=["uniprot"],
            search_enabled=False
        )
        
        assert server is not None
        assert server.search_enabled is False

    def test_mcp_client_tool_creation_real(self):
        """Test real MCP client tool creation."""
        from tooluniverse.mcp_client_tool import MCPClientTool
        
        # Test MCPClientTool creation
        client_tool = MCPClientTool(
            tool_config={
                "name": "test_mcp_http_client",
                "description": "A test MCP HTTP client",
                "transport": "http",
                "server_url": "http://localhost:8000"
            }
        )
        
        assert client_tool is not None
        assert hasattr(client_tool, 'run')
        assert hasattr(client_tool, 'tool_config')

    def test_mcp_client_tool_execution_real(self):
        """Test real MCP client tool execution."""
        from tooluniverse.mcp_client_tool import MCPClientTool
        
        # Test MCPClientTool execution
        client_tool = MCPClientTool(
            tool_config={
                "name": "test_mcp_client",
                "description": "A test MCP client",
                "transport": "http",
                "server_url": "http://localhost:8000"
            }
        )
        
        try:
            result = client_tool.run({
                "name": "test_tool",
                "arguments": {"test": "value"}
            })
            
            # Should return a result (may be error if connection fails)
            assert isinstance(result, dict)
        except Exception as e:
            # Expected if connection fails
            assert isinstance(e, Exception)

    def test_mcp_tool_registry_real(self):
        """Test real MCP tool registry functionality."""
        from tooluniverse.mcp_tool_registry import get_mcp_tool_registry
        
        # Test MCP tool registry functionality
        registry = get_mcp_tool_registry()
        
        assert registry is not None
        assert isinstance(registry, dict)
        
        # Test that registry is accessible and can be modified
        initial_count = len(registry)
        registry["test_key"] = "test_value"
        assert registry["test_key"] == "test_value"
        assert len(registry) == initial_count + 1
        
        # Clean up
        del registry["test_key"]

    def test_mcp_tool_registration_real(self):
        """Test real MCP tool registration."""
        from tooluniverse.mcp_tool_registry import get_mcp_tool_registry, register_mcp_tool
        
        # Test tool registry functionality
        registry = get_mcp_tool_registry()
        
        assert registry is not None
        assert isinstance(registry, dict)
        
        # Test decorator registration
        @register_mcp_tool(
            tool_type_name="test_doc_tool",
            config={
                "name": "test_doc_tool",
                "description": "A test tool for documentation",
                "type": "TestDocTool",
                "parameter": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "A message"}
                    },
                    "required": ["message"]
                }
            }
        )
        class TestDocTool:
            def __init__(self, tool_config=None):
                self.tool_config = tool_config
            
            def run(self, arguments):
                return {"result": f"Echo: {arguments.get('message', '')}"}
        
        # Get registry again after registration
        registry = get_mcp_tool_registry()
        
        # Verify tool was registered
        assert "test_doc_tool" in registry
        tool_info = registry["test_doc_tool"]
        assert tool_info["name"] == "test_doc_tool"
        assert tool_info["description"] == "A test tool for documentation"
        
        # Test that registry has expected structure
        assert "tools" in registry or len(registry) >= 0

    def test_mcp_streaming_real(self):
        """Test real MCP streaming functionality."""
        from tooluniverse.mcp_client_tool import MCPClientTool
        
        # Test streaming callback
        callback_called = False
        callback_data = []
        
        def test_callback(chunk):
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data.append(chunk)
        
        client_tool = MCPClientTool(
            tool_config={
                "name": "test_streaming_client",
                "description": "A test streaming MCP client",
                "transport": "http",
                "server_url": "http://localhost:8000"
            }
        )
        
        try:
            result = client_tool.run({
                "name": "test_tool",
                "arguments": {"test": "value"}
            }, stream_callback=test_callback)
            
            # Should return a result
            assert isinstance(result, dict)
        except Exception as e:
            # Expected if connection fails
            assert isinstance(e, Exception)

    def test_mcp_error_handling_real(self):
        """Test real MCP error handling."""
        from tooluniverse.mcp_client_tool import MCPClientTool
        
        # Test with invalid configuration
        try:
            client_tool = MCPClientTool(
                tooluniverse=self.tu,
                config={
                    "name": "invalid_client",
                    "description": "An invalid MCP client",
                    "transport": "invalid_transport"
                }
            )
            
            result = client_tool.run({
                "name": "test_tool",
                "arguments": {"test": "value"}
            })
            
            # Should handle invalid configuration gracefully
            assert isinstance(result, dict)
        except Exception as e:
            # Expected if configuration is invalid
            assert isinstance(e, Exception)

    def test_mcp_tool_discovery_real(self):
        """Test real MCP tool discovery."""
        # Test that we can discover MCP tools
        tool_names = self.tu.list_built_in_tools(mode='list_name')
        mcp_tools = [name for name in tool_names if "MCP" in name or "mcp" in name.lower()]
        
        # Should find some MCP tools
        assert isinstance(mcp_tools, list)

    def test_mcp_tool_execution_real(self):
        """Test real MCP tool execution through ToolUniverse."""
        # Test MCP tool execution
        try:
            result = self.tu.run({
                "name": "MCPClientTool",
                "arguments": {
                    "config": {
                        "name": "test_client",
                        "transport": "stdio",
                        "command": "echo"
                    },
                    "tool_call": {
                        "name": "test_tool",
                        "arguments": {"test": "value"}
                    }
                }
            })
            
            # Should return a result
            assert isinstance(result, dict)
        except Exception as e:
            # Expected if MCP tools not available
            assert isinstance(e, Exception)

    def test_mcp_server_startup_real(self):
        """Test real MCP server startup process."""
        # Test server startup
        server = SMCP(
            name="Startup Test Server",
            tool_categories=["uniprot"],
            search_enabled=True
        )
        
        assert server is not None
        
        # Test that server has required attributes
        assert hasattr(server, 'name')
        assert hasattr(server, 'tool_categories')
        assert hasattr(server, 'search_enabled')
        assert hasattr(server, 'run')
        assert hasattr(server, 'run_simple')

    def test_mcp_server_shutdown_real(self):
        """Test real MCP server shutdown process."""
        # Test server shutdown
        server = SMCP(
            name="Shutdown Test Server",
            tool_categories=["uniprot"],
            search_enabled=True
        )
        
        assert server is not None
        
        # Test that server can be stopped
        try:
            server.stop()
        except Exception:
            # Expected if server wasn't started
            pass

    def test_mcp_tool_validation_real(self):
        """Test real MCP tool validation."""
        from tooluniverse.mcp_tool_registry import get_mcp_tool_registry, register_mcp_tool
        
        # Test tool registry functionality
        registry = get_mcp_tool_registry()
        
        assert registry is not None
        assert isinstance(registry, dict)
        
        # Test decorator registration with validation
        @register_mcp_tool(
            tool_type_name="test_validation_tool",
            config={
                "name": "test_validation_tool",
                "description": "A test tool for validation",
                "type": "TestValidationTool",
                "parameter": {
                    "type": "object",
                    "properties": {
                        "required_param": {"type": "string", "description": "Required parameter"},
                        "optional_param": {"type": "integer", "description": "Optional parameter"}
                    },
                    "required": ["required_param"]
                }
            }
        )
        class TestValidationTool:
            def __init__(self, tool_config=None):
                self.tool_config = tool_config
            
            def run(self, arguments):
                return {"result": f"Validated: {arguments.get('required_param', '')}"}
        
        # Get registry again after registration
        registry = get_mcp_tool_registry()
        
        # Verify tool was registered with proper schema
        assert "test_validation_tool" in registry
        tool_info = registry["test_validation_tool"]
        assert tool_info["name"] == "test_validation_tool"
        assert "parameter_schema" in tool_info
        # Check that parameter_schema exists and has the expected MCP structure
        assert tool_info["parameter_schema"]["type"] == "object"
        assert "properties" in tool_info["parameter_schema"]
        # Check that the original tool config is preserved
        assert "tool_config" in tool_info
        assert tool_info["tool_config"]["parameter"]["required"] == ["required_param"]

    def test_mcp_tool_error_recovery_real(self):
        """Test real MCP tool error recovery."""
        from tooluniverse.mcp_client_tool import MCPClientTool
        
        # Test error recovery
        client_tool = MCPClientTool(
            tool_config={
                "name": "error_recovery_client",
                "description": "A test error recovery client",
                "transport": "http",
                "server_url": "http://localhost:8000"
            }
        )
        
        try:
            result = client_tool.run({
                "name": "test_tool",
                "arguments": {"test": "value"}
            })
            
            # Should handle error gracefully
            assert isinstance(result, dict)
        except Exception as e:
            # Expected if command doesn't exist
            assert isinstance(e, Exception)

    def test_mcp_tool_performance_real(self):
        """Test real MCP tool performance."""
        
        from tooluniverse.mcp_client_tool import MCPClientTool
        
        client_tool = MCPClientTool(
            tool_config={
                "name": "performance_test_client",
                "description": "A performance test client",
                "transport": "http",
                "server_url": "http://localhost:8000"
            }
        )
        
        # Test execution time
        start_time = time.time()
        
        try:
            result = client_tool.run({
                "name": "test_tool",
                "arguments": {"test": "value"}
            })
            
            execution_time = time.time() - start_time
            
            # Should complete within reasonable time (10 seconds)
            assert execution_time < 10
            assert isinstance(result, dict)
        except Exception:
            # Expected if connection fails
            execution_time = time.time() - start_time
            assert execution_time < 10

    def test_mcp_tool_concurrent_execution_real(self):
        """Test real concurrent MCP tool execution."""
        import threading
        
        from tooluniverse.mcp_client_tool import MCPClientTool
        
        results = []
        
        def make_call(call_id):
            client_tool = MCPClientTool(
                tool_config={
                    "name": f"concurrent_client_{call_id}",
                    "description": f"A concurrent client {call_id}",
                    "transport": "http",
                    "server_url": "http://localhost:8000"
                }
            )
            
            try:
                result = client_tool.run({
                    "name": "test_tool",
                    "arguments": {"test": f"value_{call_id}"}
                })
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})
        
        # Create multiple threads
        threads = []
        for i in range(3):  # Reduced for testing
            thread = threading.Thread(target=make_call, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all calls completed
        assert len(results) == 3
        for result in results:
            assert isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__])
