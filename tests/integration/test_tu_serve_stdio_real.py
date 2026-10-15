"""`tu serve` with no arguments has to start the MCP stdio server -- for real.

It did not. run_default_stdio_server parses sys.argv itself, and under `tu serve` that still
holds "serve", so the command exited 2 with "unrecognized arguments: serve". The `tooluniverse`
entry point worked, because its argv is just the program name. The only test of this path
mocked run_default_stdio_server, so the argv parse never ran in any test.

So this one does not mock anything: it starts the real command and speaks MCP to it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading

import pytest


def _first_reply(proc: subprocess.Popen, timeout: float) -> str:
    out: list[str] = []

    def read() -> None:
        line = proc.stdout.readline()
        out.append(line)

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    reader.join(timeout)
    return out[0] if out else ""


@pytest.mark.timeout(180)
def test_tu_serve_answers_an_mcp_initialize(tmp_path):
    env = dict(os.environ, HOME=str(tmp_path))
    proc = subprocess.Popen(
        [sys.executable, "-m", "tooluniverse.cli", "serve"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )
    try:
        proc.stdin.write(json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "test", "version": "1"}},
        }) + "\n")
        proc.stdin.flush()

        reply = _first_reply(proc, timeout=150)

        if not reply:
            proc.kill()
            err = proc.stderr.read()[-1500:]
            pytest.fail(f"no MCP reply; exit={proc.poll()} stderr tail:\n{err}")
        message = json.loads(reply)
        assert message.get("id") == 1
        assert "result" in message, message
    finally:
        proc.kill()
        proc.wait(timeout=10)
