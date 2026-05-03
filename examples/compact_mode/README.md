# SMCP Compact Mode

Compact mode is a special configuration for SMCP server that only exposes 4-5 core tools to prevent context window overflow, while maintaining full functionality through search and execute capabilities.

## What is Compact Mode?

When enabled, compact mode:
- **Only exposes 4-5 core tools** instead of 1000++ tools
- **Reduces context window usage by ~99%**
- **Maintains full functionality** - all tools are still accessible via `execute_tool`
- **Enables progressive disclosure** - start with minimal info, get details when needed

## Core Tools

Compact mode exposes 4 core discovery tools, plus optionally `find_tools` if search is enabled (default):

1. **`list_tools`** - List available tools with different modes:
   - `mode="names"` - List only tool names
   - `mode="categories"` - List category statistics
   - `mode="by_category"` - List tools grouped by category

2. **`grep_tools`** - Search tools by text or regex pattern:
   - Search in tool names, descriptions, or other fields
   - Supports text and regex search modes

3. **`get_tool_info`** - Get tool information:
   - `detail_level="description"` - Get name and description
   - `detail_level="full"` - Get complete tool definition
   - Supports single or multiple tools

4. **`execute_tool`** - Execute any ToolUniverse tool by name:
   - Pass tool name and arguments as dictionary
   - Returns tool execution result

5. **`find_tools`** - AI-powered tool discovery using natural language queries (optional, enabled by default):
   - Natural language search for tools
   - Supports category filtering
   - Uses AI-powered semantic search when available

## Usage

### Command Line

```bash
# STDIO mode (for Claude Desktop)
tooluniverse-smcp-stdio --compact-mode

# HTTP mode
tooluniverse-smcp-server --compact-mode --port 8000
```

### Claude Desktop Configuration

Add this to your Claude Desktop settings (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "tooluniverse-compact": {
      "command": "python",
      "args": [
        "-m", "tooluniverse.smcp_server",
        "--transport", "stdio",
        "--compact-mode"
      ],
      "env": {
        "FASTMCP_NO_BANNER": "1",
        "PYTHONWARNINGS": "ignore"
      }
    }
  }
}
```

## Workflow Example

1. **List available tools**
   ```python
   tools = list_tools(mode="names")
   # Returns: ~750 tool names
   ```

2. **Search for relevant tools**
   ```python
   results = grep_tools(pattern="protein", field="name", limit=10)
   # Returns: Tools matching "protein" in name
   ```

3. **Get tool details**
   ```python
   info = get_tool_info(tool_names="UniProt_get_entry_by_accession", detail_level="full")
   # Returns: Complete tool definition with parameters
   ```

4. **Execute tool**
   ```python
   result = execute_tool(
       tool_name="UniProt_get_entry_by_accession",
       arguments={"accession": "P05067"}
   )
   ```

## Comparison

| Feature | Normal Mode | Compact Mode |
|---------|------------|--------------|
| Tools Exposed | ~750 tools | 4-5 tools (4 core + find_tools if search enabled) |
| Context Window Usage | High | Low (~99% reduction) |
| Functionality | Full | Full (via execute_tool) |

## See Also

- [`complete_example.py`](./complete_example.py) - Complete usage example with MCP client
- [`test_stdio_simple.py`](./test_stdio_simple.py) - Simple stdio mode test script
- [Compact Mode Guide](../../../docs/guide/compact_mode.rst) - Detailed documentation
- [SMCP Documentation](../../../docs/) - General SMCP documentation
