# Adding MCP Tools to ToolUniverse

This tutorial will Tutorial you through integrating Model Context Protocol (MCP) tools into ToolUniverse. ToolUniverse provides multiple ways to connect and use tools from MCP servers.

## Table of Contents

1. [MCP Tool Types Overview](#mcp-tool-types-overview)
2. [Configuring MCP Client Tools](#configuring-mcp-client-tools)
3. [Using Auto Loader](#using-auto-loader)
4. [Proxy Tool Configuration](#proxy-tool-configuration)
5. [Advanced Configuration Options](#advanced-configuration-options)
6. [Troubleshooting](#troubleshooting)

## MCP Tool Types Overview

ToolUniverse supports three main types of MCP tools:

### 1. MCPClientTool
- **Purpose**: General-purpose MCP client supporting all MCP operations
- **Features**: Manual configuration, precise control
- **Use Cases**: When you need access to multiple MCP functions (tools, resources, prompts)

### 2. MCPAutoLoaderTool
- **Purpose**: Automatically discover and load all tools from an MCP server
- **Features**: Automated configuration, batch loading
- **Use Cases**: Quick integration of entire MCP server tool sets

### 3. MCPProxyTool
- **Purpose**: Create direct proxy for specific MCP tools
- **Features**: One-to-one mapping, transparent forwarding
- **Use Cases**: Integrate individual MCP tools as ToolUniverse tools

## Configuring MCP Client Tools

### Basic Configuration

Create a general-purpose MCP client tool configuration:

```json
{
    "name": "my_mcp_client",
    "description": "Client connecting to my MCP server",
    "type": "MCPClientTool",
    "server_url": "http://localhost:8000",
    "transport": "http",
    "timeout": 600,
    "parameter": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["list_tools", "call_tool", "list_resources", "read_resource", "list_prompts", "get_prompt"],
                "description": "MCP operation to execute"
            },
            "tool_name": {
                "type": "string",
                "description": "Name of tool to call (required for call_tool operation)"
            },
            "tool_arguments": {
                "type": "object",
                "description": "Arguments to pass to the tool (for call_tool operation)"
            },
            "uri": {
                "type": "string",
                "description": "Resource URI (required for read_resource operation)"
            },
            "prompt_name": {
                "type": "string",
                "description": "Prompt name (required for get_prompt operation)"
            },
            "prompt_arguments": {
                "type": "object",
                "description": "Arguments to pass to the prompt (for get_prompt operation)"
            }
        },
        "required": ["operation"]
    }
}
```

### Usage Examples

```python
from tooluniverse import ToolUniverse

# Initialize ToolUniverse
tu = ToolUniverse()

# Call MCP tool
result = tu.tools.my_mcp_client(
    operation="call_tool",
    tool_name="calculator",
    tool_arguments={"expression": "2 + 2"}
)

# List available tools
tools = tu.tools.my_mcp_client(operation="list_tools")
```

## Using Auto Loader

### Basic Auto Loader Configuration

```json
{
    "name": "mcp_auto_loader",
    "description": "Automatically load MCP server tools",
    "type": "MCPAutoLoaderTool",
    "server_url": "http://localhost:8000",
    "transport": "http",
    "auto_register": true,
    "tool_prefix": "mcp_",
    "timeout": 30
}
```

### Advanced Auto Loader Configuration

```json
{
    "name": "expert_tool_loader",
    "description": "Load expert consultation tools",
    "type": "MCPAutoLoaderTool",
    "server_url": "http://localhost:7001/mcp",
    "transport": "http",
    "auto_register": true,
    "tool_prefix": "expert_",
    "selected_tools": ["consult_expert", "get_expert_response"],
    "timeout": 60
}
```

### Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `server_url` | string | - | MCP server URL |
| `transport` | string | "http" | Transport protocol (http/websocket) |
| `auto_register` | boolean | true | Whether to automatically register discovered tools |
| `tool_prefix` | string | "mcp_" | Tool name prefix |
| `selected_tools` | array | null | List of specific tools to load |
| `timeout` | integer | 30 | Request timeout in seconds |

### Using Auto Loader for Tool Discovery

```python
# Discover tools
discovered = tu.tools.mcp_auto_loader(operation="discover")

# Generate proxy tool configurations
configs = tu.tools.mcp_auto_loader(operation="generate_configs")

# Directly call MCP tool
result = tu.tools.mcp_auto_loader(
    operation="call_tool",
    tool_name="calculator",
    tool_arguments={"expression": "10 * 5"}
)
```

## Proxy Tool Configuration

### Manual Proxy Tool Creation

```json
{
    "name": "mcp_calculator",
    "description": "Calculator tool from MCP server",
    "type": "MCPProxyTool",
    "server_url": "http://localhost:8000",
    "transport": "http",
    "target_tool_name": "calculator",
    "parameter": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Mathematical expression to calculate"
            }
        },
        "required": ["expression"]
    }
}
```

### Batch Proxy Tool Creation

Use the `MCPServerDiscovery` class to batch discover and create proxy tools:

```python
from tooluniverse.mcp_client_tool import MCPServerDiscovery
import asyncio

async def create_proxy_tools():
    # Discover server tools
    tool_configs = await MCPServerDiscovery.discover_server_tools(
        server_url="http://localhost:8000",
        transport="http"
    )

    # Save configuration to JSON file
    import json
    with open("discovered_mcp_tools.json", "w") as f:
        json.dump(tool_configs, f, indent=2)

# Run discovery process
asyncio.run(create_proxy_tools())
```

## Advanced Configuration Options

### Supported Transport Protocols

#### HTTP Transport
```json
{
    "transport": "http",
    "server_url": "http://localhost:8000"
}
```

#### WebSocket Transport
```json
{
    "transport": "websocket",
    "server_url": "ws://localhost:8000"
}
```

### Environment Variable Support

You can use environment variables in configurations:

```json
{
    "server_url": "${MCP_SERVER_URL}",
    "timeout": "${MCP_TIMEOUT:30}"
}
```

### Error Handling and Retry

```json
{
    "name": "robust_mcp_client",
    "type": "MCPClientTool",
    "server_url": "http://localhost:8000",
    "timeout": 120,
    "retry_attempts": 3,
    "retry_delay": 5
}
```

## Configuration File Organization

### Recommended Directory Structure

```
src/tooluniverse/data/
├── mcp_client_tools.json          # Basic MCP client tools
├── expert_feedback_tools.json     # Expert feedback tools
├── analysis_tools.json            # Analysis tools
└── custom_mcp_tools.json          # Custom MCP tools
```

### Modular Configuration Example

`expert_feedback_tools.json`:
```json
[
    {
        "name": "mcp_auto_loader_expert",
        "description": "Automatically discover and load expert consultation tools",
        "type": "MCPAutoLoaderTool",
        "server_url": "http://localhost:7001/mcp",
        "tool_prefix": "expert_"
    },
    {
        "name": "consult_human_expert",
        "description": "Consult human medical expert",
        "type": "MCPClientTool",
        "server_url": "http://localhost:7001",
        "transport": "http",
        "mcp_tool_name": "consult_human_expert",
        "parameter": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Medical question requiring expert consultation"
                },
                "specialty": {
                    "type": "string",
                    "description": "Required specialty field",
                    "default": "general"
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "normal", "high", "urgent"],
                    "default": "normal"
                }
            },
            "required": ["question"]
        }
    }
]
```

## Practical Application Examples

### Example 1: Medical Expert Consultation System

```python
# Configure expert consultation tool
expert_config = {
    "name": "medical_expert",
    "type": "MCPClientTool",
    "server_url": "https://expert-api.medical.com",
    "mcp_tool_name": "consult_expert"
}

# Use expert tool
consultation = tu.tools.medical_expert(
    operation="call_tool",
    tool_name="consult_expert",
    tool_arguments={
        "question": "Patient presents with chest pain and shortness of breath, how to diagnose?",
        "specialty": "cardiology",
        "priority": "high"
    }
})
```

### Example 2: Data Analysis Tool Set

```python
# Auto-load analysis tools
analysis_loader = {
    "name": "analysis_tools_loader",
    "type": "MCPAutoLoaderTool",
    "server_url": "http://analysis-server:8080",
    "tool_prefix": "analysis_",
    "selected_tools": [
        "statistical_analysis",
        "data_visualization",
        "correlation_analysis"
    ]
}

# Run statistical analysis
stats_result = tu.tools.analysis_statistical_analysis(
    data=[1, 2, 3, 4, 5],
    test_type="t_test"
)
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Connection Timeout
```
Error: MCP request failed with status 408: Request Timeout
```

**Solutions**:
- Increase `timeout` value
- Check network connection
- Verify server URL

#### 2. Transport Protocol Mismatch
```
Error: Invalid transport 'invalid'. Supported: ['http', 'websocket']
```

**Solutions**:
- Ensure `transport` is set to "http" or "websocket"
- Check server supported protocols

#### 3. Tool Not Found
```
Error: Tool 'unknown_tool' not found on MCP server
```

**Solutions**:
- Use `list_tools` operation to view available tools
- Check tool name spelling
- Confirm server is running

#### 4. Parameter Validation Failed
```
Error: Required parameter 'question' missing
```

**Solutions**:
- Check tool parameter schema
- Ensure all required parameters are provided
- Verify parameter data types

### Debugging Tips

#### Enable Verbose Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Detailed request/response information will be shown when running tools
```

#### Test Connection
```python
# Test basic connection
connection_test = tu.tools.my_mcp_client(operation="list_tools")

if "error" in connection_test:
    print("Connection failed:", connection_test["error"])
else:
    print("Connection successful, available tools:", len(connection_test["tools"]))
```

#### Validate Tool Configuration
```python
# Validate auto loader discovered tools
discovery_result = tu.tools.mcp_auto_loader(operation="discover")

print("Number of discovered tools:", discovery_result["discovered_count"])
print("Tool list:", discovery_result["tools"])
```

## Best Practices

### 1. Security Considerations
- Use HTTPS connections for production MCP servers
- Configure appropriate timeout values to avoid long waits
- Validate all input parameters

### 2. Performance Optimization
- Enable caching for frequently used tools
- Set reasonable `timeout` values
- Use `selected_tools` to load only needed tools

### 3. Error Handling
- Always check for `error` field in return results
- Implement retry mechanisms for temporary network issues
- Log detailed error information for debugging

### 4. Configuration Management
- Use environment variables for sensitive configurations
- Organize configuration files by functional modules
- Regularly update and validate configurations

## Summary

Through this tutorial, you have learned:

1. ✅ Understanding the purposes and characteristics of three MCP tool types
2. ✅ Configuring and using MCPClientTool for general MCP operations
3. ✅ Using MCPAutoLoaderTool to automatically discover and load tools
4. ✅ Creating MCPProxyTool for direct tool proxying
5. ✅ Handling common issues and troubleshooting
6. ✅ Applying best practices for security and performance

Now you can integrate tools from any MCP server into ToolUniverse, expanding your tool ecosystem!

## Reference Resources

- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)
- [ToolUniverse Official Documentation](../README.md)
- [MCP Tool Configuration Examples](../../data/mcp_client_tools.json)
- [API Reference Documentation](../../api/mcp_tools.rst)
