#!/usr/bin/env python3
"""
Real HTTP server tests for SMCP functionality.

This module tests the actual SMCP HTTP server by:
1. Starting a real HTTP server in a separate process
2. Making actual HTTP requests to the server
3. Verifying responses and functionality
4. Testing MCP protocol over HTTP
"""

import asyncio
import json
import time
import subprocess
import signal
import os
import requests
import pytest
import sys

# Ensure src/ is importable
CURRENT_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.join(CURRENT_DIR, "..", "..", "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

try:
    from tooluniverse.smcp import SMCP  # type: ignore
except ImportError:
    # Fallback for when running from different directory
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from tooluniverse.smcp import SMCP  # type: ignore


class TestSMCPHTTPServer:
    """Test real SMCP HTTP server functionality."""
    
    @pytest.fixture(scope="class")
    def smcp_server_process(self):
        """Start SMCP HTTP server in background process."""
        # Start server on a different port to avoid conflicts
        process = subprocess.Popen([
            "python", "-m", "tooluniverse.smcp_server",
            "--port", "8002",
            "--host", "127.0.0.1",
            "--tool-categories", "uniprot,pubmed"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=SRC_DIR)
        
        # Wait for server to start
        time.sleep(5)
        
        yield process
        
        # Clean up
        try:
            process.terminate()
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    
    def test_server_health_check(self, smcp_server_process):
        """Test server health endpoint.
        
        Note: FastMCP does not provide a /health REST endpoint by default.
        This test is skipped as it expects an endpoint that doesn't exist.
        Health checking should be done via MCP protocol or server process status.
        """
        pytest.skip("FastMCP does not provide /health REST endpoint by default")
    
    def test_tools_endpoint(self, smcp_server_process):
        """Test tools endpoint.
        
        Note: FastMCP does not provide a /tools REST endpoint by default.
        This test is skipped as it expects an endpoint that doesn't exist.
        Tools should be accessed via MCP protocol using POST /mcp with tools/list method.
        """
        pytest.skip("FastMCP does not provide /tools REST endpoint by default")
    
    def test_mcp_tools_list_over_http(self, smcp_server_process):
        """Test MCP tools/list over HTTP.
        
        Note: FastMCP with streamable-http transport requires proper MCP client
        library usage rather than direct POST requests.
        """
        pytest.skip(
            "FastMCP streamable-http requires proper MCP client, "
            "not raw HTTP POST requests"
        )
    
    def test_mcp_tools_find_over_http(self, smcp_server_process):
        """Test MCP tools/find over HTTP.
        
        Note: FastMCP with streamable-http transport requires proper MCP client
        library usage rather than direct POST requests.
        """
        pytest.skip(
            "FastMCP streamable-http requires proper MCP client, "
            "not raw HTTP POST requests"
        )
    
    def test_mcp_tools_call_over_http(self, smcp_server_process):
        """Test MCP tools/call over HTTP.
        
        Note: FastMCP with streamable-http transport requires proper MCP client
        library usage rather than direct POST requests.
        """
        pytest.skip(
            "FastMCP streamable-http requires proper MCP client, "
            "not raw HTTP POST requests"
        )
        
        # Unreachable code after skip - kept for reference but should be
        # removed if properly implemented
        try:
            # First get tools list
            tools_request = {
                "jsonrpc": "2.0",
                "id": "tools-list",
                "method": "tools/list",
                "params": {}
            }
            
            tools_response = requests.post(
                "http://127.0.0.1:8002/mcp",
                json=tools_request,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if tools_response.status_code != 200:
                pytest.skip("Could not get tools list")
            
            tools_data = tools_response.json()
            tools = tools_data["result"]["tools"]
            
            # Find a simple tool to test
            test_tool = None
            for tool in tools:
                if "info" in tool["name"].lower():
                    test_tool = tool
                    break
            
            if not test_tool:
                pytest.skip("No suitable test tool found")
            
            # Try to call the tool
            call_request = {
                "jsonrpc": "2.0",
                "id": "test-call",
                "method": "tools/call",
                "params": {
                    "name": test_tool["name"],
                    "arguments": {}
                }
            }
            
            call_response = requests.post(
                "http://127.0.0.1:8002/mcp",
                json=call_request,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            assert call_response.status_code == 200
            call_data = call_response.json()
            
            # Should either succeed or fail gracefully
            if "result" in call_data:
                print(f"✅ Tool call succeeded: {test_tool['name']}")
            elif "error" in call_data:
                print(f"⚠️ Tool call failed (expected): {call_data['error']['message']}")
            else:
                pytest.fail("Unexpected response format")
        except requests.exceptions.RequestException as e:
            pytest.skip(f"MCP tools/call not accessible: {e}")
    
    def test_concurrent_http_requests(self, smcp_server_process):
        """Test concurrent HTTP requests to server using MCP protocol.
        
        Note: FastMCP with streamable-http transport requires proper MCP client
        library usage rather than direct POST requests.
        """
        pytest.skip(
            "FastMCP streamable-http requires proper MCP client, "
            "not raw HTTP POST requests"
        )
    
    def test_error_handling_over_http(self, smcp_server_process):
        """Test error handling over HTTP.
        
        Note: FastMCP with streamable-http transport requires proper MCP client
        library usage rather than direct POST requests.
        """
        pytest.skip(
            "FastMCP streamable-http requires proper MCP client, "
            "not raw HTTP POST requests"
        )
        
        # Unreachable code after skip - kept for reference but should be
        # removed if properly implemented
        try:
            # Test invalid MCP request
            invalid_request = {
                "jsonrpc": "2.0",
                "id": "error-test",
                "method": "invalid/method",
                "params": {}
            }
            
            response = requests.post(
                "http://127.0.0.1:8002/mcp",
                json=invalid_request,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "error" in data
            assert data["error"]["code"] == -32601  # Method not found
            
            print("✅ Error handling works correctly over HTTP")
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Error handling test failed: {e}")


class TestSMCPDirectIntegration:
    """Test SMCP server directly without HTTP."""
    
    @pytest.mark.asyncio
    async def test_smcp_server_direct_startup(self):
        """Test SMCP server startup directly."""
        server = SMCP(
            name="Direct Test Server",
            tool_categories=["uniprot", "pubmed"],
            search_enabled=True,
            max_workers=2
        )
        
        # Test server initialization
        assert server.name == "Direct Test Server"
        assert server.search_enabled is True
        
        # Test tool loading
        tools = await server.get_tools()
        assert isinstance(tools, dict)
        assert len(tools) > 0
        
        print(f"✅ Direct server started with {len(tools)} tools")
    
    @pytest.mark.asyncio
    async def test_smcp_with_hooks_direct(self):
        """Test SMCP server with hooks enabled directly."""
        server = SMCP(
            name="Hooks Test Server",
            tool_categories=["uniprot", "pubmed"],
            search_enabled=True,
            max_workers=2,
            hooks_enabled=True,
            hook_type="SummarizationHook"
        )
        
        # Test server initialization
        assert server.hooks_enabled is True
        assert server.hook_type == "SummarizationHook"
        
        # Test tool loading
        tools = await server.get_tools()
        assert isinstance(tools, dict)
        assert len(tools) > 0
        
        # Check if hook manager exists
        if hasattr(server.tooluniverse, 'hook_manager'):
            hook_manager = server.tooluniverse.hook_manager
            print(f"✅ Hook manager found with {len(hook_manager.hooks)} hooks")
        else:
            print("⚠️ No hook manager found")
        
        print(f"✅ Hooks-enabled server started with {len(tools)} tools")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
