#!/usr/bin/env python3
"""
Complete example: Using Compact Mode with MCP Client

This example demonstrates how to create an MCP client
and use compact mode tools.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("❌ MCP library not installed. Install with: pip install mcp")
    sys.exit(1)


async def use_compact_mode():
    """Complete example of using compact mode tools"""

    print("=" * 60)
    print("Compact Mode - Complete Usage Example")
    print("=" * 60)

    # Step 1: Create client connection to compact mode server
    print("\n1. Creating MCP client connection...")
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "tooluniverse.smcp_server",
              "--transport", "stdio",
              "--compact-mode"]
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()
            print("   ✅ Connected to compact mode server")

            # List available tools
            print("\n2. Listing available tools...")
            tools = await session.list_tools()
            print(f"   Found {len(tools.tools)} tools in compact mode")
            tool_names = [t.name for t in tools.tools[:5]]
            print(f"   Tool names: {tool_names}...")

            # Step 2: Get overview of available tools
            print("\n3. Getting tool overview with list_tools...")
            result = await session.call_tool("list_tools", {"mode": "names"})
            tools_data = json.loads(result.content[0].text)
            all_tools = tools_data.get('tools', [])
            print(f"   ✅ Found {len(all_tools)} total tools available")
            if all_tools:
                # For mode="names", tools is a list of strings
                first_tool = all_tools[0]
                if isinstance(first_tool, str):
                    tool_name = first_tool
                else:
                    tool_name = first_tool.get('name', '')
                print(f"   Example: {tool_name}")

            # Step 3: Search for tools with grep_tools
            print("\n4. Searching for tools with grep_tools...")
            try:
                result = await session.call_tool("grep_tools", {
                    "pattern": "protein",
                    "field": "name",
                    "search_mode": "text",
                    "limit": 5
                })
                if result.content and len(result.content) > 0:
                    grep_data = json.loads(result.content[0].text)
                    if "error" in grep_data:
                        print(f"   ⚠️  Error: {grep_data['error']}")
                    else:
                        grep_tools = grep_data.get('tools', [])
                        count = len(grep_tools)
                        msg = f"   ✅ Found {count} tools matching 'protein'"
                        print(msg)
                        for tool in grep_tools[:3]:
                            name = tool.get('name')
                            desc = tool.get('description', '')[:60]
                            print(f"   - {name}: {desc}...")
                else:
                    print("   ⚠️  No result returned")
            except Exception as e:
                print(f"   ⚠️  Error calling grep_tools: {e}")

            # Step 4: Get tool information
            print("\n5. Getting tool information...")
            result = await session.call_tool("get_tool_info", {
                "tool_names": "list_tools",
                "detail_level": "description"
            })
            tool_info = json.loads(result.content[0].text)
            if isinstance(tool_info, list):
                tool_info = tool_info[0]
            print(f"   ✅ Retrieved info for: {tool_info.get('name')}")
            desc = tool_info.get('description', '')[:80]
            print(f"   Description: {desc}...")

            # Step 5: Execute a tool via execute_tool
            print("\n6. Executing tool via execute_tool...")
            result = await session.call_tool("execute_tool", {
                "tool_name": "list_tools",
                "arguments": {"mode": "categories"}
            })
            categories = json.loads(result.content[0].text)
            category_count = len(categories.get('categories', {}))
            msg = (f"   ✅ Executed successfully, "
                   f"found {category_count} categories")
            print(msg)

            print("\n" + "=" * 60)
            print("✅ All examples completed successfully!")
            print("=" * 60)
            print("\nCompact mode exposes 4-5 core tools:")
            print("  - list_tools: List available tools with different modes")
            print("  - grep_tools: Search tools by text/regex pattern")
            msg = ("  - get_tool_info: Get tool information "
                   "(description or full definition)")
            print(msg)
            print("  - execute_tool: Execute any ToolUniverse tool by name")
            print("  - find_tools: AI-powered tool discovery (if search enabled, default)")
            print("\nNote: In Claude Desktop, the client is automatically "
                  "created.")
            print("You just need to configure the server and use it through "
                  "conversation.")


if __name__ == "__main__":
    try:
        asyncio.run(use_compact_mode())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
