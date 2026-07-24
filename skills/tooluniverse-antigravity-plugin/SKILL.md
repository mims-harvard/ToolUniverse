---
name: tooluniverse-antigravity-plugin
description: Install, set up, verify, update, pin, uninstall, or troubleshoot the ToolUniverse plugin on Google Antigravity (AGY / Antigravity IDE / Antigravity 2.0). ALWAYS consult this skill for any of those — don't answer from memory, because the exact CLI name (agy), the "agy plugin install <path>" flow, the uvx tooluniverse MCP server, and the API-key env vars are easy to get wrong. Use it whenever someone wants to get ToolUniverse (or "the 1000+ scientific tools" / "the harvard tools") working on Antigravity, says the Antigravity plugin or its tools/skills won't load, hits a uvx or MCP-server startup error, asks how Antigravity updates it, wants to pin or remove it, or finds it running an old tool version. Not for the Codex plugin (use tooluniverse-codex-plugin) or Claude Code plugin (use tooluniverse-claude-code-plugin), for running research with the tools, or for authoring new tools or skills.
disable-model-invocation: true
---

# Install the ToolUniverse Plugin for Google Antigravity (AGY)

One-step install on Google Antigravity (AGY / Antigravity IDE / Antigravity 2.0): an MCP server exposing 1000+ scientific tools plus 120+ research skills — all auto-configured.

## Prerequisites (check once)

```bash
uv --version   # provides `uvx`; if missing: curl -LsSf https://astral.sh/uv/install.sh | sh
agy --version  # Antigravity CLI; if missing: https://antigravity.google
```

## Install

In Antigravity, plugins can be installed using the `agy` CLI:

### Option 1: Direct path / imported plugin install (recommended)

```bash
# If installed via Claude Code / Codex marketplace cache or cloned repo:
agy plugin install /path/to/ToolUniverse/plugin
```

### Option 2: Clone + install

```bash
git clone https://github.com/mims-harvard/ToolUniverse.git
cd ToolUniverse
agy plugin install ./plugin
```

Restart Antigravity. The MCP server auto-starts via `uvx tooluniverse` on first use (~30 s cold start while the package downloads, instant after).

## Verify it worked

```bash
agy plugin list
```

Expect output showing `tooluniverse` under `imports`:

```json
{
  "imports": [
    {
      "name": "tooluniverse",
      "source": "claude-code",
      "components": [
        "skills",
        "agents",
        "mcpServers",
        "hooks",
        "commands"
      ]
    }
  ]
}
```

Inside Antigravity, just ask naturally:

```
What are the top mutated genes in breast cancer?
Research the drug metformin.
```

The research skills auto-activate on matching questions, and the MCP tools are discovered and run via `find_tools` → `execute_tool` — no command prefix needed.

## What you get

| Component | What it does | How it's used |
|---|---|---|
| **MCP server** | 1000+ tools via `find_tools`, `get_tool_info`, `execute_tool` | Auto-loaded; no action needed |
| **120+ skills** | Structured research workflows (drug discovery, variant interpretation, pharmacovigilance, phylogenetics, statistical modeling, etc.) | Auto-activate on matching questions |
| **Research agent** | Autonomous multi-database research subagent | Auto-routed on complex research tasks |

## API keys (optional, but recommended)

Most tools work without keys. For higher rate limits or gated databases, set the keys you care about in `~/.gemini/config/plugins/tooluniverse/mcp_config.json` or pass them in environment variables:

```bash
export NCBI_API_KEY="your_key"
export ONCOKB_API_TOKEN="your_token"
export SEMANTIC_SCHOLAR_API_KEY="your_key"
```

## Update

```bash
uv cache clean tooluniverse
```

Restart Antigravity.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `uvx: command not found` | Install `uv` (see Prerequisites), reopen terminal. |
| MCP server won't start | Run `uv cache clean tooluniverse` or `uvx --refresh tooluniverse --help` in terminal. |
| Plugin installs but tools missing | Restart Antigravity CLI/IDE. First launch downloads the package (~30 s). |
| `requires-python >= 3.10` | `uv python install 3.12` |

Still stuck: https://github.com/mims-harvard/ToolUniverse/issues
