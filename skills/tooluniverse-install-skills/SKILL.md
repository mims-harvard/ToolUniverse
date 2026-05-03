---
name: tooluniverse-install-skills
description: Detect and auto-install missing ToolUniverse research skills by checking common client skill directories and cloning from GitHub if absent. Use when ToolUniverse specialized skills are not installed, when setting up a new project, or when the tooluniverse router skill needs to bootstrap its sub-skills before routing.
---

# ToolUniverse Install Skills

Checks whether the ToolUniverse specialized skills are installed and installs them automatically if not.

## Detection

Use the Shell tool to check for the canary file across all common client locations:

```bash
ls .cursor/skills/tooluniverse-drug-research/SKILL.md 2>/dev/null \
  || ls .agents/skills/tooluniverse-drug-research/SKILL.md 2>/dev/null \
  || ls .windsurf/skills/tooluniverse-drug-research/SKILL.md 2>/dev/null \
  || ls .gemini/skills/tooluniverse-drug-research/SKILL.md 2>/dev/null \
  || ls .claude/skills/tooluniverse-drug-research/SKILL.md 2>/dev/null \
  || ls .opencode/skills/tooluniverse-drug-research/SKILL.md 2>/dev/null \
  || ls .trae/skills/tooluniverse-drug-research/SKILL.md 2>/dev/null \
  || ls .skills/tooluniverse-drug-research/SKILL.md 2>/dev/null \
  || echo "NOT_INSTALLED"
```

- **Output is a file path** → skills already installed, stop here.
- **Output is `NOT_INSTALLED`** → proceed to installation.

## Installation

```bash
# 1. Download skills from GitHub (shallow, sparse — only skills/ folder)
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/mims-harvard/ToolUniverse.git /tmp/tu-skills
cd /tmp/tu-skills && git sparse-checkout set skills

# 2. Copy to the correct directory for the detected client:
mkdir -p .cursor/skills  && cp -r /tmp/tu-skills/skills/* .cursor/skills/   # Cursor
# mkdir -p .agents/skills  && cp -r /tmp/tu-skills/skills/* .agents/skills/  # Codex/OpenAI
# mkdir -p .windsurf/skills && cp -r /tmp/tu-skills/skills/* .windsurf/skills/ # Windsurf
# mkdir -p .gemini/skills  && cp -r /tmp/tu-skills/skills/* .gemini/skills/  # Gemini CLI
# mkdir -p .claude/skills  && cp -r /tmp/tu-skills/skills/* .claude/skills/  # Claude Code
# mkdir -p .opencode/skills && cp -r /tmp/tu-skills/skills/* .opencode/skills/ # OpenCode
# mkdir -p .trae/skills    && cp -r /tmp/tu-skills/skills/* .trae/skills/    # Trae
# mkdir -p .skills         && cp -r /tmp/tu-skills/skills/* .skills/         # Cline/VS Code

# 3. Clean up
rm -rf /tmp/tu-skills
```

If the client cannot be detected automatically, ask the user which one they use before running step 2.

## Client Detection

Detect the client from the presence of config files:

| Config file present | Client |
|---|---|
| `.cursor/` | Cursor |
| `.agents/` | Codex / OpenAI |
| `.windsurf/` | Windsurf |
| `.gemini/` | Gemini CLI |
| `.claude/` | Claude Code |
| `.opencode/` | OpenCode |
| `.trae/` | Trae |
| None of the above | Ask the user |

## After Installation

Confirm success:
```bash
ls .cursor/skills/tooluniverse-drug-research/SKILL.md
```

Tell the user: "ToolUniverse skills installed successfully. You now have access to 50+ specialized research workflows."
