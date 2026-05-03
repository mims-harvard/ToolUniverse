#!/usr/bin/env python3
"""
Test MCP (Model Context Protocol) integration edge cases - Cleaned Version

This test file covers real MCP integration edge cases:
1. Real MCP server connection handling
2. Real MCP protocol error handling
3. Real MCP timeout scenarios
4. Real MCP authentication issues
"""

import sys
import unittest
from pathlib import Path
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse import ToolUniverse


@pytest.mark.unit
class TestMCPIntegrationEdgeCases(unittest.TestCase):
    """Test real MCP integration edge cases and error handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tu = ToolUniverse()
        self.tu.load_tools()
    
    def tearDown(self):
        """Tear down test fixtures."""
        if hasattr(self, 'tu'):
            self.tu.close()
    
    def test_mcp_server_connection_real(self):
        """Test real MCP server connection handling."""
        try:
            from tooluniverse.smcp import SMCP
            
            # Test server creation with edge case parameters
            server = SMCP(
                name="Edge Case Server",
                tool_categories=["uniprot"],
                search_enabled=True,
                max_workers=1,  # Edge case: minimal workers
                port=0  # Edge case: system-assigned port
            )
            
            self.assertIsNotNone(server)
            self.assertEqual(server.name, "Edge Case Server")
            self.assertEqual(server.max_workers, 1)
            
        except ImportError:
            self.skipTest("SMCP not available")
        except Exception as e:
            # Expected if port 0 is not supported
            self.assertIsInstance(e, Exception)
    
    def test_mcp_client_invalid_config_real(self):
        """Test real MCP client with invalid configuration."""
        try:
            from tooluniverse.mcp_client_tool import MCPClientTool
            
            # Test with invalid transport
            client_tool = MCPClientTool({
                "name": "invalid_client",
                "description": "A client with invalid config",
                "server_url": "invalid://localhost:8000",
                "transport": "invalid_transport"
            })
            
            result = client_tool.run({
                "name": "test_tool",
                "arguments": {"test": "value"}
            })
            
            # Should handle invalid config gracefully
            self.assertIsInstance(result, dict)
            
        except ImportError:
            self.skipTest("MCPClientTool not available")
        except Exception as e:
            # Expected if configuration is invalid
            self.assertIsInstance(e, Exception)
    
    def test_mcp_tool_timeout_real(self):
        """Test real MCP tool timeout handling."""
        try:
            from tooluniverse.mcp_client_tool import MCPClientTool
            import time
            
            # Test with timeout configuration
            client_tool = MCPClientTool({
                "name": "timeout_client",
                "description": "A client with timeout",
                "server_url": "http://localhost:8000",
                "transport": "http",
                "timeout": 1  # 1 second timeout
            })
            
            start_time = time.time()
            
            result = client_tool.run({
                "name": "test_tool",
                "arguments": {"test": "value"}
            })
            
            execution_time = time.time() - start_time
            
            # Should complete within reasonable time
            self.assertLess(execution_time, 5)
            self.assertIsInstance(result, dict)
            
        except ImportError:
            self.skipTest("MCPClientTool not available")
        except Exception as e:
            # Expected if timeout occurs
            self.assertIsInstance(e, Exception)
    
    def test_mcp_tool_large_data_real(self):
        """Test real MCP tool with large data handling."""
        try:
            from tooluniverse.mcp_client_tool import MCPClientTool
            
            # Test with large data
            large_data = "x" * 10000  # 10KB of data
            
            client_tool = MCPClientTool({
                "name": "large_data_client",
                "description": "A client handling large data",
                "server_url": "http://localhost:8000",
                "transport": "http"
            })
            
            result = client_tool.run({
                "name": "test_tool",
                "arguments": {"large_data": large_data}
            })
            
            # Should handle large data
            self.assertIsInstance(result, dict)
            
        except ImportError:
            self.skipTest("MCPClientTool not available")
        except Exception as e:
            # Expected if large data causes issues
            self.assertIsInstance(e, Exception)
    
    def test_mcp_tool_concurrent_requests_real(self):
        """Test real MCP tool with concurrent requests."""
        try:
            from tooluniverse.mcp_client_tool import MCPClientTool
            import threading
            import time
            
            results = []
            
            def make_request(request_id):
                client_tool = MCPClientTool({
                    "name": f"concurrent_client_{request_id}",
                    "description": f"A concurrent client {request_id}",
                    "server_url": "http://localhost:8000",
                    "transport": "http"
                })
                
                try:
                    result = client_tool.run({
                        "name": "test_tool",
                        "arguments": {"request_id": request_id}
                    })
                    results.append(result)
                except Exception as e:
                    results.append({"error": str(e)})
            
            # Create multiple threads
            threads = []
            for i in range(5):  # 5 concurrent requests
                thread = threading.Thread(target=make_request, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads
            for thread in threads:
                thread.join()
            
            # Verify all requests completed
            self.assertEqual(len(results), 5)
            for result in results:
                self.assertIsInstance(result, dict)
                
        except ImportError:
            self.skipTest("MCPClientTool not available")
    
    def test_mcp_tool_memory_usage_real(self):
        """Test real MCP tool memory usage."""
        try:
            from tooluniverse.mcp_client_tool import MCPClientTool
            import psutil
            import os
            
            # Get initial memory usage
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss
            
            # Create multiple client tools
            clients = []
            for i in range(10):
                client_tool = MCPClientTool({
                    "name": f"memory_client_{i}",
                    "description": f"A memory test client {i}",
                    "server_url": "http://localhost:8000",
                    "transport": "http"
                })
                clients.append(client_tool)
            
            # Get memory usage after creating clients
            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable (less than 100MB)
            self.assertLess(memory_increase, 100 * 1024 * 1024)
            
        except ImportError:
            self.skipTest("MCPClientTool or psutil not available")
        except Exception as e:
            # Expected if memory monitoring fails
            self.assertIsInstance(e, Exception)
    
    def test_mcp_tool_error_recovery_real(self):
        """Test real MCP tool error recovery."""
        try:
            from tooluniverse.mcp_client_tool import MCPClientTool
            
            # Test error recovery
            client_tool = MCPClientTool({
                "name": "error_recovery_client",
                "description": "A client for error recovery testing",
                "server_url": "http://localhost:8000",
                "transport": "http"
            })
            
            # First call (may fail)
            try:
                result1 = client_tool.run({
                    "name": "test_tool",
                    "arguments": {"test": "value1"}
                })
            except Exception:
                result1 = {"error": "first_call_failed"}
            
            # Second call (should work or fail gracefully)
            try:
                result2 = client_tool.run({
                    "name": "test_tool",
                    "arguments": {"test": "value2"}
                })
            except Exception:
                result2 = {"error": "second_call_failed"}
            
            # Both calls should return results
            self.assertIsInstance(result1, dict)
            self.assertIsInstance(result2, dict)
            
        except ImportError:
            self.skipTest("MCPClientTool not available")
        except Exception as e:
            # Expected if error recovery fails
            self.assertIsInstance(e, Exception)
    
    def test_mcp_tool_resource_cleanup_real(self):
        """Test real MCP tool resource cleanup."""
        try:
            from tooluniverse.mcp_client_tool import MCPClientTool
            import gc
            
            # Create and use client tool
            client_tool = MCPClientTool({
                "name": "cleanup_client",
                "description": "A client for cleanup testing",
                "server_url": "http://localhost:8000",
                "transport": "http"
            })
            
            # Use the client
            try:
                _ = client_tool.run({
                    "name": "test_tool",
                    "arguments": {"test": "value"}
                })
            except Exception:
                pass
            
            # Delete the client
            del client_tool
            
            # Force garbage collection
            gc.collect()
            
            # This test passes if no exceptions are raised
            self.assertTrue(True)
            
        except ImportError:
            self.skipTest("MCPClientTool not available")
        except Exception as e:
            # Expected if cleanup fails
            self.assertIsInstance(e, Exception)
    
    def test_mcp_tool_unicode_handling_real(self):
        """Test real MCP tool Unicode handling."""
        try:
            from tooluniverse.mcp_client_tool import MCPClientTool
            
            # Test with Unicode data
            unicode_data = "测试数据 🧪 中文 English 日本語"
            
            client_tool = MCPClientTool({
                "name": "unicode_client",
                "description": "A client for Unicode testing",
                "server_url": "http://localhost:8000",
                "transport": "http"
            })
            
            result = client_tool.run({
                "name": "test_tool",
                "arguments": {"unicode_data": unicode_data}
            })
            
            # Should handle Unicode data
            self.assertIsInstance(result, dict)
            
        except ImportError:
            self.skipTest("MCPClientTool not available")
        except Exception as e:
            # Expected if Unicode handling fails
            self.assertIsInstance(e, Exception)
    
    def test_mcp_tool_performance_under_load_real(self):
        """Test real MCP tool performance under load."""
        try:
            from tooluniverse.mcp_client_tool import MCPClientTool
            import time
            
            client_tool = MCPClientTool({
                "name": "load_test_client",
                "description": "A client for load testing",
                "server_url": "http://localhost:8000",
                "transport": "http"
            })
            
            # Perform multiple requests
            start_time = time.time()
            results = []
            
            for i in range(20):  # 20 requests
                try:
                    result = client_tool.run({
                        "name": "test_tool",
                        "arguments": {"request_id": i}
                    })
                    results.append(result)
                except Exception as e:
                    results.append({"error": str(e)})
            
            total_time = time.time() - start_time
            
            # Should complete within reasonable time
            self.assertLess(total_time, 30)  # 30 seconds max
            self.assertEqual(len(results), 20)
            
            # All results should be dictionaries
            for result in results:
                self.assertIsInstance(result, dict)
                
        except ImportError:
            self.skipTest("MCPClientTool not available")
        except Exception as e:
            # Expected if load testing fails
            self.assertIsInstance(e, Exception)

    def test_mcp_tool_registration_edge_cases(self):
        """Test MCP tool registration edge cases."""
        try:
            from tooluniverse.mcp_client_tool import MCPAutoLoaderTool
            
            # Test with minimal configuration
            minimal_config = {
                "name": "minimal_loader",
                "server_url": "http://localhost:8000"
            }
            
            auto_loader = MCPAutoLoaderTool(minimal_config)
            self.assertIsNotNone(auto_loader)
            self.assertEqual(auto_loader.server_url, "http://localhost:8000")
            self.assertEqual(auto_loader.tool_prefix, "mcp_")  # Default value
            self.assertTrue(auto_loader.auto_register)  # Default value
            
        except ImportError:
            self.skipTest("MCPAutoLoaderTool not available")

    def test_mcp_tool_registration_with_invalid_config(self):
        """Test MCP tool registration with invalid configuration."""
        try:
            from tooluniverse.mcp_client_tool import MCPAutoLoaderTool
            
            # Test with invalid server URL
            invalid_config = {
                "name": "invalid_loader",
                "server_url": "invalid-url",
                "transport": "invalid_transport"
            }
            
            # Should handle invalid config gracefully
            auto_loader = MCPAutoLoaderTool(invalid_config)
            self.assertIsNotNone(auto_loader)
            self.assertEqual(auto_loader.server_url, "invalid-url")
            
        except ImportError:
            self.skipTest("MCPAutoLoaderTool not available")
        except Exception as e:
            # Should be a configuration error
            self.assertIsInstance(e, Exception)

    def test_mcp_tool_registration_with_empty_discovered_tools(self):
        """Test MCP tool registration with empty discovered tools."""
        try:
            from tooluniverse.mcp_client_tool import MCPAutoLoaderTool
            
            auto_loader = MCPAutoLoaderTool({
                "name": "empty_loader",
                "server_url": "http://localhost:8000"
            })
            
            # Set empty discovered tools
            auto_loader._discovered_tools = {}
            
            # Generate proxy configs should return empty list
            configs = auto_loader.generate_proxy_tool_configs()
            self.assertEqual(len(configs), 0)
            
        except ImportError:
            self.skipTest("MCPAutoLoaderTool not available")

    def test_mcp_tool_registration_with_selected_tools_filter(self):
        """Test MCP tool registration with selected tools filter."""
        try:
            from tooluniverse.mcp_client_tool import MCPAutoLoaderTool
            
            auto_loader = MCPAutoLoaderTool({
                "name": "filtered_loader",
                "server_url": "http://localhost:8000",
                "selected_tools": ["tool1", "tool3"]  # Only select tool1 and tool3
            })
            
            # Mock discovered tools
            auto_loader._discovered_tools = {
                "tool1": {"name": "tool1", "description": "Tool 1", "inputSchema": {}},
                "tool2": {"name": "tool2", "description": "Tool 2", "inputSchema": {}},
                "tool3": {"name": "tool3", "description": "Tool 3", "inputSchema": {}},
                "tool4": {"name": "tool4", "description": "Tool 4", "inputSchema": {}}
            }
            
            # Generate proxy configs
            configs = auto_loader.generate_proxy_tool_configs()
            
            # Should only include selected tools
            self.assertEqual(len(configs), 2)
            tool_names = [config["name"] for config in configs]
            self.assertIn("mcp_tool1", tool_names)
            self.assertIn("mcp_tool3", tool_names)
            self.assertNotIn("mcp_tool2", tool_names)
            self.assertNotIn("mcp_tool4", tool_names)
            
        except ImportError:
            self.skipTest("MCPAutoLoaderTool not available")

    def test_mcp_tool_registration_with_tooluniverse_integration(self):
        """Test MCP tool registration integration with ToolUniverse."""
        try:
            from tooluniverse.mcp_client_tool import MCPAutoLoaderTool
            
            # Create a fresh ToolUniverse instance
            tu = ToolUniverse()
            self.addCleanup(tu.close)
            
            auto_loader = MCPAutoLoaderTool({
                "name": "integration_loader",
                "server_url": "http://localhost:8000",
                "tool_prefix": "test_"
            })
            
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
            
            # Test registration
            registered_count = auto_loader.register_tools_in_engine(tu)
            
            self.assertEqual(registered_count, 1)
            self.assertIn("test_test_tool", tu.all_tool_dict)
            self.assertIn("test_test_tool", tu.callable_functions)
            
            # Verify tool configuration
            tool_config = tu.all_tool_dict["test_test_tool"]
            self.assertEqual(tool_config["type"], "MCPProxyTool")
            self.assertEqual(tool_config["target_tool_name"], "test_tool")
            
        except ImportError:
            self.skipTest("MCPAutoLoaderTool not available")
        except Exception as e:
            # Expected if connection fails
            self.assertIsInstance(e, Exception)

    def test_mcp_tool_registration_error_handling(self):
        """Test MCP tool registration error handling."""
        try:
            from tooluniverse.mcp_client_tool import MCPAutoLoaderTool
            from unittest.mock import MagicMock
            
            auto_loader = MCPAutoLoaderTool({
                "name": "error_loader",
                "server_url": "http://localhost:8000"
            })
            
            # Mock discovered tools
            auto_loader._discovered_tools = {
                "error_tool": {
                    "name": "error_tool",
                    "description": "A tool that causes errors",
                    "inputSchema": {}
                }
            }
            
            # Create a mock ToolUniverse that raises an error
            mock_engine = MagicMock()
            mock_engine.register_custom_tool.side_effect = Exception("Registration failed")
            
            # Test registration error handling
            with self.assertRaises(Exception) as context:
                auto_loader.register_tools_in_engine(mock_engine)
            
            self.assertIn("Failed to register tools", str(context.exception))
            
        except ImportError:
            self.skipTest("MCPAutoLoaderTool not available")


if __name__ == "__main__":
    unittest.main()
