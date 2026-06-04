---
name: tooluniverse-claude-code-plugin
description: Install the ToolUniverse Claude Code plugin in one step — provides MCP server with 1000+ scientific tools, 120+ research skills, slash commands, hooks, and the research agent. Use for first-time plugin install, troubleshooting plugin not loading, verifying MCP server connection, listing API key requirements, or configuring auto-update.
disable-model-invocation: true
---

# Install the ToolUniverse Plugin for Claude Code

One-step install of the ToolUniverse plugin: MCP server with 1000+ tools, 120+ research skills, slash commands, and the research agent — all auto-configured.

## Prerequisites (check once)

```bash
uv --version      # must exist; if not:  curl -LsSf https://astral.sh/uv/install.sh | sh
claude --version  # Claude Code CLI; if not: https://claude.com/claude-code
```

## Install (two commands)

```bash
# 1. Register the ToolUniverse marketplace from GitHub
claude plugin marketplace add mims-harvard/ToolUniverse

# 2. Install the plugin
claude plugin install tooluniverse@tooluniverse
```

That's it. Restart Claude Code. The MCP server auto-starts via `uvx tooluniverse` on first use (~30 s cold start, instant after).

### Important: Remove global skills if previously installed

If you previously installed ToolUniverse skills globally (via `tooluniverse-install-skills` or manual copy), **remove them**. The plugin includes all skills — global copies interfere with the plugin's skill routing.

```bash
# Check for global skills
ls ~/.claude/skills/tooluniverse-* 2>/dev/null | wc -l

# Remove them (the plugin replaces them)
rm -rf ~/.claude/skills/tooluniverse-*
rm -rf ~/.claude/skills/create-tooluniverse-skill
rm -rf ~/.claude/skills/setup-tooluniverse
```

### Pin the tool version (optional, for reproducibility)

The MCP server runs the `tooluniverse` PyPI package via `uvx`. To lock tool behavior for a long-running analysis, pin the package version in the plugin's `.mcp.json` — change the args to:

```json
"args": ["tooluniverse@1.2.2"]
```

Replace `1.2.2` with any released version from https://pypi.org/project/tooluniverse/. Restart Claude Code to apply. (`.mcp.json` location is shown under "API keys" below.)

## Verify it worked

```bash
claude plugin list
# Expect: tooluniverse  (enabled)
```

Inside Claude Code, just ask naturally:
```
What are the top mutated genes in breast cancer?
Research the drug metformin.
```

The router skill auto-dispatches to the right specialized skill — no command prefix needed.

## What you get

| Component | What it does | How to invoke |
|---|---|---|
| **MCP server** | 1000+ tools via `find_tools`, `get_tool_info`, `execute_tool` | Auto-loaded; no action needed |
| **`/tooluniverse:research`** | Multi-database investigation inline in this chat (you see each step) | Slash command |
| **`/tooluniverse:translate-id`** | Resolve an ID across all relevant namespaces | Slash command |
| **`/tooluniverse:cross-validate`** | Verify a claim across 3+ independent databases | Slash command |
| **`/tooluniverse:compare`** | N-way side-by-side comparison with domain-appropriate columns | Slash command |
| **`/tooluniverse:literature-sweep`** | Graded mini-review across PubMed + EuropePMC + Semantic Scholar | Slash command |
| **`/tooluniverse:researcher`** | Same investigation as `research`, delegated to a forked subagent | Slash command |
| **120+ skills** | Structured workflows (drug research, variant interpretation, pharmacovigilance, CRISPR screens, statistical modeling, etc.) | Auto-activate on matching questions |

## API keys (optional, but recommended)

Most tools work without keys. For enhanced access, add the keys you care about to the MCP server's `env` block. Locate the installed plugin's `.mcp.json`:

```bash
# Show component inventory + on-disk location:
claude plugin details tooluniverse

# Or find the file directly:
find ~/.claude/plugins -name '.mcp.json' -path '*tooluniverse*'

# Typical install location after marketplace install:
# ~/.claude/plugins/cache/tooluniverse/tooluniverse/<version>/.mcp.json
```

```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "uvx",
      "args": ["tooluniverse"],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "NCBI_API_KEY": "your_key",
        "NVIDIA_API_KEY": "your_key",
        "ONCOKB_API_TOKEN": "your_token"
      }
    }
  }
}
```

Full API-key list: `setup-tooluniverse` skill → `API_KEYS_REFERENCE.md`.

## Update

```bash
claude plugin update tooluniverse
# Also refresh the MCP server's tool cache:
uv cache clean tooluniverse
```

Restart Claude Code.

## Uninstall

```bash
claude plugin uninstall tooluniverse
claude plugin marketplace remove tooluniverse
```

## Alternative install paths

### Clone + local install (air-gapped or forks)

```bash
git clone https://github.com/mims-harvard/ToolUniverse.git
cd ToolUniverse
claude plugin marketplace add ./
claude plugin install tooluniverse@tooluniverse
```

### Download the release zip (no git needed)

Grab `tooluniverse-plugin-vX.Y.Z.zip` from https://github.com/mims-harvard/ToolUniverse/releases, unzip, then:

```bash
claude plugin marketplace add /path/to/unzipped-dir
claude plugin install tooluniverse@tooluniverse
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `marketplace add` fails with "no marketplace.json" | Ensure you're using `mims-harvard/ToolUniverse` (owner/repo), not the plugin subdir. |
| `uvx: command not found` | Install `uv` (see Prerequisites), reopen terminal. |
| MCP server won't start | Test in terminal: `uvx tooluniverse`. If it fails there, it's an `uv`/Python issue. |
| Plugin installs but tools missing | Restart Claude Code. First launch downloads the package (~30 s). |
| `requires-python >= 3.10` | `uv python install 3.12` |
| Tools feel outdated | `uv cache clean tooluniverse` then restart Claude Code. |
| New release not picked up / tools run an OLD version | Run `uv tool list \| grep tooluniverse`. If it's listed, a global `uv tool install` is **shadowing** the plugin's `uvx` (uvx prefers an installed tool over the latest published version). Fix: `uv tool uninstall tooluniverse`, then restart. Normal users without that install always get the latest automatically. |

Still stuck: https://github.com/mims-harvard/ToolUniverse/issues

## Automated diagnosis & repair

If the table above didn't fix it, hand this skill to an agent — *"read the
tooluniverse-claude-code-plugin skill and diagnose & fix my plugin install"* — or
run these checks yourself in order. Each is safe and idempotent; apply the `FIX`
for whatever fails, then restart Claude Code.

```bash
# 1. Is uv/uvx installed?  (most common cause of "no tools at all")
command -v uvx || echo "FIX: curl -LsSf https://astral.sh/uv/install.sh | sh"

# 2. Can the MCP package actually resolve + run?  (non-hanging proxy for the server)
uvx --from tooluniverse tu --version || echo "FIX: uv/Python issue — see steps 1 and 5"

# 3. Running an OLD version even after updating?  (non-obvious!)
uv tool list | grep -q tooluniverse \
  && echo "FIX: uv tool uninstall tooluniverse   (a global install shadows the plugin's uvx)" \
  || echo "ok: nothing shadowing uvx"

# 4. A new pip version was released but tools still stale?  force a refresh
uv cache clean tooluniverse        # or one-shot: uvx --refresh tooluniverse --version

# 5. Python too old (requires >= 3.10)?
uv python install 3.12

# 6. Global skills interfering with the plugin's routing?
ls ~/.claude/skills/tooluniverse-* 2>/dev/null && echo "FIX: rm -rf ~/.claude/skills/tooluniverse-*"

# 7. Is the plugin actually enabled?
claude plugin list | grep tooluniverse || echo "FIX: claude plugin install tooluniverse@tooluniverse"
```

An agent can run the whole sequence, apply each `FIX`, and tell you to restart —
you don't need to understand the internals.

## For plugin maintainers

This skill documents the **user-facing** install flow. The plugin source lives at `/plugin` in the repo with its own `.claude-plugin/plugin.json` and `.mcp.json`. The root `.claude-plugin/marketplace.json` is what makes `claude plugin marketplace add mims-harvard/ToolUniverse` work directly — it lists the plugin with `"source": "./plugin"`.

When cutting a **plugin** release:
- Easiest: put `[release:patch]` (or `:minor`/`:major`) in a commit message that touches `plugin/` or `.claude-plugin/` on `main`. `auto-release.yml` runs `scripts/release-plugin.sh`, which bumps `plugin/.claude-plugin/plugin.json` + root `.claude-plugin/marketplace.json`, commits, and tags; the tag push triggers `release-plugin.yml` to build the zip + GitHub Release. (Or run "Auto-release plugin" from the Actions UI.)
- The next-version baseline is `max(plugin.json, latest vX.Y.Z tag)`, so a manifest that has drifted behind the tag line won't collide with an existing tag.
- Plugin auto-update reaches users as soon as the version-bump commit lands on `main` (independent of the tag/zip).

The **pip package** (`tooluniverse` on PyPI) is a SEPARATE release line: bump `pyproject.toml` → `publish-pypi.yml` publishes it (→ `publish-mcp-registry.yml`). Plugin and pip versions need NOT move together — `uvx tooluniverse` auto-resolves to the latest published pip version for users, so plugin-only and pip-only releases are both fine.
