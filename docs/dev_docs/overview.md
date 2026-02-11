# TxAgent Documentation

This directory contains documentation for TxAgent and guides on integrating with MCP (Model Context Protocol) servers and ToolUniverse.

## Available Documentation

### �️ [Adding Tools Tutorial](Adding_Tools_Tutorial.md)
**NEW!** Complete Tutorial for adding custom tools to ToolUniverse:
- Decorator-based auto-registration system
- Step-by-step examples with real code
- Configuration best practices
- Troubleshooting and testing guides
- Multiple registration methods

### �📖 [MCP Server Tutorial](MCP_Server_Tutorial.md)
A comprehensive Tutorial that covers:
- Converting your Python program into an MCP server
- Creating ToolUniverse configuration files
- Integration best practices
- Troubleshooting common issues
- Complete working examples

## Overview

**TxAgent** is an AI agent for precision therapeutics and personalized treatment recommendations. This documentation helps you:

1. **Add Custom Tools**: Create your own tools using the decorator-based system
2. **Expose TxAgent as an MCP Server**: Make TxAgent accessible via the Model Context Protocol
3. **Integrate with ToolUniverse**: Use TxAgent tools within the ToolUniverse framework
4. **Create Your Own MCP Tools**: Convert any Python program into an MCP server

## Key Components

### MCP Server
- **Purpose**: Standardized way to expose AI tools and functions
- **Protocol**: HTTP-based communication
- **Benefits**: Remote access, scalability, standardization

### ToolUniverse Integration
- **Auto-discovery**: Automatically finds and registers MCP tools
- **Unified Interface**: Single API for multiple tool types
- **Configuration**: JSON-based tool definitions

### FastMCP Framework
- **Library**: Python framework for creating MCP servers
- **Features**: Easy decorator-based tool definition
- **Transport**: HTTP and other protocols supported

## Getting Started

1. **Want to add your own tools?** Start with the [Adding Tools Tutorial](Adding_Tools_Tutorial.md)
2. **New to MCP?** Check out the [MCP Server Tutorial](MCP_Server_Tutorial.md)
3. **Need quick optimization?** Use the [Tool Description Optimizer Quick Start](Tool_Description_Optimizer_Quick_Start.md)

## Example Files

In the parent directory, you'll find:
- `run_mcp.py` - TxAgent MCP server implementation
- `tooluni_client.py` - Example of using TxAgent through ToolUniverse
- `txagent_client_tools.json` - ToolUniverse configuration for TxAgent

## Architecture Overview

```
┌─────────────────┐    HTTP/MCP     ┌──────────────────┐
│   Your Client   │ ◄─────────────► │   MCP Server     │
│  (ToolUniverse) │                 │  (Your Program)  │
└─────────────────┘                 └──────────────────┘
        │                                    │
        │                                    │
        ▼                                    ▼
┌─────────────────┐                 ┌──────────────────┐
│ Configuration   │                 │  Tool Functions  │
│ JSON File       │                 │  (@server.tool)  │
└─────────────────┘                 └──────────────────┘
```

## Support

If you encounter issues:
1. Check the troubleshooting sections in the tutorials
2. Verify your configuration matches the examples
3. Ensure all dependencies are properly installed
4. Test MCP server functionality independently

## Contributing

When adding new documentation:
1. Follow the existing markdown structure
2. Include practical examples
3. Test all code snippets
4. Update this README if adding new files

---

For questions about TxAgent specifically, refer to the main project README in the parent directory.
