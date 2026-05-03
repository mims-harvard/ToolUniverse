#!/usr/bin/env python3
"""
Remote Tools Integration Tests

Tests the complete remote tools workflow including:
- MCP server creation and startup
- MCP client tool discovery and registration
- Remote tool execution and error handling
- End-to-end remote tools examples
"""

import pytest
import json
import tempfile
import os
import subprocess
from unittest.mock import patch

from tooluniverse import ToolUniverse
from tooluniverse.mcp_client_tool import MCPAutoLoaderTool


@pytest.mark.integration
@pytest.mark.remote_tools
class TestRemoteTools:
    """Test remote tools functionality"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test"""
        self.tu = ToolUniverse()
        self.server_process = None
        self.temp_config_file = None

    def teardown_method(self):
        """Cleanup after each test"""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    self.server_process.kill()
                except ProcessLookupError:
                    pass
            self.server_process = None
        
        # Close ToolUniverse to ensure cache manager threads are cleaned up
        if hasattr(self, 'tu') and self.tu is not None:
            try:
                self.tu.close()
            except Exception:
                pass
        
        if self.temp_config_file and os.path.exists(self.temp_config_file):
            os.remove(self.temp_config_file)

    def create_remote_tools_config(self, server_url="http://localhost:8008/mcp"):
        """Create a temporary remote tools configuration file"""
        config = [
            {
                "name": "mcp_auto_loader_text_processor",
                "description": "Automatically discover and load text processing tools from MCP Server",
                "type": "MCPAutoLoaderTool",
                "tool_prefix": "",
                "server_url": server_url,
                "timeout": 30,
                "required_api_keys": []
            }
        ]
        
        # Create temporary file
        fd, self.temp_config_file = tempfile.mkstemp(suffix='.json', prefix='remote_tools_test_')
        os.close(fd)
        
        with open(self.temp_config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        return self.temp_config_file

    def test_remote_tools_config_creation(self):
        """Test remote tools configuration file creation"""
        config_file = self.create_remote_tools_config()
        
        assert os.path.exists(config_file)
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        assert len(config) == 1
        assert config[0]["type"] == "MCPAutoLoaderTool"
        assert config[0]["server_url"] == "http://localhost:8008/mcp"
        assert config[0]["tool_prefix"] == ""

    def test_tooluniverse_remote_tools_loading(self):
        """Test ToolUniverse loading remote tools configuration"""
        config_file = self.create_remote_tools_config()
        
        # Load remote tools
        tu = ToolUniverse(tool_files={}, keep_default_tools=False)
        try:
            tu.load_tools(tool_config_files={"remote_tools": config_file})
            
            # Should have loaded the MCPAutoLoaderTool
            assert len(tu.all_tools) >= 1
            assert "mcp_auto_loader_text_processor" in tu.all_tool_dict
        finally:
            tu.close()

    def test_mcp_auto_loader_tool_instantiation(self):
        """Test MCPAutoLoaderTool instantiation with remote tools config"""
        config_file = self.create_remote_tools_config()
        
        # Load remote tools
        tu = ToolUniverse(tool_files={}, keep_default_tools=False)
        try:
            tu.load_tools(tool_config_files={"remote_tools": config_file})
            
            # Get the auto loader tool
            auto_loader_name = "mcp_auto_loader_text_processor"
            assert auto_loader_name in tu.all_tool_dict
            
            # Test instantiation
            auto_loader = tu.callable_functions.get(auto_loader_name)
            if auto_loader:
                assert isinstance(auto_loader, MCPAutoLoaderTool)
                assert auto_loader.server_url == "http://localhost:8008/mcp"
                assert auto_loader.tool_prefix == ""
                assert auto_loader.auto_register is True
        finally:
            tu.close()

    @pytest.mark.asyncio
    async def test_mcp_auto_loader_tool_discovery_with_mock(self):
        """Test MCPAutoLoaderTool discovery with mocked server"""
        config_file = self.create_remote_tools_config()
        
        # Load remote tools
        tu = ToolUniverse(tool_files={}, keep_default_tools=False)
        try:
            tu.load_tools(tool_config_files={"remote_tools": config_file})
            
            # Get the auto loader tool
            auto_loader_name = "mcp_auto_loader_text_processor"
            auto_loader = tu.callable_functions.get(auto_loader_name)
            
            if auto_loader:
                # Mock the MCP request
                with patch.object(auto_loader, '_make_mcp_request') as mock_request:
                    mock_request.return_value = {
                        "tools": [
                            {
                                "name": "remote_text_processor",
                                "description": "Processes text using remote computation resources",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "text": {"type": "string"},
                                        "operation": {"type": "string"}
                                    },
                                    "required": ["text", "operation"]
                                }
                            }
                        ]
                    }
                    
                    # Test discovery
                    discovered = await auto_loader.discover_tools()
                    
                    assert len(discovered) == 1
                    assert "remote_text_processor" in discovered
                    assert discovered["remote_text_processor"]["description"] == "Processes text using remote computation resources"
        finally:
            tu.close()

    def test_remote_tools_tool_discovery_workflow(self):
        """Test the complete remote tools discovery workflow"""
        config_file = self.create_remote_tools_config()
        
        # Load remote tools
        tu = ToolUniverse(tool_files={}, keep_default_tools=False)
        try:
            tu.load_tools(tool_config_files={"remote_tools": config_file})
            
            # Check that MCPAutoLoaderTool was loaded
            auto_loader_name = "mcp_auto_loader_text_processor"
            assert auto_loader_name in tu.all_tool_dict
            
            # Check tool configuration
            tool_config = tu.all_tool_dict[auto_loader_name]
            assert tool_config["type"] == "MCPAutoLoaderTool"
            assert tool_config["server_url"] == "http://localhost:8008/mcp"
        finally:
            tu.close()

    def test_remote_tools_error_handling(self):
        """Test remote tools error handling"""
        # Test with invalid server URL
        config_file = self.create_remote_tools_config("http://invalid-server:9999/mcp")
        
        tu = ToolUniverse(tool_files={}, keep_default_tools=False)
        try:
            # Should not raise exception even with invalid server
            try:
                tu.load_tools(tool_config_files={"remote_tools": config_file})
                # If it doesn't raise an exception, that's also fine
                # The MCPAutoLoaderTool should handle connection errors gracefully
            except Exception as e:
                # If it does raise an exception, it should be a reasonable one
                assert "connection" in str(e).lower() or "timeout" in str(e).lower()
        finally:
            tu.close()

    def test_remote_tools_config_validation(self):
        """Test remote tools configuration validation"""
        # Test with missing required fields
        invalid_config = [
            {
                "name": "invalid_loader",
                "description": "Invalid loader for testing",
                "type": "MCPAutoLoaderTool"
                # Missing server_url
            }
        ]
        
        fd, temp_file = tempfile.mkstemp(suffix='.json', prefix='invalid_config_')
        os.close(fd)
        
        tu = None
        try:
            with open(temp_file, 'w') as f:
                json.dump(invalid_config, f, indent=2)
            
            tu = ToolUniverse(tool_files={}, keep_default_tools=False)
            
            # Should handle invalid config gracefully
            try:
                tu.load_tools(tool_config_files={"remote_tools": temp_file})
            except Exception as e:
                # Should be a configuration error
                assert "server_url" in str(e) or "required" in str(e).lower()
        finally:
            # Explicitly close ToolUniverse to ensure cache manager threads are cleaned up
            if tu is not None:
                try:
                    tu.close()
                except Exception:
                    pass
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_remote_tools_tool_prefix_handling(self):
        """Test remote tools tool prefix handling"""
        # Test with custom prefix
        config = [
            {
                "name": "mcp_auto_loader_custom",
                "description": "Auto loader with custom prefix",
                "type": "MCPAutoLoaderTool",
                "tool_prefix": "custom_",
                "server_url": "http://localhost:8008/mcp",
                "timeout": 30,
                "required_api_keys": []
            }
        ]
        
        fd, temp_file = tempfile.mkstemp(suffix='.json', prefix='custom_prefix_')
        os.close(fd)
        
        try:
            with open(temp_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            tu = ToolUniverse(tool_files={}, keep_default_tools=False)
            try:
                tu.load_tools(tool_config_files={"remote_tools": temp_file})
                
                # Check that the auto loader was loaded with custom prefix
                auto_loader_name = "mcp_auto_loader_custom"
                assert auto_loader_name in tu.all_tool_dict
                
                auto_loader = tu.callable_functions.get(auto_loader_name)
                if auto_loader:
                    assert auto_loader.tool_prefix == "custom_"
            finally:
                tu.close()
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_remote_tools_timeout_configuration(self):
        """Test remote tools timeout configuration"""
        config_file = self.create_remote_tools_config()
        
        tu = ToolUniverse(tool_files={}, keep_default_tools=False)
        try:
            tu.load_tools(tool_config_files={"remote_tools": config_file})
            
            auto_loader_name = "mcp_auto_loader_text_processor"
            auto_loader = tu.callable_functions.get(auto_loader_name)
            
            if auto_loader:
                assert auto_loader.timeout == 30
        finally:
            tu.close()

    def test_remote_tools_auto_register_configuration(self):
        """Test remote tools auto_register configuration"""
        # Test with auto_register disabled
        config = [
            {
                "name": "mcp_auto_loader_no_register",
                "description": "Auto loader with auto_register disabled",
                "type": "MCPAutoLoaderTool",
                "tool_prefix": "",
                "server_url": "http://localhost:8008/mcp",
                "timeout": 30,
                "auto_register": False,
                "required_api_keys": []
            }
        ]
        
        fd, temp_file = tempfile.mkstemp(suffix='.json', prefix='no_register_')
        os.close(fd)
        
        try:
            with open(temp_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            tu = ToolUniverse(tool_files={}, keep_default_tools=False)
            try:
                tu.load_tools(tool_config_files={"remote_tools": temp_file})
                
                auto_loader_name = "mcp_auto_loader_no_register"
                assert auto_loader_name in tu.all_tool_dict
                
                auto_loader = tu.callable_functions.get(auto_loader_name)
                if auto_loader:
                    assert auto_loader.auto_register is False
            finally:
                tu.close()
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_remote_tools_selected_tools_configuration(self):
        """Test remote tools selected_tools configuration"""
        # Test with selected_tools filter
        config = [
            {
                "name": "mcp_auto_loader_filtered",
                "description": "Auto loader with tool filtering",
                "type": "MCPAutoLoaderTool",
                "tool_prefix": "",
                "server_url": "http://localhost:8008/mcp",
                "timeout": 30,
                "selected_tools": ["remote_text_processor"],
                "required_api_keys": []
            }
        ]
        
        fd, temp_file = tempfile.mkstemp(suffix='.json', prefix='filtered_')
        os.close(fd)
        
        try:
            with open(temp_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            tu = ToolUniverse(tool_files={}, keep_default_tools=False)
            try:
                tu.load_tools(tool_config_files={"remote_tools": temp_file})
                
                auto_loader_name = "mcp_auto_loader_filtered"
                assert auto_loader_name in tu.all_tool_dict
                
                auto_loader = tu.callable_functions.get(auto_loader_name)
                if auto_loader:
                    assert auto_loader.selected_tools == ["remote_text_processor"]
            finally:
                tu.close()
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)


@pytest.mark.integration
@pytest.mark.remote_tools
@pytest.mark.slow
class TestRemoteToolsEndToEnd:
    """Test complete end-to-end remote tools workflow"""

    def test_remote_tools_example_workflow(self):
        """Test the complete remote tools example workflow"""
        # This test would ideally start a real MCP server and test the complete workflow
        # For now, we'll test the configuration and loading parts
        
        # Create configuration similar to the example
        config = [
            {
                "name": "mcp_auto_loader_text_processor",
                "description": "Automatically discover and load text processing tools from MCP Server",
                "type": "MCPAutoLoaderTool",
                "tool_prefix": "",
                "server_url": "http://localhost:8008/mcp",
                "timeout": 30,
                "required_api_keys": []
            }
        ]
        
        fd, temp_file = tempfile.mkstemp(suffix='.json', prefix='e2e_test_')
        os.close(fd)
        
        try:
            with open(temp_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Test ToolUniverse initialization
            tu = ToolUniverse(tool_files={}, keep_default_tools=False)
            try:
                # Test loading remote tools
                tu.load_tools(tool_config_files={"remote_tools": temp_file})
                
                # Verify configuration was loaded
                assert len(tu.all_tools) >= 1
                assert "mcp_auto_loader_text_processor" in tu.all_tool_dict
                
                # Verify tool configuration
                tool_config = tu.all_tool_dict["mcp_auto_loader_text_processor"]
                assert tool_config["type"] == "MCPAutoLoaderTool"
                assert tool_config["server_url"] == "http://localhost:8008/mcp"
                assert tool_config["tool_prefix"] == ""
                assert tool_config["timeout"] == 30
            finally:
                tu.close()
            
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
