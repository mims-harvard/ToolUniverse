"""AtlasFold held resident on the GPU, answering one request at a time.

Run by the model's own interpreter with the kit's mode variable in the
environment::

    ATLASFOLD_OPT=big MODEL_OPT_LEVERS_OFF=atom_sdpa \
        <model python> atlasfold_resident_worker.py --socket … --slug …

WHY HOLDING MATTERS HERE, AND WHAT IT HOLDS. Stock AtlasFold has no object that
survives a prediction: ``atlasfold.cli.monomer.run`` defines a nested
``load_model`` and calls it *inside* the run, so every invocation reads
6,128,042,331 bytes of AtlasLM-3B plus an 859,549,307-byte folding head off disk
and puts both on the card before the first residue is folded. The kit's own
README prices the per-run overhead at "≈11 s start-up and model load: ≈15 s per
Run example", and on top of that the first call of a kit mode compiles its
Triton/NVRTC kernels and runs the shared core's one-time numerical self-check of
its fused kernels. This worker pays all of it once.

**Who holds the weights: this worker.** That is a decision and not a detail, and
the kit is why it is safe. Under a kit mode the kits usually replace the
upstream loader and refuse to activate if anything replaced it first, so a
worker that memoises the load silently turns the whole kit off -- Chai-1's
provider is the cautionary case. Not here: ``atlasfold_opt.registry.LEVERS`` has
no site anywhere on ``atlasfold.pretrained``, and ``atlasfold.pretrained`` is
only a *trigger* for activation, never a patch target. So nothing of the kit
owns the load, upstream does not memoise it itself, and this worker therefore
wraps ``atlasfold.pretrained.load_model`` with a one-entry cache -- installed
AFTER the kit has activated, so it wraps whatever the kit left there rather than
racing it. Every reply and the ready line say ``weights_held_by: "worker"``.

**One model at a time, on purpose.** The monomer and multimer heads are separate
``AtlasFold`` / ``AtlasFold_Multimer`` instances and each carries its OWN copy of
the 6.1 GiB language model, so holding both would roughly double the footprint
for a capability most deployments use one half of. The cache therefore holds
exactly one: a request for the other model type drops the first, calls
``torch.cuda.empty_cache()`` and loads the second, which costs one model load and
is reported as ``model_switch`` in the reply. ``TOOLUNIVERSE_ATLASFOLD_PRELOAD``
(``monomer`` | ``multimer`` | ``none``, default ``monomer``) decides which one the
build loads, so a multimer-only deployment does not pay for a monomer load it
will immediately throw away.

TRITON 3.3.1 CANNOT EMIT CODE FOR THIS CARD, AND THAT SHAPES EVERYTHING BELOW.
The first smoke on a GB10 (cc 12.1) died like this, after a clean activation and
a model load, at ``Starting monomer inference``::

    'sm_121a' is not a recognized processor for this target (ignoring processor)   [x12]
    LLVM ERROR: Cannot select: intrinsic %llvm.nvvm.shfl.sync.bfly.i32

and the process aborted, which the supervisor reported as
``smoke_protocolerror -- peer closed the connection mid-message``: the worker
died without speaking, because ``abort()`` is not an exception.

The cause is not the kit. ``triton==3.3.1``, which the kit's lock pins beside
torch 2.7.1+cu128, carries an LLVM that does not know ``sm_121a``. It ignores
the processor, falls back to a default subtarget, and then cannot lower the
warp shuffle that every block reduction emits. Measured on this machine, same
kernel, same card: triton 3.3.1 aborts; 3.6.0 and 3.7.1 run it. A newer
``ptxas`` does NOT help, because the failure is upstream of ptxas -- a one-add
kernel (no shuffle) reaches ptxas and fails there, and pointing Triton at a CUDA
12.9 ``ptxas`` fixes that one and leaves the shuffle abort untouched.
``TRITON_OVERRIDE_ARCH`` does not help either: it reaches ``options.arch`` but
the target string LLVM complains about comes from the MLIR module, and forcing
``sm_120a`` or even ``sm_90a`` through ``sm_arch_from_capability`` leaves the
abort in place.

Two consequences, and the second one is the surprising one:

1. **Every Triton-backed lever of the kit has to come off** -- ``TRITON_LEVERS``
   below, declared in ``[kit] levers_off``. Which ones those are was measured,
   not guessed, by trapping ``JITFunction.run`` during a fold.

2. **Upstream's own default triangle backend has to come off too.**
   ``atlasfold.utils.kernel.cuequiv_available`` resolves ``--kernel auto`` to
   ``cuequiv`` whenever ``cuequivariance_torch`` merely imports -- and
   cuEquivariance 0.10.0 ships its own Triton kernels. Measured: STOCK AtlasFold,
   no kit word at all, folds 35 residues under ``--kernel auto`` and ABORTS at
   200, 400, 500 and 600 on
   ``cuequivariance_ops.triton.fused_layer_norm_triton:layer_norm_transpose_forward_kernel``.
   So on this card the pinned stack cannot fold anything of a useful size even
   with the kit switched off entirely. ``--kernel torch`` folds all of them.

That is why the backend is chosen by a probe in ``_build`` rather than written
down: on a host whose Triton knows its card, ``auto`` is upstream's default and
the faster path, and nothing here should force it away. The probe runs in a
CHILD process because the answer it is looking for is an abort.

And it is why the worker REFUSES TO START when the probe fails while a
Triton-backed lever is still in the kit's row. An LLVM abort cannot be caught,
so the only place to put the decision is before the first compile; a named
refusal at start-up is the difference between "this provider is misconfigured
for this host" and a worker that dies mid-request on the first input long enough
to reach a size gate. Which is the real trap here: every one of those kernel
levers is gated at 512 tokens, so a 35-residue smoke exercises NONE of them. A
smaller ablation list passes the smoke and aborts on the first real request.

THE ORDER OF THE FIRST SIX LINES OF ``_build`` IS LOAD-BEARING. Each one is
there because something fails without it:

1. ``import torch`` FIRST. The kit's own ``stack.WARM_LIBRARIES`` puts torch
   first and says why: "a cu13 ops wheel imported before torch fails to load
   libnvrtc and the ops stay unavailable for the process".

2. ``_preload_nvrtc()``. ``nvidia-cuda-nvrtc-cu12`` puts ``libnvrtc.so.12``
   inside site-packages and torch 2.7.1 does not preload it, so
   ``cuequivariance_ops``'s ``libcue_ops.so`` dlopens it by soname and fails::

     Error while loading libcue_ops.so: libnvrtc.so.12: cannot open shared
     object file: No such file or directory

   This is not cosmetic and it is not caught by upstream's own availability
   test. ``atlasfold.utils.kernel.cuequiv_available`` checks only
   ``importlib.util.find_spec("cuequivariance_torch")``, which succeeds, so
   ``--kernel auto`` selects ``cuequiv`` regardless -- and the first triangle
   attention then raises ``ImportError: Error importing triangle_attention from
   cuequivariance_ops_torch``. Measured both ways on this host: without the
   preload that call raises, with it the call reaches the kernel's own operand
   validation. The file is located through ``nvidia.__file__``, so no path is
   written down here.

3. ``atlasfold_opt.cli.jit_env()``. The kit's own function, which keys the
   first-use compile caches by the running stack under ``$MODEL_OPT_JIT_ROOT``
   (which the launcher sets) and exports ``TRITON_CACHE_DIR`` and friends into
   this process. It has to run before anything compiles, because Triton reads
   its cache directory at its first compile. ``run.sh`` gets this from
   ``cli.cmd_pred``; a worker the launcher starts directly has to ask for it.

4. ``import atlasfold.model``. This is what ARMS the kit: the ``.pth``'s
   meta-path finder fires on the first import of the model family and calls
   ``atlasfold_opt.enable(word)`` before the module body runs. The ACTIVE line
   lands on stderr here, and it is the only proof that the mode engaged.
   Nothing may build an ``AtlasFold`` before this point -- the kit's own
   ``late_activation`` gate refuses with "N AtlasFold instance(s) already built
   (enable() before load_model)".

5. ``phase_timing.install()``. The kit's per-item PHASE / PEAK lines around the
   trunk, sampler and confidence passes. Timing only, no computed value
   touched; ``cli.cmd_pred`` installs it and this worker does the same so the
   transcript of a resident run reads like the transcript of a ``run.sh`` run.

6. The ``load_model`` memo, and only then the preload.

WHAT THIS WORKER DELIBERATELY DOES *NOT* DO.

* **It does not go through ``atlasfold_opt.cli.cmd_pred``.** That function would
  give the kit's own OUTPUTS / FINAL accounting for free, but it also catches
  every exception the fold raises, prints ``RUN raised <Type>: <first 400
  chars>`` to stderr and returns an integer. A resident provider has to hand the
  caller upstream's own account of a failure, so this worker calls
  ``atlasfold.cli.{monomer,multimer}.run`` directly, lets the exception
  propagate, and reproduces the three things ``cmd_pred`` adds that matter: the
  weights injection (``--model-path`` / ``--lm-path`` from the weights root),
  the completion count (one ``done.txt`` per FASTA record) and the kit's gate
  census (``stack.gates_verdict()``), which it reports per request instead of
  folding into an exit code.

* **It never passes ``--gpu-ids``, and refuses a request that asks for it.**
  That flag makes ``atlasfold.cli.multigpu`` ``torch.multiprocessing.spawn`` one
  interpreter per id -- on a one-GPU box included -- each of which loads the
  model again. Spawning model-sized children out of a process that already owns
  the card is the fork hazard with a different start method, and a resident
  worker has nothing to gain from it.

* **It does not set ``num_workers``, because there is none to set.** This is the
  one place this provider diverges from the standard's unconditional rule, and
  it was checked rather than assumed: ``torch.utils.data.DataLoader`` appears
  nowhere under ``stock/src/src/atlasfold/`` except
  ``train/{monomer,multimer}/datamodule.py``, which inference never imports.
  ``monomer.run`` iterates ``FoldingRunner.fold_iter_batch`` on the calling
  thread. The kit's ``output_overlap`` lever *does* start one child process, and
  it does it correctly -- a ``multiprocessing`` SPAWN-context process with
  ``CUDA_VISIBLE_DEVICES=""`` and the kit word removed, which nulls
  ``__main__.__spec__`` and deletes ``__main__.__file__`` for the instant of the
  spawn so this script is not re-run as ``__mp_main__``. It is left alone.

* **It writes a fresh FASTA and uses the request's own output directory, and
  passes ``--overwrite``.** Upstream skips any target whose
  ``<out_dir>/<name>/done.txt`` exists and logs "All targets are complete.
  Nothing to do." A caller who reuses a directory would otherwise get a
  successful reply and no new structure -- the same false pass
  ``[runtime] outputs`` exists to catch, arriving through the back door.

* **It raises when it produced no structure.** ``write_outputs`` writes the
  mmCIF first and touches ``done.txt`` last, so a target that produced nothing
  leaves neither; the reply never has to be read to discover that.
"""

from __future__ import annotations

import argparse
import ctypes
import glob
import json
import os
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="atlasfold", help="provider slug, echoed in ping")
args = ap.parse_args()

T0 = time.time()


def _refuse(message: str) -> SystemExit:
    """A refusal exits 3, per STANDARD section 8; its message goes to stderr.

    `raise SystemExit("text")` would print the text and exit **1**, which the
    standard reserves for "failed" -- a distinction a caller branches on, and
    the whole point of a named refusal is that a caller can.
    """
    sys.stderr.write(str(message).rstrip("\n") + "\n")
    sys.stderr.flush()
    return SystemExit(3)


def say(msg: str) -> None:
    print(f"[atlasfold-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds AtlasFold's pinned stack
    and nothing of ToolUniverse, and importing the package would defeat that."""
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
            f"[atlasfold-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

# The kit's mode, as the launcher set it from [kit] mode. "off" is this kit's
# documented default and cannot be served resident at all -- under it the kit
# runs the stock CLI in a clean subprocess by construction -- so the worker says
# so rather than silently holding a model the kit will not touch.
MODE = (os.environ.get("ATLASFOLD_OPT") or "off").strip().lower()
LEVERS_OFF = os.environ.get("MODEL_OPT_LEVERS_OFF") or ""
WEIGHTS_ROOT = os.environ.get("ATLASFOLD_WEIGHTS_DIR") or ""
PRELOAD = (
    (os.environ.get("TOOLUNIVERSE_ATLASFOLD_PRELOAD") or "monomer").strip().lower()
)

MODEL_TYPES = ("monomer", "multimer")
# Every lever of this kit whose cell compiles a TRITON kernel, as measured on
# this machine by trapping `triton.runtime.jit.JITFunction.run` during a fold
# and reading which modules reached it. See the module docstring: on a host
# whose Triton cannot emit code for the card, each of these aborts the PROCESS
# (LLVM, not a Python exception), so the decision has to be made before the
# first compile and the worker refuses rather than starts.
#
# OBSERVED reaching Triton in a 35-residue fold under mode=big:
#   trimul_v4         opt_core.kernels.fpf_trimul.kernels:_k_ln_rows
#   flash_triattn     flash_triattn:_bias_prep, flash_triattn_k2:_bias_prep,
#                     triatt_k2b:_bias_prep
#   pair_transition   opt_core.kernels.fpf_transition_v2.kernel:_pair_transition_kernel
#   transition_exact  fpf_transition.transition:_fused_transition_kernel
#   exactln           opt_core.kernels.ln_proj:_ln_rows_kernel,
#                     opt_core.kernels.lnl_fused:_fused_transition_kernel
#   atom_rows         opt_core.kernels.dtk_kernels:_ln_mod_kernel
# ALSO LISTED, because their cells are the same Triton families behind a
# 512-token size gate that a 35-residue smoke does not reach -- and a lever that
# compiles only above the smoke's length is the worst kind to leave in:
#   triattn_exact triatt_block triatt_block_exact triattn_core
#   pair_block_residual dit_apb
TRITON_LEVERS = frozenset(
    {
        "trimul_v4",
        "flash_triattn",
        "triattn_exact",
        "triatt_block_exact",
        "triatt_block",
        "triattn_core",
        "transition_exact",
        "pair_transition",
        "pair_block_residual",
        "exactln",
        "dit_apb",
        "atom_rows",
    }
)

# The smallest Triton kernel that needs a warp shuffle: `tl.sum` over a block
# lowers to llvm.nvvm.shfl.sync.bfly.i32, which is the intrinsic a Triton whose
# LLVM does not know this card's target cannot select. Run in a SUBPROCESS,
# because the failure is `LLVM ERROR: ...` followed by abort(), which no
# try/except in this process could survive.
_TRITON_PROBE_SRC = """
import torch, triton, triton.language as tl

@triton.jit
def _reduce(X, Y, BLOCK: tl.constexpr):
    off = tl.arange(0, BLOCK)
    tl.store(Y, tl.sum(tl.load(X + off), axis=0))

x = torch.ones(256, device="cuda")
y = torch.zeros(1, device="cuda")
_reduce[(1,)](x, y, BLOCK=256)
torch.cuda.synchronize()
assert abs(float(y[0]) - 256.0) < 1e-3, float(y[0])
print("TRITON_SHUFFLE_OK")
"""
# Upstream's own repository names, from atlasfold.pretrained.MODEL_NAME_MAP.
MODEL_NAMES = {"monomer": "atlasfold-260703", "multimer": "atlasfold-m-260725"}
# The request options this worker forwards to upstream's parser, each with the
# stock flag it becomes. Nothing else reaches the stock command line, and the
# values upstream defaults to are left alone: PINS.json records them as the
# stock contract (monomer 4 recycles / 5 samples / 20-30-100 steps by length;
# multimer 10 recycles / 5 samples / 200 steps) and the kit "changes no run
# setting".
OPTION_FLAGS = {
    "num_samples": "--num-samples",
    "num_recycles": "--num-recycles",
    "num_steps": "--num-steps",
    "mlm_prob": "--mlm-prob",
    "max_tokens_per_batch": "--max-tokens-per-batch",
}

STATE: dict = {"model": None, "model_type": None, "load_s": None, "loads": 0}
# The stock `--kernel` word this worker will pass, decided in _build() from
# the Triton probe. A one-element list so _argv_for can read it without a
# global statement.
KERNEL_BACKEND = ["auto"]
# Filled by _build() under __main__; declared here so the ready line's reader
# does not depend on import order.
FACTS: dict = {}
BUILD_S: float = 0.0


# --------------------------------------------------------------------- build
def _triton_can_compile_shuffle() -> tuple:
    """``(ok, detail)``: can this interpreter's Triton emit a warp-shuffle kernel
    for this card?

    Run as a child process on purpose. A Triton whose bundled LLVM does not know
    the device's target does not raise -- it prints
    ``'sm_<cc>a' is not a recognized processor for this target``, falls back to a
    default subtarget, and then calls ``abort()`` with ``LLVM ERROR: Cannot
    select: intrinsic %llvm.nvvm.shfl.sync.bfly.i32``. There is no exception to
    catch and no state to recover, so the only way to ask the question safely is
    to ask it somewhere that is allowed to die.
    """
    import subprocess
    import tempfile

    # A FILE, not `python -c`: @triton.jit reads its own body with
    # inspect.getsource, and a kernel defined in a -c string fails with
    # `OSError: could not get source code` -- which looks exactly like the
    # answer being sought and is not it. (Measured: this is what the first
    # version of this probe reported, and it was right by accident.)
    try:
        with tempfile.NamedTemporaryFile(
            "w", suffix="_atlasfold_triton_probe.py", delete=False
        ) as fh:
            fh.write(_TRITON_PROBE_SRC)
            probe_path = fh.name
    except OSError as exc:
        return False, f"probe-unwritable:{type(exc).__name__}"
    try:
        proc = subprocess.run(
            [sys.executable, probe_path],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"probe-failed:{type(exc).__name__}"
    finally:
        try:
            os.unlink(probe_path)
        except OSError:
            pass
    if "TRITON_SHUFFLE_OK" in (proc.stdout or ""):
        return True, "ok"
    blob = (proc.stderr or "") + (proc.stdout or "")
    for marker in (
        "LLVM ERROR",
        "not a recognized processor",
        "ptxas fatal",
        "PTXASError",
    ):
        if marker in blob:
            line = next(ln for ln in blob.splitlines() if marker in ln)
            return False, f"rc={proc.returncode}: {line.strip()[:160]}"
    return (
        False,
        f"rc={proc.returncode}: {(blob.strip().splitlines() or ['no output'])[-1][:160]}",
    )


def _preload_nvrtc() -> str:
    """Make ``libnvrtc.so.12`` loadable for ``libcue_ops.so``; see the module
    docstring. Returns a word for the ready line, never raises."""
    try:
        import nvidia
    except Exception as exc:  # noqa: BLE001
        return f"absent:{type(exc).__name__}"
    pattern = os.path.join(
        os.path.dirname(nvidia.__file__), "cuda_nvrtc", "lib", "libnvrtc.so*"
    )
    found = sorted(
        p for p in glob.glob(pattern) if "builtins" not in os.path.basename(p)
    )
    if not found:
        return "absent:no-wheel"
    for path in found:
        try:
            ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)
        except OSError as exc:
            return f"failed:{exc}"[:120]
        return os.path.basename(path)
    return "absent"


def _weights_paths() -> dict:
    """``{lm, monomer, multimer}`` absolute checkpoint paths under the weights
    root, resolved by the KIT's own function so the layout is never restated."""
    from atlasfold_opt import weights as W

    root = W.weights_dir(WEIGHTS_ROOT or None)
    if not root:
        raise _refuse(
            "[atlasfold-resident] no weights root: ATLASFOLD_WEIGHTS_DIR is unset "
            "(the launcher exports it from [weights] root_env)"
        )
    paths = W.paths(root)
    missing = [p for p in paths.values() if not os.path.isfile(p)]
    if missing:
        raise _refuse(
            "[atlasfold-resident] weights absent under "
            f"{root}: {missing} — run `tu remote setup atlasfold`"
        )
    return paths


def _install_load_memo():
    """Wrap ``atlasfold.pretrained.load_model`` with a one-entry cache.

    Installed after the kit has activated, so it wraps whatever the kit left on
    that attribute. Nothing in this kit patches it -- checked against
    ``registry.LEVERS`` -- so there is no route being taken over here, only a
    load being paid once instead of once per request.
    """
    import atlasfold.pretrained as P

    stock = getattr(P.load_model, "__wrapped_stock__", None) or P.load_model

    def load_model(model_name=P.ATLASFOLD_260703, device="cpu", **kw):
        name = P.get_model_name(model_name)
        kind = "multimer" if name == P.ATLASFOLD_M_260725 else "monomer"
        if STATE["model_type"] == kind and STATE["model"] is not None:
            # A HELD MODEL STILL HAS TO HONOUR THE REQUESTED BACKEND. Upstream
            # resolves `--kernel` inside the load it no longer performs, so a
            # memo that keys on the model alone silently keeps whatever backend
            # the FIRST load chose. That cost one acceptance run: the ready line
            # said `kernel=torch`, the fold logged `Using triangle kernel
            # backend: cuequiv`, and the process aborted in cuEquivariance's
            # Triton LayerNorm. `set_kernel_backend` is upstream's own setter and
            # is idempotent.
            want = kw.get("kernel", "auto")
            model = STATE["model"]
            if getattr(model, "kernel_backend", None) != want:
                try:
                    model.set_kernel_backend(want)
                except Exception as exc:  # noqa: BLE001
                    say(f"set_kernel_backend({want!r}) failed: {type(exc).__name__}")
            return model
        if STATE["model"] is not None:
            # One head at a time: each carries its own copy of the 6.1 GiB
            # language model, so the other one is dropped rather than kept.
            say(
                f"model switch {STATE['model_type']} -> {kind}: dropping the held model"
            )
            STATE["model"] = None
            STATE["model_type"] = None
            _torch().cuda.empty_cache()
        t = time.time()
        model = stock(model_name, device, **kw)
        STATE["model"] = model
        STATE["model_type"] = kind
        STATE["load_s"] = round(time.time() - t, 1)
        STATE["loads"] += 1
        say(f"{kind} model loaded in {STATE['load_s']}s (load #{STATE['loads']})")
        return model

    load_model.__wrapped_stock__ = stock
    load_model.__qualname__ = "load_model[tooluniverse:atlasfold-resident:memo]"
    P.load_model = load_model


def _torch():
    import torch

    return torch


def _build() -> dict:
    """Everything that is identical for every request. Order matters; see the
    module docstring."""
    facts: dict = {}
    import torch  # (1) before cuEquivariance, as the kit's own warm list requires

    facts["nvrtc"] = _preload_nvrtc()  # (2)
    say(f"libnvrtc preload: {facts['nvrtc']}")

    if MODE not in ("exact", "fast", "big"):
        raise _refuse(
            f"[atlasfold-resident] ATLASFOLD_OPT={MODE!r} cannot be served "
            f"resident. This kit's `off` runs the stock CLI in a clean "
            f"subprocess by construction (atlasfold_opt.stock_pred), which is a "
            f"fresh process per prediction — the opposite of holding the model. "
            f"Set [kit] mode to exact, fast or big."
        )

    from atlasfold_opt import cli as KCLI  # (3) the kit's compile-cache keying

    note = KCLI.jit_env()
    facts["jit"] = note or "no MODEL_OPT_JIT_ROOT: library defaults"
    say(f"jit caches: {facts['jit']}")

    paths = _weights_paths()
    facts["weights_root"] = WEIGHTS_ROOT

    import atlasfold.model  # noqa: F401  (4) ARMS THE KIT: the ACTIVE line is here

    import atlasfold_opt

    report = atlasfold_opt.status()
    if not report.get("active"):
        raise _refuse(
            f"[atlasfold-resident] the kit did not activate under "
            f"ATLASFOLD_OPT={MODE!r}: {report.get('reason') or report}"
        )
    facts["kit_mode"] = report.get("mode")
    facts["levers"] = list(report.get("levers_applied") or ())
    facts["levers_ablated"] = list(report.get("levers_ablated") or ())
    facts["levers_skipped"] = dict(report.get("levers_skipped") or {})
    gpu = report.get("gpu") or {}
    facts["gpu"] = f"{gpu.get('name')}({gpu.get('sm')})"

    # (5) CAN TRITON EMIT CODE FOR THIS CARD? Asked once, in a child process,
    # before anything compiles -- and the answer decides two things that cannot
    # be decided later, because the failure is an abort and not an exception.
    triton_ok, triton_detail = _triton_can_compile_shuffle()
    facts["triton_shuffle"] = triton_detail
    facts["triton_ok"] = triton_ok
    say(
        f"triton warp-shuffle compile: {'ok' if triton_ok else 'UNAVAILABLE'} ({triton_detail})"
    )

    # (5a) A Triton-backed lever still in the row on a host where Triton cannot
    # compile would abort the process on the first fold that reaches its size
    # gate. Refuse by name instead, naming the levers and the door.
    if not triton_ok:
        live = sorted(TRITON_LEVERS.intersection(facts["levers"]))
        if live:
            raise _refuse(
                "[atlasfold-resident] this interpreter's Triton cannot compile a "
                f"warp-shuffle kernel for this GPU ({triton_detail}), and the kit "
                f"mode {MODE!r} still carries Triton-backed lever(s): "
                f"{', '.join(live)}. Each one aborts the PROCESS on the first fold "
                f"that reaches its size gate (LLVM ERROR: Cannot select: intrinsic "
                f"%llvm.nvvm.shfl.sync.bfly.i32), which no worker can catch. Add "
                f"them to [kit] levers_off in provider.toml, or run this provider "
                f"on a host whose Triton knows this card."
            )
    # (5b) The triangle-kernel backend, which is NOT a lever but a stock CLI
    # flag. Upstream's `--kernel auto` resolves to cuequiv whenever
    # `cuequivariance_torch` merely IMPORTS, and cuEquivariance 0.10.0's fused
    # LayerNorm is itself a Triton kernel -- so on a host without a working
    # Triton, `auto` aborts STOCK AtlasFold too, above about 128 tokens. `torch`
    # is then the only backend that folds at all. On a host with a working
    # Triton this stays `auto`, which is upstream's default and the faster path.
    KERNEL_BACKEND[0] = "auto" if triton_ok else "torch"
    facts["kernel_backend_requested"] = KERNEL_BACKEND[0]
    if not triton_ok:
        say(
            "forcing --kernel torch: cuEquivariance 0.10.0's fused LayerNorm is a "
            "Triton kernel and `--kernel auto` would abort this process above "
            "~128 tokens, stock included"
        )

    from atlasfold_opt import phase_timing  # (6)

    phase_timing.install()

    _install_load_memo()  # (7)

    facts["device"] = "cuda" if torch.cuda.is_available() else "cpu"
    if facts["device"] != "cuda":
        raise _refuse(
            "[atlasfold-resident] no CUDA device; this provider declares "
            '[gpu] policy = "required" and the kit\'s levers are CUDA kernels'
        )
    # Upstream sets this inside its own run(); set once here so the first
    # request does not change global matmul precision mid-flight.
    torch.set_float32_matmul_precision("highest")

    if PRELOAD in MODEL_TYPES:
        _model_for(PRELOAD, paths)
    facts["preloaded"] = PRELOAD if PRELOAD in MODEL_TYPES else "none"
    return facts


def _model_for(kind: str, paths: dict):
    """The held model of ``kind``, loading it through the memo if needed."""
    import atlasfold.pretrained as P

    return P.load_model(
        MODEL_NAMES[kind],
        device="cuda",
        # The probed backend, not upstream's `auto`: see _build step (5b). A
        # model built with `auto` on this card holds cuEquivariance's Triton
        # LayerNorm and aborts the process above ~128 tokens.
        kernel=KERNEL_BACKEND[0],
        lm_path=paths["lm"],
        model_path=paths[kind],
    )


# ------------------------------------------------------------------- request
def _parse_fasta(text: str) -> list:
    """``[(name, sequence)]`` from FASTA text, raising ValueError by name."""
    records, name, chunks = [], None, []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            if name is not None:
                records.append((name, "".join(chunks)))
            header = line[1:].split()
            if not header:
                raise ValueError("a FASTA record has an empty header")
            name = header[0]
            chunks = []
        else:
            if name is None:
                raise ValueError("the input does not start with a '>' header")
            chunks.append(line)
    if name is not None:
        records.append((name, "".join(chunks)))
    if not records:
        raise ValueError("no FASTA records in the input")
    for rec_name, seq in records:
        if not seq:
            raise ValueError(f"FASTA target {rec_name!r} has an empty sequence")
        if rec_name in {".", ".."} or "/" in rec_name or "\\" in rec_name:
            raise ValueError(
                f"FASTA target name must not contain path components: {rec_name!r}"
            )
    return records


def _records_of(req: dict) -> list:
    """The request's targets, from ``input`` (FASTA text) or ``records``.

    ``input`` is the neutral key the setup step sends -- it hands the provider
    the smoke file's text and lets the provider decide what it means -- and for
    this model it means a FASTA, which is the only input form the stock CLI
    takes (``-i/--input-fasta``).
    """
    given = req.get("records")
    if given:
        if not isinstance(given, list):
            raise ValueError("'records' must be an array of {name, sequence} objects")
        out = []
        for i, rec in enumerate(given):
            if not isinstance(rec, dict):
                raise ValueError(f"record {i} must be an object")
            seq = (rec.get("sequence") or "").strip().upper()
            if not seq:
                raise ValueError(f"record {i}: 'sequence' must be a non-empty string")
            out.append((str(rec.get("name") or f"target{i + 1}"), seq))
        return out
    text = req.get("input")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("give either 'records' or 'input' (FASTA text)")
    return [(n, s.upper()) for n, s in _parse_fasta(text)]


def _model_type_of(records: list, asked) -> str:
    """``monomer`` or ``multimer``, from the request or from the ':' convention.

    The kit's and upstream's own convention: a multimer record joins its chains
    with ':' (README, "multimer: a record's chains joined with ':'"). A mixed
    set is refused rather than guessed, because the two heads are different
    models and a batch cannot span them.
    """
    if asked is not None:
        if asked not in MODEL_TYPES:
            raise ValueError(f"'model' must be one of {list(MODEL_TYPES)}")
        return asked
    multi = {":" in seq for _, seq in records}
    if len(multi) > 1:
        raise ValueError(
            "this input mixes single-chain and ':'-joined multi-chain records; "
            "AtlasFold's monomer and multimer heads are different models, so "
            "send them as separate requests (or set 'model' explicitly)"
        )
    return "multimer" if multi.pop() else "monomer"


def _argv_for(
    kind: str, fasta: Path, out_dir: Path, seeds: list, options: dict, paths: dict
) -> list:
    """The stock command line, built from the request and upstream's own flags."""
    argv = [
        "--input-fasta",
        os.fspath(fasta),
        "--out-dir",
        os.fspath(out_dir),
        # The kit's own `_inject_weights` adds exactly these two from the
        # weights root when the stock line lacks them; here they are always
        # supplied, so nothing is ever fetched from the hub at request time.
        "--model-path",
        paths[kind],
        "--lm-path",
        paths["lm"],
        "--device",
        "cuda",
        # Decided by the Triton probe in _build(), not by the caller: `auto`
        # (upstream's default, resolves to cuequiv) where Triton works, `torch`
        # where it does not -- because cuEquivariance's own fused LayerNorm is a
        # Triton kernel and `auto` would abort the process rather than raise.
        "--kernel",
        KERNEL_BACKEND[0],
        # A target whose done.txt exists is otherwise SKIPPED, silently, and
        # the reply would carry a success with no new structure.
        "--overwrite",
        "--seed",
        *[str(s) for s in seeds],
    ]
    fmt = options.get("format", "cif")
    if fmt not in ("cif", "pdb"):
        raise ValueError("'format' must be 'cif' or 'pdb'")
    argv += ["--format", fmt]
    for key, flag in OPTION_FLAGS.items():
        if key in options and options[key] is not None:
            argv += [flag, str(options[key])]
    if options.get("save_confidence_arrays"):
        argv.append("--save-confidence-arrays")
    if options.get("save_distogram"):
        argv.append("--save-distogram")
    return argv


def _collect(target_dir: Path, fmt: str) -> dict:
    """The structures, the per-sample confidence, and the ranked pick."""
    structures, scores, ranked = [], {}, None
    for path in sorted(target_dir.glob(f"*_model.{fmt}")):
        stem = path.name[: -len(f"_model.{fmt}")]
        is_ranked = stem.endswith("_ranked")
        entry = {
            "name": stem,
            "path": os.fspath(path),
            "format": fmt,
            "ranked": is_ranked,
        }
        conf_path = target_dir / f"{stem}_confidence.json"
        if conf_path.is_file():
            try:
                conf = json.loads(conf_path.read_text())
            except (OSError, ValueError):
                conf = None
            if conf is not None:
                # Confidence is ALWAYS returned, never opt-in. With upstream's
                # default of five diffusion samples the one thing a caller must
                # do is rank them, and avg_plddt / ptm is how; dropping these
                # would make that impossible.
                scores[stem] = conf
        if is_ranked:
            ranked = stem
        else:
            structures.append(entry)
    return {"structures": structures, "scores": scores, "ranked": ranked}


def _predict_one(req: dict) -> dict:
    import torch

    t_start = time.time()
    records = _records_of(req)
    options = dict(req.get("options") or {})
    for forbidden in ("gpu_ids", "gpu-ids", "n_gpu"):
        if forbidden in options:
            raise ValueError(
                f"'{forbidden}' is not available on a resident worker. It makes "
                f"atlasfold.cli.multigpu torch.multiprocessing.spawn one "
                f"interpreter per id, each loading the model again, out of a "
                f"process that already holds the card — and a resident worker "
                f"has nothing to gain from it."
            )
    kind = _model_type_of(records, req.get("model"))

    seeds = req.get("seed", 1)
    if isinstance(seeds, int) and not isinstance(seeds, bool):
        seeds = [seeds]
    if (
        not isinstance(seeds, list)
        or not seeds
        or not all(isinstance(s, int) and not isinstance(s, bool) for s in seeds)
    ):
        raise ValueError("'seed' must be an integer or a non-empty array of integers")

    out_dir = Path(req.get("out_dir") or ".").expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    fasta = out_dir / "input.fasta"
    fasta.write_text("".join(f">{n}\n{s}\n" for n, s in records))

    paths = _weights_paths()
    switched = STATE["model_type"] not in (None, kind)
    model = _model_for(kind, paths)  # held, or loaded once through the memo

    from atlasfold.cli import monomer, multimer

    module = multimer if kind == "multimer" else monomer
    parser = module.create_parser(prog=f"atlasfold {kind}")
    fmt = options.get("format", "cif")
    parsed = parser.parse_args(_argv_for(kind, fasta, out_dir, seeds, options, paths))

    torch.cuda.reset_peak_memory_stats()
    t_fold = time.time()
    # Upstream's own run(), unwrapped: anything it raises reaches the caller
    # with its own words. `cmd_pred` would have swallowed it into a printed
    # line and an exit code.
    module.run(parsed)
    fold_s = round(time.time() - t_fold, 1)

    files, structures, scores, ranked = [], [], {}, {}
    for name, _seq in records:
        target_dir = out_dir / name
        if not target_dir.is_dir():
            # The target never reached write_outputs: no directory, nothing to
            # collect. The empty-structure check below is what reports it.
            scores[name] = {}
            ranked[name] = None
            continue
        found = _collect(target_dir, fmt)
        structures += found["structures"]
        scores[name] = found["scores"]
        ranked[name] = found["ranked"]
        files += [os.fspath(p) for p in sorted(target_dir.iterdir()) if p.is_file()]

    if not structures:
        # `write_outputs` writes the mmCIF first and touches done.txt last, so
        # neither exists for a target that produced nothing. Raising here is
        # what keeps a reply from carrying an empty list as if it were an
        # answer -- the failure openfold3's provider shipped for a week.
        done = sorted(str(p) for p in out_dir.glob("*/done.txt"))
        raise RuntimeError(
            f"AtlasFold wrote no {fmt} structure for "
            f"{[n for n, _ in records]} under {out_dir}. "
            f"done.txt markers present: {done or 'none'}. "
            f"The run's own PHASE / LEVER lines are in this worker's transcript."
        )

    from atlasfold_opt.stack import gates_verdict

    gates = gates_verdict()
    body = {
        "model": f"AtlasFold v1.0.0 {kind}",
        "model_type": kind,
        "n_structures": len(structures),
        "structures": [s["path"] for s in structures],
        "structure_files": structures,
        "ranked": ranked,
        "scores": scores,
        "files": files,
        "seeds": list(seeds),
        "output_dir": os.fspath(out_dir),
        "kernel_backend": getattr(model, "kernel_backend", None),
        "kernel_backend_requested": KERNEL_BACKEND[0],
        "triton_usable": FACTS.get("triton_ok"),
        "weights_held_by": "worker",
        "kit_mode": MODE,
        "kit_levers_off": LEVERS_OFF or "none",
        # The kit's own per-request verdict, reported rather than folded into an
        # exit code: `cmd_pred` turns a refused gate into exit 3, which a
        # resident worker has no way to return. `refused` being non-empty means
        # a lever took an UNEXPECTED fallback and the structures, while
        # complete, were not produced the way the mode says.
        "kit_gates_ok": bool(gates.get("ok")),
        "kit_gates_refused": [
            {"lever": lever, "reason": reason}
            for lever, reason in gates.get("refused") or ()
        ],
        "timing": {
            "fold_s": fold_s,
            "total_s": round(time.time() - t_start, 1),
            "model_load_s": STATE["load_s"],
            "model_loads": STATE["loads"],
            "model_switch": switched,
        },
        "peak_reserved_gib": round(torch.cuda.max_memory_reserved() / 2**30, 2),
    }
    if req.get("include_structure_text"):
        texts = []
        for entry in structures:
            try:
                texts.append(
                    {"name": entry["name"], "text": Path(entry["path"]).read_text()}
                )
            except (OSError, UnicodeError) as exc:
                texts.append({"name": entry["name"], "error": type(exc).__name__})
        body["structure_text"] = texts
    return body


def _on_reset() -> None:
    import torch

    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()


def _ready() -> dict:
    return {
        "build_s": round(BUILD_S, 1),
        "device": FACTS.get("device"),
        "gpu": FACTS.get("gpu"),
        "weights_held_by": "worker",
        "held_model": STATE["model_type"] or "none",
        "model_load_s": STATE["load_s"],
        "kit_mode": FACTS.get("kit_mode"),
        "kit_levers": len(FACTS.get("levers") or ()),
        "kit_levers_ablated": FACTS.get("levers_ablated"),
        "kit_levers_skipped": FACTS.get("levers_skipped"),
        "libnvrtc_preload": FACTS.get("nvrtc"),
        "triton_shuffle_compile": FACTS.get("triton_shuffle"),
        "kernel_backend_requested": KERNEL_BACKEND[0],
        "jit_caches": FACTS.get("jit"),
        "weights_root": FACTS.get("weights_root"),
        "preloaded": FACTS.get("preloaded"),
        "data_loader_workers": "n/a: this inference path has no DataLoader",
    }


if __name__ == "__main__":
    FACTS.update(_build())
    BUILD_S = time.time() - T0
    say(
        f"ready in {BUILD_S:.1f}s — mode={FACTS.get('kit_mode')} "
        f"levers={len(FACTS.get('levers') or ())} "
        f"ablated={FACTS.get('levers_ablated') or 'none'} "
        f"gpu={FACTS.get('gpu')} kernel={KERNEL_BACKEND[0]} "
        f"triton={'ok' if FACTS.get('triton_ok') else 'unusable'} "
        f"held_model={STATE['model_type'] or 'none'} "
        f"weights_held_by=worker"
    )
    raise SystemExit(
        WB.serve(
            slug=args.slug,
            socket_path=args.socket,
            on_predict=_predict_one,
            ready=_ready,
            on_reset=_on_reset,
            log=say,
        )
    )
