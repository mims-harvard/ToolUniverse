# ToolUniverse + Claude Desktop

Use ToolUniverse with Claude Desktop by creating a curated whitelist of tools that respect Claude Desktop's 64-character tool name limit.

## Quick Start

### 1. Create your tool whitelist

Edit `tools_short.txt` and add tools (one per line). Include only tool names ≤64 characters.

```
ArXiv_search_papers
SemanticScholar_search_papers
PubMed_search_articles
```

### 2. Configure Claude Desktop

Add this to your Claude Desktop settings (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

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

### 3. Restart Claude Desktop

Restart to load the configuration.