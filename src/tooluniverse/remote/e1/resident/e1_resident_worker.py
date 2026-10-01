"""Profluent E1 held resident on the GPU, answering one request at a time.

Run by the model's own interpreter with the kit's mode variable in the
environment::

    E1_OPT=off <model python> e1_resident_worker.py --socket … --slug e1 \
        --variant 600m --max-batch-tokens 65536

That is the whole activation, and it is the form 30 of the 36 kits offer. The
kit installs ``e1_opt_autoload.pth``, which imports ``e1_opt._autoload`` at
interpreter start; with ``E1_OPT`` naming a kit mode a meta-path finder waits
for the first import of ``E1.predictor`` or ``E1.scorer`` and calls
``e1_opt.enable(mode, variant, strict=True)`` right after that module's body
runs. With ``E1_OPT`` unset or ``off`` **no finder is installed at all** and
nothing of the kit is imported, which is the mode this provider ships (see
provider.toml ``[kit]`` for the reason).

**The mode variable's name is the kit's own, and it is not where you would look
first.** ``e1_opt/modes.py`` -- the module ``kit_launch``'s probe reads first --
defines no ``ENV``. The names live in ``e1_opt/_names.py``
(``ENV, ENV_VARIANT, ENV_DET = "E1_OPT", "E1_VARIANT", "E1_OPT_DET"``) and
``_autoload.py`` imports them, so the probe's second place, ``_autoload.ENV``,
answers ``"E1_OPT"``. Nothing here guesses it from the slug.

**One model size per process, and it is the kit's rule, not a preference.** The
kit says so in three places -- README ("``--variant 150m|300m|600m`` … one size
per process"), ``run.sh`` ("one variant per process, never two") and
``stack._effective_variant``, which refuses a variant disagreeing with
``E1_VARIANT`` by name. The size also chooses the checkpoint, so it cannot come
out of a kit row; it is this script's own ``--variant``, pinned in
``[runtime] worker_args``.

**Who holds the weights: this worker, in both modes -- and this kit is the
reason that question has to be asked per kit rather than answered once.** Chai-1
and ESM C both have kit modes that *replace* the upstream loader, so under those
kits the kit holds the weights and a worker that memoised them would turn the
kit off. ``e1_opt`` replaces nothing of the kind: it wraps
``E1Predictor.__init__`` / ``E1Scorer.__init__`` and applies its lever set to a
model that is *already loaded and already on the device*
(``e1_opt.apply(model)`` is documented as taking "a bare ``E1ForMaskedLM``
ALREADY ON THE GPU"). ``E1ForMaskedLM.from_pretrained`` is untouched in every
mode. So the worker reads the checkpoint, the worker keeps it, and the ready
line and every reply say ``weights_held_by=worker``. Under a kit mode the
``P1_precast`` lever then casts those weights to bf16 in place, which mutates
what the worker holds rather than re-reading it; the reply names the lever list
so the distinction is visible.

**Nothing forks.** E1 uses no ``torch.utils.data.DataLoader`` anywhere --
``E1Predictor`` batches in-process -- so the standard's unconditional
``num_workers = 0`` has no parameter to set here. There is no fork point to
disarm, which is worth stating rather than leaving as a silent absence.

**Why hold it.** Every ``score`` process pays about 15 s on interpreter start
and checkpoint read before any forward happens -- the kit's own README says so
("Every ``score`` process also spends ≈15 s on interpreter start and checkpoint
read in either mode, so the small Run example gains little end to end; the gain
grows with forward work per process"). A held worker pays it once. The first
forward additionally compiles torch's flex-attention and, under a kit mode, the
kit's Triton kernels; those caches are per process too and
``MODEL_OPT_JIT_ROOT`` keeps the on-disk half across restarts.

**The two operations.** ``score`` is the kit's own documented entry point: one
parent sequence and its equal-length mutants, scored by masked-marginal or
wildtype-marginal log-probability ratio, optionally against retrieved context
sequences. ``embed`` is one forward over one sequence returning the mean-pooled
hidden state. Both answer with arrays and write no files unless asked, which is
why ``provider.toml`` declares ``output_keys`` rather than ``outputs``.

**Bounds are enforced here as well as in the tool.** A request that did not come
through ``e1_tool.py`` must not be able to build a reply nothing can transport:
the MCP transport truncated Chai-1's oversized reply at exactly 100,000
characters, producing invalid JSON rather than an honest refusal. So the inline
window is counted in FLOATS, an over-size window is refused rather than clipped,
and the whole per-residue matrix comes back as a path to a ``.npy``.

One request at a time: two inside one CUDA context would interleave their
allocations and make an out-of-memory attributable to neither.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import os
import re
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------- the bounds
#
# MAX_RESIDUES is a memory decision, not a model limit: E1's own
# DataPrepConfig allows 8192 positions within a sequence. It is set here at the
# length the VRAM envelope in provider.toml [gpu] was derived for.
MAX_RESIDUES = 2_048
MAX_MUTANTS = 256
MAX_CONTEXTS = 4
MAX_CONTEXT_RESIDUES = 1_024
# Counted in floats, because what the transport cares about is the number of
# numbers and not the number of residues: at 600m's hidden width of 1280 this
# is 15 residue vectors, at 150m's 768 it is 26.
MAX_INLINE_VALUES = 20_000
MAX_POSITIONS_INLINE = 2_048
# E1Scorer asserts uppercase A-Z with no X. The set is upstream's, not a
# superset of it: a sequence this worker accepted and upstream then rejected
# would be an assertion failure three frames down rather than a named refusal.
AA = set("ABCDEFGHIJKLMNOPQRSTUVWYZ")

SCORING_METHODS = ("masked_marginal", "wildtype_marginal")
CONTEXT_REDUCTIONS = ("mean", "none")

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="e1", help="provider slug, echoed in ping")
ap.add_argument(
    "--variant",
    default="600m",
    choices=("150m", "300m", "600m"),
    help="one model size per process (the kit's rule): the checkpoint size",
)
ap.add_argument(
    "--max-batch-tokens",
    type=int,
    default=65_536,
    help=(
        "upstream's own default (E1.tools.score --max-batch-tokens). It is a "
        "constructor argument of E1Scorer, so it is fixed for the life of this "
        "process and is what the VRAM envelope was derived at."
    ),
)
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
    print(f"[e1-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds E1's pinned stack and
    nothing of ToolUniverse, and importing the package would defeat that."""
    override = os.environ.get("TOOLUNIVERSE_REMOTE_WORKER_BASE")
    here = Path(__file__).resolve()
    path = (
        Path(override)
        if override
        else here.parents[3] / "remote_resident" / "worker_base.py"
    )
    if not path.is_file():
        raise _refuse(
            f"[e1-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

VARIANT = args.variant
MODE = (os.environ.get("E1_OPT") or "off").strip().lower() or "off"

# The weights are pinned and verified before this process starts; nothing is
# fetched at request time. The kit's configs/<card>.env export both of these and
# this worker is not run through run.sh, so it sets them itself -- and before
# huggingface_hub is imported, which is when HF_HOME is read.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
# No .pyc into the shared kit checkout, which `tu remote setup` refuses when it
# has local modifications. configs/<card>.env sets this for the same reason.
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")


def _ptxas_knows(path: Path, target: str) -> bool:
    """Does this ``ptxas`` list ``--gpu-name=<target>``? Its own ``--help`` says."""
    import subprocess

    try:
        out = subprocess.run(
            [os.fspath(path), "--help"], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return f"'{target}'" in (out.stdout or "") + (out.stderr or "")


def _point_triton_at_a_usable_ptxas() -> str:
    """Make sure Triton can assemble PTX for the card in this box. Returns a word.

    THIS IS THE ONE THING THAT STOPS THIS PROVIDER DEAD ON A GB10, and it is
    invisible to every check the standard already has. ``setup``'s
    ``_check_torch_targets_this_gpu`` reads ``torch.cuda.get_arch_list()``, which
    here is ``['sm_80', 'sm_90', 'sm_100', 'sm_120']`` -- sm_120 runs on sm_121,
    so torch's own cubins are fine and the check passes. Triton is a separate
    toolchain: it generates PTX at run time and shells out to the ``ptxas`` that
    ships inside the ``triton`` wheel. triton 3.4.0 -- the version this kit pins
    -- bundles exactly one, from CUDA 12.8, and CUDA 12.8 has no sm_121 at all::

        ptxas fatal : Value 'sm_121a' is not defined for option 'gpu-name'
        triton.runtime.errors.PTXASError: PTXAS error: Internal Triton PTX
        codegen error

    sm_121 first appears in CUDA 12.9. Triton 3.7.1 (which four other providers
    on this box run) solves it by shipping a SECOND binary, ``ptxas-blackwell``
    from CUDA 13.1, and picking it for the newer architectures; 3.4.0 has no such
    thing. So without this, every Triton kernel in the process fails -- and under
    `off` as much as under a kit mode, because stock E1 itself puts its global
    layers through ``torch.compile(flex_attention)``, which lowers to Triton, and
    loads a Triton RMSNorm kernel from the Hugging Face hub.

    The fix is one binary and one variable. ``nvidia-cuda-nvcc-cu12==12.9.86``
    (in ``environment/requirements.lock``, declared there as a deviation) carries
    a CUDA 12.9 ``ptxas`` that knows ``sm_121a``, and Triton takes
    ``TRITON_PTXAS_PATH``. It must be a **12.9** ptxas and not the 13.x one at
    ``/usr/local/cuda-13.0``: triton 3.4.0's ``ptx_get_version`` has a hard table
    that ends at CUDA 12 and raises ``RuntimeError: Triton only support CUDA 10.0
    or higher, but got CUDA version: 13.0`` on anything newer.

    Conditional on the actual gap, not on this host: the bundled ptxas is asked
    whether it knows this card's target, and on a machine where it does
    (an H100 is ``sm_90a``, which CUDA 12.8 has) nothing is changed at all.
    ``TRITON_OVERRIDE_ARCH`` is not the answer either -- in triton 3.4.0 the
    NVIDIA backend uses it only in the compilation cache key
    (``backends/nvidia/compiler.py``), never for the emitted ``--gpu-name``.
    """
    if os.environ.get("TRITON_PTXAS_PATH"):
        return f"preset={os.environ['TRITON_PTXAS_PATH']}"
    import shutil
    import subprocess
    import sysconfig

    exe = shutil.which("nvidia-smi")
    if not exe:
        return "skipped(no nvidia-smi)"
    try:
        out = subprocess.run(
            [exe, "--query-gpu=compute_cap", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return "skipped(nvidia-smi failed)"
    cap = (out.stdout or "").strip().splitlines()[0].strip() if out.stdout else ""
    if not cap or "." not in cap:
        return f"skipped(compute_cap unreadable: {cap!r})"
    # Triton's own spelling: backends/nvidia/compiler.py sm_arch_from_capability
    # appends "a" at capability 90 and above.
    digits = cap.replace(".", "")
    target = f"sm_{digits}a" if int(digits) >= 90 else f"sm_{digits}"

    lib = Path(sysconfig.get_paths()["purelib"])
    bundled = lib / "triton" / "backends" / "nvidia" / "bin" / "ptxas"
    if not bundled.is_file() or _ptxas_knows(bundled, target):
        return f"bundled ptxas already targets {target}"
    newer = lib / "nvidia" / "cuda_nvcc" / "bin" / "ptxas"
    if not newer.is_file():
        return (
            f"NO USABLE ptxas for {target}: triton's bundled "
            f"{bundled} does not list it and {newer} is absent -- install "
            f"nvidia-cuda-nvcc-cu12==12.9.86 (environment/requirements.lock)"
        )
    if not _ptxas_knows(newer, target):
        return f"NO USABLE ptxas for {target}: neither {bundled} nor {newer} lists it"
    os.environ["TRITON_PTXAS_PATH"] = os.fspath(newer)
    return f"TRITON_PTXAS_PATH={newer} (for {target}; triton's own predates it)"


PTXAS_WORD = _point_triton_at_a_usable_ptxas()
say(f"ptxas: {PTXAS_WORD}")


def _snapshot_dir() -> str:
    """The checkpoint directory, resolved by the KIT's own pins module.

    ``--model-name`` must be the snapshot directory and not the repo id: the
    cache holds no ``refs/main`` for the model, because the kit's downloader
    fetches by revision, so upstream's repo-id form does not resolve offline
    (STOCK.md, "Pin"). The revision is therefore not typed here -- the kit's
    ``pins.weights_snapshot(size, hf_home)`` is asked, loaded from its file the
    way the kit's own ``registry.load_pins`` loads it. It is a stdlib-only
    module: no torch, no upstream, nothing of the kit's package.
    """
    model_opt = os.environ.get("MODEL_OPT")
    if not model_opt:
        raise _refuse(
            "[e1-resident] MODEL_OPT is not set, so the kit's pins module "
            "cannot be found; it is exported by kit_launch.build_command"
        )
    path = Path(model_opt) / "opt" / "forward" / "engines" / "e1" / "kits" / "pins.py"
    if not path.is_file():
        raise _refuse(f"[e1-resident] the kit's pins module is not at {path}")
    spec = importlib.util.spec_from_file_location("_e1_pins", path)
    pins = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pins)
    snap = pins.weights_snapshot(VARIANT)
    if not os.path.isfile(os.path.join(snap, "model.safetensors")):
        raise _refuse(
            f"[e1-resident] no model.safetensors under {snap}; run "
            f"`tu remote setup e1 --only weights`"
        )
    return snap


SNAPSHOT = _snapshot_dir()
HF_REPO = {
    "150m": "Profluent-Bio/E1-150m",
    "300m": "Profluent-Bio/E1-300m",
    "600m": "Profluent-Bio/E1-600m",
}

import numpy as np  # noqa: E402
import torch  # noqa: E402

torch.set_grad_enabled(False)


def _key_the_jit_caches() -> str:
    """Put Triton's and Inductor's caches under ``MODEL_OPT_JIT_ROOT``. A word.

    The supervisor already exports ``MODEL_OPT_JIT_ROOT``
    (``kit_launch.build_command``), but in THIS kit nothing reads it in-process:
    the only readers are ``run.sh`` and ``configs/<card>.env``, which derive
    ``TRITON_CACHE_DIR`` and ``TORCHINDUCTOR_CACHE_DIR`` from it -- and the
    resident route runs neither. So without this the compile caches land in
    Triton's and Inductor's own defaults and a worker restart recompiles
    everything. On the first provider on the standard a warm cache took the
    smoke prediction from 42 s to 12 s.

    The key is the kit's own (``e1_opt.stack.jit_cache_key``,
    ``torch<version>-cu<CUDA>-sm<arch>``) rather than a second copy of the same
    arithmetic. It is asked for AFTER torch is imported on purpose: the kit's
    ``probe_gpu`` prefers ``nvidia-smi``, whose ``memory.total`` reads ``[N/A]``
    on this card's unified memory, so the only probe that answers is torch's --
    and that one is tried last and only when torch is loaded. Asked earlier the
    key would read ``smNA`` and every card would share one cache directory.

    Importing ``e1_opt`` here is not an activation: under ``E1_OPT=off`` the
    .pth installed no finder, and ``e1_opt.stack`` imports nothing but the
    standard library.
    """
    root = os.environ.get("MODEL_OPT_JIT_ROOT")
    if not root:
        return "unkeyed (MODEL_OPT_JIT_ROOT unset)"
    try:
        from e1_opt.stack import jit_cache_key

        key = jit_cache_key()
    except Exception as exc:  # noqa: BLE001 - a lost cache is slow, never wrong
        return f"unkeyed ({type(exc).__name__}: {exc})"
    for var, leaf in (
        ("TRITON_CACHE_DIR", "triton"),
        ("TORCHINDUCTOR_CACHE_DIR", "inductor"),
    ):
        if not os.environ.get(var):
            path = os.path.join(root, key, leaf)
            os.makedirs(path, exist_ok=True)
            os.environ[var] = path
    return f"{root}/{key}/{{triton,inductor}}"


JIT_WORD = _key_the_jit_caches()
say(f"jit cache: {JIT_WORD}")

# These two imports are the kit's triggers (`E1.predictor`, `E1.scorer`): under a
# kit mode the finder fires here and the activation report is printed before
# anything is loaded.
from E1 import dist  # noqa: E402
from E1.modeling import E1ForMaskedLM  # noqa: E402
from E1.predictor import E1Predictor  # noqa: E402
from E1.scorer import E1Scorer, EncoderScoreMethod  # noqa: E402

DEVICE = dist.get_device()
say(
    f"imports done t={time.time() - T0:.1f}s torch={torch.__version__} "
    f"cuda={torch.version.cuda} device={DEVICE} variant={VARIANT} mode={MODE}"
)

_t = time.time()
# Upstream's own call, verbatim from E1/tools/score.py L43-44: fp32 weights, the
# forward then runs under bf16 autocast inside E1Predictor.predict_batch_padded.
MODEL = E1ForMaskedLM.from_pretrained(SNAPSHOT, dtype=torch.float).to(DEVICE)
MODEL.eval()
LOAD_S = time.time() - _t

# Built here rather than per request, for three reasons. It is where a kit mode
# applies its lever set and runs its KERNELS proof (both fire at the first
# E1Predictor construction), so a refusal lands at start-up instead of inside a
# request. It holds the KV cache that the kit's kvcache:* levers act on. And its
# construction is what the kit's own wraps are installed on.
_t = time.time()
SCORERS = {
    "masked_marginal": E1Scorer(
        MODEL,
        method=EncoderScoreMethod.MASKED_MARGINAL,
        max_batch_tokens=args.max_batch_tokens,
    )
}
# A second predictor for the embedding operation. E1Scorer's own predictor keeps
# only logits (``fields_to_save=["logits"]``), so embeddings need their own.
# Both wrap the SAME module; nothing is loaded twice.
EMBEDDER = E1Predictor(
    MODEL,
    max_batch_tokens=args.max_batch_tokens,
    fields_to_save=["token_embeddings", "mean_token_embeddings"],
    keep_predictions_in_gpu=False,
)
BUILD_S = time.time() - _t


def _activation_report() -> dict:
    """The kit's own account of what it did, or an empty one under `off`."""
    if MODE in ("", "off"):
        return {}
    try:
        import e1_opt

        return dict(e1_opt.status() or {})
    except Exception as exc:  # noqa: BLE001 - the kit's absence is not fatal here
        return {"status_error": f"{type(exc).__name__}: {exc}"}


REPORT = _activation_report()
_APPLIED = REPORT.get("applied") or {}
LEVERS = [str(x) for x in (_APPLIED.get("levers_on") or _APPLIED.get("levers") or [])]
# Read, not assumed. e1_opt wraps the two constructors and applies levers to an
# already-loaded model; it replaces no loader in any mode, so this worker is the
# holder whatever the mode says.
HOLDER = "worker"
EMBED_DIM = int(MODEL.config.hidden_size)
say(
    f"model resident on {DEVICE} load={LOAD_S:.1f}s build={BUILD_S:.1f}s "
    f"(variant={VARIANT} hidden_size={EMBED_DIM} "
    f"max_batch_tokens={args.max_batch_tokens} weights_held_by={HOLDER} "
    f"kit={MODE} levers_applied={','.join(LEVERS) or 'none'})"
)


# ---------------------------------------------------------------- the input
def _records(text: str) -> list:
    """[(id, sequence)] from a FASTA, or one unnamed record from a bare sequence.

    ``;`` and ``#`` open a comment line, which is how ``smoke/input.fasta``
    carries its provenance; ``;`` is FASTA's own comment character.
    """
    lines = [ln.strip() for ln in (text or "").splitlines()]
    lines = [ln for ln in lines if not ln.startswith((";", "#"))]
    if not any(ln.startswith(">") for ln in lines):
        seq = re.sub(r"\s+", "", "".join(lines)).upper()
        return [("query", seq)] if seq else []
    out, name, cur = [], None, []
    for ln in lines:
        if ln.startswith(">"):
            if name is not None:
                out.append((name, "".join(cur)))
            name, cur = ln[1:].strip().split()[0] if ln[1:].strip() else "", []
        elif ln:
            cur.append(ln)
    if name is not None:
        out.append((name, "".join(cur)))
    return [
        (n or f"seq{i}", re.sub(r"\s+", "", s).upper())
        for i, (n, s) in enumerate(out)
        if s
    ]


def _check_sequence(seq: str, what: str, limit: int = MAX_RESIDUES) -> str:
    bad = sorted(set(seq) - AA)
    if bad:
        raise ValueError(
            f"{what} holds {bad}, which E1Scorer does not accept (uppercase "
            f"A-Z, and X is excluded by upstream's own assertion)"
        )
    if len(seq) > limit:
        raise ValueError(
            f"{what} is {len(seq)} residues; this worker accepts {limit} at "
            f"most (a memory decision, not a model limit: E1's own "
            f"DataPrepConfig allows 8192 within-sequence positions)"
        )
    return seq


def _floats(tensor, decimals: int) -> list:
    return [round(float(x), decimals) for x in tensor.reshape(-1).tolist()]


def _contexts(opts: dict) -> dict:
    """``{id: sequence}`` of retrieved context sequences, or ``{}``.

    This is E1's distinguishing feature -- the scores are conditioned on
    homologues -- and it is also what the kit's ``multiseq:*``, ``kvcache:*``
    and ``tokenmemo`` levers act on; a single-sequence job never reaches them.
    It is bounded here because each context is a prefill of its own length and
    the scoring then runs once per context.
    """
    raw = opts.get("context_sequences")
    if not raw:
        return {}
    if isinstance(raw, str):
        items = _records(raw)
    elif isinstance(raw, dict):
        items = [(str(k), str(v).upper()) for k, v in raw.items()]
    elif isinstance(raw, list):
        items = [(f"ctx{i}", str(v).upper()) for i, v in enumerate(raw)]
    else:
        raise ValueError(
            "'context_sequences' must be a FASTA string, a list or an object"
        )
    if len(items) > MAX_CONTEXTS:
        raise ValueError(
            f"{len(items)} context sequences were given; this worker accepts "
            f"{MAX_CONTEXTS} at most (scoring runs once per context, so the "
            f"forward work is multiplied by their number)"
        )
    out = {}
    for name, seq in items:
        _check_sequence(seq, f"context {name!r}", MAX_CONTEXT_RESIDUES)
        out[name] = seq
    return out


# ---------------------------------------------------------------- the requests
def _score(records: list, opts: dict) -> dict:
    """One parent and its mutants, scored. Upstream's own E1Scorer.score."""
    (parent_id, parent), mutants = records[0], records[1:]
    if not mutants:
        raise ValueError(
            "scoring needs a parent and at least one mutant: the first FASTA "
            "record is the parent and every record after it is a mutant of the "
            "same length (upstream's own rule -- E1.tools.score asserts exactly "
            "one parent sequence)"
        )
    if len(mutants) > MAX_MUTANTS:
        raise ValueError(
            f"{len(mutants)} mutants were given; this worker accepts "
            f"{MAX_MUTANTS} at most"
        )
    _check_sequence(parent, f"the parent {parent_id!r}")
    lengths = {len(s) for _, s in mutants}
    if lengths != {len(parent)}:
        raise ValueError(
            f"the mutants are {sorted(lengths)} residues long and the parent is "
            f"{len(parent)}; E1Scorer asserts that all sequences and the parent "
            f"have one length (it scores substitutions, not indels)"
        )
    for name, seq in mutants:
        _check_sequence(seq, f"mutant {name!r}")

    method = str(opts.get("scoring_method") or "masked_marginal").strip().lower()
    if method not in SCORING_METHODS:
        raise ValueError(
            f"scoring_method {method!r} is not one of {list(SCORING_METHODS)}"
        )
    reduction = str(opts.get("context_reduction") or "mean").strip().lower()
    if reduction not in CONTEXT_REDUCTIONS:
        raise ValueError(
            f"context_reduction {reduction!r} is not one of {list(CONTEXT_REDUCTIONS)}"
        )
    contexts = _contexts(opts)

    scorer = SCORERS.get(method)
    if scorer is None:
        # Built once and kept: it wraps the same module, so this costs a KV
        # cache and a tokenizer, not a second checkpoint read.
        scorer = SCORERS[method] = E1Scorer(
            MODEL,
            method=EncoderScoreMethod(method),
            max_batch_tokens=args.max_batch_tokens,
        )

    t = time.time()
    rows = scorer.score(
        parent_sequence=parent,
        sequences=[s for _, s in mutants],
        sequence_ids=[n for n, _ in mutants],
        context_seqs=contexts or None,
        context_reduction=reduction,
    )
    forward_s = time.time() - t

    scores = [
        {
            "id": str(r["id"]),
            "context_id": None if r["context_id"] is None else str(r["context_id"]),
            "score": round(float(r["score"]), 6),
        }
        for r in rows
    ]
    ordered = sorted(scores, key=lambda r: r["score"], reverse=True)
    top_n = max(0, min(100, int(opts.get("top_n", 10))))
    return {
        "operation": "score",
        "parent_id": parent_id,
        "parent_length": len(parent),
        "n_mutants": len(mutants),
        "n_scored": len(scores),
        "scoring_method": method,
        "context_reduction": reduction,
        "context_ids": sorted(contexts),
        "score_units": (
            "log-probability of the mutant residue minus that of the parent "
            "residue, summed over the substituted positions; higher is more "
            "favoured by the model"
        ),
        "scores": scores,
        "best": ordered[:top_n],
        "timing": {"forward_s": round(forward_s, 3)},
    }


def _embed(records: list, opts: dict) -> dict:
    """One forward over one sequence: the mean-pooled hidden state."""
    if len(records) != 1:
        raise ValueError(
            f"the input holds {len(records)} records; the embed operation takes "
            f"one sequence per request (two or more records are read as a "
            f"parent and its mutants, which is the score operation)"
        )
    name, seq = records[0]
    _check_sequence(seq, f"the sequence {name!r}")
    decimals = max(1, min(8, int(opts.get("decimals", 5))))

    t = time.time()
    preds = list(EMBEDDER.predict([seq], [name]))
    forward_s = time.time() - t
    if len(preds) != 1:
        raise RuntimeError(
            f"the predictor yielded {len(preds)} predictions for one sequence"
        )
    residues = preds[0]["token_embeddings"].float()  # (L, hidden)
    mean_vec = preds[0]["mean_token_embeddings"].float()
    if residues.shape[0] != len(seq):
        raise RuntimeError(
            f"the model returned {residues.shape[0]} residue vectors for "
            f"{len(seq)} residues"
        )

    body = {
        "operation": "embed",
        "sequence_id": name,
        "sequence_length": len(seq),
        "embedding_dim": int(residues.shape[1]),
        "pooling": "mean over the sequence's own tokens, boundary tokens excluded",
        "mean_embedding": _floats(mean_vec, decimals),
        "mean_embedding_norm": round(float(mean_vec.norm()), 6),
        "timing": {"forward_s": round(forward_s, 3)},
    }

    window = opts.get("residue_range")
    if window:
        start, end = int(window[0]), int(window[1])
        if not (1 <= start <= end <= len(seq)):
            raise ValueError(
                f"residue_range {[start, end]} is outside 1..{len(seq)} "
                f"(1-based and inclusive)"
            )
        count = (end - start + 1) * int(residues.shape[1])
        if count > MAX_INLINE_VALUES:
            raise ValueError(
                f"residue_range {[start, end]} is {count} floats, over the "
                f"{MAX_INLINE_VALUES} an inline reply may carry; narrow the "
                f"range (at hidden_size {int(residues.shape[1])} that is "
                f"{MAX_INLINE_VALUES // max(1, int(residues.shape[1]))} "
                f"residues) or ask for per_residue_file"
            )
        body["residue_embeddings"] = {
            "start": start,
            "end": end,
            "values": [_floats(residues[i], decimals) for i in range(start - 1, end)],
        }

    if opts.get("per_residue_file"):
        out_dir = Path(opts.get("out_dir") or ".")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{opts.get('name') or 'e1'}_residue_embeddings.npy"
        # float32 on purpose: the model computes under bf16 autocast and float32
        # is the smallest format that carries every bit of that without a dtype
        # a downstream reader may not have.
        np.save(path, residues.cpu().numpy().astype(np.float32))
        body["per_residue_file"] = {
            "path": str(path),
            "format": "numpy .npy",
            "dtype": "float32",
            "shape": [int(residues.shape[0]), int(residues.shape[1])],
            "bytes": path.stat().st_size,
        }
    return body


def _predict_one(req: dict) -> dict:
    """One request. The operation is explicit, or inferred from the input."""
    opts = dict(req.get("options") or {})
    opts.setdefault("out_dir", req.get("out_dir"))
    opts.setdefault("name", req.get("name"))
    records = _records(req.get("input") or req.get("sequence") or "")
    if not records:
        raise ValueError("the input carries no sequence")

    op = str(opts.get("op") or "").strip().lower()
    if not op:
        op = "embed" if len(records) == 1 else "score"
    if op not in ("score", "embed"):
        raise ValueError(f"op {op!r} is not one of ['score', 'embed']")

    if DEVICE.type == "cuda":
        torch.cuda.reset_peak_memory_stats()
    body = _score(records, opts) if op == "score" else _embed(records, opts)
    if DEVICE.type == "cuda":
        torch.cuda.synchronize()
        body["peak_reserved_gib"] = round(torch.cuda.max_memory_reserved() / 2**30, 2)
    body.update(
        {
            "model": "Profluent E1 1.0.0",
            "variant": VARIANT,
            "hf_repo": HF_REPO[VARIANT],
            "max_batch_tokens": args.max_batch_tokens,
            "weights_held_by": HOLDER,
            "kit_mode": MODE,
            "levers_applied": LEVERS,
        }
    )
    return body


def _ready() -> dict:
    return {
        "load_s": round(LOAD_S, 1),
        "build_s": round(BUILD_S, 1),
        "device": str(DEVICE),
        "variant": VARIANT,
        "hidden_size": EMBED_DIM,
        "max_batch_tokens": args.max_batch_tokens,
        "weights_held_by": HOLDER,
        "kit_mode": MODE,
        "levers_applied": LEVERS,
        "ptxas": PTXAS_WORD,
        "jit_cache": JIT_WORD,
    }


if __name__ == "__main__":
    sys.exit(
        WB.serve(
            slug=args.slug,
            socket_path=args.socket,
            on_predict=_predict_one,
            ready=_ready,
            log=say,
        )
    )
