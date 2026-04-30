# ToolUniverse Plugin for Claude Code

1000+ scientific research tools for biology, chemistry, medicine, and data science.

## Install

```bash
# 1. Register the marketplace from GitHub
claude plugin marketplace add mims-harvard/ToolUniverse

# 2. Install the plugin
claude plugin install tooluniverse@tooluniverse
```

Restart Claude Code. Done.

**Full install guide** (troubleshooting, API keys, offline zip install, version pinning): see the [`tooluniverse-claude-code-plugin`](../skills/tooluniverse-claude-code-plugin/SKILL.md) skill.

### Local development install

```bash
# From the repo root:
claude plugin marketplace add ./
claude plugin install tooluniverse@tooluniverse
```

## What's Included

- **MCP Server**: Auto-configured via `.mcp.json`. Provides `find_tools`, `list_tools`, `get_tool_info`, `execute_tool` — accessing 1000+ scientific APIs.
- **114 Research Skills**: Specialized workflows for genomics, drug discovery, clinical analysis, statistical modeling, data wrangling, and more.
- **Slash Commands**: `/tooluniverse:find-tools`, `/tooluniverse:run-tool`
- **Research Agent**: `/tooluniverse:researcher` — autonomous agent for complex multi-database research.

## Usage

**Default: just ask.** The router skill auto-dispatches scientific questions to the matching sub-skill — no command prefix needed.

```
What do we know about drug resistance mutations in EGFR?
Compute differential expression for these RNA-seq counts.
What's the prevalence of distal renal tubular acidosis?
```

For specific surfaces, use the right interaction below.

### Discover tools

| Use this | When |
|---|---|
| `find_tools("topic")` (MCP, agent-side) | One-shot keyword search, you already know the topic |
| `tu find "topic"` (CLI) | Same, from the shell |
| `/tooluniverse:find-tools <research goal>` | You want **multiple** tools for a goal — the command decomposes the goal into sub-questions, runs separate searches per sub-question, follows tool-to-tool links across descriptions, and returns a structured toolkit grouped by sub-question. Use when "what tools do I need to answer X" is itself the question. |

### Run a tool

| Use this | When |
|---|---|
| `tu run <name> '<json>'` (Bash) | You know the exact tool name and JSON args. Fastest. Good in scripts and when piping output. |
| `execute_tool` (MCP, agent-side) | Same as above, from the agent. Equivalent to `tu run` for the agent. |
| `/tooluniverse:run-tool <name> <json-or-natural-language>` | You're not sure of the exact name (fuzzy match works), or you want auto-correction of common alias/type mistakes (`gene` → `gene_symbol`, `"10"` → `10`), or you want the output parsed into a readable summary instead of raw JSON, or you want follow-up tool suggestions. Slower than `tu run` but more forgiving. |

### Launch the research agent

| Use this | When |
|---|---|
| `/tooluniverse:researcher <question>` | Complex multi-database research where you want a forked autonomous agent — useful when the question would otherwise pollute your main conversation context with many tool calls and intermediate data. |

### Bulk tool calls (5+ in a loop)

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()
for gene in ["TP53", "BRCA1", "PIK3CA", "PTEN", "KRAS"]:
    print(tu.run_one_function({"name": "ensembl_lookup_gene",
                                "arguments": {"gene_id": gene, "species": "homo_sapiens"}}))
```

Use the SDK over `tu run` in a Bash loop — registry loads once, avoiding per-call startup overhead.

## Design Philosophy

- **The router skill is the front door.** Just ask scientific questions in natural language; the router auto-routes to the specialized skill. No slash command needed for normal research.
- **`tu run` is the fastest tool surface** when you know what you want.
- **The slash commands earn their weight** only when they add a process the bare tool call doesn't have: `/find-tools` adds multi-hop discovery, `/run-tool` adds input validation and output parsing.
- **MCP** (`find_tools`, `get_tool_info`, `execute_tool`) is what the agent uses internally — exposed for direct use too, but `tu run` from Bash is usually simpler.

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
