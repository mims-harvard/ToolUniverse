# MCP Configuration — Special Formats

Most clients use the standard `mcpServers` JSON format (see SKILL.md). These clients use different formats:

## VS Code (Copilot)

Uses `"servers"` key (not `"mcpServers"`) and requires `"type"` field. Add to `.vscode/mcp.json`:
```json
{
  "servers": {
    "tooluniverse": {
      "type": "stdio",
      "command": "uvx",
      "args": ["tooluniverse"],
      "env": { "PYTHONIOENCODING": "utf-8" }
    }
  }
}
```

## Codex (TOML format)

Add to `~/.codex/config.toml`:
```toml
[mcp_servers.tooluniverse]
command = "uvx"
args = ["tooluniverse"]
env = { "PYTHONIOENCODING" = "utf-8" }
```

## OpenCode

Uses `mcp` key with `type` and `command` as array in `opencode.json`:
```json
{
  "mcp": {
    "tooluniverse": {
      "type": "local",
      "command": ["uvx", "tooluniverse"],
      "enabled": true,
      "environment": { "PYTHONIOENCODING": "utf-8" }
    }
  }
}
```

## Antigravity

Standard `mcpServers` format. Access via: "..." dropdown → Manage MCP Servers → View raw config.
```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "uvx",
      "args": ["tooluniverse"],
      "env": { "PYTHONIOENCODING": "utf-8" }
    }
  }
}
```
