# MCP (Model Context Protocol) Examples

This directory contains examples and tools for using ToolUniverse with the Model Context Protocol (MCP).

## Files

### Core Examples

- **mcp_call_example.py**: Demonstrates how to call MCP tools with type coercion and parameter passing.
- **mcp_server_example.py**: Example of setting up and testing an MCP server.
- **mcp_server_test.py**: Test script for verifying that the generated FastMCP server is working properly.
- **mcp_tool_example.py**: Comprehensive test file for MCP tools integration, including tool discovery and execution.

### Claude Desktop Integration

The `tools_file_filter_claude_desktop/` directory contains:

- **README.md**: Instructions for integrating ToolUniverse with Claude Desktop using MCP.
- **stdio_wrapper.py**: STDIO wrapper for SMCP server integration with Claude Desktop.
- **tools_short.txt**: Whitelist of tools that respect Claude Desktop's 64-character tool name limit.

## Usage

### Running MCP Examples

#### Basic MCP Call
```bash
python examples/mcp/mcp_call_example.py
```

#### Test MCP Server
```bash
python examples/mcp/mcp_server_example.py
```

#### Comprehensive MCP Tool Test
```bash
python examples/mcp/mcp_tool_example.py
```

### Setting up Claude Desktop Integration

See `tools_file_filter_claude_desktop/README.md` for detailed instructions on:
- Creating a tool whitelist
- Configuring Claude Desktop
- Using the STDIO wrapper

## What is MCP?

Model Context Protocol (MCP) is a protocol for connecting LLM applications to various data sources and tools. ToolUniverse supports MCP integration, allowing you to:

- Expose ToolUniverse tools as MCP tools
- Use MCP tools within ToolUniverse workflows
- Integrate with MCP-compatible clients like Claude Desktop

