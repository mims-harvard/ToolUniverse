---
name: setup-keys
description: Set up ToolUniverse API keys. Opens a graphical setup page (or guides you in chat) listing every key tools can use, with registration links, and saves them permanently to a .env that the MCP server, CLI, and SDK all read. Use when a tool reports a missing API key or when first configuring ToolUniverse.
---

You are setting up ToolUniverse API keys for the user. Keys are read from the
environment by tools at run time and persisted in a `.env` that ToolUniverse
auto-loads. Follow these steps exactly.

## Step 1 — Ask which mode

Ask the user (use the AskUserQuestion tool):
- **Graphical interface** — a local web page with a form for all keys.
- **Agent-guided** — I ask you for keys here in chat.

## Step 2 — Ask where to store

Ask the user:
- **Global `~/.tooluniverse/.env`** (recommended) — works across all projects.
- **Project-local `./.tooluniverse/.env`** — only this project; read when the
  MCP server runs from this directory.

Resolve the target path:
- Global -> `~/.tooluniverse/.env`
- Local  -> `<current working directory>/.tooluniverse/.env`

## Step 3a — Graphical mode

Run (do NOT redirect or background it; it prints a URL and blocks until the
user saves, then exits):

```
python "${CLAUDE_PLUGIN_ROOT}/scripts/setup_keys_server.py" --target <TARGET_ENV_PATH>
```

If `api_keys_catalog.json` is not found next to the script (e.g. running from a
source checkout), add `--catalog <repo>/src/tooluniverse/data/api_keys_catalog.json`.

Show the user the printed `http://127.0.0.1:...` URL in case the browser does
not open automatically. When the command exits, report the target path and the
number of keys saved. Never print the key values.

## Step 3b — Agent-guided mode

1. Read the catalog: `python -c "import json; print(json.dumps(json.load(open('${CLAUDE_PLUGIN_ROOT}/scripts/api_keys_catalog.json'))))"`
   (fall back to the repo path `src/tooluniverse/data/api_keys_catalog.json`).
2. Ask the user whether to set all **required** keys, or name specific APIs.
3. For each selected key, show its `register_url` and `description`, then ask
   for the value. Do not echo previously stored values.
4. Write all collected values at once with the helper. `keys_env.py` exposes
   `merge_env(path, updates)`; call it from a short inline Python snippet,
   passing the target path and a dict of the values you collected:

```
python -c "import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts'); import keys_env; keys_env.merge_env('<TARGET_ENV_PATH>', {'OMIM_API_KEY': '...'})"
```

   Confirm the path and the names set (not the values).

## Step 4 — Finish

Tell the user to restart the ToolUniverse MCP server / CLI session so the new
keys load. Confirm storage location and which key names were set.
