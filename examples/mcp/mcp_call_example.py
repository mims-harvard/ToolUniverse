#!/usr/bin/env python3
"""MCP call example - demonstrates type coercion"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("❌ pip install mcp")
    sys.exit(1)


async def main():
    server = StdioServerParameters(
        command="uv",
        args=["run", "tooluniverse-smcp-stdio", "--no-search"]
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            args = {
                "query": "gene:MEIOB",
                "limit": "5"  # String!
            }
            
            result = await session.call_tool("UniProt_search", args)
            
            for content in result.content:
                print(content.text)


if __name__ == "__main__":
    asyncio.run(main())
