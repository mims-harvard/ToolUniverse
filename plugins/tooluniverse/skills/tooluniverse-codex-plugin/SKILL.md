---

name: tooluniverse-codex-plugin
description: "Install, set up, verify, update, pin, uninstall, or troubleshoot the ToolUniverse plugin on OpenAI Codex. ALWAYS consult this skill for any of those — don't answer from memory, because the exact marketplace name (mims-harvard/ToolUniverse), the \"codex plugin marketplace add\" then \"codex plugin add -m tooluniverse\" flow, Codex's startup auto-upgrade behavior, the uvx tooluniverse MCP server, and the API-key env vars are easy to get wrong. Use it whenever someone wants to get ToolUniverse (or \"the 1000+ scientific tools\" / \"the harvard tools\") working on Codex, says the Codex plugin or its tools/skills won't load, hits a uvx or MCP-server startup error, asks how Codex updates it, wants to pin or remove it, or finds it running an old tool version — even if they never say the word \"plugin\". Not for the Claude Code plugin (use tooluniverse-claude-code-plugin), for running research with the tools, or for authoring new tools or skills."
---

# Install the ToolUniverse Plugin for OpenAI Codex

One-step install on Codex: an MCP server exposing 1000+ scientific tools plus 130+ research skills — all auto-configured. (For the Claude Code version, see `tooluniverse-claude-code-plugin`.)

## Prerequisites (check once)

```bash
uv --version     # provides `uvx`; if missing:  curl -LsSf https://astral.sh/uv/install.sh | sh
codex --version  # OpenAI Codex CLI; if missing: https://developers.openai.com/codex
```

## Install (two commands)

```bash
# 1. Register the ToolUniverse marketplace from GitHub
codex plugin marketplace add mims-harvard/ToolUniverse

# 2. Install the plugin from that marketplace
codex plugin add tooluniverse -m tooluniverse
```

Restart Codex. The MCP server auto-starts via `uvx tooluniverse` on first use (~30 s cold start while the package downloads, instant after).

> `mims-harvard/ToolUniverse` is an owner/repo shorthand, so Codex records it as a **Git** marketplace — which is what enables automatic updates (see "Updates"). Don't point it at the plugin subfolder or a raw URL.

## Verify it worked

```bash
codex plugin list           # expect: tooluniverse (enabled)
codex plugin list --json    # the JSON includes the installed "version"
```

Then just ask naturally inside Codex:

```
What are the top mutated genes in breast cancer?
Research the drug metformin.
```

The research skills auto-activate on matching questions, and the MCP tools are discovered and run via `find_tools` → `execute_tool` — no command prefix needed.

## What you get

| Component | What it does | How it's used |
|---|---|---|
| **MCP server** | 1000+ tools via `find_tools`, `get_tool_info`, `execute_tool` | Auto-loaded; no action needed |
| **130+ skills** | Structured research workflows — drug discovery, variant interpretation, pharmacovigilance, phylogenetics, statistical modeling, and more | Auto-activate on matching questions |

> Unlike the Claude Code plugin, the Codex plugin ships **MCP tools + skills only** — there are no slash commands. You drive everything by asking naturally.

## API keys (optional, but recommended)

Most tools work without keys. For higher rate limits or gated databases, set the keys you care about in the **environment you launch Codex from** — the MCP server (`uvx tooluniverse`) inherits them:

```bash
export NCBI_API_KEY="your_key"
export ONCOKB_API_TOKEN="your_token"
export SEMANTIC_SCHOLAR_API_KEY="your_key"
# ...then start codex from that same shell
```

Exported env vars are the durable choice because they survive plugin upgrades. (You *can* instead edit the `env` block of the installed plugin's `.mcp.json` in the cache — see below — but the cached copy is replaced on every update.)

Full key list: the bundled `setup-tooluniverse` skill → `API_KEYS_REFERENCE.md`.

## Updates

Codex **auto-upgrades Git marketplaces on startup by default**. Because you added `mims-harvard/ToolUniverse` (owner/repo) as a Git marketplace, a newly published version reaches you on your **next Codex launch** with no action needed. (There is no `codex plugin update` command — updating is marketplace-driven.)

Refresh on demand instead of waiting:

```bash
codex plugin marketplace upgrade              # all configured Git marketplaces
codex plugin marketplace upgrade tooluniverse # just this one
```

In the TUI, open `/plugins` and press **Ctrl+U** on the marketplace tab.

The tools themselves come from the `tooluniverse` PyPI package via `uvx`, so if tools feel stale after an upgrade, clear the uvx cache:

```bash
uv cache clean tooluniverse
```

### Pin the tool version (optional, for reproducibility)

To lock tool behavior for a long-running analysis, edit the installed plugin's `.mcp.json` and pin the package version:

```json
"args": ["tooluniverse@1.3.0"]
```

Replace `1.3.0` with any release from https://pypi.org/project/tooluniverse/, then restart Codex. (Find the file under `~/.codex/plugins/cache/`.)

## Uninstall

```bash
codex plugin remove tooluniverse
codex plugin marketplace remove tooluniverse
```

## Alternative install (local checkout / air-gapped)

```bash
git clone https://github.com/mims-harvard/ToolUniverse.git
codex plugin marketplace add ./ToolUniverse
codex plugin add tooluniverse -m tooluniverse
```

A marketplace added by **local path** is NOT auto-upgraded (only owner/repo Git marketplaces are). After pulling new commits, re-run `codex plugin marketplace upgrade` or restart Codex.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `marketplace add` fails | Use `mims-harvard/ToolUniverse` (owner/repo), not a path to the plugin subfolder or a raw URL. |
| `uvx: command not found` | Install `uv` (see Prerequisites), reopen the terminal. |
| Plugin installed but no tools | Restart Codex; the first launch downloads the package (~30 s). Sanity-check the server: run `uvx tooluniverse` in a terminal. |
| MCP server won't start | If `uvx tooluniverse` also fails in a plain terminal, it's a `uv`/Python issue, not Codex. |
| `requires-python >= 3.10` | `uv python install 3.12` |
| Tools feel outdated after update | `uv cache clean tooluniverse`, then restart Codex. |
| Update never arrived | Auto-upgrade only applies to **Git** marketplaces (owner/repo). If you added a local path, run `codex plugin marketplace upgrade`. |
| Tools run an OLD version | `uv tool list \| grep tooluniverse` — a global `uv tool install tooluniverse` *shadows* `uvx`. Fix: `uv tool uninstall tooluniverse`, then restart. |

Still stuck: https://github.com/mims-harvard/ToolUniverse/issues

## Automated diagnosis & repair

Hand this skill to the agent — *"read the tooluniverse-codex-plugin skill and diagnose & fix my Codex plugin"* — or run these in order. Each is safe and idempotent; apply the `FIX` for whatever fails, then restart Codex.

```bash
# 1. Is uv/uvx installed?  (most common cause of "no tools at all")
command -v uvx || echo "FIX: curl -LsSf https://astral.sh/uv/install.sh | sh"

# 2. Can the MCP package resolve + run?  (non-hanging proxy for the server)
uvx --from tooluniverse tu --version || echo "FIX: uv/Python issue — see steps 1 and 6"

# 3. Is the plugin installed + enabled?
codex plugin list | grep -q tooluniverse || echo "FIX: codex plugin add tooluniverse -m tooluniverse"

# 4. Running an OLD version even after updating?  (a global install shadows uvx)
uv tool list | grep -q tooluniverse \
  && echo "FIX: uv tool uninstall tooluniverse" \
  || echo "ok: nothing shadowing uvx"

# 5. Pull the latest plugin version now (don't wait for next startup)
codex plugin marketplace upgrade tooluniverse

# 6. Python too old (requires >= 3.10)?
uv python install 3.12

# 7. Force a fresh tool package
uv cache clean tooluniverse        # or one-shot: uvx --refresh tooluniverse --version
```

## For plugin maintainers

This skill documents the **user-facing** install flow. The Codex plugin source lives at `plugins/tooluniverse/` with its own `.codex-plugin/plugin.json`, `.mcp.json`, and `skills/`. The repo-root `.agents/plugins/marketplace.json` is what makes `codex plugin marketplace add mims-harvard/ToolUniverse` work — it lists the plugin with `"source": {"source": "local", "path": "./plugins/tooluniverse"}` (a path *inside* the cloned marketplace repo, not an external one).

- Skills are generated copies — edit the canonical `skills/` tree, then run `plugin/sync-skills.sh`. It rebuilds both the Claude and Codex skill sets and applies the Codex-specific normalizations (drops the `disable-model-invocation` marker Codex ignores, compacts descriptions over Codex's 1024-char limit).
- The Codex plugin version lives in `plugins/tooluniverse/.codex-plugin/plugin.json`; `scripts/release-plugin.sh` bumps it alongside the Claude manifests so both plugins stay on `<package MAJOR.MINOR>.<plugin revision>`.
- Codex delivers updates via the **git push** (startup auto-upgrade), independent of the version string — but the bump keeps the two plugins coherent and serves Codex's per-version cache.
