# ToolUniverse Plugin for Codex

1000+ scientific research tools for biology, chemistry, medicine, and data science.

## What is included

- MCP server configuration for ToolUniverse discovery and execution tools.
- Generated copies of ToolUniverse skills from the repository root `skills/` directory.
- Research workflows for genomics, drug discovery, clinical analysis, literature review, statistical modeling, and scientific data analysis.

## Development

The `skills/` directory in this plugin is generated. Do not edit it directly.

Update the canonical skills under the repository root `skills/` directory, then run:

```bash
scripts/sync-codex-plugin-skills.sh
scripts/build-codex-plugin.sh
```

The build output is written to:

```text
dist/tooluniverse-codex-plugin/
```
