"""The half of a resident worker that is the same for every model.

This file runs inside the *model's* environment, not ToolUniverse's, and is
loaded by path for the same reason ``protocol.py`` is: that environment holds a
pinned scientific stack and nothing of this package, and importing
``tooluniverse`` there would drag in a dependency set it has no reason to carry.
Its own imports are therefore the standard library only; the one function that
needs the model's stack (:func:`release_cublas_workspaces`) imports inside the
call.

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
# Set to "1" to stop :func:`serve` releasing cuBLAS workspaces after each
# request. Nothing in the fleet needs it; it is here so that the leak can be
# reproduced on a provider that no longer has it, which is how the fix was
# checked in the first place and how the next one will be.
NO_CUBLAS_RELEASE_ENV = "TOOLUNIVERSE_RESIDENT_NO_CUBLAS_RELEASE"


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
    path = (
        Path(override) if override else Path(__file__).resolve().parent / "protocol.py"
    )
    if not path.is_file():
        raise SystemExit(
            f"the wire protocol is not at {path}; set {PROTOCOL_ENV} to its path"
        )
    return _load_by_path("_tu_remote_protocol", path)


def release_cublas_workspaces() -> int:
    """Give back the cuBLAS workspaces torch caches per (handle, stream).

    Returns the bytes freed, or 0 on a build with no such call and on CPU.

    WHY A HELD MODEL NEEDS THIS. torch allocates a cuBLAS workspace the first
    time a GEMM runs on a (handle, stream) pair and keeps it in a C++ static
    map that nothing clears. A kit that captures a CUDA graph creates a fresh
    side stream per request to warm up on before capturing, so every request
    abandons a stream and leaves its workspace behind -- measured at exactly
    ``torch.backends.cuda.blas_workspace_size()``, 32 MiB on this GB10, per
    request on byte-identical input.

    It is invisible to every ordinary check. The bytes are in
    ``memory_allocated`` but held by no Python object, so a census of every
    reachable CUDA tensor stays frozen while the number climbs,
    ``gc.collect()`` returns nothing, and ``empty_cache()`` returns nothing --
    it only drops blocks the allocator is *caching*, and these are live. What
    it looks like from outside is one new fully-allocated allocator segment per
    request, on a stream id that was not there before. ``chai1`` and ``genie3``
    each grew ~0.04 GiB per request until this call, which is 140 requests to
    chai1's whole declared budget; their manifests carry the measurements.

    A HELD GRAPH, MEASURED RATHER THAN FEARED. This used to say the call was
    safe only where no captured graph outlives the request, on the reasoning
    that a graph which captured cuBLAS calls holds the workspace pointer, and
    on that reasoning it was a call each provider had to make for itself.
    `rosettafold3` is why it finally got tested rather than repeated: its
    `fast` mode keeps pairformer-stack graphs across folds, so it could not
    use the argument. The reasoning is wrong twice over.

    * A replay cannot read a freed workspace's contents, because the
      workspace is scratch that each kernel writes before it reads.
      ``cudaMemset`` it to 0xAB and the replay returns the same bits, so "the
      output did not change" was never evidence of anything either.
    * The failure that WOULD be real is the other direction -- the replay
      still writes to that address, and writing over a tensor the allocator
      has since handed to someone else corrupts it. It does not happen: a
      workspace allocated during a capture belongs to that graph's PRIVATE
      memory pool (``segment_pool_id`` (1, 0), not (0, 0)), so clearing the
      map hands the block back to a pool only a capture into the same pool
      draws from.

    Checked on every torch in this fleet -- 2.7.0+cu128, 2.7.1+cu128,
    2.8.0+cu129, 2.10.0+cu128, 2.11.0+cu128, 2.11.0+cu130, 2.12.0+cu130,
    2.13.0+cu130 -- and on each one with a POSITIVE CONTROL first, because
    without one the test is vacuous and two of the first three written here
    were. The control reads the workspace bytes back to show that this build's
    replay does write to them; which GEMM does that is a function of the
    cuBLAS version and has to be searched for per build (fp32 ``mm`` works
    everywhere here; fp16 writes on 13.0 and not on 12.8, and a square
    ``1024**3`` writes on neither). With the control passing, 34 workspaces'
    worth of live tensors on the default stream and on fresh ones never
    landed on the address, twenty cleared replays scribbled on nothing, and
    with five graphs captured and four dropped the survivor still wrote only
    into its own private pool. The workspace is 32 MiB on torch >= 2.12 and
    8.12 MiB before it, and on the older builds it sits INSIDE a 20 MiB
    segment -- a probe that filters segments by size rather than blocks finds
    nothing there and proves nothing, which is how the first pass missed it.

    So this is not a call a provider has to prove its graphs dead to make,
    and it is no longer a call a provider makes at all: :func:`serve` does it
    after every request, for everybody. See ``NO_CUBLAS_RELEASE_ENV`` for the
    way back out.
    """
    # The one function here that touches the model's stack rather than the
    # standard library, and it imports inside the call so that the module's
    # import stays what the docstring says it is.
    try:
        import torch  # noqa: PLC0415
    except Exception:  # noqa: BLE001 - a worker without torch has no workspaces
        return 0
    clear = getattr(getattr(torch, "_C", None), "_cuda_clearCublasWorkspaces", None)
    if clear is None or not torch.cuda.is_available():
        return 0
    before = torch.cuda.memory_allocated()
    clear()
    return max(0, before - torch.cuda.memory_allocated())


def _fatal_reply(exc: BaseException) -> Dict[str, Any]:
    """The last thing a worker says when a request takes it down with it.

    A ``SystemExit`` raised out of ``on_predict`` is not a failed request. It
    is the process declaring that it must not answer another one, and three of
    the kits do exactly that: ``af3_jax``, ``rfdiffusion3`` and ``opendde``
    each define a ``KernelsRefused(SystemExit)`` and raise it from inside a
    prediction when the kernel route they required is not the route that
    loaded. All three carry code **5**, which is this standard's own code for
    an expected accelerator absent (section 8). That verdict is about the
    PROCESS, not about the request, and honouring it is right: a provider that
    advertises a kit's kernels and then answers on stock ones is returning
    results whose provenance is a lie.

    **Swallowing it would not even keep the worker alive.** af3_jax's
    ``refuse_exit`` arms a ``threading.Timer`` that calls ``os._exit(5)``
    sixty seconds later, in its own words "should anything swallow the
    SystemExit", and rfdiffusion3's ``finish_at_exit`` hook forces the same
    code at interpreter end. Catching the refusal and carrying on buys one
    minute of serving and then an abrupt death in the middle of whichever
    request is running by then -- strictly worse than dying now, and harder to
    attribute.

    So the worker still dies. What it must not do is die SILENTLY, which is
    what it did before this existed: the refusal unwound the whole loop, the
    client's ``recv_line`` hit EOF and raised ``ProtocolError: peer closed the
    connection mid-message``, and the KERNELS line naming the cause sat in a
    transcript nobody was pointed at. This builds the reply that names it; the
    loop sends it, then re-raises so the exit still happens.
    """
    code = exc.code if isinstance(exc, SystemExit) else None
    # ``SystemExit(int)`` exits with that status; ``SystemExit(anything else)``
    # prints it and exits 1; ``SystemExit()`` exits 0. KeyboardInterrupt has no
    # code at all.
    exit_code = code if isinstance(code, int) else (None if code is None else 1)
    # All three KernelsRefused classes pass the CODE to ``SystemExit``, so
    # ``str(exc)`` is the bare number and the readable part is on an attribute
    # instead: ``.reason`` on rfdiffusion3's, ``.line`` on opendde's. Prefer
    # whichever is there over printing "5" twice. This is a convenience, not a
    # protocol -- an exception with neither is reported as it prints.
    said = next(
        (
            str(v).strip()
            for v in (getattr(exc, "reason", None), getattr(exc, "line", None))
            if isinstance(v, str) and v.strip()
        ),
        str(exc),
    )
    tail = (
        f"the worker exits {exit_code} rather than answering again"
        if exit_code is not None
        else "the worker is exiting rather than answering again"
    )
    return {
        "ok": False,
        "error": f"{type(exc).__name__}: {said} \u2014 {tail}",
        "reason": "worker_exiting",
        "exit_code": exit_code,
        "traceback": traceback.format_exc(limit=8),
    }


def serve(
    *,
    slug: str,
    socket_path: str,
    on_predict: Callable[[Dict[str, Any]], Dict[str, Any]],
    ready: Optional[Callable[[], Dict[str, Any]]] = None,
    on_reset: Optional[Callable[[], None]] = None,
    log: Optional[Callable[[str], None]] = None,
    orphan_grace_s: Optional[float] = None,
    release_cublas: bool = True,
) -> int:
    """Answer requests on ``socket_path`` until told to stop.

    ``on_predict`` receives the request dict and returns the body of a
    successful reply. Raising is fine and expected: the failure is named back to
    the caller and the model stays up, because a bad request must not cost the
    minutes it took to build one. ``on_reset`` runs just before each prediction
    (peak-memory counters and the like); ``ready`` adds fields to the ping.

    Raising something that is *not* an ``Exception`` is the other case, and it
    is not a failed request: the caller is told and then the worker goes down.
    :func:`_fatal_reply` is where that is argued, because the argument is the
    whole of why this loop has two except clauses instead of one.

    One request at a time, by construction. Two inside one CUDA context would
    interleave their allocations and make an out-of-memory attributable to
    neither, so this loop accepts and answers serially and callers queue.

    After each prediction it calls :func:`release_cublas_workspaces`, which is
    where the reasoning for doing that for everybody is written down. A
    provider that wants it off passes ``release_cublas=False``; so does
    ``TOOLUNIVERSE_RESIDENT_NO_CUBLAS_RELEASE=1``, which exists to reproduce
    the leak rather than to live in a deployment.
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
    release = release_cublas and os.environ.get(NO_CUBLAS_RELEASE_ENV) != "1"

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
            result = None
            try:
                result = on_predict(req)
            finally:
                # After on_predict rather than inside it, which is the same
                # moment: the providers that used to do this themselves did
                # it on their last line. It does not disturb the peak they
                # report either -- clearing returns allocated bytes, and the
                # allocator goes on caching the blocks, so memory_reserved
                # does not move.
                #
                # In a `finally` because a request that RAISED can have got
                # far enough to capture a graph and abandon its stream, and a
                # worker answering a run of bad requests is exactly where
                # that would add up unnoticed.
                if release:
                    freed = release_cublas_workspaces()
                    if freed and isinstance(result, dict):
                        result.setdefault(
                            "cublas_workspaces_freed_mib", round(freed / 2**20, 1)
                        )
            return {"ok": True, "result": result}
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
    threading.Thread(
        target=orphan_watchdog, name="orphan-watchdog", daemon=True
    ).start()
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
                    except BaseException as exc:  # noqa: BLE001 - see below
                        # NOT an Exception, so the model is not staying up:
                        # answer first, then let it go. :func:`_fatal_reply`
                        # carries the reasoning for both halves of that.
                        reply = _fatal_reply(exc)
                        say(reply["error"])
                        try:
                            P.send_line(conn, reply)
                        except OSError:
                            pass  # the caller is gone; the exit is what matters
                        raise
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


__all__ = [
    "protocol",
    "serve",
    "bootstrap",
    "release_cublas_workspaces",
    "PROTOCOL_ENV",
    "ORPHAN_GRACE_ENV",
    "NO_CUBLAS_RELEASE_ENV",
]
