#!/usr/bin/env bash
# Verify the benchmark setup before running. Exits 1 if any check fails.
#
# A misconfigured plugin does not announce itself: the run completes and the
# score looks plausible. These checks catch the configurations that silently
# measure something other than the ToolUniverse you intend to test.
#
# Usage:
#   bash preflight.sh [--plugin DIR] [--src DIR]
#
#   --plugin DIR   built plugin directory (default: <repo>/dist/tooluniverse-plugin)
#   --src DIR      ToolUniverse source the MCP server should load
#                  (default: <repo>/src)
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
PLUGIN="$REPO/dist/tooluniverse-plugin"
SRC="$REPO/src"
while [ $# -gt 0 ]; do
  case "$1" in
    --plugin) PLUGIN="$2"; shift 2 ;;
    --src) SRC="$2"; shift 2 ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

fail=0
ok()  { printf "  ok   %s\n" "$1"; }
bad() { printf "  FAIL %s\n" "$1"; fail=1; }

# 1. The MCP server must load the ToolUniverse under test. An editable install
#    can resolve `tooluniverse` to an entirely different checkout, so the server
#    needs PYTHONPATH set explicitly in .mcp.json.
MCP_JSON="$PLUGIN/.mcp.json"
if [ ! -f "$MCP_JSON" ]; then
  bad "no .mcp.json at $MCP_JSON"
else
  configured=$(python3 - "$MCP_JSON" <<'PYCONFIG'
import json, sys
try:
    env = json.load(open(sys.argv[1]))['mcpServers']['tooluniverse'].get('env', {})
    print(env.get('PYTHONPATH', ''))
except (OSError, ValueError, KeyError):
    print('')
PYCONFIG
)
  if [ -z "$configured" ]; then
    bad "no PYTHONPATH in .mcp.json - the server may load a different install"
  elif [ "$(cd "$configured" 2>/dev/null && pwd)" != "$(cd "$SRC" 2>/dev/null && pwd)" ]; then
    bad "MCP PYTHONPATH is $configured, expected $SRC"
  else
    ok "MCP server loads the ToolUniverse under test"
  fi
fi

# 2. dist/ holds COPIES of the skills. Editing skills/ in a source tree changes
#    nothing the agent reads.
drift=0; checked=0
for a in "$REPO"/skills/*/SKILL.md; do
  [ -f "$a" ] || continue
  b="$PLUGIN/skills/$(basename "$(dirname "$a")")/SKILL.md"
  [ -f "$b" ] || continue
  checked=$((checked+1))
  cmp -s "$a" "$b" || { printf "       stale: %s\n" "$(basename "$(dirname "$a")")"; drift=1; }
done
if [ "$checked" -eq 0 ]; then bad "no skills found to compare"
elif [ "$drift" -eq 0 ]; then ok "plugin skills match the checkout ($checked compared)"
else bad "plugin skills are stale - rebuild the plugin or copy them into dist/"; fi

# 3. Prove the tools work by CALLING one. Asking the model whether it can call a
#    tool returns an answer from priors that is wrong in both directions.
probe=$(python3 "$HERE/probe_tool_call.py" --plugin "$PLUGIN" 2>/dev/null)
case "$probe" in
  *ATCTTGTCACT*) ok "MCP tool call returns the expected sequence" ;;
  *)             bad "MCP tool call did not return the expected sequence (got '${probe:-nothing}')" ;;
esac

# 4. This is deterministic and must not contact a model judge.
if python3 - "$REPO" <<'PYGRADER'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / 'skills/devtu-benchmark-harness/scripts'))
from grade_answers import grade_answer
assert not grade_answer('definitely incorrect', 'required benchmark answer', 'str_verifier', use_llm=False)['correct']
PYGRADER
then ok "grader rejects a deliberately wrong answer"
else bad "grader accepted a wrong answer or could not run"; fi

echo
if [ "$fail" -eq 0 ]; then echo "PREFLIGHT PASS"; else echo "PREFLIGHT FAIL - fix the above before running"; fi
exit $fail
