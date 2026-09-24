#!/usr/bin/env python3
"""Entry point for ToolUniverse MCP Server (stdio transport for Claude Desktop).

This wrapper calls run_stdio_server with compact mode enabled.
Compact mode exposes only 5 core tools (list_tools, grep_tools, get_tool_info, execute_tool, find_tools)
while loading all 764+ tools in the background for execute_tool to access.
This prevents context window overflow from the massive tool list.
"""

import os
import sys

# Claude Desktop substitutes every ``${user_config.*}`` entry in the manifest's
# env block, including the ones the user left blank. An empty string still
# counts as "set" to os.environ, and ToolUniverse loads its .env files with
# override=False, so a blank field would shadow a key the user had already put
# in ~/.tooluniverse/.env and silently disable those tools. Drop anything that
# arrived empty, and anything that arrived as an unexpanded placeholder.
for _name, _value in list(os.environ.items()):
    if _value == "" or _value.startswith("${user_config."):
        del os.environ[_name]

# Optional escape hatch for the keys that have no field of their own: point
# TOOLUNIVERSE_ENV_FILE at a .env file and its entries are loaded here, before
# ToolUniverse reads anything. Existing environment variables still win, which
# matches how the package treats its own .env files.
_env_file = os.environ.get("TOOLUNIVERSE_ENV_FILE", "").strip()
if _env_file and os.path.isfile(_env_file):
    try:
        with open(_env_file, encoding="utf-8") as _handle:
            for _line in _handle:
                _line = _line.strip()
                if not _line or _line.startswith("#") or "=" not in _line:
                    continue
                _key, _, _val = _line.partition("=")
                _key = _key.strip()
                _val = _val.strip().strip('"').strip("'")
                if _key and _val and _key not in os.environ:
                    os.environ[_key] = _val
    except OSError as _exc:  # pragma: no cover - unreadable file, keep starting
        print(f"Could not read TOOLUNIVERSE_ENV_FILE: {_exc}", file=sys.stderr)

# Enable compact mode by default
sys.argv = [
    sys.argv[0],
    "--compact-mode",
]

from tooluniverse.smcp_server import run_stdio_server  # noqa: E402

if __name__ == "__main__":
    run_stdio_server()
