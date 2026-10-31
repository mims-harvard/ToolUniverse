"""Carbon-X, held resident behind llama.cpp.

THE FIRST PROVIDER ON THIS STANDARD WHOSE MODEL IS NOT HELD BY THIS PROCESS.
Every other resident worker imports a Python stack, builds the model in its
own address space and reports ``torch.cuda.max_memory_reserved()``. This one
holds a **child process** -- upstream's own ``llama-server`` -- and talks to
it over a second Unix socket. The reasons are not stylistic:

* Carbon-X's DNA tokenizer is custom Python (``trust_remote_code=True``) for
  the Transformers path, and a GGUF runtime cannot load it. llama.cpp grew a
  native ``HybridDNATokenizer`` in **b11742**, which is the floor the vendor's
  own GGUF card states and the build this provider pins. Older builds load the
  file and tokenize DNA wrongly -- silently, which is the dangerous kind.
* The quantized weights are the point. bf16 is 29.7 GB; Q8_0 is 15.8 GB and
  the vendor's own re-run of FrontierVEP and NextBase puts it within one
  standard error of the unquantized model served by vLLM. On a shared card
  14 GB is 14 GB.
* There is no llama.cpp Python binding at b11742, and building one would mean
  compiling CUDA for ``sm_121`` from source. The published
  ``ubuntu-cuda-13.4-arm64`` tarball already ships an ``sm_121a`` cubin --
  checked with ``cuobjdump``, not assumed.

SO THE LIFETIME PROBLEM IS REAL AND IS SOLVED BY THE KERNEL. ``worker_base``'s
orphan watchdog ends a stranded worker with ``os._exit(0)``, which runs no
``atexit`` hook and no ``finally``. A child started the ordinary way would
survive that and go on holding 16 GiB that nothing can reach -- exactly the
failure the watchdog exists to prevent, reintroduced one process deeper. The
child is therefore started with ``PR_SET_PDEATHSIG(SIGKILL)``, so the kernel
kills it when this process dies by ANY means, signal and ``_exit`` included.
:func:`_spawn_engine` carries the detail.

WHAT RESIDENCY COLLECTS HERE. The model load measured **7 s** on the verified
card -- fast, because Q8_0 is mapped rather than converted -- but llama.cpp
also allocates the whole KV cache at load, so the 16.9 GiB footprint is paid
once per process rather than once per request. The larger saving is that a
per-request process would re-read 15.8 GB from disk every time; held, the
second request begins evaluating its prompt immediately.

THIS WORKER NEEDS NOTHING BUT THE STANDARD LIBRARY. There is no torch here,
so :func:`WB.serve` is called with ``release_cublas=False``: the cuBLAS
workspace release it does for everybody else imports torch, and there is no
torch in this environment to import. The CUDA context lives in the child,
where this process cannot reach it and does not pretend to.
"""

from __future__ import annotations

import argparse
import ctypes
import http.client
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="carbonx", help="provider slug, echoed in ping")
ap.add_argument("--gguf", required=True, help="path to the Q8_0 GGUF")
ap.add_argument("--engine", required=True, help="directory holding llama-server")
ap.add_argument(
    "--ctx",
    type=int,
    default=16384,
    help="llama-server context in tokens; the VRAM budget was measured at it",
)
ap.add_argument(
    "--max-input-tokens",
    type=int,
    default=12288,
    help="ceiling on the rendered prompt, counted by the engine's own tokenizer",
)
ap.add_argument(
    "--max-output-tokens",
    type=int,
    default=4096,
    help="ceiling on max_tokens per request",
)
args = ap.parse_args()

T0 = time.time()

MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_SEQUENCES = 16
MAX_NAME_LEN = 64

# IUPAC nucleotide codes. Carbon-X forms 6-mers from A/C/G/T only and turns any
# 6-mer containing another character into a single `<oov>` token, so ambiguity
# codes are accepted but cost resolution -- the tool's description says so.
_DNA = re.compile(r"^[ACGTURYSWKMBDHVN]+$")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._:+-]*$")


def _refuse(message: str) -> SystemExit:
    """A refusal exits 3, per STANDARD section 8; its message goes to stderr.

    ``raise SystemExit("text")`` would print the text and exit **1**, which the
    standard reserves for "failed" -- a distinction a caller branches on.
    """
    sys.stderr.write(str(message).rstrip("\n") + "\n")
    sys.stderr.flush()
    return SystemExit(3)


def say(msg: str) -> None:
    print(f"[carbonx-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds the engine's own
    environment and nothing of ToolUniverse, and importing the package would
    defeat that."""
    import importlib.util

    override = os.environ.get("TOOLUNIVERSE_REMOTE_WORKER_BASE")
    here = Path(__file__).resolve()
    path = (
        Path(override)
        if override
        else here.parents[3] / "remote_resident" / "worker_base.py"
    )
    if not path.is_file():
        raise _refuse(
            f"[carbonx-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()


# --------------------------------------------------------------------------
# the engine


class _EngineError(RuntimeError):
    """The engine answered, and what it said was a failure."""


class _EngineGone(SystemExit):
    """The engine process is gone, so this worker must not answer again.

    Exit **1** -- "failed" in STANDARD section 8 -- and not 3: nothing was
    refused, a child died. It is a ``SystemExit`` so that `serve` reads it as a
    verdict about the PROCESS rather than about the request, which is what
    `_fatal_reply` exists for: the caller is told by name, and then the worker
    exits instead of holding a queue it can no longer answer.

    THIS EXISTS BECAUSE THE WORKER HAD NO WAY TO SAY IT. Measured 2026-10-31:
    SIGKILL the llama-server child and the worker stays up with its socket
    bound, `ping` keeps answering `ready: True`, and every request after that
    fails in 0.0 s with `ConnectionRefusedError: [Errno 111] Connection
    refused` -- forever, because `_spawn_engine` runs once in `__main__` and
    nothing respawns it. The supervisor could not see it either: its
    `is_running()` polls the WORKER's pid, so it finds a live process and a
    bound socket and returns without rebuilding. `_ready()` did report
    `engine_alive: False`, to nobody -- that key had no reader in the repo.

    So recovery is not rebuilt here, it is HANDED to the path that already
    works. Killing the worker instead was measured in the same session: the
    supervisor rebuilt worker and engine and answered correctly in 8.7 s. This
    turns the death it cannot see into the death it can.
    """

    def __init__(self, reason: str):
        super().__init__(1)
        self.reason = reason


def _engine_gone_or(exc: OSError) -> BaseException:
    """``exc``, unless the engine is dead -- then the fatal verdict instead.

    The distinction is the whole point, because one
    ``ConnectionRefusedError`` means two opposite things. While the engine is
    STARTING, refused is the expected answer and `_spawn_engine` polls through
    it; making that fatal would turn a provider that is merely slow to load
    into a provider that reports itself broken. Once it has loaded, refused
    means the child is not there any more.

    ``load_s`` is the discriminator for that, because it is set exactly once,
    after ``/health`` first answers ok. "Has this engine ever been healthy" is
    therefore already recorded and nothing new has to be tracked to ask it.
    Before that moment startup owns the error, and its refusal exits 3.

    AFTER IT, THE SOCKET ITSELF IS THE EVIDENCE -- NOT ``poll()``. On an
    ``AF_UNIX`` socket ECONNREFUSED means no process is accepting on that path
    and ENOENT means the path is gone; neither can be a busy or slow engine,
    the way they could be over TCP. That matters because asking the child
    instead loses a race: measured 2026-10-31, the first request after a
    SIGKILL got ``poll() is None`` -- the child was killed but not yet reaped
    -- and so was reported as an ordinary ``request_failed``, and only the
    SECOND request saw ``exit -9`` and took the worker down. One death cost
    two failures. Reading the socket is race-free, and `poll()` is kept only
    for the OTHER errors: a timeout or a reset mid-request can mean a wedged
    but living engine, which is a failed request and not a verdict, unless the
    child is demonstrably gone.
    """
    proc = _ENGINE.get("proc")
    if _ENGINE.get("load_s") is None:
        return exc
    nobody_listening = isinstance(exc, (ConnectionRefusedError, FileNotFoundError))
    reaped = proc is not None and proc.poll() is not None
    if not (nobody_listening or reaped):
        return exc
    rc = proc.returncode if proc is not None else None
    how = f"exit {rc}" if rc is not None else f"not listening: {exc}"
    return _EngineGone(
        f"the llama-server child is gone ({how}); this worker cannot start "
        "another, so it exits and the supervisor rebuilds both"
    )


_ENGINE: dict = {"proc": None, "sock": None, "dir": None, "build": None, "load_s": None}

# PR_SET_PDEATHSIG from <linux/prctl.h>. Hard-coded because this worker has no
# third-party packages by design, and the constant has been 1 since 2.6.0.
_PR_SET_PDEATHSIG = 1


def _pdeathsig() -> None:
    """Ask the kernel to SIGKILL this child when its parent thread dies.

    THIS IS THE WHOLE ANSWER TO THE ORPHAN PROBLEM, and nothing in Python can
    substitute for it. ``worker_base``'s watchdog calls ``os._exit(0)``, which
    by design unwinds nothing: no ``atexit``, no ``finally``, no signal
    handler. A SIGKILL to this worker is the same. In both cases a child
    started without this call keeps the GPU, and the one thing the watchdog
    exists to guarantee -- that a stranded worker gives the card back -- would
    be false one process deeper than anybody looks.

    Set in the child between ``fork`` and ``exec``. It is keyed to the
    *thread* that forked, which is the main thread here; the engine is spawned
    before :func:`WB.serve` starts any other.
    """
    ctypes.CDLL("libc.so.6", use_errno=True).prctl(_PR_SET_PDEATHSIG, signal.SIGKILL)


class _UnixHTTP(http.client.HTTPConnection):
    """http.client over AF_UNIX. The engine listens on a socket, not a port."""

    def __init__(self, path: str, timeout: float):
        super().__init__("localhost", timeout=timeout)
        self._path = path

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self._path)


def _engine_call(method: str, route: str, body=None, timeout: float = 3600.0) -> dict:
    conn = _UnixHTTP(_ENGINE["sock"], timeout)
    try:
        payload = json.dumps(body).encode() if body is not None else None
        try:
            conn.request(method, route, payload, {"Content-Type": "application/json"})
            response = conn.getresponse()
            raw = response.read()
        except OSError as exc:
            # A socket error here is either an engine that has not come up yet
            # or one that is never coming back. `_engine_gone_or` is where that
            # is told apart, and why it has to be.
            raise _engine_gone_or(exc) from exc
        if response.status != 200:
            raise _EngineError(
                f"llama-server answered {response.status} on {route}: "
                f"{raw[:400].decode('utf-8', 'replace')}"
            )
        return json.loads(raw)
    finally:
        conn.close()


def _engine_get(route: str, timeout: float = 30.0) -> dict:
    return _engine_call("GET", route, None, timeout)


def _engine_post(route: str, body: dict, timeout: float = 3600.0) -> dict:
    return _engine_call("POST", route, body, timeout)


def _spawn_engine() -> None:
    """Start llama-server on its own Unix socket and wait until it is healthy.

    The socket goes in a private temporary directory rather than beside this
    worker's: ``sun_path`` is 108 bytes, the supervisor's socket path is
    already long, and appending to it is how that limit gets discovered in
    production rather than here.
    """
    engine_dir = Path(args.engine).resolve()
    server = engine_dir / "llama-server"
    if not server.is_file():
        raise _refuse(
            f"[carbonx-resident] no llama-server at {server} -- run "
            f"`tu remote setup carbonx`"
        )
    gguf = Path(args.gguf).resolve()
    if not gguf.is_file():
        raise _refuse(
            f"[carbonx-resident] no weights at {gguf} -- run "
            f"`tu remote setup carbonx`"
        )

    run_dir = Path(tempfile.mkdtemp(prefix="carbonx-"))
    sock = run_dir / "engine.sock"
    _ENGINE["dir"] = run_dir
    _ENGINE["sock"] = os.fspath(sock)

    argv = [
        os.fspath(server),
        "-m", os.fspath(gguf),
        "--host", os.fspath(sock),
        "-ngl", "99",
        "-c", str(args.ctx),
        # ONE SLOT, NOT FOUR. llama-server defaults to four request slots that
        # share `-c` between them, and `worker_base` already serialises: a
        # second slot could only hold a context no request will ever be given,
        # while every co-tenant pays for its KV cache.
        "-np", "1",
        "--jinja",
        "--chat-template-kwargs", '{"enable_thinking": false}',
        # Carbon-X's own defaults from generation_config.json, which are the
        # settings every published benchmark number was produced with.
        # llama.cpp's defaults differ (temp 0.8, top-k 40, min-p 0.05), so
        # leaving them unset would quietly evaluate a different model.
        "--temp", "0.6",
        "--top-p", "0.95",
        "--top-k", "20",
        "--min-p", "0",
        "--no-webui",
    ]
    env = dict(os.environ)
    # The backends are dlopened from beside the binary; a stray libggml on the
    # system path would otherwise win and be a build this provider has not
    # pinned.
    env["LD_LIBRARY_PATH"] = os.pathsep.join(
        [os.fspath(engine_dir)] + ([env["LD_LIBRARY_PATH"]] if env.get("LD_LIBRARY_PATH") else [])
    )
    # NOT in run_dir, which is removed on exit. The engine's own log is the
    # first thing anybody debugging this provider needs, and it is worth least
    # at exactly the moment a crash would delete it. It sits beside the
    # worker transcript the supervisor writes, which is where the README's
    # troubleshooting section sends a reader.
    log_dir = Path(
        os.environ.get("TOOLUNIVERSE_REMOTE_LOG_DIR")
        or Path.home() / ".cache" / "tooluniverse" / "remote-logs"
    )
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{args.slug}-engine.log"
        log = open(log_path, "wb")
    except OSError:
        log_path = run_dir / "llama-server.log"
        log = open(log_path, "wb")
    started = time.time()
    proc = subprocess.Popen(
        argv,
        stdout=log,
        stderr=subprocess.STDOUT,
        preexec_fn=_pdeathsig,  # noqa: PLW1509 - see _pdeathsig
        env=env,
    )
    _ENGINE["proc"] = proc

    deadline = started + 600.0
    while time.time() < deadline:
        if proc.poll() is not None:
            tail = log_path.read_text(errors="replace").splitlines()[-25:]
            raise _refuse(
                f"[carbonx-resident] llama-server exited {proc.returncode} "
                f"before becoming healthy:\n  " + "\n  ".join(tail)
            )
        try:
            if _engine_get("/health", timeout=5.0).get("status") == "ok":
                break
        except (OSError, _EngineError, ValueError):
            time.sleep(0.5)
    else:
        _stop_engine()
        raise _refuse("[carbonx-resident] llama-server never became healthy")

    _ENGINE["load_s"] = round(time.time() - started, 1)
    props = _engine_get("/props", timeout=30.0)
    _ENGINE["build"] = props.get("build_info")
    _ENGINE["n_ctx"] = props.get("default_generation_settings", {}).get(
        "n_ctx", args.ctx
    )


def _engine_device_gib() -> float:
    """What the driver says the engine process holds on the card, or 0.0.

    THE ONLY FOOTPRINT READING AVAILABLE TO A WORKER WITH NO TORCH, and the
    sibling providers' `torch.cuda.max_memory_reserved()` is not a thing this
    process could call even if it wanted to: the CUDA context belongs to the
    child. `nvidia-smi --query-compute-apps` reports per-process device memory
    and does so on this card, where `--query-gpu=memory.used` returns N/A
    because the pool is unified with system RAM.

    IT IS A DIFFERENT KIND OF NUMBER FROM A TORCH PROVIDER'S, in two ways a
    reader has to know. It is the driver's view of one process rather than an
    allocator's high-water mark, so it includes the CUDA context and excludes
    nothing. And it is not a *peak*: llama.cpp allocates weights, KV cache and
    compute buffers when the model loads and does not grow, which is why a
    point-in-time reading is the whole story here and would be meaningless on
    a provider whose allocator ratchets. The provider's declared budget is
    larger again, because it was measured as a whole-pool delta.

    Never fatal. A host without `nvidia-smi`, or one that reports `[N/A]`,
    gets 0.0 and a reply with one field less.
    """
    proc = _ENGINE.get("proc")
    if proc is None:
        return 0.0
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                "--query-compute-apps=pid,used_memory",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return 0.0
    for line in (out.stdout or "").splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 2 and parts[0] == str(proc.pid):
            try:
                return round(int(parts[1]) / 1024, 2)
            except ValueError:
                return 0.0
    return 0.0


def _stop_engine() -> None:
    proc = _ENGINE.get("proc")
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
    run_dir = _ENGINE.get("dir")
    if run_dir is not None:
        shutil.rmtree(run_dir, ignore_errors=True)


# --------------------------------------------------------------------------
# one request


def _document(req: dict) -> dict:
    """The request document, which arrives as JSON text under ``input``.

    Both paths into this worker build the same thing: the MCP tool composes a
    document and sends ``json.dumps`` of it, and the smoke file IS one. A
    shape that only the smoke exercises is a shape that has not been tested.
    """
    raw = req.get("input")
    if raw is None:
        raise ValueError("the request has no 'input'.")
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        raise ValueError("'input' must be a JSON document or a string holding one.")
    if len(raw.encode()) > MAX_INPUT_BYTES:
        raise ValueError(
            f"'input' is {len(raw.encode())} bytes; the ceiling is "
            f"{MAX_INPUT_BYTES}. Carbon-X reads sequences, it does not index "
            f"genomes."
        )
    try:
        document = json.loads(raw)
    except ValueError as exc:
        raise ValueError(f"'input' is not valid JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError("'input' must be a JSON object.")
    return document


def _prompt(document: dict) -> tuple:
    """``(prompt text, cleaned sequences)``, validated.

    The assembly is upstream's ``ask``: context first if there is one, then
    the question, then one ``name: <dna>...</dna>`` line per sequence. Keeping
    it identical matters because every benchmark number on the model card was
    produced with the sequence and the question in one user message.
    """
    question = document.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("'question' must be a non-empty string.")

    sequences = document.get("sequences")
    if not isinstance(sequences, dict) or not sequences:
        raise ValueError(
            "'sequences' must be a non-empty object of name -> DNA. This tool "
            "answers questions about DNA you supply; it is not a general chat "
            "endpoint."
        )
    if len(sequences) > MAX_SEQUENCES:
        raise ValueError(
            f"'sequences' has {len(sequences)} entries; the ceiling is "
            f"{MAX_SEQUENCES}."
        )

    cleaned = {}
    for name, dna in sequences.items():
        if not isinstance(name, str) or not _NAME.match(name) or len(name) > MAX_NAME_LEN:
            raise ValueError(
                f"sequence name {name!r} must be 1-{MAX_NAME_LEN} characters of "
                f"letters, digits, spaces and ._:+- , starting alphanumeric."
            )
        if not isinstance(dna, str):
            raise ValueError(f"sequence {name!r} must be a string.")
        bases = "".join(dna.split()).upper()
        if not bases:
            raise ValueError(f"sequence {name!r} is empty.")
        if not _DNA.match(bases):
            bad = sorted(set(bases) - set("ACGTURYSWKMBDHVN"))
            raise ValueError(
                f"sequence {name!r} contains {', '.join(bad)}, which are not "
                f"IUPAC nucleotide codes. Carbon-X reads DNA; it does not read "
                f"protein."
            )
        cleaned[name] = bases

    context = document.get("context") or ""
    if not isinstance(context, str):
        raise ValueError("'context' must be a string.")

    parts = ([context.strip()] if context.strip() else []) + [question.strip()]
    parts += [f"{name}: <dna>{dna}</dna>" for name, dna in cleaned.items()]
    return "\n\n".join(parts), cleaned


def _count_prompt_tokens(messages: list) -> int:
    """The rendered prompt's length, counted by the engine's own tokenizer.

    COUNTED, NOT ESTIMATED, AND NOT COUNTED ON THE OTHER SIDE. The arithmetic
    that looks like a substitute -- one token per six bases -- is right only
    for canonical A/C/G/T; an ambiguity code collapses a whole 6-mer into one
    `<oov>`, the English half of the prompt is BPE, and the chat template adds
    tokens of its own. The engine renders the template through
    ``/apply-template`` and tokenizes the result, so the number refused on is
    the number that would have been evaluated.
    """
    rendered = _engine_post("/apply-template", {"messages": messages}, timeout=60.0)
    prompt = rendered.get("prompt")
    if not isinstance(prompt, str):
        raise _EngineError("/apply-template did not return a prompt")
    tokens = _engine_post("/tokenize", {"content": prompt}, timeout=120.0)
    return len(tokens.get("tokens") or [])


def _ask(req: dict) -> dict:
    document = _document(req)
    prompt, sequences = _prompt(document)

    max_tokens = document.get("max_tokens", 1024)
    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool):
        raise ValueError("'max_tokens' must be an integer.")
    if not 1 <= max_tokens <= args.max_output_tokens:
        raise ValueError(
            f"'max_tokens' is {max_tokens}; it must be between 1 and "
            f"{args.max_output_tokens}."
        )

    seed = document.get("seed")
    if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool)):
        raise ValueError("'seed' must be an integer.")

    messages = [{"role": "user", "content": prompt}]
    prompt_tokens = _count_prompt_tokens(messages)
    budget = min(args.max_input_tokens, args.ctx - max_tokens)
    if prompt_tokens > budget:
        raise ValueError(
            f"the prompt is {prompt_tokens} tokens and the ceiling here is "
            f"{budget} (context {args.ctx}, max_tokens {max_tokens}, provider "
            f"ceiling {args.max_input_tokens}). Carbon-X was mid-trained at "
            f"8,192 tokens and post-trained below 16k, and upstream has not "
            f"evaluated inputs much longer. Send a shorter window around the "
            f"site you are asking about."
        )

    body = {
        "messages": messages,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    if seed is not None:
        body["seed"] = seed

    started = time.time()
    reply = _engine_post("/v1/chat/completions", body)
    elapsed = time.time() - started

    choice = (reply.get("choices") or [{}])[0]
    answer = (choice.get("message") or {}).get("content")
    if not isinstance(answer, str):
        raise _EngineError(f"the engine returned no message content: {reply}")
    usage = reply.get("usage") or {}
    timings = reply.get("timings") or {}
    device_gib = _engine_device_gib()

    return {
        "model": "HuggingFaceBio/Carbon-X-GGUF:Q8_0",
        "answer": answer,
        # A truncated answer is the one failure that looks like success, so it
        # is a field rather than something a caller has to infer from a length.
        "truncated": choice.get("finish_reason") == "length",
        "sequences": {name: len(dna) for name, dna in sequences.items()},
        "prompt_tokens": usage.get("prompt_tokens", prompt_tokens),
        "completion_tokens": usage.get("completion_tokens"),
        "seed": seed,
        "max_tokens": max_tokens,
        "timing": {
            "total_s": round(elapsed, 2),
            "prompt_eval_per_s": round(timings.get("prompt_per_second") or 0.0, 1),
            "generate_per_s": round(timings.get("predicted_per_second") or 0.0, 1),
        },
        "weights_held_by": "worker:carbonx (llama-server child)",
        # Reported under the name every other provider uses so that
        # `tu remote setup`'s measured record is not empty for this one, and
        # named again as what it actually is. :func:`_engine_device_gib`
        # carries the two ways it differs from a torch provider's figure.
        "peak_reserved_gib": device_gib or None,
        "engine_device_gib": device_gib or None,
    }


def _ready() -> dict:
    proc = _ENGINE.get("proc")
    return {
        "build_s": round(time.time() - T0, 1),
        "model": "HuggingFaceBio/Carbon-X-GGUF:Q8_0",
        "engine": _ENGINE.get("build"),
        "engine_pid": proc.pid if proc else None,
        # DIAGNOSTIC, NOT A GATE, and it was mistaken for one. Nothing reads
        # this key -- it reported `false` at a provider that was refusing
        # every request and no caller noticed, because there is no caller.
        # An engine death is handled where it is detected instead: see
        # `_EngineGone`. Left in because an operator reading a ping wants it.
        "engine_alive": bool(proc and proc.poll() is None),
        "engine_load_s": _ENGINE.get("load_s"),
        "n_ctx": _ENGINE.get("n_ctx"),
        "max_input_tokens": args.max_input_tokens,
        "max_output_tokens": args.max_output_tokens,
        "weights_held_by": "worker:carbonx (llama-server child)",
        "kit": None,
    }


if __name__ == "__main__":
    _spawn_engine()
    say(
        f"ready t={time.time() - T0:.1f}s engine={_ENGINE['build']} "
        f"load={_ENGINE['load_s']}s ctx={_ENGINE.get('n_ctx')} "
        f"limits={args.max_input_tokens}in/{args.max_output_tokens}out "
        f"(no optimization kit: the engine is upstream's llama.cpp)"
    )
    try:
        sys.exit(
            WB.serve(
                slug=args.slug,
                socket_path=args.socket,
                on_predict=_ask,
                ready=_ready,
                log=say,
                # No torch in this environment, and the CUDA context is the
                # child's. There is nothing here to release.
                release_cublas=False,
            )
        )
    finally:
        # Covers the ordinary exits -- a shutdown request, a signal that
        # Python handles, an exception. It deliberately does NOT cover
        # `os._exit(0)` or SIGKILL; PR_SET_PDEATHSIG does, and is the only
        # thing that can.
        _stop_engine()
