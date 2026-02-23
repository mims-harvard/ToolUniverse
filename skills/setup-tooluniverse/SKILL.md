---
name: setup-tooluniverse
description: Install and configure ToolUniverse with MCP integration for any AI coding client (Cursor, Claude Desktop, Windsurf, VS Code, Codex, Gemini CLI, Trae, Cline, Antigravity, OpenCode, etc.). Covers uv/uvx setup, MCP configuration, API key walkthrough, skill installation, and upgrading. Use when setting up ToolUniverse, configuring MCP servers, troubleshooting installation issues, upgrading versions, or when user mentions installing ToolUniverse or setting up scientific tools.
---

# Setup ToolUniverse

Guide the user step-by-step through setting up ToolUniverse with MCP (Model Context Protocol) integration.

## Agent Behavior — READ THIS FIRST AND ENFORCE IT THROUGHOUT

**This is a setup wizard, not a reference manual. You must stay interactive at every step.**

### The one rule that overrides everything else
**After every single step: STOP. Ask if it worked. Wait for the user's reply before continuing.**
Never run ahead. Never explain Step 3 while the user is still on Step 1. Never output a wall of instructions. One step, then pause.

### How to behave at each step
- **Show one thing at a time.** Give one command or one question. Wait for the result.
- **Confirm before moving on.** "Did that work? What did you see?" — then react to the answer.
- **Explain briefly** what each step does and why, in plain language. One sentence is enough.
- **Use the AskQuestion tool** for structured choices when available (client selection, research areas, etc.).
- **Detect the user's language** from their first message. If they write in Chinese, Japanese, Spanish, etc., respond in that language throughout the entire setup. All explanations, questions, and celebrations should be in their language. Only keep commands, code blocks, URLs, and env variable names in English (those are technical and must stay as-is).
- **Celebrate small wins** — when uv installs successfully, when the MCP server appears, when the first tool call works.
- **When something goes wrong**, be reassuring and help troubleshoot before moving on.

### What NOT to do
- ❌ Do not paste multiple steps at once
- ❌ Do not pre-explain upcoming steps "just in case"
- ❌ Do not move to the next step without hearing that the current one succeeded
- ❌ Do not reproduce large blocks from the reference files — summarize and act

## Internal Notes (do not show to user)

⚠️ **ToolUniverse has 1200+ tools** which will cause context window overflow if all exposed directly. The default `tooluniverse` command enables compact mode automatically, exposing only 5 core tools (list_tools, grep_tools, get_tool_info, execute_tool, find_tools) while keeping all 1200+ accessible via execute_tool.

**This skill's own URL** (for bootstrapping):
`https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/SKILL.md`

**Reference files** — fetch by GitHub raw URL (works whether this skill was loaded locally or from GitHub):

| File | GitHub URL |
|------|------------|
| `CLAUDE_DESKTOP.md` | https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/CLAUDE_DESKTOP.md |
| `API_KEYS_REFERENCE.md` | https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/API_KEYS_REFERENCE.md |
| `MCP_CONFIG.md` | https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/MCP_CONFIG.md |
| `SKILLS_CATALOG.md` | https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/SKILLS_CATALOG.md |
| `TROUBLESHOOTING.md` | https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/TROUBLESHOOTING.md |

## Step 0: Auto-Detect & Quick Start

Welcome the user, then immediately run these detection commands **before asking any questions**:

```bash
echo "=== Detecting OS ===" && \
  ([ "$(uname)" = "Darwin" ] && echo "OS: macOS") || \
  ([ "$(uname)" = "Linux" ] && echo "OS: Linux") || \
  echo "OS: Unknown"

echo "=== Detecting your AI client ===" && \
  ([ -f ~/.cursor/mcp.json ] && echo "✅ Cursor detected") || true && \
  ([ -f ~/Library/Application\ Support/Claude/claude_desktop_config.json ] && echo "✅ Claude Desktop detected (macOS)") || true && \
  ([ -f ~/.config/Claude/claude_desktop_config.json ] && echo "✅ Claude Desktop detected (Linux)") || true && \
  ([ -f ~/.claude.json ] && echo "✅ Claude Code detected") || true && \
  ([ -f ~/.codeium/windsurf/mcp_config.json ] && echo "✅ Windsurf detected") || true && \
  ([ -f ~/.gemini/settings.json ] && echo "✅ Gemini CLI detected") || true && \
  ([ -f ~/.codex/config.toml ] && echo "✅ Codex CLI detected") || true && \
  ([ -f ~/.qwen/settings.json ] && echo "✅ Qwen Code detected") || true && \
  ([ -f opencode.json ] && echo "✅ OpenCode detected") || true && \
  echo "=== Detection complete ==="
```

**On Windows**, detection won't run in bash — ask the user to check manually: Claude Desktop `%APPDATA%\Claude\claude_desktop_config.json`, Cursor `%USERPROFILE%\.cursor\mcp.json`.

**Remember the detected OS** — it changes config paths, uv install commands, and log locations in later steps.

Based on results:
- **One client detected**: "I can see you're using [Client]. I'll set up ToolUniverse for that." Skip Question 1.
- **Multiple detected**: Ask which one to configure.
- **None detected**: Ask Question 1 below.

> ⏸️ **Now**: Report what was detected, then ask Question 1 if needed. Wait for the client answer before continuing.

**Question 1 (only if not auto-detected):** Which app are you using?
Cursor · Claude Desktop · VS Code / Copilot · Windsurf · Claude Code · Gemini CLI · Qwen Code · Codex (OpenAI) · Cline · Trae · Antigravity · OpenCode · Other

⚠️ **If Claude Desktop is detected or selected**: Step 2 is completely different — you must fetch and follow CLAUDE_DESKTOP.md instead of the standard config. Hold this in mind.

**Bootstrap check (terminal-based clients only — OpenCode, Gemini CLI, Codex CLI, Claude Code):**
If the user arrived here from README/docs (not from inside their client), give them this one-liner to paste into their client instead and stop:
```
Please read https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/SKILL.md and follow it to help me set up ToolUniverse.
```

> ⏸️ **Now**: Ask "Would you like a **quick start** (~3 min, no questions) or a **full setup** (API keys + options)?" — then wait for the answer.

- **Quick start**: `brew install uv` (or curl), write config with python3 one-liner, restart app, confirm tools appear, install skills with `npx skills add mims-harvard/ToolUniverse`. Skip API keys (add later). Skills are included — they're what make ToolUniverse genuinely useful.
- **Full setup**: Continue with all steps including API keys.

**Question 2 (full setup only):** How will you use ToolUniverse?
- **MCP server** (use scientific tools through chat) — default for most users
- **Python coding** (write scripts that `import tooluniverse`) — also needs pip install

> ⏸️ **Wait for Question 2 answer** before proceeding to Step 1.

## Step 1: Make sure uv is installed

Check first — **skip install entirely if uv is already present**:

```bash
which uv && uv --version || echo "NOT_INSTALLED"
```

- **Found**: "✅ uv is already installed — skipping." Go to Step 2.
- **NOT_INSTALLED**: Explain uv is a fast package manager that makes MCP setup simple, then install.

**macOS — check for Homebrew first (preferred for Claude Desktop):**
```bash
which brew && echo "Homebrew found" || echo "No Homebrew"
```

- **Homebrew found:**
  ```bash
  brew install uv
  ```
  Verify with Homebrew path directly (GUI apps use this, not the shell's `which uvx`):
  ```bash
  /opt/homebrew/bin/uvx --version   # Apple Silicon
  /usr/local/bin/uvx --version      # Intel Mac
  ```

- **No Homebrew:**
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  source "$HOME/.local/bin/env" 2>/dev/null || source ~/.zshrc 2>/dev/null || source ~/.bashrc 2>/dev/null
  ```

**Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh && source "$HOME/.local/bin/env" 2>/dev/null || source ~/.bashrc`

**Windows (PowerShell):** `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` then reopen PowerShell.

Verify: `uvx --version`

> ⏸️ **After Step 1**: Ask "Did `uvx --version` print a version number?" Wait for confirmation before continuing.

## Step 2: Add ToolUniverse to your MCP config

### 🖥️ Claude Desktop users — your path diverges here

**Fetch and read this file now, then follow it entirely for Step 2:**
https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/CLAUDE_DESKTOP.md

CLAUDE_DESKTOP.md contains all Claude Desktop-specific instructions: the PATH fix (Claude Desktop is a GUI app that cannot see `uvx` in your shell PATH), the correct config to write, the one-liner to safely create or merge it, how to restart, and how to verify. **Do not use the standard config below for Claude Desktop — it will silently fail.** After completing CLAUDE_DESKTOP.md, skip to Step 3.

---

### All other clients — standard config

**First, validate uvx tooluniverse works before touching any config:**

```bash
uvx tooluniverse --help
```

- **Prints usage text** → proceed.
- **Error** → fix the uv install (see [TROUBLESHOOTING.md](https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/TROUBLESHOOTING.md) Issue 2) before writing the config.

**Check if config file already exists:**
```bash
cat <CONFIG_PATH> 2>/dev/null || echo "CONFIG_NOT_FOUND"
```

- **CONFIG_NOT_FOUND**: Create with config below.
- **Exists, no `tooluniverse` entry**: Merge the `tooluniverse` block into the existing `mcpServers`.
- **Already has `tooluniverse`**: "ToolUniverse is already configured — I'll skip rewriting to avoid overwriting any API keys." Only overwrite if user asks.

**Ask:** "Would you like ToolUniverse to auto-update whenever your app starts? (~1–2s startup overhead, recommended: yes)"

- **Yes** → use `["--refresh", "tooluniverse"]` in args
- **No** → use `["tooluniverse"]`; upgrade manually with `uv cache clean tooluniverse`

**Standard config (Cursor, Windsurf, Claude Code, Gemini CLI, Qwen Code, Trae, Cline):**
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

**One-liner to write or merge the config safely:**
```bash
python3 -c "
import json, os
p = os.path.expanduser('CONFIG_PATH')
os.makedirs(os.path.dirname(p), exist_ok=True)
cfg = json.load(open(p)) if os.path.exists(p) else {}
cfg.setdefault('mcpServers', {})['tooluniverse'] = {
    'command': 'uvx', 'args': ['--refresh', 'tooluniverse'],
    'env': {'PYTHONIOENCODING': 'utf-8'}
}
json.dump(cfg, open(p, 'w'), indent=2)
print('Done — tooluniverse added to', p)
"
```

Replace `CONFIG_PATH` with the path for the user's client:

| Client | Config File |
|--------|-------------|
| **Cursor** | `~/.cursor/mcp.json` |
| **Claude Desktop** | ← See CLAUDE_DESKTOP.md above |
| **Claude Code** | `~/.claude.json` or `.mcp.json` |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` |
| **VS Code (Copilot)** | `.vscode/mcp.json` — uses `"servers"` key, needs `"type": "stdio"` — see [MCP_CONFIG.md](https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/MCP_CONFIG.md) |
| **Codex (OpenAI)** | TOML format: `codex mcp add tooluniverse -- uvx tooluniverse` — see [MCP_CONFIG.md](https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/MCP_CONFIG.md) |
| **OpenCode** | `opencode.json` — uses `"mcp"` key — see [MCP_CONFIG.md](https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/MCP_CONFIG.md) |
| **Gemini CLI** | `~/.gemini/settings.json` |
| **Qwen Code** | `~/.qwen/settings.json` |
| **Trae** | `.trae/mcp.json` |
| **Cline** | `cline_mcp_settings.json` (in VS Code extension globalStorage) |
| **Antigravity** | `mcp_config.json` |

For VS Code, Codex, and OpenCode special formats, read [MCP_CONFIG.md](https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/MCP_CONFIG.md).

> ⏸️ **After Step 2**: Ask "Did the config file get written? Anything look wrong?" Wait before continuing.

## Step 3 (coding use only): Install Python package

Skip if user only needs MCP. For scripting use:
```bash
pip install tooluniverse
```
Verify:
```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
print(f"ToolUniverse version: {tu.__version__}")
```

> ⏸️ **After Step 3 (if applicable)**: Ask "Did the import work?" Wait for the answer.

## Step 4: Set up API Keys

Many tools work without keys, but some unlock powerful features. First, **ask the user about their research interests** to recommend only what's relevant. Use AskQuestion if available:
- Literature search & publications
- Drug discovery & pharmacology
- Protein structure & interactions
- Genomics & disease associations
- Rare diseases & clinical
- AI-powered analysis (needs LLM key)
- Not sure yet / skip for now

Fetch [API_KEYS_REFERENCE.md](https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/API_KEYS_REFERENCE.md) to see the full list with registration steps. Map the user's research interest to 2–4 recommended keys from that file, then walk through them **one at a time**: explain what each unlocks → give the registration link → wait for them to get the key → help add it to the `env` block in their MCP config:

```json
"env": {
  "PYTHONIOENCODING": "utf-8",
  "NCBI_API_KEY": "your_key_here"
}
```

> ⏸️ **After Step 4**: Walk through **one key at a time**. After each key: "Got it? Want to add another, or skip for now?" Don't list all keys at once.

## Step 5: Test & Status Check

**Pre-flight check before restarting:**
```bash
timeout 10 uvx tooluniverse --help
```
- Prints usage → proceed to restart.
- Fails → fix first (see [TROUBLESHOOTING.md](https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/TROUBLESHOOTING.md) Issue 5). Don't restart yet.

Ask user to **fully quit and reopen their app** (⌘Q on Mac — closing the window is not enough).

⏱️ **First launch takes 60–90 seconds** while the app downloads and installs ToolUniverse. **Claude Desktop only** — watch logs while it loads:
```bash
tail -f ~/Library/Logs/Claude/mcp*.log          # macOS
tail -f ~/.config/Claude/logs/mcp*.log          # Linux
```
Look for `"tooluniverse" connected` or tool schema output.

**What to look for in the app UI:**
- **Claude Desktop (newer)**: A **"Search and tools"** button or **+** icon in the chat input → click it → `tooluniverse` should appear in the connected tools list.
- **Claude Desktop (older) / Cursor / Windsurf**: 🔨 hammer icon at the bottom of the chat input → click to see available tools.
- **Claude Code / Gemini CLI / Codex CLI**: Run `/mcp` or `mcp list`.

**Show this status summary** and fill in each line:
```
Setup Status
─────────────────────────────────────
✅/❌  uv installed         (uvx --version)
✅/❌  ToolUniverse starts  (uvx tooluniverse --help)
✅/❌  MCP config created   (config file found)
✅/❌  Server visible       ("Search and tools" / 🔨 hammer / Settings → Developer → MCP Servers)
✅/❌  Test tool call works
⬜     Skills installed     (do Step 6 next — required)
⬜     API keys (optional — add anytime)
─────────────────────────────────────
```

**Live test call:**
```
list_tools
```
or
```
execute_tool("PubMed_search_articles", {"query": "CRISPR", "max_results": 1})
```

If all ✅, celebrate! 🎉 If any ❌, jump to the matching issue in [TROUBLESHOOTING.md](https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/TROUBLESHOOTING.md).

> ⏸️ **After Step 5**: Ask "Do you see ToolUniverse in the tools list? Did the test call return anything?" Wait for confirmation — then **immediately proceed to Step 6**. Do not skip it. Skills are what transform ToolUniverse from a raw API layer into an intelligent research assistant.

## Step 6: Install ToolUniverse Skills ⭐ highly recommended

**This is the most impactful step of the whole setup.** Without skills, the user has access to 1200+ tools but no guidance on how to use them together. With skills, they get 65+ expert research workflows — each one knows exactly which tools to call, in what order, to produce a complete research report on drugs, targets, diseases, cancer variants, genomics, and more.

**Say this to the user** (adapt to their language and research interest from Step 4):

> "Now for the best part — ToolUniverse comes with 65+ research skills that work like expert guides. Instead of calling tools manually, you just say 'Research the drug metformin' or 'What genes are associated with type 2 diabetes?' and the right skill takes over, calls the right tools in the right order, and gives you a full evidence-graded report. This takes about a minute to install."

**Strongly encourage installation.** If the user hesitates or says "maybe later", remind them:
- Skills work immediately — no extra configuration needed after install
- They can always add more skills later, but having them from the start makes ToolUniverse far more accessible
- The install is one command and takes under a minute

**Option A — User runs in terminal (quickest):**
```bash
npx skills add mims-harvard/ToolUniverse
```
This auto-detects the client and installs into the correct directory. Ask the user to confirm it completed successfully.

**Option B — Agent installs directly** (use this if you have shell/terminal access, or if npx fails):
```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/mims-harvard/ToolUniverse.git /tmp/tu-skills
cd /tmp/tu-skills && git sparse-checkout set skills
```
Find the right skills directory for the user's client in [SKILLS_CATALOG.md](https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/SKILLS_CATALOG.md), then copy:
```bash
# Example for Cursor:
mkdir -p .cursor/skills && cp -r /tmp/tu-skills/skills/* .cursor/skills/
rm -rf /tmp/tu-skills
```

**Suggest a skill to try** based on their research interests from Step 4:
- "Try: **'Research the drug metformin'**" — triggers the drug-research skill
- "Try: **'What does the literature say about CRISPR in cancer?'**" — triggers literature-deep-research

> ⏸️ **After Step 6**: Don't just confirm installation — **immediately ask the user what problem they want to solve**. Say something like: "Skills are ready! What would you like to research? Tell me your topic — a drug, disease, gene, or research question — and I'll use the right skill to give you a full report." Then activate the matching skill based on their answer. This is the whole point of the setup.

## Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| uv not found | `uvx: command not found` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` then re-source shell |
| GUI app can't find uvx | "Failed to spawn process" / "ENOENT" | `brew install uv` on macOS, or use absolute path in config |
| Server won't appear | No "Search and tools" entry / no hammer after restart | Diagnostic chain → [TROUBLESHOOTING.md](https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/TROUBLESHOOTING.md) Issue 5 |
| API key rejected | 401/403 errors | Move key to `env` block in MCP config; restart app |
| Context overflow | Client very slow | Already in compact mode; narrow categories if needed |
| Python too new (3.14+) | `SyntaxError` / `requires-python` errors | `uvx --python 3.12 tooluniverse --help` → [TROUBLESHOOTING.md](https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/TROUBLESHOOTING.md) Issue 8 |
| Stale/broken package | Tool errors or missing tools | `uv cache clean tooluniverse` → [TROUBLESHOOTING.md](https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/TROUBLESHOOTING.md) Issue 9 |
| Still broken after all above | Persistent unexplained error | Run the issue-filing script in [TROUBLESHOOTING.md](https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/TROUBLESHOOTING.md) "Still Stuck?" — it collects system info and generates a pre-filled GitHub issue URL |

Full diagnostics and GitHub issue helper in [TROUBLESHOOTING.md](https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/TROUBLESHOOTING.md).

## What's Next?

Setup is complete. **Explain to the user how to use ToolUniverse skills**, then immediately ask what they want to research.

### How skills work (tell the user this)

Skills activate automatically — the user just writes a natural language request. No special commands, no prefixes. Examples:

| Say this… | What happens |
|-----------|-------------|
| `"Research the drug metformin"` | drug-research skill runs: identity, pharmacology, targets, safety, ADMET |
| `"What is known about Alzheimer's disease?"` | disease-research skill runs: genetics, mechanisms, treatments, trials |
| `"What are the known targets of imatinib?"` | target-research skill runs: structure, interactions, druggability |
| `"What does the literature say about CRISPR in sickle cell?"` | literature-deep-research skill runs: PubMed search, evidence grading, synthesis |
| `"Interpret the EGFR L858R mutation in lung cancer"` | cancer-variant-interpretation skill runs: clinical evidence, therapies, trials |

The skill reads the question, calls the right tools in the right order, and produces a full evidence-graded report. The user doesn't need to know which skill to pick — just ask the question.

### Now ask the user

> "What would you like to research first? Tell me a drug, disease, gene, or question and I'll generate a full report."

Take their answer and activate the `tooluniverse` skill — it is a router that automatically picks the right sub-skill and runs it. Don't end the conversation here — end it with the user getting real value.

The user can add more API keys or skills anytime. Issues → https://github.com/mims-harvard/ToolUniverse/issues.
