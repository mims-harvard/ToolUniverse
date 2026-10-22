"""Line-delimited JSON over a Unix stream socket.

The transport between a remote tool's MCP server (light, CPU-only, one per
provider) and its resident model worker (heavy, holds the GPU). Both live on
the same host: the worker is what keeps model weights on the device between
requests, which is the whole point of the split. A Unix socket rather than a
TCP port because the worker is never addressable from outside the machine --
``tu remote share`` publishes the MCP server, never this.

Framing is one JSON object per line, UTF-8, no embedded newlines (``json.dumps``
escapes them). A request carries ``op``; a reply carries ``ok`` plus either the
operation's own fields or ``error`` and ``reason``. ``reason`` is one
blank-free token so callers can branch on it without parsing prose.
"""

from __future__ import annotations

import json
import os
import socket
from typing import Any, Dict

# Operations every resident worker answers, whatever model it holds.
OP_PING = "ping"  # -> {"ok": True, "model": <slug>, "ready": bool, "uptime_s": float}
OP_SHUTDOWN = "shutdown"  # -> {"ok": True}; the worker exits after replying
OP_PREDICT = "predict"  # model-specific payload; -> {"ok": ..., "result": {...}}

CONNECT_TIMEOUT_S = 10.0
# A cold model build is minutes, an inference tens of seconds; the caller sets
# its own deadline per request and this is only the socket's backstop.
DEFAULT_REQUEST_TIMEOUT_S = 3600.0


class ProtocolError(RuntimeError):
    """The peer closed mid-message, or sent something that is not one JSON line."""


def socket_path(slug: str, runtime_dir: str | None = None) -> str:
    """The worker socket for ``slug``.

    Under ``XDG_RUNTIME_DIR`` when the session has one (tmpfs, 0700, cleaned on
    logout), else a per-uid directory under the temp dir -- never a shared path
    another user could pre-create as a symlink.
    """
    root = runtime_dir or os.environ.get("XDG_RUNTIME_DIR")
    if not root:
        root = os.path.join(
            os.environ.get("TMPDIR", "/tmp"), f"tooluniverse-remote-uid{os.getuid()}"
        )
    root = os.path.join(root, "tooluniverse-remote")
    os.makedirs(root, mode=0o700, exist_ok=True)
    return os.path.join(root, f"{slug}.sock")


def send_line(sock: socket.socket, payload: Dict[str, Any]) -> None:
    sock.sendall((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))


def recv_line(sock: socket.socket, buf: bytearray) -> Dict[str, Any]:
    """One JSON object from ``sock``; ``buf`` carries bytes read past its newline."""
    while b"\n" not in buf:
        chunk = sock.recv(65536)
        if not chunk:
            raise ProtocolError("peer closed the connection mid-message")
        buf.extend(chunk)
    line, _, rest = bytes(buf).partition(b"\n")
    buf.clear()
    buf.extend(rest)
    try:
        return json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"peer sent a line that is not JSON: {exc}") from exc
