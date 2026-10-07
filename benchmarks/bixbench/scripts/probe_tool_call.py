"""Check an observed MCP result, never an agent's claim about tool availability."""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

PROMPT = (
    "Call mcp__tooluniverse__execute_tool with name='UCSC_get_sequence' and "
    "arguments={'genome':'hg38','region':'chr14:89000000-89000010'}. "
    "Reply with only the returned dna string, or FAILED."
)
EXPECTED = "ATCTTGTCACT"


def observed_sequence(events):
    calls = {}
    for event in events:
        for block in event.get("message", {}).get("content", []):
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                calls[block["id"]] = block
            elif block.get("type") == "tool_result" and not block.get("is_error"):
                call = calls.get(block.get("tool_use_id"), {})
                if (
                    call.get("name", "").startswith("mcp__tooluniverse__")
                    and "UCSC_get_sequence" in json.dumps(call.get("input", {}))
                    and EXPECTED in json.dumps(block.get("content"))
                ):
                    return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plugin", required=True)
    args = ap.parse_args()
    plugin = Path(args.plugin).resolve()
    command = [
        "claude",
        "--print",
        "--verbose",
        "--output-format",
        "stream-json",
        "--setting-sources",
        "",
        "--strict-mcp-config",
        "--plugin-dir",
        str(plugin),
        "--mcp-config",
        str(plugin / ".mcp.json"),
        "--max-turns",
        "14",
    ]
    env = dict(os.environ)
    env.setdefault("MCP_TIMEOUT", "600000")
    env.setdefault("MCP_TOOL_TIMEOUT", "600000")
    with tempfile.TemporaryDirectory(prefix="bixbench-probe-") as workdir:
        try:
            run = subprocess.run(
                command,
                input=PROMPT,
                capture_output=True,
                text=True,
                env=env,
                cwd=workdir,
                timeout=560,
            )
        except (OSError, subprocess.TimeoutExpired):
            return 1
    events = []
    for line in (run.stdout or "").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if run.returncode == 0 and observed_sequence(events):
        print(EXPECTED)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
