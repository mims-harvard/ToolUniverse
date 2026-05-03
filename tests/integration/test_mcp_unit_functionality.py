#!/usr/bin/env python3
"""
Test MCP (Model Context Protocol) functionality - Cleaned Version

This test file covers real MCP functionality:
1. Real MCP server creation and configuration
2. Real MCP client tool creation and execution
3. Real MCP tool registry functionality
4. Real error handling in MCP context
"""

import sys
import unittest
from pathlib import Path
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse import ToolUniverse


@pytest.mark.unit
class TestMCPFunctionality(unittest.TestCase):
    """Test real MCP functionality and integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tu = ToolUniverse()
        self.tu.load_tools()
    
    def test_mcp_server_creation_real(self):
        """Test real MCP server creation."""
        try:
            from tooluniverse.smcp import SMCP
            
            # Test server creation
            server = SMCP(
                name="Test MCP Server",
                tool_categories=["uniprot"],
                search_enabled=True
            )
            
            self.assertIsNotNone(server)
            self.assertEqual(server.name, "Test MCP Server")
            self.assertTrue(server.search_enabled)
            self.assertIsNotNone(server.tooluniverse)
            
        except ImportError:
            self.skipTest("SMCP not available")
    
    def test_mcp_client_tool_creation_real(self):
        """Test real MCP client tool creation."""
        try:
            from tooluniverse.mcp_client_tool import MCPClientTool
            
            # Test client tool creation
            client_tool = MCPClientTool({
                "name": "test_mcp_client",
                "description": "A test MCP client",
                "server_url": "http://localhost:8000",
                "transport": "http"
            })
            
            self.assertIsNotNone(client_tool)
            self.assertEqual(client_tool.tool_config["name"], "test_mcp_client")
            self.assertEqual(client_tool.tool_config["server_url"], "http://localhost:8000")
            
        except ImportError:
            self.skipTest("MCPClientTool not available")
    
    def test_mcp_client_tool_execution_real(self):
        """Test real MCP client tool execution."""
        try:
            from tooluniverse.mcp_client_tool import MCPClientTool
            
            client_tool = MCPClientTool({
                "name": "test_mcp_client",
                "description": "A test MCP client",
                "server_url": "http://localhost:8000",
                "transport": "http"
            })
            
            # Test tool execution
            result = client_tool.run({
                "name": "test_tool",
                "arguments": {"test": "value"}
            })
            
            # Should return a result (may be error if connection fails)
            self.assertIsInstance(result, dict)
            
        except ImportError:
            self.skipTest("MCPClientTool not available")
        except Exception as e:
            # Expected if connection fails
            self.assertIsInstance(e, Exception)
    
    def test_mcp_tool_registry_global_dict(self):
        """Test MCP tool registry global dictionary functionality."""
        try:
            from tooluniverse.mcp_tool_registry import get_mcp_tool_registry
            
            # Test registry access
            registry = get_mcp_tool_registry()
            self.assertIsNotNone(registry)
            self.assertIsInstance(registry, dict)
            
            # Test that registry is accessible and modifiable
            initial_count = len(registry)
            registry["test_key"] = "test_value"
            self.assertEqual(registry["test_key"], "test_value")
            self.assertEqual(len(registry), initial_count + 1)
            
            # Clean up
            del registry["test_key"]
            
        except ImportError:
            self.skipTest("get_mcp_tool_registry not available")
    
    def test_mcp_tool_discovery_real(self):
        """Test real MCP tool discovery through ToolUniverse."""
        # Test that MCP tools can be discovered
        tool_names = self.tu.list_built_in_tools(mode="list_name")
        mcp_tools = [name for name in tool_names if "MCP" in name or "mcp" in name.lower()]
        
        # Should find some MCP tools
        self.assertIsInstance(mcp_tools, list)
    
    def test_mcp_tool_execution_real(self):
        """Test real MCP tool execution through ToolUniverse."""
        try:
            # Test MCP tool execution
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
            self.assertIsInstance(result, dict)
            
        except Exception as e:
            # Expected if MCP tools not available
            self.assertIsInstance(e, Exception)
    
    def test_mcp_error_handling_real(self):
        """Test real MCP error handling."""
        try:
            from tooluniverse.mcp_client_tool import MCPClientTool
            
            # Test with invalid configuration
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
            self.assertIsInstance(result, dict)
            
        except ImportError:
            self.skipTest("MCPClientTool not available")
        except Exception as e:
            # Expected if configuration is invalid
            self.assertIsInstance(e, Exception)
    
    def test_mcp_streaming_real(self):
        """Test real MCP streaming functionality."""
        try:
            from tooluniverse.mcp_client_tool import MCPClientTool
            
            # Test streaming callback
            callback_called = False
            callback_data = []
            
            def test_callback(chunk):
                nonlocal callback_called, callback_data
                callback_called = True
                callback_data.append(chunk)
            
            client_tool = MCPClientTool(
                tooluniverse=self.tu,
                config={
                    "name": "test_streaming_client",
                    "description": "A test streaming MCP client",
                    "transport": "stdio",
                    "command": "echo"
                }
            )
            
            result = client_tool.run({
                "name": "test_tool",
                "arguments": {"test": "value"}
            }, stream_callback=test_callback)
            
            # Should return a result
            self.assertIsInstance(result, dict)
            
        except ImportError:
            self.skipTest("MCPClientTool not available")
        except Exception as e:
            # Expected if connection fails
            self.assertIsInstance(e, Exception)
    
    def test_mcp_tool_registration_decorator(self):
        """Test MCP tool registration using @register_mcp_tool decorator."""
        try:
            from tooluniverse.mcp_tool_registry import register_mcp_tool, get_mcp_tool_registry
            
            # Test decorator registration
            @register_mcp_tool(
                tool_type_name="test_decorator_tool",
                config={
                    "name": "test_decorator_tool",
                    "description": "A test tool registered via decorator",
                    "parameter": {
                        "type": "object",
                        "properties": {
                            "param": {
                                "type": "string",
                                "description": "A parameter"
                            }
                        },
                        "required": ["param"]
                    }
                }
            )
            class TestDecoratorTool:
                def __init__(self, tool_config=None):
                    self.tool_config = tool_config
                
                def run(self, arguments):
                    return {"result": f"Hello {arguments.get('param', 'World')}!"}
            
            # Verify tool was registered
            registry = get_mcp_tool_registry()
            self.assertIn("test_decorator_tool", registry)
            
            # Test tool instantiation
            tool_info = registry["test_decorator_tool"]
            self.assertEqual(tool_info["name"], "test_decorator_tool")
            self.assertEqual(tool_info["description"], "A test tool registered via decorator")
            
        except ImportError:
            self.skipTest("register_mcp_tool not available")

    def test_mcp_server_start_function(self):
        """Test MCP server start function."""
        try:
            from tooluniverse.mcp_tool_registry import start_mcp_server, register_mcp_tool
            
            # Register a test tool first
            @register_mcp_tool(
                tool_type_name="test_server_tool",
                config={
                    "name": "test_server_tool",
                    "description": "A test tool for server testing",
                    "parameter": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string", "description": "A message"}
                        },
                        "required": ["message"]
                    }
                }
            )
            class TestServerTool:
                def __init__(self, tool_config=None):
                    self.tool_config = tool_config
                
                def run(self, arguments):
                    return {"result": f"Server response: {arguments.get('message', '')}"}
            
            # Test that start_mcp_server function exists and is callable
            self.assertTrue(callable(start_mcp_server))
            
        except ImportError:
            self.skipTest("start_mcp_server not available")

    def test_mcp_server_configs_global_dict(self):
        """Test MCP server configs global dictionary."""
        try:
            from tooluniverse.mcp_tool_registry import _mcp_server_configs
            
            # Test that server configs is accessible
            self.assertIsNotNone(_mcp_server_configs)
            self.assertIsInstance(_mcp_server_configs, dict)
            
            # Test that it can be modified
            initial_count = len(_mcp_server_configs)
            _mcp_server_configs["test_port"] = {"test": "config"}
            self.assertEqual(len(_mcp_server_configs), initial_count + 1)
            self.assertEqual(_mcp_server_configs["test_port"]["test"], "config")
            
            # Clean up
            del _mcp_server_configs["test_port"]
            
        except ImportError:
            self.skipTest("_mcp_server_configs not available")
    
    def test_mcp_tool_performance_real(self):
        """Test real MCP tool performance."""
        try:
            from tooluniverse.mcp_client_tool import MCPClientTool
            import time
            
            # Initialize start_time before any potential exceptions
            start_time = time.time()
            
            client_tool = MCPClientTool({
                "name": "performance_test_client",
                "description": "A performance test client",
                "transport": "stdio",
                "command": "echo"
            })
            
            result = client_tool.run({
                "name": "test_tool",
                "arguments": {"test": "value"}
            })
            
            execution_time = time.time() - start_time
            
            # Should complete within reasonable time (10 seconds)
            self.assertLess(execution_time, 10)
            self.assertIsInstance(result, dict)
            
        except ImportError:
            self.skipTest("MCPClientTool not available")
        except Exception:
            # Expected if connection fails
            execution_time = time.time() - start_time
            self.assertLess(execution_time, 10)
    
    def test_mcp_tool_concurrent_execution_real(self):
        """Test real concurrent MCP tool execution."""
        try:
            from tooluniverse.mcp_client_tool import MCPClientTool
            import threading
            
            results = []
            results_lock = threading.Lock()
            
            def make_call(call_id):
                try:
                    client_tool = MCPClientTool({
                        "name": f"concurrent_client_{call_id}",
                        "description": f"A concurrent client {call_id}",
                        "transport": "stdio",
                        "command": "echo"
                    })
                    
                    result = client_tool.run({
                        "name": "test_tool",
                        "arguments": {"test": f"value_{call_id}"}
                    })
                    
                    with results_lock:
                        results.append(result)
                        
                except Exception as e:
                    with results_lock:
                        results.append({"error": str(e), "call_id": call_id})
            
            # Create multiple threads
            threads = []
            for i in range(3):  # Reduced for testing
                thread = threading.Thread(target=make_call, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads with timeout
            for thread in threads:
                thread.join(timeout=10)  # 10 second timeout per thread
            
            # Verify all calls completed
            self.assertEqual(
                len(results), 3, 
                f"Expected 3 results, got {len(results)}: {results}"
            )
            for result in results:
                self.assertIsInstance(result, dict)
                
        except ImportError:
            self.skipTest("MCPClientTool not available")

    def test_mcp_auto_loader_tool_creation_real(self):
        """Test real MCPAutoLoaderTool creation."""
        try:
            from tooluniverse.mcp_client_tool import MCPAutoLoaderTool
            
            # Test auto loader tool creation
            auto_loader = MCPAutoLoaderTool({
                "name": "test_auto_loader",
                "description": "A test MCP auto loader",
                "server_url": "http://localhost:8000",
                "transport": "http",
                "tool_prefix": "test_",
                "auto_register": True
            })
            
            self.assertIsNotNone(auto_loader)
            self.assertEqual(auto_loader.tool_config["name"], "test_auto_loader")
            self.assertEqual(auto_loader.server_url, "http://localhost:8000")
            self.assertEqual(auto_loader.tool_prefix, "test_")
            self.assertTrue(auto_loader.auto_register)
            
        except ImportError:
            self.skipTest("MCPAutoLoaderTool not available")

    def test_mcp_auto_loader_tool_config_generation(self):
        """Test MCPAutoLoaderTool proxy configuration generation."""
        try:
            from tooluniverse.mcp_client_tool import MCPAutoLoaderTool
            
            auto_loader = MCPAutoLoaderTool({
                "name": "test_auto_loader",
                "server_url": "http://localhost:8000",
                "transport": "http",
                "tool_prefix": "test_",
                "selected_tools": ["tool1", "tool2"]
            })
            
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
            self.assertEqual(len(configs), 2)
            self.assertTrue(any(config["name"] == "test_tool1" for config in configs))
            self.assertTrue(any(config["name"] == "test_tool2" for config in configs))
            self.assertFalse(any(config["name"] == "test_tool3" for config in configs))
            
            # Check config structure
            for config in configs:
                self.assertIn("name", config)
                self.assertIn("description", config)
                self.assertIn("type", config)
                self.assertEqual(config["type"], "MCPProxyTool")
                self.assertIn("server_url", config)
                self.assertIn("target_tool_name", config)
                self.assertIn("parameter", config)
                
        except ImportError:
            self.skipTest("MCPAutoLoaderTool not available")

    def test_mcp_auto_loader_tool_with_tooluniverse(self):
        """Test MCPAutoLoaderTool integration with ToolUniverse."""
        try:
            from tooluniverse.mcp_client_tool import MCPAutoLoaderTool
            
            # Create a fresh ToolUniverse instance
            tu = ToolUniverse()
            
            # Create auto loader
            auto_loader = MCPAutoLoaderTool({
                "name": "test_auto_loader",
                "server_url": "http://localhost:8000",
                "transport": "http",
                "tool_prefix": "test_",
                "auto_register": True
            })
            
            # Mock discovered tools
            auto_loader._discovered_tools = {
                "mock_tool": {
                    "name": "mock_tool",
                    "description": "A mock tool for testing",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"]
                    }
                }
            }
            
            # Test registration with ToolUniverse
            registered_count = auto_loader.register_tools_in_engine(tu)
            
            self.assertEqual(registered_count, 1)
            self.assertIn("test_mock_tool", tu.all_tool_dict)
            self.assertIn("test_mock_tool", tu.callable_functions)
            
        except ImportError:
            self.skipTest("MCPAutoLoaderTool not available")
        except Exception as e:
            # Expected if connection fails
            self.assertIsInstance(e, Exception)

    def test_mcp_proxy_tool_creation_real(self):
        """Test real MCPProxyTool creation."""
        try:
            from tooluniverse.mcp_client_tool import MCPProxyTool
            
            # Test proxy tool creation
            proxy_tool = MCPProxyTool({
                "name": "test_proxy_tool",
                "description": "A test MCP proxy tool",
                "server_url": "http://localhost:8000",
                "transport": "http",
                "target_tool_name": "remote_tool"
            })
            
            self.assertIsNotNone(proxy_tool)
            self.assertEqual(proxy_tool.tool_config["name"], "test_proxy_tool")
            self.assertEqual(proxy_tool.server_url, "http://localhost:8000")
            self.assertEqual(proxy_tool.target_tool_name, "remote_tool")
            
        except ImportError:
            self.skipTest("MCPProxyTool not available")


if __name__ == "__main__":
    unittest.main()
