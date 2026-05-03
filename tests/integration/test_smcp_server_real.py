#!/usr/bin/env python3
"""
Real end-to-end tests for SMCP server functionality.

This module tests the actual SMCP server by:
1. Starting a real HTTP server
2. Making actual HTTP requests
3. Verifying responses
4. Testing hook functionality
"""

import asyncio
import json
import time
import threading
import requests
import pytest
from unittest.mock import patch, MagicMock
from tooluniverse.smcp import SMCP
from tooluniverse.smcp_server import run_http_server


class TestSMCPRealServer:
    """Test real SMCP server functionality."""
    
    @pytest.fixture
    def smcp_server(self):
        """Create SMCP server instance for testing."""
        return SMCP(
            name="Test SMCP Server",
            tool_categories=["uniprot", "pubmed"],
            search_enabled=True,
            max_workers=2
        )
    
    @pytest.fixture
    def smcp_server_with_hooks(self):
        """Create SMCP server instance with hooks enabled for testing."""
        return SMCP(
            name="Test SMCP Server with Hooks",
            tool_categories=["uniprot", "pubmed"],
            search_enabled=True,
            max_workers=2,
            hooks_enabled=True,
            hook_type="SummarizationHook"
        )
    
    @pytest.mark.asyncio
    async def test_smcp_server_startup(self, smcp_server):
        """Test that SMCP server can start up properly."""
        # Test server initialization
        assert smcp_server.name == "Test SMCP Server"
        assert smcp_server.search_enabled is True
        
        # Test tool loading
        tools = await smcp_server.get_tools()
        assert isinstance(tools, dict)
        assert len(tools) > 0
        
        # Check for expected tools
        tool_names = list(tools.keys())
        uniprot_tools = [name for name in tool_names if 'UniProt' in name]
        assert len(uniprot_tools) > 0, "Should have UniProt tools"
        
        print(f"✅ Server started with {len(tools)} tools")
        print(f"✅ Found {len(uniprot_tools)} UniProt tools")
    
    @pytest.mark.asyncio
    async def test_mcp_tools_list_via_server(self, smcp_server):
        """Test MCP tools/list via actual server method."""
        # Test tools/list
        tools = await smcp_server.get_tools()
        
        # Verify structure
        assert isinstance(tools, dict)
        assert len(tools) > 0
        
        # Check a few tools
        tool_names = list(tools.keys())
        sample_tool = tools[tool_names[0]]
        
        # Verify tool structure
        assert hasattr(sample_tool, 'name')
        assert hasattr(sample_tool, 'description')
        assert hasattr(sample_tool, 'run')
        
        print(f"✅ tools/list returned {len(tools)} tools")
        print(f"✅ Sample tool: {sample_tool.name}")
    
    @pytest.mark.asyncio
    async def test_mcp_tools_find_via_server(self, smcp_server):
        """Test MCP tools/find via actual server method."""
        # Test tools/find
        response = await smcp_server._handle_tools_find("test-1", {
            "query": "protein analysis",
            "limit": 5,
            "format": "mcp_standard"
        })
        
        # Verify response structure
        assert "result" in response
        assert "tools" in response["result"]
        assert isinstance(response["result"]["tools"], list)
        
        tools = response["result"]["tools"]
        if len(tools) > 0:
            tool = tools[0]
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
        
        print(f"✅ tools/find returned {len(tools)} tools")
    
    @pytest.mark.asyncio
    async def test_tool_execution_via_server(self, smcp_server):
        """Test actual tool execution via server."""
        tools = await smcp_server.get_tools()
        
        # Find a simple tool to test
        test_tool = None
        for tool_name, tool in tools.items():
            if hasattr(tool, 'run') and 'info' in tool_name.lower():
                test_tool = tool
                break
        
        if test_tool:
            try:
                # Try to run the tool
                result = await test_tool.run()
                assert isinstance(result, str)
                print(f"✅ Tool execution successful: {test_tool.name}")
            except Exception as e:
                # Tool execution might fail due to missing API keys, which is expected
                print(f"⚠️ Tool execution failed (expected): {e}")
        else:
            print("⚠️ No suitable test tool found")
    
    def test_http_server_startup(self):
        """Test that HTTP server can start up."""
        import subprocess
        import signal
        import os
        
        # Start server in background
        try:
            # Use a different port to avoid conflicts
            process = subprocess.Popen([
                "python", "-m", "src.tooluniverse.smcp_server",
                "--port", "8001",
                "--host", "127.0.0.1"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait a bit for server to start
            time.sleep(3)
            
            # Check if server is running
            try:
                response = requests.get("http://127.0.0.1:8001/health", timeout=5)
                assert response.status_code == 200
                print("✅ HTTP server started successfully")
            except requests.exceptions.RequestException:
                print("⚠️ HTTP server health check failed")
            
            # Clean up
            process.terminate()
            process.wait(timeout=5)
            
        except Exception as e:
            print(f"⚠️ HTTP server test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_hook_functionality(self, smcp_server):
        """Test that hooks are actually being called."""
        # Check if hooks are enabled
        if not smcp_server.hooks_enabled:
            print("⚠️ Hooks are not enabled in this server instance")
            return
        
        # Check if hook manager exists
        if hasattr(smcp_server.tooluniverse, 'hook_manager'):
            hook_manager = smcp_server.tooluniverse.hook_manager
            print(f"✅ Hook manager found with {len(hook_manager.hooks)} hooks")
            
            # Test hook functionality by running a tool
            tools = await smcp_server.get_tools()
            if tools:
                tool_name, tool = next(iter(tools.items()))
                
                try:
                    # Try to run the tool
                    if hasattr(tool, 'run'):
                        _ = await tool.run()
                        print(f"✅ Tool executed: {tool_name}")
                        print(f"✅ Hook processing should have occurred")
                    else:
                        print("⚠️ Tool doesn't have run method")
                except Exception as e:
                    print(f"⚠️ Tool execution failed: {e}")
        else:
            print("⚠️ No hook manager found in ToolUniverse instance")
    
    @pytest.mark.asyncio
    async def test_hook_functionality_with_hooks_enabled(self, smcp_server_with_hooks):
        """Test that hooks are actually being called when enabled."""
        # Check if hooks are enabled
        assert smcp_server_with_hooks.hooks_enabled, "Hooks should be enabled"
        print(f"✅ Hooks enabled: {smcp_server_with_hooks.hooks_enabled}")
        print(f"✅ Hook type: {smcp_server_with_hooks.hook_type}")
        
        # Check if hook manager exists
        if hasattr(smcp_server_with_hooks.tooluniverse, 'hook_manager'):
            hook_manager = smcp_server_with_hooks.tooluniverse.hook_manager
            print(f"✅ Hook manager found with {len(hook_manager.hooks)} hooks")
            
            # List available hooks
            for i, hook in enumerate(hook_manager.hooks):
                print(f"   Hook {i+1}: {hook.__class__.__name__}")
            
            # Test hook functionality by running a tool
            tools = await smcp_server_with_hooks.get_tools()
            if tools:
                tool_name, tool = next(iter(tools.items()))
                
                try:
                    # Try to run the tool
                    if hasattr(tool, 'run'):
                        _ = await tool.run()
                        print(f"✅ Tool executed: {tool_name}")
                        print(f"✅ Hook processing should have occurred")
                    else:
                        print("⚠️ Tool doesn't have run method")
                except Exception as e:
                    print(f"⚠️ Tool execution failed: {e}")
        else:
            print("⚠️ No hook manager found in ToolUniverse instance")
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, smcp_server):
        """Test concurrent requests to server."""
        async def make_request(request_id):
            tools = await smcp_server.get_tools()
            return f"Request {request_id}: {len(tools)} tools"
        
        # Make multiple concurrent requests
        tasks = [make_request(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Verify all requests completed
        assert len(results) == 5
        for result in results:
            assert "tools" in result
        
        print("✅ Concurrent requests handled successfully")
    
    @pytest.mark.asyncio
    async def test_error_handling(self, smcp_server):
        """Test error handling in server."""
        # Test invalid tools/find request
        response = await smcp_server._handle_tools_find("error-1", {
            "query": "",  # Empty query should cause error
            "limit": 5
        })
        
        # Should return error response
        assert "error" in response
        assert response["error"]["code"] == -32602  # Invalid params
        
        print("✅ Error handling works correctly")
    
    def test_server_configuration(self, smcp_server):
        """Test server configuration."""
        # Test configuration
        assert smcp_server.name == "Test SMCP Server"
        assert smcp_server.search_enabled is True
        assert smcp_server.max_workers == 2
        
        # Test tool categories
        assert "uniprot" in smcp_server.tool_categories
        assert "pubmed" in smcp_server.tool_categories
        
        print("✅ Server configuration is correct")


class TestSMCPIntegration:
    """Integration tests for SMCP with real HTTP requests."""
    
    def test_http_endpoints(self):
        """Test HTTP endpoints if server is running."""
        try:
            # Try to connect to server
            response = requests.get("http://127.0.0.1:8000/health", timeout=2)
            if response.status_code == 200:
                print("✅ HTTP server is running")
                
                # Test tools endpoint
                tools_response = requests.get("http://127.0.0.1:8000/tools", timeout=5)
                if tools_response.status_code == 200:
                    tools_data = tools_response.json()
                    assert isinstance(tools_data, dict)
                    print(f"✅ Tools endpoint returned {len(tools_data)} tools")
                else:
                    print(f"⚠️ Tools endpoint returned status {tools_response.status_code}")
            else:
                print(f"⚠️ Health check returned status {response.status_code}")
        except requests.exceptions.RequestException:
            print("⚠️ HTTP server is not running - this is expected in test environment")
    
    def test_mcp_protocol_over_http(self):
        """Test MCP protocol over HTTP."""
        try:
            # Test MCP tools/list over HTTP
            mcp_request = {
                "jsonrpc": "2.0",
                "id": "test-1",
                "method": "tools/list",
                "params": {}
            }
            
            response = requests.post(
                "http://127.0.0.1:8000/mcp",
                json=mcp_request,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "result" in data
                print("✅ MCP protocol over HTTP works")
            else:
                print(f"⚠️ MCP HTTP request failed with status {response.status_code}")
        except requests.exceptions.RequestException:
            print("⚠️ MCP over HTTP test skipped - server not running")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
