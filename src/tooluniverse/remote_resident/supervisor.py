"""Start, reuse and retire one provider's resident model worker.

A GPU remote tool costs most of its wall clock in work that is identical for
every request: loading weights, building the CUDA context, capturing the
kernels a first pass compiles. Measured for Boltz-2 on this project's GB10 box,
a fresh worker per request spends ~102 s where a held one spends ~47 s, and the
structure pass alone falls from ~23 s to ~5.8 s because CUDA graphs captured on
one request are replayed on the next. That is what this module exists to hold
on to.

Holding a model resident spends device memory the whole time, which is the
opposite of what a box running several models wants. Both are served by the
same object: a worker is started on the first request, reused while requests
keep arriving, and shut down once ``idle_timeout_s`` passes with none -- so a
provider nobody is calling is not occupying the card. ``vram_budget_gb`` from
the provider's manifest is what a scheduler above this reads to decide how many
providers may be resident at once; this module reports it and never enforces it.

One request at a time per worker, by construction. Two requests sharing one
CUDA context would interleave their allocations and make an out-of-memory
attributable to neither, so callers queue on :attr:`ResidentWorker.lock` rather
than racing.
"""

from __future__ import annotations

import os
import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import protocol as P


class WorkerStartError(RuntimeError):
    """The worker could not be started, or did not bind its socket in time."""


class WorkerRequestError(RuntimeError):
    """The worker answered, and the answer was a failure."""

    def __init__(self, message: str, reason: str = "request_failed"):
        super().__init__(message)
        self.reason = reason


# STANDARD section 8: the exit codes are stable and branchable, which is only
# worth anything if what reads them says what they mean. A bare number in an
# error message makes an operator look the table up; these sentences are the
# table, and they are here once so the start path and the request path cannot
# drift apart on what a 5 is.
EXIT_HINTS = {
    3: "that is a refusal (exit 3), so its last line names what it refused and why",
    5: (
        "that is an expected accelerator absent (exit 5): a kit's kernel "
        "census refuses this way when the route it required is not the route "
        "that loaded, and the KERNELS line above names it"
    ),
}


def exit_hint(rc: Optional[int]) -> str:
    """The clause naming what ``rc`` means, or nothing when it has no name."""
    text = EXIT_HINTS.get(rc) if isinstance(rc, int) else None
    return f" \u2014 {text}" if text else ""


# (argv, extra environment) for one worker process. A provider builds it: the
# interpreter must be the model environment's own, never the one running
# ToolUniverse, because the two do not share a dependency set.
# The mapping is applied over the operator's environment; a None value
# REMOVES that name from the child's environment rather than setting it.
def child_env(
    extra_env: Dict[str, Optional[str]], environ: Dict[str, str]
) -> Dict[str, str]:
    """The child's environment: `environ`, with `extra_env` applied over it.

    **A launcher removes a name by mapping it to None.** It cannot remove one by
    returning a pruned copy of `environ`, and this function exists as a separate,
    testable thing because that distinction was got wrong and the wrong version
    passed review. af3_jax's launcher pruned a copy; the supervisor then rebuilt
    the child's environment from `os.environ` and applied the pruned copy over
    it, so every name the launcher had removed came straight back. An operator
    with a stray `AF3_JAX_BOGUS` exported got a worker that exited 3 at
    `import alphafold3` -- exactly the failure the pruning existed to prevent.

    The check that missed it read `build_command`'s RETURN VALUE, which is the
    one place a pruned copy looks correct. A launcher's intent has to be
    expressed in something the supervisor acts on.
    """
    env = dict(environ)
    env.update({k: v for k, v in extra_env.items() if v is not None})
    for name in [k for k, v in extra_env.items() if v is None]:
        env.pop(name, None)
    return env


CommandBuilder = Callable[
    ["ResidentWorker"], Tuple[List[str], Dict[str, Optional[str]]]
]


@dataclass
class ResidentWorker:
    """One provider's model, held in a process of its own."""

    slug: str
    build_command: CommandBuilder
    # Cold start is weights plus CUDA plus, for some providers, a first-pass
    # kernel compile; minutes, not seconds.
    start_timeout_s: float = 900.0
    request_timeout_s: float = P.DEFAULT_REQUEST_TIMEOUT_S
    # 0 disables retirement: the worker holds the card until it is stopped.
    idle_timeout_s: float = 0.0
    vram_budget_gb: Optional[float] = None
    # Whether `ensure_started` consults `admission` before spending the budget.
    # True is the default because the alternative has wedged this host; a host
    # with its own scheduler above this one turns it off and owns the decision.
    admit: bool = True
    log_path: Optional[str] = None
    # The provider's manifest, so a command builder has the declaration it was
    # built from without a second load.
    manifest: Any = None

    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)
    _proc: Optional[subprocess.Popen] = field(default=None, repr=False)
    _log: Any = field(default=None, repr=False)
    _last_used: float = field(default=0.0, repr=False)
    _reaper: Optional[threading.Thread] = field(default=None, repr=False)
    _stopping: bool = field(default=False, repr=False)

    # ------------------------------------------------------------------ state
    @property
    def socket_path(self) -> str:
        return P.socket_path(self.slug)

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def ping(self) -> Optional[Dict[str, Any]]:
        """The worker's own answer, or None when nothing is listening."""
        try:
            return self._roundtrip({"op": P.OP_PING}, timeout=P.CONNECT_TIMEOUT_S)
        except (OSError, P.ProtocolError, WorkerRequestError):
            return None

    # ------------------------------------------------------------------ start
    def ensure_started(self) -> None:
        """Start the worker if it is not already serving. Holds :attr:`lock`.

        STARTING IS WHERE THE BUDGET IS SPENT, so it is where the budget is
        checked. `admission.room_for` adds up what is already held and reads the
        machine, and a refusal raises :class:`AdmissionRefused` rather than
        starting a worker the host cannot carry -- this project wedged the host
        once by starting one anyway, with the numbers available.

        `admit` is the escape hatch and it is an ATTRIBUTE, not an environment
        variable: a stray name in the environment is the class of mistake this
        module's siblings are full of, and a host that genuinely wants an
        unchecked start says so in the object it is holding.
        """
        with self.lock:
            if self.is_running() and os.path.exists(self.socket_path):
                return
            if self.is_running():
                # Process alive but no socket: it died between bind and now, or
                # is still coming up from an earlier call that timed out.
                self._terminate()
            # No declared budget means nothing is spent from the pool, and the
            # manifest layer already guarantees that reading: a resident provider
            # whose `[gpu] policy` is not "none" cannot load without a
            # `vram_budget_gb`. So None here is esm_if1's case -- CPU only -- and
            # admitting it is not a decision anyone needs to make.
            if self.admit and self.vram_budget_gb is not None:
                from . import admission

                admission.room_for(self.slug, self.vram_budget_gb).raise_if_refused()
            self._start()

    def _start(self) -> None:
        argv, extra_env = self.build_command(self)
        env = child_env(extra_env, os.environ)

        # A socket left by a previous process would be connected to and never
        # answer; the worker unlinks it too, but not if it was killed.
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

        if self.log_path:
            os.makedirs(os.path.dirname(self.log_path) or ".", exist_ok=True)
            self._log = open(self.log_path, "a", buffering=1)
            out = self._log
        else:
            out = subprocess.DEVNULL
        self._proc = subprocess.Popen(
            argv,
            env=env,
            stdout=out,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,  # a Ctrl-C to the MCP server is not the model's
        )

        deadline = time.time() + self.start_timeout_s
        while not os.path.exists(self.socket_path):
            rc = self._proc.poll()
            if rc is not None:
                where = self._transcript()
                # A named code per STANDARD section 8, said out loud: a
                # refusal has a cause an operator can act on and its last
                # stderr line names it, where an unnamed non-zero code is a
                # crash whose transcript has to be read.
                why = exit_hint(rc)
                raise WorkerStartError(
                    f"{self.slug}: the resident worker exited {rc} before it bound "
                    f"{self.socket_path}{where}{why}"
                )
            if time.time() > deadline:
                self._terminate()
                raise WorkerStartError(
                    f"{self.slug}: the resident worker did not bind {self.socket_path} "
                    f"within {self.start_timeout_s:.0f}s"
                )
            time.sleep(0.5)

        self._last_used = time.time()
        self._start_reaper()

    # ------------------------------------------------------------------- call
    def request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """One request, serialized against every other on this worker.

        A worker that dies answering is named rather than guessed at, in both
        of the shapes that takes. Usually it manages a last reply first --
        ``worker_base`` sends one for any ``SystemExit`` out of a prediction,
        which is how the kits' ``KernelsRefused`` arrives -- and then the only
        thing missing is what the worker could not know: where its transcript
        is, and what its exit code is called. Sometimes it cannot answer at
        all (``os._exit``, the OOM killer, a segfault), and then the socket
        just ends; a bare ``ProtocolError: peer closed the connection
        mid-message`` is true and useless, so the code it exited with goes in
        its place.
        """
        with self.lock:
            self.ensure_started()
            self._last_used = time.time()
            try:
                reply = self._roundtrip(payload, timeout=self.request_timeout_s)
            except (OSError, P.ProtocolError) as exc:
                raise self._died_mid_request(exc) from exc
            finally:
                self._last_used = time.time()
            if not reply.get("ok"):
                message = reply.get("error") or "the worker reported a failure"
                reason = reply.get("reason", "request_failed")
                if reason == "worker_exiting":
                    message = (
                        f"{self.slug}: {message}{self._transcript()}"
                        f"{exit_hint(reply.get('exit_code'))}"
                    )
                raise WorkerRequestError(message, reason=reason)
            return reply

    def _transcript(self) -> str:
        return f" (its transcript is in {self.log_path})" if self.log_path else ""

    def _died_mid_request(self, exc: BaseException) -> BaseException:
        """``exc``, or a better-named error when the worker is the reason.

        The wait is short and bounded and only ever runs on this path: a
        process that has just closed its socket is milliseconds from being
        reapable, but ``poll()`` asked immediately still answers None often
        enough to lose the code. A worker that is still alive -- a request
        that simply outran ``request_timeout_s``, say -- gets ``exc`` back
        unchanged, because then the socket failed and the worker did not.
        """
        if self._proc is None:
            return exc
        try:
            rc = self._proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            return exc
        return WorkerRequestError(
            f"{self.slug}: the resident worker exited {rc} during the request "
            f"without answering{self._transcript()}{exit_hint(rc)}",
            reason="worker_died",
        )

    def _roundtrip(self, payload: Dict[str, Any], *, timeout: float) -> Dict[str, Any]:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect(self.socket_path)
            P.send_line(sock, payload)
            return P.recv_line(sock, bytearray())
        finally:
            sock.close()

    # ------------------------------------------------------------------- stop
    def stop(self, *, grace_s: float = 30.0) -> None:
        """Ask the worker to exit, then make sure it did. Frees the device."""
        with self.lock:
            self._stopping = True
            try:
                if self.is_running() and os.path.exists(self.socket_path):
                    try:
                        self._roundtrip({"op": P.OP_SHUTDOWN}, timeout=grace_s)
                    except (OSError, P.ProtocolError):
                        pass  # it is going away either way
                if self._proc is not None:
                    try:
                        self._proc.wait(timeout=grace_s)
                    except subprocess.TimeoutExpired:
                        self._terminate()
            finally:
                self._stopping = False
                self._proc = None
                if self._log is not None:
                    self._log.close()
                    self._log = None
                if os.path.exists(self.socket_path):
                    try:
                        os.unlink(self.socket_path)
                    except OSError:
                        pass

    def _terminate(self) -> None:
        proc = self._proc
        if proc is None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=15)

    # ----------------------------------------------------------------- reaper
    def _start_reaper(self) -> None:
        if self.idle_timeout_s <= 0 or (self._reaper and self._reaper.is_alive()):
            return

        def run() -> None:
            while True:
                time.sleep(min(30.0, max(1.0, self.idle_timeout_s / 4)))
                if self._stopping or not self.is_running():
                    return
                idle = time.time() - self._last_used
                if idle < self.idle_timeout_s:
                    continue
                # A request in flight holds the lock for its whole duration, so
                # a non-blocking acquire is what distinguishes "idle" from
                # "busy for longer than the timeout".
                if not self.lock.acquire(blocking=False):
                    continue
                try:
                    if time.time() - self._last_used >= self.idle_timeout_s:
                        self.stop()
                        return
                finally:
                    self.lock.release()

        self._reaper = threading.Thread(
            target=run, name=f"resident-reaper-{self.slug}", daemon=True
        )
        self._reaper.start()
