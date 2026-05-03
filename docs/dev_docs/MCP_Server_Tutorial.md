# Converting any Tool to MCP Server and Using it with ToolUniverse

This tutorial will Tutorial you through the process of converting your Python program into a Model Context Protocol (MCP) server and integrating it with ToolUniverse for easy access and management.

## Table of Contents
1. [Overview](#overview)
2. [Creating an MCP Server](#creating-an-mcp-server)
3. [Configuring ToolUniverse Integration](#configuring-tooluniverse-integration)
4. [Using Your MCP Tool in ToolUniverse](#using-your-mcp-tool-in-tooluniverse)
5. [Complete Example](#complete-example)
6. [Troubleshooting](#troubleshooting)

## Overview

MCP (Model Context Protocol) servers provide a standardized way to expose your tools and functions for use by AI agents and other applications. By converting your program to an MCP server, you can:

- Expose your functions through a standardized API
- Enable remote access to your tools
- Integrate seamlessly with ToolUniverse
- Scale your tools across different environments

## Creating an MCP Server

### Step 1: Install Required Dependencies

First, install the necessary packages:

```bash
pip install fastmcp
```

### Step 2: Convert Your Program to MCP Server

Here's how to convert your existing program into an MCP server using FastMCP:

```python
from fastmcp import FastMCP

# Import your existing modules
from your_module import YourAgent  # Replace with your actual imports
import os

# Initialize your agent/model
model_name = 'your-model-name'
agent = YourAgent(model_name)  # Replace with your actual initialization

# Create FastMCP server instance
server = FastMCP('Your MCP Server Name', stateless_http=True)

@server.tool()
def your_function_name(question: str, additional_param: bool = False):
    """
    Description of your function that will appear in the tool documentation.

    This description should clearly explain what your function does,
    what parameters it accepts, and what it returns.

    Args:
        question: Description of the main input parameter
        additional_param: Description of optional parameters

    Returns:
        Description of what the function returns
    """

    # Call your existing function/agent
    response = agent.run(
        question,
        # Add your specific parameters here
        additional_param=additional_param
    )
    return response

if __name__ == "__main__":
    print("🚀 Starting MCP server...")
    server.run(transport='streamable-http', host="0.0.0.0", port=7000)
```

### Step 3: Example Implementation (Based on TxAgent)

Here's the actual implementation from TxAgent as a reference:

```python
from fastmcp import FastMCP
from txagent import TxAgent
import os

os.environ["MKL_THREADING_LAYER"] = "GNU"

# Configuration
model_name = 'mims-harvard/TxAgent-T1-Llama-3.1-8B'
rag_model_name = 'mims-harvard/ToolRAG-T1-GTE-Qwen2-1.5B'
multiagent = False
max_round = 20

# Create server
server = FastMCP('TxAgent MCP Server', stateless_http=True)

# Initialize agent
agent = TxAgent(
    model_name,
    rag_model_name,
    enable_summary=False,
    vllm_mode='server',
    vllm_server_url="http://holygpu8a13404:8000/v1"
)

agent.init_model(tool_type=[
    'opentarget',
    'fda_drug_label',
    'special_tools',
    'monarch',
    'fda_drug_adverse_event',
    'ChEMBL',
    'EuropePMC',
    'semantic_scholar',
    'pubtator',
    'EFO',
])

@server.tool()
def run_txagent(question: str, return_conversation: bool = False):
    """Run TxAgent for precision therapeutics and personalized treatment recommendations.

    TxAgent is an AI agent that leverages multi-step reasoning and real-time scientific knowledge
    retrieval to analyze drug questions and patient-specific treatment strategies.

    Args:
        question: Medical question requiring TxAgent analysis
        return_conversation: Whether to return the full conversation history

    Returns:
        Comprehensive analysis from TxAgent including personalized treatment recommendations
    """

    response = agent.run_multistep_agent(
        question,
        temperature=0.3,
        max_new_tokens=1024,
        max_token=90240,
        call_agent=multiagent,
        max_round=max_round,
        return_conversation=return_conversation
    )
    return response

if __name__ == "__main__":
    print("🚀 Starting MCP server for TxAgent...")
    server.run(transport='streamable-http', host="0.0.0.0", port=7000)
```

## Configuring ToolUniverse Integration

### Step 1: Create a Configuration File

Create a JSON configuration file for your MCP server. This file should be placed in the ToolUniverse data directory:

```json
[
    {
        "name": "mcp_auto_loader_your_tool",
        "description": "Automatically discover and load all tools from Your MCP Server. Can register discovered tools as individual ToolUniverse tools or provide tool configurations.",
        "type": "MCPAutoLoaderTool",
        "server_url": "http://your-server-host:7000/mcp",
        "transport": "http",
        "auto_register": true,
        "tool_prefix": "mcp_",
        "selected_tools": null,
        "parameter": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["discover", "generate_configs", "call_tool"],
                    "description": "The operation to perform: discover tools, generate configs, or call a tool directly"
                },
                "tool_name": {
                    "type": "string",
                    "description": "Name of the MCP tool to call (required for call_tool operation)"
                },
                "tool_arguments": {
                    "type": "object",
                    "description": "Arguments to pass to the MCP tool (for call_tool operation)"
                }
            },
            "required": ["operation"]
        }
    }
]
```

### Step 2: Configuration Parameters Explained

- **name**: Unique identifier for your MCP loader
- **server_url**: URL where your MCP server is running
- **transport**: Communication protocol (typically "http")
- **auto_register**: Whether to automatically register tools
- **tool_prefix**: Prefix added to tool names (e.g., "mcp_")
- **selected_tools**: Specific tools to load (null means load all)

### Step 3: Save Configuration

Save your configuration file with a descriptive name in the ToolUniverse data directory:

```bash
/path/to/tooluniverse/data/your_tool_client_tools.json
```

## Using Your MCP Tool in ToolUniverse

### Step 1: Start Your MCP Server

First, start your MCP server:

```bash
python run_mcp.py
```

### Step 2: Create a Client Script

Create a Python script to use your MCP tool through ToolUniverse:

```python
from tooluniverse.execute_function import ToolUniverse

# Initialize ToolUniverse engine
engine = ToolUniverse()

# Load your MCP tool
tool_type = ['mcp_auto_loader_your_tool']  # Use your configuration name
engine.load_tools(tool_type=tool_type)

# Use your tool
result = engine.run_one_function({
    "name": "mcp_your_function_name",  # This will be prefixed with "mcp_"
    "arguments": {
        "question": "Your input question here",
        "additional_param": True  # Any additional parameters
    }
})

print(result)
```

### Step 3: Example Usage (TxAgent)

Here's how to use TxAgent through ToolUniverse:

```python
from tooluniverse.execute_function import ToolUniverse

engine = ToolUniverse()
tool_type = ['mcp_auto_loader_txagent']
engine.load_tools(tool_type=tool_type)

result = engine.run_one_function({
    "name": "mcp_run_txagent",
    "arguments": {
        "question": "What are the side effects of Panadol?",
        "return_conversation": False
    }
})

print(result)
```

## Complete Example

### 1. MCP Server (`run_mcp.py`)

```python
from fastmcp import FastMCP
from your_module import YourAgent

server = FastMCP('Your MCP Server', stateless_http=True)
agent = YourAgent()

@server.tool()
def process_query(query: str, options: dict = None):
    """Process a query using your agent."""
    return agent.process(query, options)

if __name__ == "__main__":
    server.run(transport='streamable-http', host="0.0.0.0", port=7000)
```

### 2. Configuration (`your_tool_config.json`)

```json
[
    {
        "name": "mcp_auto_loader_your_tool",
        "type": "MCPAutoLoaderTool",
        "server_url": "http://localhost:7000/mcp",
        "transport": "http",
        "auto_register": true,
        "tool_prefix": "mcp_"
    }
]
```

### 3. Client Usage (`client.py`)

```python
from tooluniverse.execute_function import ToolUniverse

engine = ToolUniverse()
engine.load_tools(tool_type=['mcp_auto_loader_your_tool'])

result = engine.run_one_function({
    "name": "mcp_process_query",
    "arguments": {"query": "Hello, world!"}
})

print(result)
```

## Troubleshooting

### Common Issues

1. **Server Connection Failed**
   - Check if your MCP server is running
   - Verify the server URL in your configuration
   - Ensure the port is not blocked by firewall

2. **Tool Not Found**
   - Verify the tool name matches your function name with prefix
   - Check if auto_register is set to true
   - Ensure the configuration file is in the correct location

3. **Import Errors**
   - Make sure all dependencies are installed
   - Check Python path for your modules
   - Verify virtual environment activation

4. **Memory Issues**
   - Set appropriate environment variables (e.g., `MKL_THREADING_LAYER`)
   - Configure model parameters for your hardware
   - Consider using model servers for large models

### Best Practices

1. **Error Handling**: Add proper error handling in your MCP server functions
2. **Documentation**: Provide clear docstrings for all exposed functions
3. **Logging**: Implement logging for debugging and monitoring
4. **Security**: Consider authentication for production deployments
5. **Performance**: Use appropriate timeouts and resource limits

### Getting Help

If you encounter issues:

1. Check the server logs for error messages
2. Verify network connectivity between components
3. Test your MCP server independently before integrating
4. Review the ToolUniverse documentation for additional configuration options

## Conclusion

By following this tutorial, you can successfully convert your Python program into an MCP server and integrate it with ToolUniverse. This approach provides a scalable and standardized way to expose your tools for use by AI agents and other applications.

For more advanced configurations and features, refer to the FastMCP and ToolUniverse documentation.
