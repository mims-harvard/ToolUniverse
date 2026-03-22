#!/usr/bin/env bash
set -euo pipefail
source "$HOME/.env.secure"

# Cache: two-tier (LRU + SQLite), singleflight dedup, async writes
export TOOLUNIVERSE_CACHE_ENABLED=true
export TOOLUNIVERSE_CACHE_PERSIST=true
export TOOLUNIVERSE_CACHE_SINGLEFLIGHT=true
export TOOLUNIVERSE_CACHE_ASYNC_PERSIST=true
export TOOLUNIVERSE_CACHE_MEMORY_SIZE=1024

# Loading: lazy (fast startup), coerce types, strict validation off
export TOOLUNIVERSE_LAZY_LOADING=true
export TOOLUNIVERSE_COERCE_TYPES=true
export TOOLUNIVERSE_STRICT_VALIDATION=false

# Logging: INFO default, STDIO mode for MCP server
export TOOLUNIVERSE_LOG_LEVEL=INFO
export TOOLUNIVERSE_STDIO_MODE=1

# Ollama: local LLM fallback for Tool_Finder_LLM
export OLLAMA_SERVER_URL="${OLLAMA_SERVER_URL:-http://localhost:11434}"

# Skills catalog: makes Claude Code skills discoverable via find_tools/grep_tools
SKILLS_CATALOG="$HOME/code/ToolUniverse/src/tooluniverse/data/skills_catalog.json"

exec uvx --from tooluniverse tooluniverse-smcp-stdio \
  --compact-mode \
  --hook-config-file "$HOME/.claude/tooluniverse-hooks.json" \
  ${SKILLS_CATALOG:+--tool-config-files "claude_code_skills:$SKILLS_CATALOG"} \
  --verbose \
  "$@"
