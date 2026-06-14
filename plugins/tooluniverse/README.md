# ToolUniverse Plugin for Codex

1000+ scientific research tools for biology, chemistry, medicine, and data science.

## What is included

- MCP server configuration for ToolUniverse discovery and execution tools.
- Generated copies of ToolUniverse skills from the repository root `skills/` directory.
- Research workflows for genomics, drug discovery, clinical analysis, literature review, statistical modeling, and scientific data analysis.

## Install

```bash
codex plugin marketplace add mims-harvard/ToolUniverse
codex plugin add tooluniverse -m tooluniverse
```

Codex auto-upgrades configured marketplaces on startup, so plugin updates arrive
on the next launch. The tools are served over MCP via `uvx tooluniverse` (the
package is fetched automatically).

## Development

The `skills/` directory in this plugin is generated. Do not edit it directly.

Update the canonical skills under the repository root `skills/` directory, then
run the shared sync — it rebuilds the skill copies for BOTH the Claude and Codex
plugins (and applies the Codex-specific normalizations):

```bash
plugin/sync-skills.sh
```

To assemble the distributable Codex bundle:

```bash
scripts/build-codex-plugin.sh
```

The build output is written to:

```text
dist/tooluniverse-codex-plugin/
```
