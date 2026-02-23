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
