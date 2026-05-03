# Using --tools-file Filter with Claude Desktop

This example demonstrates how to use the `--tools-file` parameter to restrict the tools exposed by the ToolUniverse SMCP server, making it compatible with Claude Desktop's 64-character tool name limit.

## Use Case

When connecting ToolUniverse SMCP server to Claude Desktop via STDIO transport, you may encounter tool names that exceed Claude Desktop's 64-character limit. By providing a whitelist of short-named tools using `--tools-file`, you can selectively expose only the tools you need.

## Example Files

- `tools_short.txt` - Whitelist with 3 example tool names (all <64 chars)
- `stdio_wrapper.py` - STDIO wrapper script for Claude Desktop integration

## How It Works

The `--tools-file` parameter accepts a path to a text file containing tool names (one per line). The SMCP server will only expose tools listed in this file, filtering out all others.

### Creating Your Own Whitelist

1. Create a text file with one tool name per line (comments starting with `#` are ignored)
2. Only include tool names with ≤64 characters to ensure Claude Desktop compatibility
3. Use the path to this file with the `--tools-file` parameter

### Example tools_short.txt

```
# Literature search tools
ArXiv_search_papers
SemanticScholar_search_papers
PubMed_search_articles

# Add more tools as needed (one per line)
```

## Claude Desktop Configuration

To use ToolUniverse with Claude Desktop, add this configuration to your Claude Desktop settings:

```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "python",
      "args": [
        "-m", "tooluniverse.smcp_server",
        "--transport", "stdio",
        "--tools-file", "/absolute/path/to/tools_short.txt"
      ],
      "env": {
        "FASTMCP_NO_BANNER": "1",
        "PYTHONWARNINGS": "ignore"
      }
    }
  }
}
```

### Alternative: Using stdio_wrapper.py

For more advanced filtering of stdout/stderr, you can use the included `stdio_wrapper.py`:

```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "python",
      "args": [
        "stdio_wrapper.py"
      ],
      "env": {
        "FASTMCP_NO_BANNER": "1",
        "PYTHONWARNINGS": "ignore"
      }
    }
  }
}
```

## Finding Available Tools

To find available tools that fit the 64-character limit, you can list all tools:

```bash
# List all available tools
python -m tooluniverse.smcp_server --list-tools

# List tools in specific categories
python -m tooluniverse.smcp_server --categories literature --list-tools

# Save to a file for editing
python -m tooluniverse.smcp_server --list-tools > all_tools.txt
```

## Tips

1. **Keep tool names short**: Claude Desktop has a 64-character limit
2. **Start with commonly used tools**: Build your whitelist incrementally
3. **Test your configuration**: Verify the tools you need are available
4. **Update as needed**: You can modify `tools_short.txt` and restart Claude Desktop

