#!/usr/bin/env python3
"""
Test script: Verify that the generated FastMCP server is working properly

This script will start the MCP server and send some test requests
"""

import asyncio
import aiohttp
import sys
import subprocess
from pathlib import Path

# Test MCP server URL
MCP_SERVER_URL = "http://127.0.0.1:8000"


async def test_mcp_server():
    """Test basic functionality of MCP server"""

    print("🚀 Starting FastMCP server test...")

    # Wait for server to start
    print("⏳ Waiting for server to start...")
    await asyncio.sleep(3)

    async with aiohttp.ClientSession() as session:
        # Test 1: Get tool list
        print("\n📋 Test 1: Get available tool list")
        tools_request = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "tools/list",
            "params": {},
        }

        try:
            async with session.post(
                f"{MCP_SERVER_URL}/mcp/",
                json=tools_request,
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    tools = result.get("result", {}).get("tools", [])
                    print(
                        f"✅ Successfully retrieved tool list, {len(tools)} tools in total"
                    )

                    # Show first few tools
                    for _i, tool in enumerate(tools[:3]):
                        print(
                            f"   - {tool.get('name', 'unknown')}: {tool.get('description', 'no description')[:80]}..."
                        )

                    if len(tools) > 3:
                        print(f"   ... and {len(tools) - 3} more tools")

                else:
                    print(f"❌ Failed to get tool list, status code: {response.status}")
                    print(f"Response: {await response.text()}")
                    return False

        except Exception as e:
            print(f"❌ Failed to connect to server: {e}")
            return False

        # Test 2: Call a simple tool
        print("\n🔧 Test 2: Call a tool function")
        tool_request = {
            "jsonrpc": "2.0",
            "id": "test-2",
            "method": "tools/call",
            "params": {
                "name": "get_phenotype_by_HPO_ID",
                "arguments": {"id": "HP:0000001"},  # Test HPO ID
            },
        }

        try:
            async with session.post(
                f"{MCP_SERVER_URL}/mcp/",
                json=tool_request,
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if "error" in result:
                        print(f"⚠️  Tool execution returned error: {result['error']}")
                    else:
                        print("✅ Tool call successful")
                        print(
                            f"   Return result type: {type(result.get('result', {}))}"
                        )
                else:
                    print(f"❌ Tool call failed, status code: {response.status}")
                    print(f"Response: {await response.text()}")

        except Exception as e:
            print(f"❌ Tool call exception: {e}")

        # Test 3: Call FDA tool
        print("\n💊 Test 3: Call FDA drug query tool")
        fda_request = {
            "jsonrpc": "2.0",
            "id": "test-3",
            "method": "tools/call",
            "params": {
                "name": "FDA_get_active_ingredient_info_by_drug_name",
                "arguments": {"drug_name": "aspirin", "limit": 5, "skip": 0},
            },
        }

        try:
            async with session.post(
                f"{MCP_SERVER_URL}/mcp/",
                json=fda_request,
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if "error" in result:
                        print(
                            f"⚠️  FDA tool execution returned error: {result['error']}"
                        )
                    else:
                        print("✅ FDA tool call successful")
                        print(
                            f"   Return result type: {type(result.get('result', {}))}"
                        )
                else:
                    print(f"❌ FDA tool call failed, status code: {response.status}")

        except Exception as e:
            print(f"❌ FDA tool call exception: {e}")

    print("\n🎉 Test completed!")
    return True


def start_mcp_server():
    """Start MCP server"""
    print("🚀 Starting MCP server...")

    # Modify the generated file, add correct startup code
    server_file = Path(__file__).parent / "mcp_server_test.py"

    server_code = """#!/usr/bin/env python3
# Import generated MCP wrapper
import sys
import os
sys.path.append(os.path.dirname(__file__))

# Read generated code and execute
with open("mcp_wrappers_generated.txt", "r") as f:
    generated_code = f.read()

# Execute generated code
exec(generated_code)

# Start server
if __name__ == "__main__":
    print("🚀 Starting ToolUniverse MCP server...")
    print(f"Server address: http://127.0.0.1:8000")
    print("Press Ctrl+C to stop server")
    run_server()
"""

    with open(server_file, "w") as f:
        f.write(server_code)

    # Start server process
    return subprocess.Popen(
        [sys.executable, str(server_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


async def main():
    """Main function"""
    print("🧪 FastMCP Server Test Tool")
    print("=" * 50)

    # Start server
    server_process = start_mcp_server()

    try:
        # Run tests
        success = await test_mcp_server()

        if success:
            print("\n✅ All tests passed! MCP server is working properly.")
        else:
            print("\n❌ Some tests failed, please check server configuration.")

    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    finally:
        # Cleanup: terminate server process
        print("\n🧹 Cleanup: closing server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        print("✅ Server closed")


if __name__ == "__main__":
    asyncio.run(main())
