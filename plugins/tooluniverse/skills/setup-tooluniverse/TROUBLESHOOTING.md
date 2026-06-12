# Troubleshooting ToolUniverse Setup

When something fails, always provide the **exact copy-paste fix command** — don't just say "check the logs."

## Issue 1: Python Version Incompatibility

**Symptom**: Error containing `requires-python = ">=3.10"` or `Python 3.9 is not supported`

**Fix**:
```bash
brew install python@3.12        # macOS
# or: sudo apt install python3.12  # Ubuntu/Debian
python3.12 -m pip install tooluniverse
```

## Issue 2: uvx or uv Not Found

**Symptom**: `uvx: command not found` or `uv: command not found`

**Fix**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zshrc 2>/dev/null || source ~/.bashrc 2>/dev/null
uvx --version   # verify it worked
```

## Issue 3: Context Window Overflow

**Symptom**: MCP server loads but the client becomes very slow, or gives "context too large" errors

**Note**: Compact mode is already the default — the `tooluniverse` entry point enables it automatically. If still hitting context limits:
```json
"args": ["--refresh", "tooluniverse", "--tool-categories", "uniprot,chembl,pubmed"]
```
Restart the app after editing.

## Issue 4: Import Errors for Specific Tools

**Symptom**: Tool fails with `ModuleNotFoundError: No module named 'rdkit'` (or similar)

**Fix**:
```bash
pip install tooluniverse[all]
# Or the specific extra needed:
# pip install tooluniverse[visualization]   # rdkit, py3Dmol
# pip install tooluniverse[singlecell]       # cellxgene
# pip install tooluniverse[ml,embedding]     # sentence-transformers, admet-ai
```

## Issue 5: MCP Server Won't Start

**Symptom**: No tooluniverse server in client's server list, "Failed to spawn process", "ENOENT", "command not found"

**#1 most common cause — GUI apps (Claude Desktop, Windsurf) don't inherit shell PATH.**

**Option A — Homebrew (macOS, recommended, permanent):**
```bash
brew install uv
# Then restart the app — can now use "uvx" everywhere, no absolute path needed
```

**Option B — Symlink (macOS/Linux, permanent):**
```bash
sudo ln -sf "$(which uvx)" /usr/local/bin/uvx   # Intel Mac / Linux
# OR for Apple Silicon Mac:
sudo ln -sf "$(which uvx)" /opt/homebrew/bin/uvx
```

**Option C — Absolute path (all platforms, quick fix):**
```bash
which uvx   # macOS/Linux → e.g. /opt/homebrew/bin/uvx or /Users/you/.local/bin/uvx
where uvx   # Windows
```
Use that full path as `"command"` in your config instead of `"uvx"`.

**Full diagnostic chain — run these in order:**
```bash
# 1. Can uvx find and run it?
uvx tooluniverse --help

# 2. Does it start without errors? (Ctrl+C to stop)
uvx tooluniverse

# 3. Is the config file valid JSON?
python3 -m json.tool ~/.cursor/mcp.json   # replace path for your client

# 4. View the client's MCP logs
tail -50 ~/Library/Logs/Claude/mcp*.log 2>/dev/null        # Claude Desktop (macOS)
tail -50 ~/Library/Application\ Support/Cursor/logs/*.log  # Cursor (macOS)
```

Fix based on where the chain breaks. Other common causes: trailing commas in JSON, wrong config file path.

## Issue 6: API Key Errors (401/403)

**Symptom**: Tool returns `"unauthorized"`, `"forbidden"`, or `"invalid API key"`

**Diagnostic**:
```bash
echo $NCBI_API_KEY    # replace with the failing key name
```

**Common fixes**:
- Keys must be in the `"env"` block in your MCP config file (not a `.env` file the app doesn't load):
  ```json
  "env": { "PYTHONIOENCODING": "utf-8", "NCBI_API_KEY": "your_key_here" }
  ```
- Wrong key name: variable must match exactly (e.g., `ONCOKB_API_TOKEN` not `ONCOKB_API_KEY`)
- Restart required after editing the config file
- Free tier pending: DisGeNET and OMIM may take 24–48h for account approval

## Issue 7: Upgrading ToolUniverse

**Symptom**: User wants a newer version, or tools are missing / behavior is outdated

The recommended config uses `"--refresh"` which auto-updates on every launch. If the user's config doesn't have it:
```json
"args": ["--refresh", "tooluniverse"]
```

To upgrade immediately:
```bash
uv cache clean tooluniverse   # clears uvx cache, then restart the MCP client
```

To pin a specific version:
```json
"args": ["tooluniverse==1.0.19"]
```

For pip users:
```bash
pip install --upgrade tooluniverse
```

## Issue 8: Python Version Too New

**Symptom**: Errors like `requires-python >=3.10,<3.14`, `SyntaxError` in ToolUniverse code, or `ModuleNotFoundError` for a built-in module after upgrading Python.

ToolUniverse supports Python 3.10–3.13. Python 3.14+ (pre-release) may break things.

**Check your Python version:**
```bash
python3 --version
uvx tooluniverse --help   # see what Python uvx picks up
```

**Fix — pin to a compatible Python for uvx:**
```bash
uvx --python 3.12 tooluniverse --help
```

If that works, update your MCP config to use the pinned version:
```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "uvx",
      "args": ["--python", "3.12", "--refresh", "tooluniverse"],
      "env": { "PYTHONIOENCODING": "utf-8" }
    }
  }
}
```

## Issue 9: Stale or Broken Package Version

**Symptom**: A tool that used to work now errors, or a new tool listed in docs isn't available, or you see `AttributeError` / `ImportError` referencing ToolUniverse internals.

**Step 1 — force a fresh install:**
```bash
uv cache clean tooluniverse
uvx tooluniverse --version   # should pull the latest
```

**Step 2 — check what version is running:**
```bash
uvx tooluniverse --version
```

**Step 3 — pin to latest stable if auto-update pulls a broken release:**
```bash
# In your MCP config args:
"args": ["tooluniverse==<last-known-good-version>"]
# Check releases: https://github.com/mims-harvard/ToolUniverse/releases
```

## Still Stuck? File a GitHub Issue

If none of the above fixes it, open a GitHub issue. Run this script first — it collects system info with **no personal data** (paths and usernames are stripped):

```bash
python3 - << 'EOF'
import sys, platform, subprocess, os, re, urllib.parse

home = os.path.expanduser("~")
def run(cmd):
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True).strip()
    except Exception as e:
        out = f"error: {e}"
    return re.sub(re.escape(home), "~", out)

lines = [
    "**Environment**",
    f"- OS: {platform.system()} {platform.release()} {platform.machine()}",
    f"- Python: {sys.version.split()[0]}",
    f"- uv: {run('uv --version')}",
    f"- uvx: {run('uvx --version')}",
    f"- ToolUniverse: {run('uvx tooluniverse --version 2>/dev/null || echo unknown')}",
    "",
    "**Steps to reproduce**",
    "1. <describe what you did>",
    "",
    "**Error message**",
    "```",
    "<paste full error here>",
    "```",
    "",
    "**Expected behavior**",
    "<what you expected to happen>",
]

body = "\n".join(lines)
title = "Bug: <brief description>"
url = ("https://github.com/mims-harvard/ToolUniverse/issues/new"
       "?title=" + urllib.parse.quote(title)
       + "&body=" + urllib.parse.quote(body))

print("=" * 60)
print("ISSUE BODY (copy-paste if opening manually):")
print("=" * 60)
print(body)
print()
print("=" * 60)
print("PRE-FILLED ISSUE URL (open in browser):")
print("=" * 60)
print(url)
EOF
```

The script prints two things:
1. **Issue body** — copy-paste it into https://github.com/mims-harvard/ToolUniverse/issues/new
2. **Pre-filled URL** — open it in a browser to get a GitHub issue form with the info already filled in

**If GitHub CLI (`gh`) is installed**, you can create the issue directly — paste the body from above, then run:
```bash
gh issue create --repo mims-harvard/ToolUniverse \
  --title "Bug: <brief description>" \
  --body "<paste issue body here>"
```

You can also email [Shanghua Gao](mailto:shanghuagao@gmail.com) with the issue body.
