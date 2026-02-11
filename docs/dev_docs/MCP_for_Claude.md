# ToolUniverse MCP Integration with Claude Desktop App

This tutorial will Tutorial you through setting up ToolUniverse as an MCP (Model Context Protocol) server for Claude Desktop App.

## Example Integration

For a practical example of using ToolUniverse-MCP with Claude, see the following shared chat log:

[Claude MCP Integration Example](https://claude.ai/share/ab797b7f-6e6b-46f6-b1d5-5a790b90f42d)

## Prerequisites

- Claude Desktop App installed on your system
- ToolUniverse>=0.2.0 installed
- UV package manager installed

## Configuration Steps

### 1. Locate Claude Desktop Configuration

To access the configuration file, open the Claude Desktop App and navigate to **Settings → Developer → Edit Config**. This will allow you to directly edit Claude configuration file.

### 2. Add ToolUniverse MCP Server

Open the configuration file and add the ToolUniverse MCP server configuration:

```json
{
    "mcpServers": {
      "tooluniverse": {
        "command": "uv",
        "args": [
            "--directory",
            "/path/to/tooluniverse-env",  # Working directory: uv manages .venv here
            "run",
            "tooluniverse-smcp-stdio"
        ]
      }
    }
}
```

**Important Configuration Notes**:

- Replace `/path/to/tooluniverse-env` with your actual ToolUniverse working directory
- The working directory is where uv will create and manage the virtual environment (`.venv`)
- Install ToolUniverse first: ``mkdir -p /path/to/tooluniverse-env && uv --directory /path/to/tooluniverse-env pip install tooluniverse``
- Use absolute paths for better reliability

### 3. Configuration Explanation

- **mcpServers**: The main container for all MCP server configurations
- **tooluniverse**: The name identifier for your ToolUniverse MCP server
- **command**: Uses `uv` package manager to run the MCP server
- **args**: Command line arguments passed to uv:
  - `--directory`: Specifies the working directory where uv manages the virtual environment (`.venv`)
  - `run`: Tells uv to run a command
  - `tooluniverse-smcp-stdio`: The specific MCP command to execute

### 4. Restart Claude Desktop

After saving the configuration file, completely quit and restart the Claude Desktop App to load the new MCP server configuration.

### 5. Verify Integration

Once Claude Desktop restarts, you should be able to access ToolUniverse tools and capabilities through the MCP integration. The tools will be available in your conversations with Claude.

## Troubleshooting

**Too Many Tools Loaded**: If you enable too many tools in ToolUniverse, Claude may exceed its context window limit, which can cause errors. To avoid this, only enable a subset of essential tools in your Claude.
