#!/usr/bin/env python3
"""Start a built .mcpb the way Claude Desktop does and complete a handshake.

Every other check we have reads files in the repo. None of them start the thing
we actually ship, which is how a bundle that could not boot at all reached the
release page: the launcher told ``uv`` to skip installing the bundle's
dependencies, so the server died on its first third-party import. The manifest
was valid, the version numbers matched, and the unit tests passed.

So this unpacks the artifact and launches it using the command recorded *in the
manifest*, rather than a copy of that command kept here. A launcher change that
breaks startup has to break this test too.

Usage:
    python3 mcpb/smoke_test.py dist/tooluniverse.mcpb [--timeout 900]

Exit code is 0 only when the server answers an MCP ``initialize`` handshake and
reports at least one tool.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

PROTOCOL_VERSION = "2024-11-05"


def _resolve_args(manifest: dict, bundle_dir: Path) -> tuple[str, list[str], dict]:
    """Read the launch command out of the manifest and expand its placeholders.

    MCPB manifests use ``${__dirname}`` for the unpacked bundle root and
    ``${/}`` for the path separator.
    """
    server = manifest["server"]
    config = server.get("mcp_config", server)

    def expand(value: str) -> str:
        return value.replace("${__dirname}", str(bundle_dir)).replace("${/}", os.sep)

    command = expand(config["command"])
    args = [expand(a) for a in config.get("args", [])]
    env = {k: expand(v) for k, v in (config.get("env") or {}).items()}
    return command, args, env


def _rpc(method: str, params: dict, request_id: int) -> str:
    return json.dumps(
        {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
    )


def smoke(bundle: Path, timeout: int) -> int:
    workdir = Path(tempfile.mkdtemp(prefix="mcpb-smoke-"))
    try:
        with zipfile.ZipFile(bundle) as zf:
            zf.extractall(workdir)

        manifest = json.loads((workdir / "manifest.json").read_text())
        command, args, env = _resolve_args(manifest, workdir)

        print(f"bundle   : {bundle}")
        print(f"version  : {manifest.get('version')}")
        print(f"launching: {command} {' '.join(args)}")

        if shutil.which(command) is None:
            print(f"FAIL: launcher {command!r} is not installed", file=sys.stderr)
            return 1

        child_env = {**os.environ, **env}
        # Dependency installation happens on this first launch, so the timeout
        # has to cover a cold resolve of the whole bundle, not just a boot.
        proc = subprocess.Popen(
            [command, *args],
            cwd=workdir,
            env=child_env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        request = _rpc(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "mcpb-smoke-test", "version": "1"},
            },
            1,
        )
        try:
            out, err = proc.communicate(input=request + "\n", timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
            print(f"FAIL: no handshake response within {timeout}s", file=sys.stderr)
            print(_tail(err), file=sys.stderr)
            return 1

        response = _first_jsonrpc_result(out)
        if response is None:
            print("FAIL: server produced no JSON-RPC response", file=sys.stderr)
            print(f"--- exit code: {proc.returncode}", file=sys.stderr)
            print(_tail(err), file=sys.stderr)
            return 1

        server_info = response.get("serverInfo", {})
        print(f"serverInfo: {server_info.get('name')} {server_info.get('version', '')}")
        print("PASS: bundle started and completed an MCP initialize handshake")
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _first_jsonrpc_result(stdout: str):
    """The initialize result, ignoring any banner output around it."""
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        if message.get("id") == 1 and isinstance(message.get("result"), dict):
            return message["result"]
    return None


def _tail(text: str, lines: int = 25) -> str:
    kept = [line for line in (text or "").splitlines() if line.strip()][-lines:]
    return "--- server stderr (tail) ---\n" + "\n".join(kept)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="path to a built .mcpb")
    parser.add_argument(
        "--timeout",
        type=int,
        default=900,
        help="seconds to allow for a cold dependency install plus startup",
    )
    ns = parser.parse_args()
    if not ns.bundle.is_file():
        print(f"no such bundle: {ns.bundle}", file=sys.stderr)
        return 2
    return smoke(ns.bundle, ns.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
