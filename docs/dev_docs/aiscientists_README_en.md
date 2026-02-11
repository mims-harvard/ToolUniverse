# MCP Tutorials

Welcome to the ToolUniverse Model Context Protocol (MCP) tutorials!

## Tutorial List

### 📚 Basic Tutorials
- **[Adding MCP Tools](adding_mcp_tools_en.md)** - Complete Tutorial: How to integrate MCP tools in ToolUniverse
  - MCP tool types overview (MCPClientTool, MCPAutoLoaderTool, MCPProxyTool)
  - Configuration and usage Tutorial
  - Advanced configuration options
  - Troubleshooting and best practices

### � Advanced Tutorials
- **[MCP Tool Registration System](mcp_tool_registration_en.md)** - Register local tools as MCP tools
  - Use `@register_mcp_tool` decorator
  - Automatically start MCP servers
  - Auto-load remote tools in other ToolUniverse instances
  - Reuse SMCP functionality for tool sharing

### �📚 中文教程
- **[添加 MCP 工具](adding_mcp_tools.md)** - 完整指南：如何在 ToolUniverse 中集成 MCP 工具
- **[MCP 工具注册系统](mcp_tool_registration_zh.md)** - 将本地工具注册为 MCP 工具

## Quick Start

If you're new to MCP tools, we recommend learning in this order:

1. 🔰 **[Adding MCP Tools](adding_mcp_tools_en.md)** - Start here!
2. 🚀 **[MCP Tool Registration System](mcp_tool_registration_en.md)** - Learn how to expose local tools as MCP services

## What is MCP?

Model Context Protocol (MCP) is an open protocol for connecting AI applications with external tools and data sources. In ToolUniverse, MCP tools enable you to:

- 🔗 Connect to remote MCP servers
- 🛠️ Automatically discover and load remote tools
- 📋 Access remote resources and prompts
- 🚀 Rapidly expand your tool ecosystem

## Tool Types Overview

| Tool Type | Purpose | Use Cases |
|-----------|---------|-----------|
| **MCPClientTool** | General-purpose MCP client | Need complete MCP functionality |
| **MCPAutoLoaderTool** | Automatic tool discovery | Batch integration of tool sets |
| **MCPProxyTool** | Single tool proxy | Transparent tool forwarding |

## Sample Configuration Preview

### Quick Auto Loader
```json
{
    "name": "mcp_auto_loader",
    "type": "MCPAutoLoaderTool",
    "server_url": "http://localhost:8000",
    "auto_register": true,
    "tool_prefix": "mcp_"
}
```

### Dedicated Tool Proxy
```json
{
    "name": "mcp_calculator",
    "type": "MCPProxyTool",
    "server_url": "http://localhost:8000",
    "target_tool_name": "calculator"
}
```

## Related Resources

- 📖 [ToolUniverse Main Documentation](../../README.md)
- 🔧 [API Reference](../../api/)
- 💡 [Configuration Examples](../../../src/tooluniverse/data/)
- 🌐 [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)

---

**Ready to get started?** Click [Adding MCP Tools](adding_mcp_tools_en.md) to begin your MCP journey!
