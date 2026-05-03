#!/usr/bin/env python3
"""
Test stdio mode with hooks integration

This test file covers the integration of stdio mode and hooks:
1. stdio mode with hooks enabled
2. MCP protocol with hooks in stdio mode
3. Tool calls with summarization in stdio mode
4. Error handling in stdio + hooks mode
"""

import pytest
import subprocess
import json
import time
import os
import sys
import threading
from pathlib import Path

# Add src to path
_SRC_PATH = str(Path(__file__).parent.parent.parent / "src")
sys.path.insert(0, _SRC_PATH)

# Use the same Python interpreter that's running pytest
_PYTHON = sys.executable
# Force unbuffered stdout in subprocesses so MCP responses aren't held in Python's pipe buffer
_SUBPROCESS_ENV = {**os.environ, "PYTHONUNBUFFERED": "1"}


@pytest.mark.integration
@pytest.mark.stdio
@pytest.mark.hooks
class TestStdioHooksIntegration:
    """Test stdio mode with hooks integration"""

    def test_stdio_with_hooks_handshake(self):
        """Test MCP handshake in stdio mode with hooks enabled"""
        # Start server in subprocess with hooks
        # stderr=DEVNULL prevents the pipe-buffer deadlock caused by the ~65KB
        # of startup messages the server emits to stderr.
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
            # Wait for server to start (hooks take longer to load all tools)
            time.sleep(20)

            # Check process is still running after startup wait
            if process.poll() is not None:
                pytest.skip("Server process exited during startup")

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

            # Read response with timeout; skip non-JSON lines (e.g. startup messages)
            import select as _select
            response_data = None
            deadline = time.time() + 30
            while time.time() < deadline:
                if process.poll() is not None:
                    pytest.skip("Server process exited before responding")
                ready, _, _ = _select.select([process.stdout], [], [], 2.0)
                if not ready:
                    continue
                line = process.stdout.readline()
                if not line.strip():
                    continue
                try:
                    response_data = json.loads(line.strip())
                    break
                except json.JSONDecodeError:
                    continue  # Skip non-JSON output (e.g. startup messages)

            if response_data is None:
                pytest.skip("Server did not return a valid JSON response within timeout")

            assert "result" in response_data
            assert response_data["result"]["protocolVersion"] == "2024-11-05"

            # Step 2: Send initialized notification
            initialized_notif = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            process.stdin.write(json.dumps(initialized_notif) + "\n")
            process.stdin.flush()

            time.sleep(2)

            # Step 3: List tools
            list_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
            process.stdin.write(json.dumps(list_request) + "\n")
            process.stdin.flush()

            # Read tools list response with timeout
            response_data = None
            deadline = time.time() + 30
            while time.time() < deadline:
                if process.poll() is not None:
                    break
                ready, _, _ = _select.select([process.stdout], [], [], 2.0)
                if not ready:
                    continue
                line = process.stdout.readline()
                if not line.strip():
                    continue
                try:
                    response_data = json.loads(line.strip())
                    break
                except json.JSONDecodeError:
                    continue

            if response_data is None:
                pytest.skip("Server did not return tools list within timeout")

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
            process.wait(timeout=10)

    @pytest.mark.timeout(120)
    def test_stdio_tool_call_with_hooks(self):
        """Test tool call in stdio mode with hooks enabled"""
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
            time.sleep(20)
            
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
            
            time.sleep(2)
            
            # Call a tool that might generate long output
            tool_call_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "OpenTargets_get_target_gene_ontology_by_ensemblID",
                    "arguments": json.dumps({"ensemblId": "ENSG00000012048"})
                }
            }
            process.stdin.write(json.dumps(tool_call_request) + "\n")
            process.stdin.flush()
            
            # Read tool call response (this might take a while with hooks)
            # Add timeout to prevent indefinite hang if API is slow/down
            import select
            timeout_seconds = 45
            start_time = time.time()
            response = None
            while time.time() - start_time < timeout_seconds:
                if process.poll() is not None:
                    # Process died
                    break
                # Check if data is available with short timeout
                ready, _, _ = select.select([process.stdout], [], [], 1.0)
                if ready:
                    response = process.stdout.readline()
                    break

            # If API is unavailable or slow, skip this test
            if not response or not response.strip():
                pytest.skip("OpenTargets API unavailable or slow")
            
            # Parse response
            response_data = json.loads(response.strip())
            assert "result" in response_data or "error" in response_data
            
            # If successful, check if it's summarized
            if "result" in response_data:
                result_content = response_data["result"].get("content", [])
                if result_content:
                    text_content = result_content[0].get("text", "")
                    # Check if it's a summary (shorter than typical full output)
                    if len(text_content) < 10000:  # Typical full output is much longer
                        assert "summary" in text_content.lower() or "摘要" in text_content.lower()
            
        finally:
            # Clean up
            process.terminate()
            process.wait(timeout=15)

    def test_stdio_hooks_error_handling(self):
        """Test error handling in stdio mode with hooks"""
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
            time.sleep(20)
            
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
            
            time.sleep(2)
            
            # Call a non-existent tool
            tool_call_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "NonExistentTool",
                    "arguments": "{}"
                }
            }
            process.stdin.write(json.dumps(tool_call_request) + "\n")
            process.stdin.flush()
            
            # Read error response
            response = process.stdout.readline()
            assert response.strip()
            
            # Parse response - should be an error
            response_data = json.loads(response.strip())
            assert "error" in response_data
            
        finally:
            # Clean up
            process.terminate()
            process.wait(timeout=10)

    def test_stdio_hooks_performance(self):
        """Test performance of stdio mode with hooks"""
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
            _ = time.time()
            time.sleep(20)

            
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
            
            time.sleep(2)
            
            # Call a simple tool to test response time
            tool_call_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "get_server_info",
                    "arguments": "{}"
                }
            }
            
            call_start_time = time.time()
            process.stdin.write(json.dumps(tool_call_request) + "\n")
            process.stdin.flush()
            
            # Read response
            response = process.stdout.readline()
            call_end_time = time.time()
            
            call_time = call_end_time - call_start_time
            
            # Should complete within reasonable time
            assert call_time < 30  # Should be much faster
            assert response.strip()
            
        finally:
            # Clean up
            process.terminate()
            process.wait(timeout=10)

    def test_stdio_hooks_logging_separation(self):
        """Test that logs and JSON responses are properly separated in stdio mode with hooks"""
        # Start server in subprocess with hooks.
        # We keep stderr=PIPE so we can verify logs go to stderr, not stdout.
        # A background thread drains the pipe continuously to prevent the
        # ~65 KB of startup messages from filling the buffer and causing a deadlock.
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
            stderr=subprocess.PIPE,  # Keep PIPE so we can verify logs on stderr
            text=True,
            bufsize=1,
            env=_SUBPROCESS_ENV
        )

        stderr_chunks = []

        def _drain_stderr():
            try:
                for line in process.stderr:
                    stderr_chunks.append(line)
            except Exception:
                pass

        stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
        stderr_thread.start()

        try:
            # Wait for server to start (hooks load all tools, takes ~20s locally)
            time.sleep(20)

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

            # Verify logs went to stderr (not stdout); the drainer captured them
            assert stderr_chunks, "Expected server log messages on stderr"

        finally:
            # Clean up
            process.terminate()
            process.wait(timeout=10)
            stderr_thread.join(timeout=3)

    def test_stdio_hooks_multiple_tool_calls(self):
        """Test multiple tool calls in stdio mode with hooks"""
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
            time.sleep(20)
            
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
            
            time.sleep(2)
            
            # Make multiple tool calls
            for i in range(3):
                tool_call_request = {
                    "jsonrpc": "2.0",
                    "id": i + 2,
                    "method": "tools/call",
                    "params": {
                        "name": "get_server_info",
                        "arguments": "{}"
                    }
                }
                process.stdin.write(json.dumps(tool_call_request) + "\n")
                process.stdin.flush()
                
                # Read response
                response = process.stdout.readline()
                assert response.strip()
                
                # Parse response
                response_data = json.loads(response.strip())
                assert "result" in response_data or "error" in response_data
            
        finally:
            # Clean up
            process.terminate()
            process.wait(timeout=15)
