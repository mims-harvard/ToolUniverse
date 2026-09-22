"""The half of a resident worker that is the same for every model.

This file runs inside the *model's* environment, not ToolUniverse's, and is
loaded by path for the same reason ``protocol.py`` is: that environment holds a
pinned scientific stack and nothing of this package, and importing
``tooluniverse`` there would drag in a dependency set it has no reason to carry.
It therefore uses the standard library only.

A provider's worker script supplies what is genuinely its own — building the
model, and turning one request into one prediction — and calls :func:`serve`
with them. Everything below is what every model needs identically: the socket,
the request loop, a failure that does not take the model down with it, and the
two ways a held model gives the card back.

Giving the card back is the part worth being explicit about. A held model is
fast because it keeps weights, a CUDA context and compiled kernels resident,
and that is exactly why it must stop holding them when nobody is asking. The
supervisor retires an idle worker; that covers the ordinary case. It does not
cover its own death, and on this project SIGKILLing an MCP server left two
worker processes holding a GPU that nothing could then reach. So the worker
also watches for being orphaned — reparented to init — and exits once a grace
period has passed with no request, long enough that a prediction in flight when
the parent died still finishes and writes its answer.
"""

from __future__ import annotations

import importlib.util
import os
import socket
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, Optional

# The supervisor exports these so a worker never has to guess where the shared
# files are; the filesystem fallback keeps a hand-run worker working.
PROTOCOL_ENV = "TOOLUNIVERSE_REMOTE_PROTOCOL"
ORPHAN_GRACE_ENV = "TOOLUNIVERSE_RESIDENT_ORPHAN_GRACE_S"
DEFAULT_ORPHAN_GRACE_S = 120.0


def _load_by_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"[{name}] cannot be loaded from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def protocol():
    """The wire protocol module, by path — never as a ToolUniverse import."""
    override = os.environ.get(PROTOCOL_ENV)
    path = Path(override) if override else Path(__file__).resolve().parent / "protocol.py"
    if not path.is_file():
        raise SystemExit(
            f"the wire protocol is not at {path}; set {PROTOCOL_ENV} to its path"
        )
    return _load_by_path("_tu_remote_protocol", path)


def serve(
    *,
    slug: str,
    socket_path: str,
    on_predict: Callable[[Dict[str, Any]], Dict[str, Any]],
    ready: Optional[Callable[[], Dict[str, Any]]] = None,
    on_reset: Optional[Callable[[], None]] = None,
    log: Optional[Callable[[str], None]] = None,
    orphan_grace_s: Optional[float] = None,
) -> int:
    """Answer requests on ``socket_path`` until told to stop.

    ``on_predict`` receives the request dict and returns the body of a
    successful reply. Raising is fine and expected: the failure is named back to
    the caller and the model stays up, because a bad request must not cost the
    minutes it took to build one. ``on_reset`` runs just before each prediction
    (peak-memory counters and the like); ``ready`` adds fields to the ping.

    One request at a time, by construction. Two inside one CUDA context would
    interleave their allocations and make an out-of-memory attributable to
    neither, so this loop accepts and answers serially and callers queue.
    """
    P = protocol()
    say = log or (lambda msg: print(f"[{slug}-resident] {msg}", flush=True))
    started = time.time()
    state = {"last_request": time.time()}
    grace = (
        orphan_grace_s
        if orphan_grace_s is not None
        else float(os.environ.get(ORPHAN_GRACE_ENV, DEFAULT_ORPHAN_GRACE_S))
    )

    def handle(req: Dict[str, Any]) -> Dict[str, Any]:
        op = req.get("op")
        if op == P.OP_PING:
            body = {
                "ok": True,
                "model": slug,
                "ready": True,
                "uptime_s": round(time.time() - started, 1),
            }
            if ready is not None:
                body.update(ready())
            return body
        if op == P.OP_SHUTDOWN:
            return {"ok": True}
        if op == P.OP_PREDICT:
            state["last_request"] = time.time()
            if on_reset is not None:
                on_reset()
            return {"ok": True, "result": on_predict(req)}
        return {"ok": False, "error": f"unknown op {op!r}", "reason": "unknown_op"}

    def orphan_watchdog() -> None:
        while True:
            time.sleep(5)
            if os.getppid() != 1:
                continue
            idle = time.time() - state["last_request"]
            if idle < grace:
                continue
            say(
                f"orphaned (parent gone) and idle {idle:.0f}s >= {grace:.0f}s: "
                f"releasing the GPU and exiting"
            )
            os._exit(0)  # the loop is blocked in accept(); there is nothing to unwind

    if os.path.exists(socket_path):
        os.unlink(socket_path)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(socket_path)
    os.chmod(socket_path, 0o600)  # this uid only; the MCP server runs as the same user
    srv.listen(16)
    threading.Thread(target=orphan_watchdog, name="orphan-watchdog", daemon=True).start()
    say(f"listening on {socket_path}")

    try:
        while True:
            conn, _ = srv.accept()
            buf = bytearray()
            try:
                while True:
                    try:
                        req = P.recv_line(conn, buf)
                    except P.ProtocolError:
                        break
                    try:
                        reply = handle(req)
                    except Exception as exc:  # noqa: BLE001 - never lose the model
                        reply = {
                            "ok": False,
                            "error": f"{type(exc).__name__}: {exc}",
                            "reason": "request_failed",
                            "traceback": traceback.format_exc(limit=8),
                        }
                    state["last_request"] = time.time()
                    P.send_line(conn, reply)
                    if req.get("op") == P.OP_SHUTDOWN:
                        say("shutdown requested")
                        return 0
            finally:
                conn.close()
    finally:
        srv.close()
        if os.path.exists(socket_path):
            try:
                os.unlink(socket_path)
            except OSError:
                pass


def bootstrap(worker_file: str):
    """Load this module from a provider's worker script.

    Every provider's worker needs the same three lines to reach here, so they
    live here instead::

        import importlib.util, pathlib
        _wb = importlib.util.module_from_spec(...)   # see the providers

    In practice a worker calls :func:`sys.path`-free path loading directly; this
    helper exists for the symmetric case where the base is found relative to the
    worker rather than through the environment.
    """
    base = Path(worker_file).resolve().parents[3] / "remote_resident" / "worker_base.py"
    return _load_by_path("_tu_worker_base", base)


__all__ = ["protocol", "serve", "bootstrap", "PROTOCOL_ENV", "ORPHAN_GRACE_ENV"]
