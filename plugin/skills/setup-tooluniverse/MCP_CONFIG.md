# MCP Configuration Guide

Advanced configuration options for ToolUniverse MCP integration.

## Configuration File Locations

### Cursor

- **Global (all workspaces)** — macOS/Linux: `~/.cursor/mcp.json` · Windows: `%USERPROFILE%\.cursor\mcp.json`
- **Project-level (single workspace)**: `.cursor/mcp.json` in the project root — can be committed to version control for team sharing

### Claude Desktop

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### VS Code / Copilot

- **Project-level** (workspace root): `.vscode/mcp.json`
- Note: VS Code uses `"servers"` key (not `"mcpServers"`) and requires `"type": "stdio"` — see the VS Code template below.

### Windsurf

- **macOS/Linux**: `~/.codeium/windsurf/mcp_config.json`
- **Windows**: `%USERPROFILE%\.codeium\windsurf\mcp_config.json`

### Claude Code

- Global: `~/.claude.json`
- Project-level: `.mcp.json` in the project root

### Gemini CLI

- `~/.gemini/settings.json`

### Antigravity

- **macOS/Linux**: `~/.gemini/antigravity/mcp_config.json`
- **Windows**: `%USERPROFILE%\.gemini\antigravity\mcp_config.json`

Access via: Agent Panel → "..." → Manage MCP Servers → View raw config. Uses `"mcpServers"` key (same as Claude Desktop format).

### Cline

Full path to `cline_mcp_settings.json` varies by OS:

- **macOS**: `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- **Linux**: `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- **Windows**: `%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`
- **Cline CLI (standalone)**: `~/.cline/data/settings/cline_mcp_settings.json`

Access via Cline's "MCP Servers" icon → Configure tab → "Configure MCP Servers". Uses `"mcpServers"` key (same as Claude Desktop format).

### Trae

- **Windows**: `%APPDATA%\Trae\User\mcp.json`
- **macOS**: `~/Library/Application Support/Trae/User/mcp.json`
- **Linux**: `~/.config/Trae/User/mcp.json`

Verify the exact path in Trae: Settings → MCP → Open config file.

The AI agent can only access the **global** config. Project-level `.trae/mcp.json` is an experimental/beta feature and is not accessible to the agent — do not use it for MCP server registration.

For full Trae setup instructions (including manual write fallback and verification), see [TRAE.md](https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/TRAE.md).

## Configuration Templates

### Basic Configuration (Recommended)

Zero-install setup using uvx (auto-downloads and runs ToolUniverse):

```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "uvx",
      "args": ["--refresh", "tooluniverse"],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

`--refresh` keeps ToolUniverse auto-updated on each startup (~1–2s overhead). Remove it to pin to the cached version and update manually with `uv cache clean tooluniverse`.

### pip-Based Configuration (Alternative)

If you have ToolUniverse installed via `pip install tooluniverse`, you can use the installed command directly:

```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "tooluniverse-smcp-stdio",
      "args": ["--compact-mode"],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

### Development Configuration

Using development installation:

```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "python3",
      "args": [
        "-m",
        "tooluniverse.smcp_server",
        "--compact-mode"
      ],
      "cwd": "/path/to/ToolUniverse-main"
    }
  }
}
```

### VS Code / Copilot Configuration

VS Code uses a different schema. Create `.vscode/mcp.json` in the workspace root:

```json
{
  "servers": {
    "tooluniverse": {
      "command": "uvx",
      "args": ["--refresh", "tooluniverse"],
      "env": { "PYTHONIOENCODING": "utf-8" },
      "type": "stdio"
    }
  }
}
```

Key differences from standard config: uses `"servers"` (not `"mcpServers"`) and requires `"type": "stdio"`. After saving, fully restart VS Code and open Copilot Chat in that workspace.

## Configuration Options

### Compact Mode (Default with uvx)

When using `uvx tooluniverse`, compact mode is **enabled by default** — no flag needed. It exposes only 5 core tools to prevent context overflow, while keeping all 1000+ tools accessible via `execute_tool`.

If using the pip-based `tooluniverse-smcp-stdio` command, pass `--compact-mode` explicitly:
```json
"args": ["--compact-mode"]
```

**Core tools exposed in compact mode**:
- `list_tools` - List all available tools
- `grep_tools` - Search tools by keyword
- `get_tool_info` - Get tool details
- `execute_tool` - Execute any tool by name
- `find_tools` - Find tools by description

### Specific Categories

Load only specific tool categories:

```json
"args": [
  "--categories",
  "uniprot",
  "ChEMBL",
  "opentarget",
  "pdb"
]
```

**Available categories**: Run `uvx tooluniverse --list-categories` to see all.

**Warning**: Multiple categories may still cause context issues.

### Exclude Categories

Load all except specific categories:

```json
"args": [
  "--exclude-categories",
  "mcp_auto_loader_boltz",
  "mcp_auto_loader_expert_feedback"
]
```

### Specific Tools Only

Load only named tools:

```json
"args": [
  "--include-tools",
  "UniProt_get_entry_by_accession",
  "ChEMBL_get_molecule_by_chembl_id"
]
```

### Enable Hooks

Enable output processing hooks (disabled by default for stdio):

```json
"args": [
  "--refresh", "tooluniverse",
  "--hooks",
  "--hook-type",
  "SummarizationHook"
]
```

**Hook types**:
- `SummarizationHook` - Summarize long outputs
- `FileSaveHook` - Save outputs to files

### Verbose Logging

Enable detailed logging for debugging:

```json
"args": [
  "--refresh", "tooluniverse",
  "--verbose"
]
```

## Environment Variables

### Standard Variables

```json
"env": {
  "PYTHONIOENCODING": "utf-8",
  "PYTHONPATH": "/custom/python/path",
  "TOOLUNIVERSE_CACHE_DIR": "/custom/cache/dir"
}
```

### API Keys

For tools requiring authentication:

```json
"env": {
  "PYTHONIOENCODING": "utf-8",
  "OPENAI_API_KEY": "your-key-here",
  "ANTHROPIC_API_KEY": "your-key-here",
  "UMLS_API_KEY": "your-key-here"
}
```

**Security Note**: Avoid hardcoding keys. Use environment variables or .env files.

### Better API Key Management

Use environment variables from shell:

```json
"env": {
  "PYTHONIOENCODING": "utf-8",
  "OPENAI_API_KEY": "${OPENAI_API_KEY}"
}
```

Then set in shell:
```bash
export OPENAI_API_KEY=your-key-here
```

## Multiple MCP Servers

Configure multiple servers:

```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "uvx",
      "args": ["--refresh", "tooluniverse"],
      "env": { "PYTHONIOENCODING": "utf-8" }
    },
    "other-server": {
      "command": "other-mcp-server",
      "args": []
    }
  }
}
```

## Working Directory

Specify working directory:

```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "uvx",
      "args": ["--refresh", "tooluniverse"],
      "env": { "PYTHONIOENCODING": "utf-8" },
      "cwd": "/path/to/working/directory"
    }
  }
}
```

## Testing Configuration

### Validate JSON

Before saving, validate JSON syntax:

```bash
# macOS/Linux
cat mcp.json | python3 -m json.tool

# Or use online validator
```

### Test Command Directly

Test the MCP command in terminal:

```bash
uvx tooluniverse --help
# Should print usage text without errors
```

### Test with a ToolUniverse Skill

After skills are installed (see SKILL.md Step 6), verify end-to-end by invoking the `tooluniverse` router skill in your prompt:

> `"Use the tooluniverse skill to research the drug metformin"`

The `tooluniverse` skill is a router — it automatically picks the right sub-skill and calls multiple tools. Mentioning it explicitly ensures it activates on any client, since not all clients auto-detect skills from natural language alone.

If the response comes back as plain text without any tool calls, either skills are not installed, they are in the wrong directory, or the MCP server is not connected.

Other examples:
- `"Use the tooluniverse skill: what is known about Alzheimer's disease?"`
- `"Use the tooluniverse skill: what does the literature say about CRISPR in cancer?"`

### Check Logs

After restarting application, check logs:

**Cursor logs**:
- macOS: `~/Library/Application Support/Cursor/logs/`
- Look for files with "mcp" in the name

**Claude Desktop logs**:
- Access via app: Help → View Logs

## Troubleshooting Configuration

### Issue: Server Won't Start

1. Test command directly in terminal
2. Check JSON syntax (no trailing commas)
3. Verify paths are absolute, not relative
4. Check file permissions

### Issue: Context Overflow

- Ensure `--compact-mode` is in args
- Reduce number of categories
- Use specific tools only

### Issue: Command Not Found

- Verify uvx works: `uvx --version`
- Test ToolUniverse directly: `uvx tooluniverse --help`
- If uvx is missing, install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- For pip-based installs: `pip show tooluniverse` and `which tooluniverse-smcp-stdio`

### Issue: Environment Variables Not Working

- Use absolute paths
- Avoid ~ expansion (use full path)
- Check variable syntax in JSON

## Performance Optimization

### Fast Startup

Use minimal categories (compact mode is already the default):

```json
"args": [
  "--refresh", "tooluniverse",
  "--categories",
  "special_tools"
]
```

### Memory Optimization

Exclude heavy categories:

```json
"args": [
  "--refresh", "tooluniverse",
  "--exclude-categories",
  "mcp_auto_loader_boltz"
]
```

## Security Considerations

1. **API Keys**: Never commit config files with hardcoded keys
2. **Paths**: Use absolute paths to avoid ambiguity
3. **Permissions**: Restrict config file permissions (chmod 600)
4. **Validation**: Always validate JSON before saving

## Example Configurations

### Research Use Case

For scientific research with common tools:

```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "uvx",
      "args": ["--refresh", "tooluniverse"],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "NCBI_API_KEY": "your-key-here"
      }
    }
  }
}
```

### Development Use Case

For tool development and testing:

```json
{
  "mcpServers": {
    "tooluniverse-dev": {
      "command": "python3",
      "args": [
        "-m",
        "tooluniverse.smcp_server",
        "--compact-mode",
        "--verbose"
      ],
      "cwd": "/path/to/ToolUniverse-main"
    }
  }
}
```

### Production Use Case

For production with specific tool categories:

```json
{
  "mcpServers": {
    "tooluniverse-prod": {
      "command": "uvx",
      "args": [
        "tooluniverse",
        "--categories",
        "uniprot",
        "ChEMBL",
        "opentarget"
      ],
      "env": { "PYTHONIOENCODING": "utf-8" }
    }
  }
}
```

## Advanced Features

### Space Configuration

Load preset tool configurations:

```json
"args": [
  "--compact-mode",
  "--load",
  "community/proteomics-toolkit"
]
```

### Custom Hook Configuration

Use custom hook configuration file:

```json
"args": [
  "--compact-mode",
  "--hooks",
  "--hook-config-file",
  "/path/to/hook_config.json"
]
```
