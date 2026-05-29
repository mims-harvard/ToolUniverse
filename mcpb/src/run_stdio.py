#!/usr/bin/env python3
"""Entry point for ToolUniverse MCP Server (stdio transport for Claude Desktop).

This wrapper calls run_stdio_server with compact mode enabled.
Compact mode exposes only 5 core tools (list_tools, grep_tools, get_tool_info, execute_tool, find_tools)
while loading all 764+ tools in the background for execute_tool to access.
This prevents context window overflow from the massive tool list.
"""
import sys

# Enable compact mode by default
sys.argv = [
    sys.argv[0],
    "--compact-mode",
]

from tooluniverse.smcp_server import run_stdio_server

if __name__ == "__main__":
    run_stdio_server()
