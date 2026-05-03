# Trae IDE Setup

> **Use your system terminal — not Trae's built-in terminal.**
> Trae may run in a sandboxed environment. All installation commands (`uv`, `npx`, `git`) must be run in your **OS terminal** (Windows: PowerShell or Command Prompt; macOS/Linux: Terminal app). Commands run inside Trae's terminal panel may appear to succeed but Trae won't find the tools after restart.

---

## Step 1: Install uvx

Open your **system terminal** (not Trae's terminal) and check if uv is already installed:

```bash
uvx --version
```

If the command is not found, install uv:

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zshrc 2>/dev/null || source ~/.bashrc 2>/dev/null
```

**Windows (PowerShell):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```
Then close and reopen PowerShell so the new `uvx` command is available.

**Verify ToolUniverse loads:**
```bash
uvx tooluniverse --help
```

This should print help text. If it fails, see [TROUBLESHOOTING.md](https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/TROUBLESHOOTING.md).

> ⏸️ Ask: "Does `uvx tooluniverse --help` print help text in your system terminal?" Wait before continuing.

---

## Step 2: Set Up Global Config

Trae's **global** MCP config is the only config the AI agent can access.

**Find the config path:** Open Trae → Settings → MCP (or "..." menu → Open MCP config).

Expected locations by OS:
- **Windows**: `%APPDATA%\Trae\User\mcp.json` (e.g. `C:\Users\yourname\AppData\Roaming\Trae\User\mcp.json`)
- **macOS**: `~/Library/Application Support/Trae/User/mcp.json`
- **Linux**: `~/.config/Trae/User/mcp.json`

> ⏸️ Ask: "Can you open Trae Settings → MCP and confirm the config file path it shows?" Confirm before continuing.

### Config JSON

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

### Option A — Python one-liner (try first, run in system terminal)

Replace `CONFIG_PATH` with the confirmed path:

```bash
python3 -c "
import json, os
p = r'CONFIG_PATH'
os.makedirs(os.path.dirname(p), exist_ok=True)
cfg = json.load(open(p)) if os.path.exists(p) else {}
cfg.setdefault('mcpServers', {})['tooluniverse'] = {
    'command': 'uvx', 'args': ['--refresh', 'tooluniverse'],
    'env': {'PYTHONIOENCODING': 'utf-8'}
}
json.dump(cfg, open(p, 'w'), indent=2)
print('Done:', p)
"
```

### Option B — Trae Settings UI (recommended if Option A fails)

Trae has a built-in MCP configuration panel that bypasses file permission issues:

1. Press **Ctrl U** (or click the Agents icon) to open the Agents panel
2. Click the **AI Management gear icon** → **MCP** → **Configure Manually**
3. Paste the full JSON block above into the text field
4. Click **Confirm**
5. Restart Trae fully

> ⏸️ Ask: "Did tooluniverse appear in the MCP panel after restarting?" Wait before continuing.

### Option C — Direct file paste (last resort)

If both Options A and B fail:

1. Open the global config file in a text editor (Notepad, VS Code, etc.) at the path confirmed above
2. If the file is empty or missing, paste the full JSON block above
3. If the file already has content, add the `"tooluniverse"` block inside the existing `"mcpServers"` object
4. Save the file
5. Restart Trae fully

> ⏸️ Ask: "Did the config get written? Do you see tooluniverse in Settings → MCP?" Wait before continuing.

### ⚠️ Do Not Use Project-Level Config

`.trae/mcp.json` is an **experimental/beta feature**. The agent **cannot access** project-level MCP servers. If Trae shows an "Enable Project MCP" option — ignore it. Always use the global config path.

---

## Step 3: Install Skills

Skills are required for ToolUniverse to work as an intelligent research assistant. Run these in your **system terminal**.

### Option A — npx (quickest)

```bash
npx skills add mims-harvard/ToolUniverse --all
```

If `npx` is not found, install Node.js from [nodejs.org](https://nodejs.org) (the LTS version includes npm and npx), then retry.

### Option B — git clone (if npx fails: corporate network, cert issues, or proxy problems)

If `git` is not found, install it from [git-scm.com](https://git-scm.com), then retry.

**macOS / Linux:**
```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/mims-harvard/ToolUniverse.git /tmp/tu-skills
cd /tmp/tu-skills && git sparse-checkout set skills
mkdir -p ~/.trae/skills && cp -r /tmp/tu-skills/skills/* ~/.trae/skills/
rm -rf /tmp/tu-skills
```

**Windows (PowerShell — run each line separately):**
```powershell
# Run each line separately — PowerShell does not support && like bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/mims-harvard/ToolUniverse.git "$env:TEMP\tu-skills"
Set-Location "$env:TEMP\tu-skills"
git sparse-checkout set skills
New-Item -ItemType Directory -Force "$env:APPDATA\Trae\skills" | Out-Null
robocopy "$env:TEMP\tu-skills\skills" "$env:APPDATA\Trae\skills" /E
Remove-Item -Recurse -Force "$env:TEMP\tu-skills"
```

> Note: The exact skills directory for Trae may vary. Check [SKILLS_CATALOG.md](https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/SKILLS_CATALOG.md) if skills don't activate after installation.

**Verify skills were installed** — run in your system terminal:

*macOS / Linux:*
```bash
ls ~/.trae/skills | grep tooluniverse
```
*Windows (PowerShell):*
```powershell
Get-ChildItem "$env:APPDATA\Trae\skills" | Where-Object { $_.Name -like "*tooluniverse*" }
```

✅ **Pass**: You see folders like `tooluniverse`, `tooluniverse-drug-research`, etc. → proceed to Step 4.
❌ **Fail**: Nothing listed → the install didn't complete or went to the wrong directory. Re-run the install command or try the git clone option.

> ⏸️ Ask: "Do you see tooluniverse skill folders listed?" Wait before continuing.

---

## Step 4: Restart and Test

1. **Fully quit Trae** (not just close the window), then reopen it
2. **First launch takes 60–90 seconds** while Trae downloads ToolUniverse in the background

**Check MCP connection:**
Open Trae Settings → MCP. `tooluniverse` should appear with a green/connected status.

**Live tool test** (verifies MCP is working):
```
list_tools
```
or
```
execute_tool("PubMed_search_articles", {"query": "CRISPR", "max_results": 1})
```

**Skills smoke test** (verifies skills are installed):
> Say: `"Use the tooluniverse skill to research the drug metformin"`

The `tooluniverse` skill is a router — it picks the right sub-skill automatically. If the response is plain text with no tool calls, skills are not installed or not in the correct directory.

**If something is still broken, check:**
1. The config file is at the correct global path (not `.trae/mcp.json`)
2. `uvx tooluniverse --help` works in your **system terminal** (not Trae's terminal)
3. Trae was fully restarted
4. Fetch [TROUBLESHOOTING.md](https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/TROUBLESHOOTING.md) for more diagnostics, or [GITHUB_ISSUE.md](https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/GITHUB_ISSUE.md) to report the issue.
