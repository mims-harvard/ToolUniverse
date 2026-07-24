# Claude Desktop Setup

## ⚠️ The PATH Problem — Read This Before Writing Any Config

Claude Desktop is a GUI app. It launches in a clean environment and **does not inherit your shell's PATH**. This means if `uvx` lives in `~/.local/bin/uvx` (the default for the uv curl installer), Claude Desktop cannot find it — and will show a silent failure like "Failed to spawn process" or "ENOENT" with no helpful error message.

**You must resolve this before writing the config.** There are three ways:

---

### Fix A — Homebrew (macOS, recommended, permanent)

Homebrew installs `uvx` to `/opt/homebrew/bin/uvx` (Apple Silicon) or `/usr/local/bin/uvx` (Intel), which Claude Desktop can always find.

```bash
brew install uv
```

If you already installed uv via the curl installer, also run:
```bash
brew link uv --overwrite
```

Verify the Homebrew binary exists (Claude Desktop will use this path directly):
```bash
/opt/homebrew/bin/uvx --version   # Apple Silicon Mac
/usr/local/bin/uvx --version      # Intel Mac
```

With Homebrew uv installed, the standard config works:
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

---

### Fix B — Use the absolute path (all Macs, no Homebrew needed)

Find where uvx actually lives:
```bash
which uvx
```

Common outputs:
- Homebrew Apple Silicon: `/opt/homebrew/bin/uvx`
- Homebrew Intel: `/usr/local/bin/uvx`
- curl installer: `/Users/yourname/.local/bin/uvx`

Use that full path as `"command"` in the config:
```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "/Users/yourname/.local/bin/uvx",
      "args": ["--refresh", "tooluniverse"],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

Replace `/Users/yourname/.local/bin/uvx` with the actual output of `which uvx`.

---

### Fix C — Symlink (Linux / advanced)

```bash
sudo ln -sf "$(which uvx)" /usr/local/bin/uvx
```

---

## Writing the Config

Config file location:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Use the one-liner to safely create or merge without overwriting existing servers:
```bash
python3 -c "
import json, os
p = os.path.expanduser('~/Library/Application Support/Claude/claude_desktop_config.json')
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

If the user installed uv via curl (not Homebrew), replace `'command': 'uvx'` with `'command': '/Users/yourname/.local/bin/uvx'` using their actual path from `which uvx`.

## Restarting Claude Desktop

Use **⌘Q** (not just closing the window) to fully quit, then reopen.

⏱️ First launch takes 60–90 seconds while Claude Desktop downloads and installs ToolUniverse.

## Verifying MCP Tools Are Loaded

Claude Desktop's UI for MCP tools has changed across versions — look for whichever of these appears in your chat input bar:

- **Newer versions**: A **"Search and tools"** button (or a **+** icon) at the bottom of the chat input. Click it → you should see `tooluniverse` listed under connected tools/connectors. You can toggle it on/off from here.
- **Older versions**: A 🔨 **hammer icon** in the bottom-right of the chat input. Click it to see the list of available tools from `tooluniverse`.

If neither appears, check **Settings → Developer → MCP Servers** — it shows each server's connection status and any error messages.

## Verifying in the Logs

While Claude Desktop is loading, monitor the MCP logs:
```bash
tail -f ~/Library/Logs/Claude/mcp*.log          # macOS
tail -f ~/.config/Claude/logs/mcp*.log          # Linux
```

Look for `"tooluniverse" connected` — that confirms it worked.

Common error messages and what they mean:
- `ENOENT` / `spawn uvx ENOENT` → uvx not found; use absolute path or Homebrew fix
- `spawn /Users/you/.local/bin/uvx ENOENT` → wrong absolute path; run `which uvx` again
- `exit 1` immediately → run `uvx tooluniverse --help` in terminal to see the actual error

## Installing Skills (Required)

Skills are required for ToolUniverse to work as an intelligent research assistant. Run in terminal:

**Option A — npx (quickest):**
```bash
npx skills add mims-harvard/ToolUniverse --all
```
If `npx` is not found, install Node.js from [nodejs.org](https://nodejs.org) (LTS version includes npx), then retry.

**Option B — git clone (if npx fails):**
```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/mims-harvard/ToolUniverse.git /tmp/tu-skills
cd /tmp/tu-skills && git sparse-checkout set skills
# macOS — adjust path for Linux (~/.config/Claude/skills/) or Windows (%APPDATA%\Claude\skills\)
mkdir -p ~/Library/Application\ Support/Claude/skills && cp -r /tmp/tu-skills/skills/* ~/Library/Application\ Support/Claude/skills/
rm -rf /tmp/tu-skills
```

## Verifying Skills Are Installed

After running `npx skills add`, **check the terminal output** — it prints the exact directory where skills were installed. Use that path to verify:

```bash
ls <path-from-npx-output> | grep tooluniverse
```

If the output didn't show the path, the default location for Claude Desktop varies by OS:
- **macOS**: `~/Library/Application Support/Claude/skills/`
- **Linux**: `~/.config/Claude/skills/`
- **Windows**: `%APPDATA%\Claude\skills\`

```bash
# macOS example:
ls ~/Library/Application\ Support/Claude/skills | grep tooluniverse
```

✅ **Pass**: You see folders like `tooluniverse`, `tooluniverse-drug-research`, etc. → skills are ready.
❌ **Fail**: Nothing listed → wrong directory or install didn't complete. Check [SKILLS_CATALOG.md](https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/SKILLS_CATALOG.md) and retry.

**Smoke test** — in Claude Desktop, say:
> `"Use the tooluniverse skill to research the drug metformin"`

If the response is plain text with no tool calls, skills are not in the right directory.
