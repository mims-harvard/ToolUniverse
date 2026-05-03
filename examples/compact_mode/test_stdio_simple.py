#!/usr/bin/env python3
"""
Simplified stdio mode test script
For testing tool calls in compact mode

Usage:
    python test_stdio_simple.py
"""

import json
import subprocess
import time


def test_tool(server_process, tool_name, arguments):
    """Test a single tool call"""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }

    # Send request
    request_json = json.dumps(request) + "\n"
    server_process.stdin.write(request_json)
    server_process.stdin.flush()

    # Read response (skip non-JSON lines)
    for _ in range(10):  # Try up to 10 lines
        response_line = server_process.stdout.readline()
        if not response_line:
            print(f"❌ {tool_name}: No response")
            return False

        line = response_line.strip()
        if not line:
            continue

        try:
            response = json.loads(line)
            if "result" in response:
                content = response["result"].get("content", [{}])
                result_text = content[0].get("text", "")
                print(f"✅ {tool_name}: Success")
                length = len(result_text)
                print(f"   Response length: {length} characters")
                print(f"   Response: {result_text[:200]}...")
                return True
            elif "error" in response:
                print(f"❌ {tool_name}: Error")
                print(f"   Error: {response['error']}")
                print(f"   Raw response: {line[:200]}...")
                return False
        except json.JSONDecodeError:
            continue  # Skip non-JSON lines

    print(f"❌ {tool_name}: No valid response found")
    return False


def main():
    """Main test function"""
    # Start server
    print("Starting server...")
    server = subprocess.Popen(
        ["tooluniverse-smcp-stdio", "--compact-mode"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0
    )

    # Wait for server to start
    time.sleep(2)

    # Initialize
    init_request = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"}
        }
    }
    server.stdin.write(json.dumps(init_request) + "\n")
    server.stdin.flush()

    # Read initialization response
    server.stdout.readline()

    # Send initialized notification
    notification = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {}
    }
    server.stdin.write(json.dumps(notification) + "\n")
    server.stdin.flush()
    time.sleep(0.5)

    print("\nStarting tool tests...\n")

    # Test four core tools
    tests = [
        # 1. Test list_tools
        ("list_tools", {"mode": "names"}),

        # 2. Test grep_tools
        ("grep_tools", {
            "pattern": "protein",
            "field": "name",
            "search_mode": "text",
            "limit": 5
        }),

        # 3. Test get_tool_info
        ("get_tool_info", {
            "tool_names": "list_tools",
            "detail_level": "description"
        }),

        # 4. Test execute_tool - execute list_tools
        ("execute_tool", {
            "tool_name": "list_tools",
            "arguments": {"mode": "names"}
        }),
    ]

    success_count = 0
    total_count = len(tests)

    for tool_name, args in tests:
        print(f"\nTesting: {tool_name}")
        if test_tool(server, tool_name, args):
            success_count += 1
        time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"Test results: {success_count}/{total_count} successful")
    print(f"{'='*50}")

    # Cleanup
    server.terminate()
    server.wait()
    print("\nTest completed")


if __name__ == "__main__":
    main()
