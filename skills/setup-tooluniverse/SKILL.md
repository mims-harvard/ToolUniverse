---
name: setup-tooluniverse
description: Install and configure ToolUniverse for any use case — MCP server (chat-based), CLI (command line with 9 subcommands), or Python SDK (Coding API with 3 calling patterns). Covers uv/uvx setup, MCP configuration for 12+ AI clients (Cursor, Claude Desktop, Windsurf, VS Code, Codex, Gemini CLI, Trae, Cline, etc.), full CLI reference (tu list/grep/find/info/run/test/status/build/serve), Coding API quickstart, agentic tools, code executor, API key walkthrough, skill installation, and upgrading. Use when user asks how to set up ToolUniverse, which access mode to use (MCP vs CLI vs SDK), configuring MCP servers, using the CLI, troubleshooting installation, upgrading, or mentions installing ToolUniverse or setting up scientific tools. Also triggers for "how do I use ToolUniverse", "what's the best way to access tools", "command line", "tu command", "coding API", "tu build".
---

# Setup ToolUniverse

Guide the user step-by-step through setting up ToolUniverse.

## Agent Behavior

- **Detect language** from user's first message. Respond in their language; keep commands/URLs in English.
- Go **one step at a time**. Ask before proceeding.
- Use **AskQuestion** for structured choices.
- **Explain briefly** in plain language. Celebrate small wins.
- When something goes wrong, help troubleshoot before moving on.

## Internal Notes (do not show)

ToolUniverse has 1200+ tools. The `tooluniverse` command enables compact mode automatically, exposing only 5 core MCP tools (list_tools, grep_tools, get_tool_info, execute_tool, find_tools) while keeping all tools accessible via execute_tool.

## What is ToolUniverse?

**Always explain first, in plain language:**

ToolUniverse is free, open-source software connecting to 2,000+ scientific databases (PubMed, UniProt, ChEMBL, FAERS, ClinicalTrials.gov, etc.). Instead of visiting each website, you search from one place. Think of it like a universal remote for scientific databases.

**Why AI assistants?** The AI reads your question, figures out which databases to search, runs queries, and summarizes results. You just ask your question.

## Step 1: Choose How to Use It

Present using AskQuestion:

| Mode | What it means | Who it's for |
|------|---------------|-------------|
| **Chat mode** | Ask questions to an AI assistant. No coding. | Most researchers. |
| **Command line** | Type short commands in Terminal. | Quick tests. Terminal-comfortable users. |
| **Python code** | Write scripts for automated pipelines. | Programmers. |

Options: "I want to ask questions" → Chat mode | "Quick try" → CLI | "I write Python" → SDK | "I don't know" → Recommend Chat mode

**If Chat mode**, ask which app (AskQuestion): Cursor, Claude Desktop, VS Code/Copilot, Windsurf, Claude Code, Gemini CLI, Codex, Cline/Trae/Antigravity/OpenCode. "I don't have any" → Recommend [Claude Desktop](https://claude.ai/download).

## Step 2: Install uv

Only prerequisite: `uv` (manages everything else automatically).

**Terminal help** (if needed): Mac: Cmd+Space → "Terminal" → Enter. Windows: Win key → "PowerShell" → Enter.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
(This is a safe, standard command that downloads and installs `uv`, a small package manager. It's widely used by Python developers. Close and reopen your terminal after it finishes.)

Verify: `uv --version`

## CLI Setup

Make sure Step 2 is done, then try:

```bash
uvx --from tooluniverse tu status              # How many tools?
uvx --from tooluniverse tu find 'drug safety'  # Search by topic
uvx --from tooluniverse tu info FAERS_count_death_related_by_drug  # See params
uvx --from tooluniverse tu run FAERS_count_death_related_by_drug '{"drug_name": "metformin"}'
```

First run takes ~30s (downloads package), then instant. **Shortcut**: `uv tool install tooluniverse` → then just use `tu` directly.

### All CLI subcommands

| Command | What it does | Example |
|---------|-------------|---------|
| `tu status` | Show tool count and top categories | `tu status` |
| `tu list` | List tools (modes: names, categories, basic, by_category, summary, custom) | `tu list --mode basic --limit 20` |
| `tu find` | Search by natural language (keyword scoring, no API key needed) | `tu find 'protein structure analysis'` |
| `tu grep` | Text/regex pattern search | `tu grep '^UniProt' --mode regex` |
| `tu info` | Show tool parameters and schema | `tu info PubMed_search_articles` |
| `tu run` | Execute a tool | `tu run PubMed_search_articles '{"query": "CRISPR"}'` |
| `tu test` | Test a tool with its example inputs | `tu test UniProt_get_entry_by_accession` |
| `tu build` | Generate typed Python wrappers for Coding API | `tu build --output ./my_tools` |
| `tu serve` | Start MCP stdio server (same as `uvx tooluniverse`) | `tu serve` |

**Output flags** (most commands except `build`/`serve`): `--json` (pretty) or `--raw` (compact, pipe-friendly).

Continue to **Step 3** (API Keys).

## SDK Setup

Make sure Step 2 is done. For detailed patterns, invoke the `tooluniverse-sdk` skill.

```bash
uv pip install tooluniverse
```

### Coding API — 3 calling patterns

**Pattern 1: Direct import** (typed, with autocomplete):
```python
from tooluniverse.tools import UniProt_get_entry_by_accession
result = UniProt_get_entry_by_accession(accession="P12345")
```

**Pattern 2: Attribute access** (no import needed per tool):
```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()
result = tu.tools.UniProt_get_entry_by_accession(accession="P12345")
```

**Pattern 3: JSON-based** (dynamic, for pipelines):
```python
result = tu.run({"name": "UniProt_get_entry_by_accession", "arguments": {"accession": "P12345"}})
```

Generate typed wrappers: `tu build` (creates importable Python modules with autocomplete).

### Agentic Tools & Code Executor

ToolUniverse also includes **23 AI-powered agentic tools** (ScientificTextSummarizer, HypothesisGenerator, ExperimentalDesignScorer, peer-review tools, etc.) and **2 code executor tools** (python_code_executor, python_script_runner). These are called like any other tool — via `tu.run()` or `execute_tool()`. Agentic tools require an LLM API key (e.g., `OPENAI_API_KEY`).

Continue to **Step 3** (API Keys).

## MCP Setup (Chat Mode)

Make sure Step 2 is done (`uv --version` works).

### Add ToolUniverse to your app's config

**Config file help** (if user seems unfamiliar): Config files are plain text that store settings — like a preference list for the app. You don't need to understand the format; just paste exactly what's shown below. Most apps have a Settings button that opens the file for you (see table). If the file is empty, paste the entire block. If it already has content, the agent should help merge it.

**Default config** (same for most clients):
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

**Config file locations:**

| Client | File | How to Access |
|--------|------|---------------|
| Cursor | `~/.cursor/mcp.json` | Settings → MCP → Add new global MCP server |
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` | Settings → Developer → Edit Config |
| Claude Code | `~/.claude.json` or `.mcp.json` | `claude mcp add` or edit directly |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | MCP hammer icon → Configure |
| Cline | `cline_mcp_settings.json` | Cline panel → MCP Servers → Configure |
| Gemini CLI | `~/.gemini/settings.json` | `gemini mcp add` or edit directly |
| Trae | `.trae/mcp.json` | Ctrl+U → AI Management → MCP → Configure |

**Different formats**: VS Code uses `"servers"` key with `"type": "stdio"`. Codex uses TOML. OpenCode uses `"mcp"` key. See [references/mcp-configs.md](references/mcp-configs.md) for these.

Continue to **Step 3** (API Keys).

## Step 3: API Keys

Many tools work without keys, but some unlock powerful features. **Ask research interests first** (AskQuestion):
- Literature / Drug discovery / Protein structure / Genomics / Rare diseases / Enzymology / Patent search / AI analysis / All / Skip

Map to recommended keys (2-4 to start). Walk through **one at a time**: explain what it unlocks, give registration link, wait for key, add to config.

**Tier 1 (Core — recommend for most users):**

| Key | Unlocks | Free? | Registration |
|-----|---------|-------|-------------|
| `NCBI_API_KEY` | PubMed (rate limit 3→10/s) | Yes | https://account.ncbi.nlm.nih.gov/settings/ |
| `NVIDIA_API_KEY` | 16 tools: AlphaFold2, docking, genomics | Yes | https://build.nvidia.com |
| `BIOGRID_API_KEY` | Protein interaction queries | Yes | https://webservice.thebiogrid.org/ |
| `FDA_API_KEY` | FDA adverse events, drug labels (rate 240→1000/min) | Yes | https://open.fda.gov/apis/authentication/ |

**Tier 2 (Specialized — based on interests):**

| Key | Unlocks | Registration |
|-----|---------|-------------|
| `DISGENET_API_KEY` | Gene-disease associations | https://disgenet.com/academic-apply |
| `OMIM_API_KEY` | Mendelian/rare disease | https://omim.org/api |
| `ONCOKB_API_TOKEN` | Precision oncology | https://www.oncokb.org/apiAccess |
| `UMLS_API_KEY` | Medical terminology | https://uts.nlm.nih.gov/uts/ |

See [API_KEYS_REFERENCE.md](API_KEYS_REFERENCE.md) for the complete list with all tiers.

**Adding keys:**

Chat mode — add to `env` block in MCP config:
```json
"env": {
  "PYTHONIOENCODING": "utf-8",
  "NCBI_API_KEY": "your_key_here"
}
```

CLI — set environment variables:
```bash
export NCBI_API_KEY="your_key_here"       # Current session
echo 'export NCBI_API_KEY="key"' >> ~/.zshrc  # Persist across sessions
```

SDK — same as CLI (export or `.env` file).

## Step 4: Test Together

**Don't just tell — do it WITH the user.**

**Chat mode**: Ask user to restart app. Then run a test call yourself:
1. `list_tools` or `grep_tools` with "PubMed" — confirm tools visible
2. `execute_tool("PubMed_search_articles", {"query": "CRISPR", "max_results": 1})` — confirm it works
3. Celebrate: "It works! You have access to 1200+ scientific tools."

**CLI**: Run together:
```bash
tu status && tu find 'protein' && tu run PubMed_search_articles '{"query": "CRISPR", "max_results": 1}'
```

**SDK**: Run the Python snippet from SDK Setup together.

**If issues**: Most common: app not restarted, `uv` not in PATH (reopen terminal), JSON syntax error in config.

## Step 5: Install Skills (Recommended for Chat Mode)

Skills are pre-built research workflows that turn basic tool calls into expert investigations.

**Chat mode users**: The agent should run this for the user:
```bash
git clone --depth 1 https://github.com/mims-harvard/ToolUniverse.git /tmp/tu-skills
```

Then copy to client's skill directory:

| Client | Command |
|--------|---------|
| Cursor | `mkdir -p .cursor/skills && cp -r /tmp/tu-skills/skills/* .cursor/skills/` |
| Claude Code | `mkdir -p .claude/skills && cp -r /tmp/tu-skills/skills/* .claude/skills/` |
| Windsurf | `mkdir -p .windsurf/skills && cp -r /tmp/tu-skills/skills/* .windsurf/skills/` |
| Codex | `mkdir -p .agents/skills && cp -r /tmp/tu-skills/skills/* .agents/skills/` |
| Gemini CLI | `mkdir -p .gemini/skills && cp -r /tmp/tu-skills/skills/* .gemini/skills/` |

Clean up: `rm -rf /tmp/tu-skills`

Skills activate automatically based on user's question. Try: "Research the drug metformin" or "What does the literature say about CRISPR in cancer?"

**CLI users**: Skills are designed for AI chat agents. Use `tu find`, `tu info`, `tu run` instead. For full multi-step workflows, use Chat mode or build SDK pipelines.

## What's Next? (Guided First Use)

**Don't list suggestions — run a live demo WITH the user.**

### Pick a demo query based on research interests (from Step 3):

| Interest | First query | Skill |
|----------|------------|-------|
| Literature | "What does the literature say about CRISPR in cancer?" | literature-deep-research |
| Drug discovery | "Research the drug metformin" | drug-research |
| Protein structure | "Find protein structures for human EGFR" | protein-structure-retrieval |
| Genomics | "What genes are associated with type 2 diabetes?" | disease-research |
| Rare diseases | "Patient with progressive ataxia and oculomotor apraxia — differential diagnosis?" | rare-disease-diagnosis |
| Drug safety | "What are the adverse events for pembrolizumab?" | pharmacovigilance |
| General | "Research the drug aspirin" | drug-research |

**Run the demo** — invoke the skill and show real results.

### Prompt cheat sheet (share after demo)

**Chat mode users:**
> 1. "Research the drug [name]" — full drug profile
> 2. "Research [disease]" — comprehensive disease analysis
> 3. "What are the known targets of [drug]?" — target intelligence
> 4. "What does the literature say about [topic]?" — deep literature review
> 5. "Find protein structures for [protein]" — 3D structures
> 6. "Is [variant] pathogenic?" — variant interpretation
> 7. "What drugs could be repurposed for [disease]?" — repurposing
> 8. "What are the adverse events for [drug]?" — safety analysis
> 9. "Find clinical trials for [disease/drug]" — trial matching
> 10. "What are the protein interactions for [gene]?" — interaction network
> 11. "What are the clinical guidelines for [condition]?" — practice guidelines
> 12. "Check drug interactions between [drug1] and [drug2]" — DDI analysis
>
> Just ask naturally — I'll figure out which databases to search.

**CLI users:**
> ```bash
> tu find 'drug safety'           # Discover tools
> tu info PubMed_search_articles  # Check parameters
> tu run PubMed_search_articles '{"query": "CRISPR cancer", "max_results": 3}'
> tu run UniProt_get_entry_by_accession '{"accession": "P12345"}'
> tu run FAERS_count_death_related_by_drug '{"drug_name": "metformin"}'
> ```

## Write Agent Memory

After setup, write a reminder to the agent's memory file so future sessions know ToolUniverse is available.

| Client | File |
|--------|------|
| Cursor | `.cursor/rules/tooluniverse.md` |
| Claude Code | `CLAUDE.md` or `.claude/CLAUDE.md` (append) |
| Windsurf | `.windsurf/rules/tooluniverse.md` |
| VS Code/Copilot | `.github/copilot-instructions.md` (append) |
| Codex / OpenCode | `AGENTS.md` (append) |
| Gemini CLI | `GEMINI.md` (append) |
| Cline | `.clinerules/tooluniverse.md` |
| Trae | `.trae/rules/tooluniverse.md` |

**Content:**
```markdown
# ToolUniverse
For any scientific research question (drugs, genes, proteins, diseases, literature, clinical trials, etc.), invoke the `tooluniverse` skill — it routes to specialized research skills and 1,200+ database tools.
```

Append (don't overwrite). Check for existing section first. Ask user permission.

## Team / Project-Level Setup

If setting up ToolUniverse for a team or shared project:

**Shared API keys**: Create a `.env` file at the project root with all keys. Most clients and the CLI/SDK will pick up keys from `.env` automatically:
```
NCBI_API_KEY=your_shared_key
NVIDIA_API_KEY=your_shared_key
```

**Project-level MCP config** (so all team members get ToolUniverse automatically):
- Cursor: `.cursor/mcp.json` in project root
- Claude Code: `.mcp.json` in project root
- VS Code: `.vscode/mcp.json` in project root
- Windsurf: project-level via Windsurf UI

**Project-level skills**: Install skills into the project (e.g., `.cursor/skills/`) so all team members share them.

**Team-wide upgrade**: Each team member runs `uv cache clean tooluniverse` and restarts their app. To pin a specific version, use `"args": ["tooluniverse==X.Y.Z"]` in the MCP config.

## Common Issues

| Issue | Fix |
|-------|-----|
| `requires-python >= 3.10` | `uv python install 3.12` |
| `uvx: command not found` | Run install script from Step 2, restart terminal |
| Context window overflow | Verify using `uvx tooluniverse` (compact mode is default) |
| `ModuleNotFoundError` | `uv pip install tooluniverse[all]` |
| MCP server won't start | Test: `uvx tooluniverse` in terminal. Check JSON syntax. |
| API key 401/403 | Check key in `env` block, restart app, verify key name |
| Upgrade needed | `uv cache clean tooluniverse` then restart app |

Still stuck? [GitHub issues](https://github.com/mims-harvard/ToolUniverse/issues) or email [Shanghua Gao](mailto:shanghuagao@gmail.com).

## Quick Reference

- **Default**: `uvx tooluniverse` — auto-installs, compact mode
- **Upgrade**: `uv cache clean tooluniverse` + restart
- **All scientific API keys are free**
- **Skills**: https://github.com/mims-harvard/ToolUniverse/tree/main/skills
