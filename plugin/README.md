# ToolUniverse Plugin for Claude Code

1000+ scientific research tools for biology, chemistry, medicine, and data science.

## Install

```bash
# One command:
claude plugin add /path/to/tooluniverse-plugin

# Or load for current session:
claude --plugin-dir /path/to/tooluniverse-plugin
```

## What's Included

- **MCP Server**: Auto-configured via `.mcp.json`. Provides `find_tools`, `list_tools`, `get_tool_info`, `execute_tool` — accessing 1000+ scientific APIs.
- **114 Research Skills**: Specialized workflows for genomics, drug discovery, clinical analysis, statistical modeling, data wrangling, and more.
- **Slash Commands**: `/tooluniverse:find-tools`, `/tooluniverse:run-tool`
- **Research Agent**: `/tooluniverse:researcher` — autonomous agent for complex multi-database research.

## Usage

```
# Discover tools (MCP — good for exploration)
/tooluniverse:find-tools protein structure prediction

# Run a single tool via CLI (one-off Bash query)
tu run UniProt_search '{"query": "BRCA1", "organism": "human"}'

# Research a question (auto-plans tool calls, uses SDK for batches)
/tooluniverse:research What are the top mutated genes in breast cancer?

# Launch research agent for complex multi-database questions
/tooluniverse:researcher What genes are associated with Alzheimer's disease?

# Or just ask — the router skill auto-dispatches
"What do we know about drug resistance mutations in EGFR?"
```

## Design Philosophy: CLI Default, SDK for Large Batches, MCP for Discovery

- **CLI** (`tu run`): Default for most tool calls — simple, direct, output flows into conversation naturally
- **Python SDK** (`from tooluniverse import ToolUniverse`): Use for large batches (5+ calls in a loop) — loads the registry once and avoids per-call startup overhead
- **MCP tools** (`find_tools`, `get_tool_info`): Best for discovering which tools exist and checking parameters

The plugin configures MCP for discovery and teaches the agent to use the CLI for most work, switching to the SDK only when looping over many items.

## API Keys (Optional)

Most tools work without API keys. For enhanced access:

| Key | Source | Free? |
|-----|--------|-------|
| `NCBI_API_KEY` | https://www.ncbi.nlm.nih.gov/account/settings/ | Yes |
| `SEMANTIC_SCHOLAR_API_KEY` | https://www.semanticscholar.org/product/api | Yes |
| `ONCOKB_API_TOKEN` | https://www.oncokb.org/apiAccess | Academic |

Set via environment variables or in the MCP server config.

## Update

The MCP server auto-updates via `uvx --refresh`. To update skills, re-install the plugin.

## Links

- [ToolUniverse Documentation](https://aiscientist.tools)
- [GitHub Repository](https://github.com/mims-harvard/ToolUniverse)
- [Tool Catalog](https://aiscientist.tools/tools)
