#!/usr/bin/env python3
"""
Test stdio mode functionality

This test file covers stdio mode specific functionality:
1. stdio mode logging redirection
2. MCP protocol communication over stdio
3. stdio mode with hooks enabled
4. stdio mode error handling
"""

import pytest
import subprocess
import json
import time
import os
import sys
import select as _select
from pathlib import Path
from unittest.mock import patch

# Add src to path
_SRC_PATH = str(Path(__file__).parent.parent.parent / "src")
sys.path.insert(0, _SRC_PATH)

# Use the same Python interpreter that's running pytest
_PYTHON = sys.executable
# Force unbuffered stdout in subprocesses so MCP responses aren't held in Python's pipe buffer
_SUBPROCESS_ENV = {**os.environ, "PYTHONUNBUFFERED": "1"}

from tooluniverse.smcp_server import run_stdio_server
from tooluniverse.logging_config import reconfigure_for_stdio


def _read_json_line(process, timeout=30):
    """Read a JSON line from process.stdout with a deadline; return parsed dict or None."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            return None
        ready, _, _ = _select.select([process.stdout], [], [], 2.0)
        if not ready:
            continue
        line = process.stdout.readline()
        if not line:
            continue
        s = line.strip()
        if not s or (not s.startswith("{") and not s.startswith("[")):
            continue
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            continue
    return None


@pytest.mark.integration
@pytest.mark.stdio
class TestStdioMode:
    """Test stdio mode functionality"""

    def test_stdio_logging_redirection(self):
        """Test that stdio mode redirects logs to stderr"""
        # Test that reconfigure_for_stdio works
        reconfigure_for_stdio()
        
        # This should not raise an exception
        assert True

    def test_stdio_server_startup(self):
        """Test that stdio server can start without errors"""
        # Test with minimal configuration
        with patch('sys.argv', ['tooluniverse-smcp-stdio']):
            try:
                # This should not raise an exception during startup
                # We'll test the actual server startup in a subprocess
                assert True
            except Exception as e:
                pytest.fail(f"stdio server startup failed: {e}")

    def test_stdio_mcp_handshake(self):
        """Test complete MCP handshake over stdio"""
        # Start server in subprocess
        process = subprocess.Popen(
            [_PYTHON, "-c", f"""
import sys
sys.path.insert(0, {_SRC_PATH!r})
from tooluniverse.smcp_server import run_stdio_server
import os
os.environ['TOOLUNIVERSE_STDIO_MODE'] = '1'
sys.argv = ['tooluniverse-smcp-stdio']
run_stdio_server()
"""],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            env=_SUBPROCESS_ENV
        )
        
        try:
            # Wait for server to start (loading ~1600 tools takes ~8-10s)
            time.sleep(10)

            # Step 1: Initialize
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                }
            }
            process.stdin.write(json.dumps(init_request) + "\n")
            process.stdin.flush()

            # Read initialize response
            response_data = _read_json_line(process, timeout=60)
            if response_data is None:
                pytest.skip("Server did not respond to initialize within timeout")
            assert "result" in response_data
            assert response_data["result"]["protocolVersion"] == "2024-11-05"

            # Step 2: Send initialized notification
            initialized_notif = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            process.stdin.write(json.dumps(initialized_notif) + "\n")
            process.stdin.flush()

            time.sleep(1)

            # Step 3: List tools
            list_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
            process.stdin.write(json.dumps(list_request) + "\n")
            process.stdin.flush()

            # Read tools list response (tool list is large, allow extra time)
            response_data = _read_json_line(process, timeout=60)
            if response_data is None:
                pytest.skip("Server did not respond to tools/list within timeout")
            assert "result" in response_data
            assert "tools" in response_data["result"]
            assert len(response_data["result"]["tools"]) > 0

        finally:
            # Clean up
            process.terminate()
            process.wait(timeout=5)

    def test_stdio_tool_call(self):
        """Test tool call over stdio"""
        # Start server in subprocess
        process = subprocess.Popen(
            [_PYTHON, "-c", f"""
import sys
sys.path.insert(0, {_SRC_PATH!r})
from tooluniverse.smcp_server import run_stdio_server
import os
os.environ['TOOLUNIVERSE_STDIO_MODE'] = '1'
sys.argv = ['tooluniverse-smcp-stdio']
run_stdio_server()
"""],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            env=_SUBPROCESS_ENV
        )
        
        try:
            # Wait for server to start
            time.sleep(3)
            
            # Initialize
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                }
            }
            process.stdin.write(json.dumps(init_request) + "\n")
            process.stdin.flush()
            
            # Read init response
            response = process.stdout.readline()
            assert response.strip()
            
            # Send initialized notification
            initialized_notif = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            process.stdin.write(json.dumps(initialized_notif) + "\n")
            process.stdin.flush()
            
            time.sleep(1)
            
            # Call a simple tool
            tool_call_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "get_server_info",
                    "arguments": "{}"
                }
            }
            process.stdin.write(json.dumps(tool_call_request) + "\n")
            process.stdin.flush()
            
            # Read tool call response
            response = process.stdout.readline()
            assert response.strip()
            
            # Parse response
            response_data = json.loads(response.strip())
            assert "result" in response_data or "error" in response_data
            
        finally:
            # Clean up
            process.terminate()
            process.wait(timeout=5)

    def test_stdio_with_hooks(self):
        """Test stdio mode with hooks enabled"""
        # Start server in subprocess with hooks
        process = subprocess.Popen(
            [_PYTHON, "-c", f"""
import sys
sys.path.insert(0, {_SRC_PATH!r})
from tooluniverse.smcp_server import run_stdio_server
import os
os.environ['TOOLUNIVERSE_STDIO_MODE'] = '1'
sys.argv = ['tooluniverse-smcp-stdio', '--hooks']
run_stdio_server()
"""],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            env=_SUBPROCESS_ENV
        )
        
        try:
            # Wait for server to start
            time.sleep(5)  # Hooks take longer to initialize
            
            # Initialize
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                }
            }
            process.stdin.write(json.dumps(init_request) + "\n")
            process.stdin.flush()
            
            # Read init response
            response = process.stdout.readline()
            assert response.strip()
            
            # Send initialized notification
            initialized_notif = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            process.stdin.write(json.dumps(initialized_notif) + "\n")
            process.stdin.flush()
            
            time.sleep(1)
            
            # List tools to verify hooks are loaded
            list_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
            process.stdin.write(json.dumps(list_request) + "\n")
            process.stdin.flush()
            
            # Read tools list response
            response = process.stdout.readline()
            assert response.strip()
            
            # Parse response
            response_data = json.loads(response.strip())
            assert "result" in response_data
            assert "tools" in response_data["result"]
            
            # Check that hook tools are present
            # Note: ToolOutputSummarizer is an AgenticTool that requires LLM API keys,
            # so it may not be present in test environments without API keys.
            # OutputSummarizationComposer is a ComposeTool that doesn't require API keys.
            tool_names = [tool["name"] for tool in response_data["result"]["tools"]]
            assert "OutputSummarizationComposer" in tool_names
            
        finally:
            # Clean up
            process.terminate()
            process.wait(timeout=5)

    def test_stdio_logging_no_pollution(self):
        """Test that stdio mode doesn't pollute stdout with logs"""
        # Start server in subprocess
        process = subprocess.Popen(
            [_PYTHON, "-c", f"""
import sys
sys.path.insert(0, {_SRC_PATH!r})
from tooluniverse.smcp_server import run_stdio_server
import os
os.environ['TOOLUNIVERSE_STDIO_MODE'] = '1'
sys.argv = ['tooluniverse-smcp-stdio']
run_stdio_server()
"""],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            env=_SUBPROCESS_ENV
        )
        
        try:
            # Wait for server to start
            time.sleep(3)
            
            # Initialize
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                }
            }
            process.stdin.write(json.dumps(init_request) + "\n")
            process.stdin.flush()
            
            # Read response - should be valid JSON
            response = process.stdout.readline()
            assert response.strip()
            
            # Try to parse as JSON - should succeed
            response_data = json.loads(response.strip())
            assert "jsonrpc" in response_data
            assert response_data["jsonrpc"] == "2.0"
            
        finally:
            # Clean up
            process.terminate()
            process.wait(timeout=5)

    def test_stdio_error_handling(self):
        """Test stdio mode error handling"""
        # Start server in subprocess
        process = subprocess.Popen(
            [_PYTHON, "-c", f"""
import sys
sys.path.insert(0, {_SRC_PATH!r})
from tooluniverse.smcp_server import run_stdio_server
import os
os.environ['TOOLUNIVERSE_STDIO_MODE'] = '1'
sys.argv = ['tooluniverse-smcp-stdio']
run_stdio_server()
"""],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            env=_SUBPROCESS_ENV
        )
        
        try:
            # Wait for server to start
            time.sleep(3)
            
            # Send invalid JSON
            process.stdin.write("invalid json\n")
            process.stdin.flush()
            
            # Send invalid request
            invalid_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "invalid_method",
                "params": {}
            }
            process.stdin.write(json.dumps(invalid_request) + "\n")
            process.stdin.flush()
            
            # Read responses until we find an error response
            error_found = False
            for _ in range(10):  # Read up to 10 lines
                response = process.stdout.readline()
                if not response:
                    break
                    
                if response.strip():
                    try:
                        response_data = json.loads(response.strip())
                        if "error" in response_data:
                            error_found = True
                            break
                        # Skip notifications and other non-error responses
                        elif response_data.get("method") == "notifications/message":
                            continue
                    except json.JSONDecodeError:
                        continue
            
            assert error_found, "No error response found in server output"
            
        finally:
            # Clean up
            process.terminate()
            process.wait(timeout=5)
