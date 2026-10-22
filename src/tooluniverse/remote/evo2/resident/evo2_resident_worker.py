"""Evo 2 held resident on the GPU, answering one request at a time.

Run by the model's own interpreter with the kit's mode variable in the
environment::

    EVO2_OPT=exact <model python> evo2_resident_worker.py --socket … --slug … --model evo2_7b

That is the whole activation, and it is the form 30 of the 36 kits offer. The
kit installs ``evo2_opt_autoload.pth``, which imports ``evo2_opt._autoload`` at
interpreter start; with ``EVO2_OPT`` naming a mode, a meta-path finder waits for
the first import of ``evo2`` and calls ``activation.enable(mode)`` before that
package's body executes. The variable's name is the kit's own and is read off
the kit by ``kit_launch``'s probe -- ``_autoload.ENV = "EVO2_OPT"`` -- never
guessed from the slug. **There is no ``evo2_opt.modes`` module in this kit at
all**, so a probe that looked only at ``modes.ENV`` would have found nothing;
that is why ``provider.toml`` declares ``[kit] env_row = "none"``.

**Who holds the weights: this worker.** The kit does NOT replace upstream's
loader. ``activation._wrap_class`` wraps ``Evo2.__init__`` so that
``evo2_opt.kit.apply`` and ``evo2_opt.gen.arm`` run *after* the original
constructor has returned, on the model it built -- so upstream's own
``load_checkpoint`` reads the 13.8 GiB file and this process holds what it
produced. What the kit holds beside it is its own device-side state: filter
caches, FFT plans, GEMM buffers, and (where applicable) a replayable CUDA
graph, one shape at a time. Both facts are on the ready line and in every
reply, because "the worker holds them" and "the kit holds them" are different
claims and three of the ten providers before this one got a different answer.

**Nothing is fetched at request time.** Upstream will happily download 13.8 GiB
by itself when ``local_path`` is None, and the kit does not stop it: STOCK.md
says a weights directory whose checkpoint the process cannot see "is not
refused: score then also takes upstream's own download". So this worker
resolves the checkpoint itself, refuses by name when it is absent, and sets
``HF_HUB_OFFLINE=1`` before ``huggingface_hub`` can be imported.

**Why hold it.** 13.8 GiB of bf16 parameters, read once. The kit's README
measures the first score in a fresh environment at "≈220 s, then 15-50 s a
run", most of which is the checkpoint and the per-shape Triton compiles -- and
both are per process. A worker that exits after each request pays all of it
again for a forward pass that then takes seconds.

**What a request may ask for is bounded in this file as well as in the tool.**
Evo 2's hidden width is 4096, so one position's embedding is 4096 floats and a
1,024 bp matrix is 4.2 million of them. The MCP transport truncated Chai-1's
oversized reply at exactly 100,000 characters, producing invalid JSON rather
than an honest refusal, so the bounds are enforced in both halves: in the tool
so a bad call never occupies the GPU, and here so a request that did not come
through the tool cannot build a reply nothing can transport.

One request at a time: two inside one CUDA context would interleave their
allocations and make an out-of-memory attributable to neither.
"""

from __future__ import annotations

import argparse
import math
import os
import re
import sys
import time
from pathlib import Path

# stock/PINS.json checkpoints.<name>.file -- the filename the kit's own fetcher
# writes into EVO2_OPT_WEIGHTS and upstream's loader reads as `local_path`.
CHECKPOINT = {
    "evo2_7b": "evo2_7b.pt",
    "evo2_40b": "evo2_40b.pt",
    "evo2_1b_base": "evo2_1b_base.pt",
}

# Bounds on what one request may ask of the card and of the transport.
#
# MAX_BP is the envelope [gpu] vram_budget_gb is declared at, and the two are
# deliberately the same number: this provider is UNMEASURED, and the cheapest
# way to keep an unmeasured budget honest is to refuse the inputs it does not
# cover. The model's own `max_seqlen` is 1,048,576, so this is a memory
# decision, not a model limit -- raise it here, in evo2_tool.py and in the
# manifest together, after measuring.
MAX_BP = 8_192
MAX_SEQUENCES = 8
MAX_TOTAL_BP = 16_384
# Counted in FLOATS rather than positions, because the width (4096) is what
# makes an embedding big.
MAX_INLINE_VALUES = 20_000
MAX_POSITIONS_INLINE = 4_000
# IUPAC nucleotide codes, upper case. Evo 2's tokenizer is byte-level
# (CharLevelTokenizer(512)) so it would accept anything; what it was trained on
# is DNA, and a protein sequence pasted in by mistake should be refused here
# rather than scored as if it meant something.
NUCLEOTIDES = set("ACGTUNRYSWKMBDHV")

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="evo2", help="provider slug, echoed in ping")
ap.add_argument(
    "--model",
    default="evo2_7b",
    choices=sorted(CHECKPOINT),
    help="one model per process: the checkpoint this worker holds",
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
    print(f"[evo2-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds Evo 2's pinned stack and
    nothing of ToolUniverse, and importing the package would defeat that."""
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
            f"[evo2-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

MODEL_NAME = args.model
MODE = (os.environ.get("EVO2_OPT") or "off").strip().lower() or "off"

# Before huggingface_hub is imported, which is when these are read. The
# checkpoint is pinned and digest-checked by the weights step; a hub call from
# this process would mean something had gone wrong, and the honest outcome is
# an error rather than a silent 13.8 GiB transfer.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
# No .pyc into the shared kit checkout, which `tu remote setup` refuses when it
# has local modifications.
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

    THIS STOPS EVO 2 DEAD ON A GB10 IN EVERY MODE, and it is invisible to every
    check the standard already has. ``setup``'s
    ``_check_torch_targets_this_gpu`` reads ``torch.cuda.get_arch_list()``,
    which here is ``['sm_90', 'sm_100', 'sm_120']`` -- an sm_120 cubin runs on
    sm_121, so torch's own check passes. Triton is a separate toolchain: it
    emits PTX at run time and shells out to a ``ptxas`` that ships inside the
    ``triton`` wheel, and ``backends/nvidia/compiler.py::sm_arch_from_capability``
    asks that ptxas for ``sm_121a``.

    **`[kit] mode = "off"` DOES NOT AVOID THIS.** Triton is on Evo 2's own
    inference path, not just the kit's: ``vortex/model/rotary.py:7`` imports
    ``apply_rotary`` from ``vortex/ops/embedding/rotary.py``, which is a
    ``@triton.jit`` kernel, and ``ApplyRotaryEmb.forward`` calls it for the five
    attention layers of evo2_7b on every forward. ``use_kernels=True`` adds
    three more upstream Triton kernels (hcs/hcm/hcl), and the kit's `exact`
    adds its own (``kit/fir3rows.py``, ``kit/rmsnorm.py``). Stock Evo 2 on this
    card needs this fix as much as the kit does.

    WHAT THIS KIT'S TRITON SHIPS, measured here rather than assumed, and it is
    NOT what triton 3.4.0 (e1's) ships:

        triton 3.3.1 bin/ptxas            CUDA 12.4.99  sm_90a yes, sm_120a no, sm_121a no
        triton 3.3.1 bin/ptxas-blackwell  CUDA 12.8.61  sm_90a yes, sm_120a YES, sm_121a no
        nvidia-cuda-nvcc-cu12 12.9.86     CUDA 12.9.86  sm_90a yes, sm_120a yes, sm_121a YES

    So 3.3.1 DOES carry a second binary -- and it still does not reach sm_121,
    because sm_121 first appears in CUDA 12.9. THE ENVIRONMENT VARIABLE IS
    THEREFORE NOT ``TRITON_PTXAS_PATH`` ON THIS STACK. ``_path_to_binary``
    builds the name as ``f"TRITON_{binary.upper()}_PATH"`` and ``get_ptxas``
    picks ``"ptxas-blackwell" if arch >= 100 else "ptxas"``, so for a
    capability-121 card the variable Triton reads is
    ``TRITON_PTXAS-BLACKWELL_PATH`` -- hyphen and all, which `export` in bash
    cannot even spell. Both names are set here, so neither the selection rule
    nor a future triton that drops the second binary can make this silently
    do nothing.

    It must be a **12.9** ptxas and not ``/usr/local/cuda-13.0``'s: triton
    3.3.1's ``ptx_get_version`` has a hard table that ends at CUDA 12 and
    raises ``RuntimeError: Triton only support CUDA 10.0 or higher, but got
    CUDA version: 13.0``. ``TRITON_OVERRIDE_ARCH`` is not the answer either --
    the NVIDIA backend uses it only in the compilation cache key, never for the
    emitted ``--gpu-name``.

    Conditional on the actual gap, not on this host: each binary Triton might
    pick is asked whether it knows this card's target, and on a machine where
    it does (an H100 is ``sm_90a``, which CUDA 12.4 already has) nothing is
    changed at all.
    """
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
    digits = cap.replace(".", "")
    # Triton's own spelling: sm_arch_from_capability appends "a" from 90 up.
    target = f"sm_{digits}a" if int(digits) >= 90 else f"sm_{digits}"

    lib = Path(sysconfig.get_paths()["purelib"])
    newer = lib / "nvidia" / "cuda_nvcc" / "bin" / "ptxas"
    words = []
    for name in ("ptxas", "ptxas-blackwell"):
        var = f"TRITON_{name.upper()}_PATH"
        if os.environ.get(var):
            words.append(f"{name}=preset")
            continue
        bundled = lib / "triton" / "backends" / "nvidia" / "bin" / name
        if not bundled.is_file() or _ptxas_knows(bundled, target):
            words.append(f"{name}=own")
            continue
        if not newer.is_file():
            words.append(f"{name}=MISSING")
            continue
        if not _ptxas_knows(newer, target):
            words.append(f"{name}=UNUSABLE")
            continue
        os.environ[var] = os.fspath(newer)
        words.append(f"{name}->{newer.name}(12.9)")
    bad = [w for w in words if "MISSING" in w or "UNUSABLE" in w]
    if bad:
        return (
            f"NO USABLE ptxas for {target}: {', '.join(words)} -- install "
            f"nvidia-cuda-nvcc-cu12==12.9.86 (environment/requirements.lock "
            f"DEVIATION 4); Triton will abort in this process otherwise"
        )
    return f"{target}: " + ", ".join(words)


PTXAS_WORD = _point_triton_at_a_usable_ptxas()
say(f"ptxas: {PTXAS_WORD}")


def _checkpoint() -> str:
    """The pinned checkpoint under EVO2_OPT_WEIGHTS, or a named refusal.

    EVO2_OPT_WEIGHTS is the kit's own variable and the kit's own layout -- "the
    directory holding <model_name>.pt" (STOCK.md Sec.Variables). kit_launch
    exports it from [weights] root_env after verify_weights() has passed, so by
    the time this runs the file has been read and matched against its sha256.
    """
    root = os.environ.get("EVO2_OPT_WEIGHTS")
    if not root:
        raise _refuse(
            "[evo2-resident] EVO2_OPT_WEIGHTS is not set, and this worker will "
            "not let upstream download 13.8 GiB at request time: set it to the "
            "directory holding "
            f"{CHECKPOINT[MODEL_NAME]} (tu remote setup evo2 --only weights)"
        )
    path = Path(root).expanduser() / CHECKPOINT[MODEL_NAME]
    if not path.is_file():
        raise _refuse(
            f"[evo2-resident] {path} is not there. EVO2_OPT_WEIGHTS is set, "
            f"which the kit does NOT treat as an error -- STOCK.md: such a "
            f"directory 'is not refused: score then also takes upstream's own "
            f"download (13.8 GB for evo2_7b)'. This worker refuses instead: "
            f"run `tu remote setup evo2 --only weights`"
        )
    return os.fspath(path)


CKPT = _checkpoint()

import numpy as np  # noqa: E402
import torch  # noqa: E402

torch.set_grad_enabled(False)

# The kit's trigger is the top-level `evo2` import: the finder fires on it and
# runs activation.enable(MODE) before evo2's own body executes. A mode that
# cannot engage prints one `[evo2-opt] NOT ACTIVE` line and raises SystemExit(3)
# from inside this import -- deliberately not caught, because a worker that
# swallowed it would serve stock under the name of the kit.
from evo2 import Evo2  # noqa: E402

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
say(
    f"imports done t={time.time() - T0:.1f}s torch={torch.__version__} "
    f"device={DEVICE} model={MODEL_NAME} kit={MODE}"
)

_t = time.time()
# upstream's own construction, and the kit's: STOCK.md Sec.'How stock is run'
# -- `Evo2('evo2_7b', use_kernels=True)` for the one-device models, which is
# "upstream's documented faster-inference switch, vortex's Triton kernels for
# the three Hyena convolutions", and "exact and fast use the off construction
# with EVO2_OPT set". use_kernels=True selects the kit's `vortex-kernels` lever
# table over its `torch-conv` one (opt/evo2_opt/kit/table.py); the kit reads the
# route off the object rather than being told.
#
# local_path is passed unconditionally. With it None, upstream's
# load_evo2_model() goes to Hugging Face for a 13.8 GiB snapshot.
MODEL = Evo2(MODEL_NAME, local_path=CKPT, use_kernels=True)
BUILD_S = time.time() - _t


def _activation_report() -> dict:
    """The kit's own account of what it did, or an empty one under `off`."""
    if MODE in ("", "off"):
        return {}
    try:
        import evo2_opt

        return dict(evo2_opt.status() or {})
    except Exception as exc:  # noqa: BLE001 - the kit's absence is not fatal here
        return {"status_error": f"{type(exc).__name__}: {exc}"}


REPORT = _activation_report()
# activation._on_constructed appends {model, route, levers, generation} per
# constructed model; one model lives in this process for its whole life.
_MODELS = list(REPORT.get("models") or [])
ROUTE = str(_MODELS[0].get("route")) if _MODELS else "stock"
LEVERS = [str(x) for x in ((_MODELS[0].get("levers") if _MODELS else None) or [])]
# Read from what the kit does, not assumed: this kit wraps Evo2.__init__ and
# applies its levers to the model the ORIGINAL constructor returned
# (activation._wrap_class -> _on_constructed), so upstream's load_checkpoint did
# the reading and this process holds the result. Contrast chai1 and esmc, whose
# kits replace the loader itself.
HOLDER = "worker"

_CFG = MODEL.model.config
HIDDEN = int(getattr(_CFG, "hidden_size", 0) or 0)
N_LAYERS = int(getattr(_CFG, "num_layers", 0) or 0)


def _embedding_layers() -> list:
    """The ``blocks.<i>.mlp.l3`` modules, in order -- the per-block hidden-state
    outputs Evo 2's own examples take embeddings from.

    Discovered from the module tree rather than written down, because the block
    count is the checkpoint's (32 for evo2_7b, 50 for the 40b) and a default
    naming a layer that does not exist is a refusal at request time.
    """
    pattern = re.compile(r"^blocks\.(\d+)\.mlp\.l3$")
    found = []
    for name, _ in MODEL.model.named_modules():
        m = pattern.match(name)
        if m:
            found.append((int(m.group(1)), name))
    return [name for _, name in sorted(found)]


EMBED_LAYERS = _embedding_layers()
DEFAULT_LAYER = EMBED_LAYERS[-1] if EMBED_LAYERS else ""
say(
    f"model resident on {DEVICE} in {BUILD_S:.1f}s (model={MODEL_NAME} "
    f"hidden={HIDDEN} layers={N_LAYERS} weights_held_by={HOLDER} kit={MODE} "
    f"route={ROUTE} levers={len(LEVERS)} default_embedding_layer={DEFAULT_LAYER})"
)


def _records(text: str) -> list:
    """[(id, sequence)] out of a FASTA, or one unnamed record out of raw text."""
    lines = [ln.strip() for ln in (text or "").splitlines()]
    out = []
    if any(ln.startswith(">") for ln in lines):
        name, chunks = None, []
        for ln in lines:
            if ln.startswith(">"):
                if name is not None:
                    out.append((name, "".join(chunks)))
                name, chunks = ln[1:].split()[0] if ln[1:].split() else "", []
            elif ln:
                chunks.append(ln)
        if name is not None:
            out.append((name, "".join(chunks)))
    else:
        joined = "".join(lines)
        if joined:
            out.append(("sequence_1", joined))
    if not out:
        raise ValueError("the input carries no sequence")
    if len(out) > MAX_SEQUENCES:
        raise ValueError(
            f"the input holds {len(out)} records; this worker takes "
            f"{MAX_SEQUENCES} at most per request"
        )

    cleaned, total = [], 0
    for i, (name, seq) in enumerate(out):
        seq = re.sub(r"\s+", "", seq).upper()
        if not seq:
            raise ValueError(f"record {name or i + 1} carries no sequence")
        bad = sorted(set(seq) - NUCLEOTIDES)
        if bad:
            raise ValueError(
                f"record {name or i + 1} holds {bad}, which are not IUPAC "
                f"nucleotide codes -- Evo 2 is a DNA model"
            )
        if len(seq) > MAX_BP:
            raise ValueError(
                f"record {name or i + 1} is {len(seq)} bp; this worker accepts "
                f"{MAX_BP} at most (a memory decision, not a model limit: Evo 2's "
                f"own max_seqlen is 1,048,576, and {MAX_BP} is the envelope this "
                f"provider's vram_budget_gb is declared at)"
            )
        total += len(seq)
        cleaned.append((name or f"sequence_{i + 1}", seq))
    if total > MAX_TOTAL_BP:
        raise ValueError(
            f"the request totals {total} bp over {len(cleaned)} records; the "
            f"limit is {MAX_TOTAL_BP} bp per request"
        )
    return cleaned


def _floats(tensor, decimals: int) -> list:
    return [round(float(x), decimals) for x in tensor.reshape(-1).tolist()]


def req_out_dir(opts: dict) -> str:
    return str(opts.get("_out_dir") or ".")


def _score(records: list, opts: dict) -> dict:
    """``Evo2.score_sequences``: the mean log-likelihood of each record.

    This is the call the kit's levers are built for. On the Transformer-Engine
    routes ``kit/gate.py::decide_route`` returns ('kit', None) for a forward
    carrying neither inference params nor a padding mask, and a PADDED forward
    -- which is what upstream's own ``prepare_batch`` produces for records of
    unequal length -- is one of the two it sends down the stock path by name.
    On ``bf16-projections`` there is no gate and "every scoring forward is the
    kit path" (kit/__init__.py's own comment). Either way batch_size defaults
    to 1, one record per forward, so no padding is introduced by batching.
    """
    reduce_method = str(opts.get("reduce", "mean")).lower()
    if reduce_method not in ("mean", "sum"):
        raise ValueError("'reduce' must be 'mean' (log-likelihood) or 'sum' (PLL)")
    batch_size = int(opts.get("batch_size", 1))
    if not 1 <= batch_size <= MAX_SEQUENCES:
        raise ValueError(f"'batch_size' must be between 1 and {MAX_SEQUENCES}")
    rc = bool(opts.get("average_reverse_complement", False))

    seqs = [s for _, s in records]
    t = time.time()
    scores = MODEL.score_sequences(
        seqs,
        batch_size=batch_size,
        reduce_method=reduce_method,
        average_reverse_complement=rc,
    )
    if DEVICE == "cuda":
        torch.cuda.synchronize()
    forward_s = time.time() - t

    values = [float(x) for x in scores]
    return {
        "task": "score",
        "reduce": reduce_method,
        "average_reverse_complement": rc,
        "batch_size": batch_size,
        "ids": [name for name, _ in records],
        "sequence_lengths": [len(s) for _, s in records],
        "scores": [round(v, 6) for v in values],
        # The kit writes `score_hex` into its own scores.jsonl so two arms can
        # be compared bit for bit; the same idea, so a caller can tell an
        # identical score from a nearly identical one.
        "scores_hex": [float(v).hex() for v in values],
        "perplexity": [
            round(math.exp(-v), 4)
            if reduce_method == "mean" and -700 < v < 700
            else None
            for v in values
        ],
        "timing": {"forward_s": round(forward_s, 3)},
    }


def _embed(records: list, opts: dict) -> dict:
    """One forward with a forward hook on a named layer: its hidden states.

    WHICH PATH A HOOKED FORWARD TAKES DEPENDS ON THE ROUTE, and both answers
    are read out of the kit rather than assumed:

    * On the Transformer-Engine routes the gate is installed and
      ``kit/hooks.py`` is explicit -- "a model carrying user forward hooks
      (Evo2.forward(return_embeddings=True)) takes the stock path by name for
      that call", named once on stderr and counted on the kit's EXIT line. A
      hook on a FOLDED PROJECTION is worse than slow: it raises
      ``KitRefusedHooks`` ("the L2 fold changes the projection's output
      layout").
    * On the ``bf16-projections`` route -- the one this provider's stack runs,
      Transformer Engine being absent -- NO GATE IS INSTALLED AT ALL.
      ``kit/bf16.py`` lists ``GATE_forward_gate_shape_manager`` as not
      applicable: "this route holds no shape-bound store ... every (batch,
      length) runs the same patched classes". So a hooked forward takes the kit
      path here, and the folded-projection refusal is not wired either --
      although the fold itself IS applied, as
      ``L2_interleave_fold_bf16_projection_weight``.

    That second case is exactly why this function restricts ``layer_name`` to
    ``blocks.<i>.mlp.l3`` itself instead of relying on the kit to refuse: on
    this route a hook on ``.projections`` would hand back the folded layout
    with nothing objecting.
    """
    if not EMBED_LAYERS:
        raise RuntimeError(
            "this model exposes no blocks.<i>.mlp.l3 modules, so there is no "
            "embedding layer to hook; inspect "
            "model.model.state_dict().keys() on the worker host"
        )
    layer = str(opts.get("layer_name") or DEFAULT_LAYER)
    if layer not in EMBED_LAYERS:
        raise ValueError(
            f"'layer_name' {layer!r} is not one of this model's "
            f"{len(EMBED_LAYERS)} hookable embedding layers "
            f"({EMBED_LAYERS[0]} .. {EMBED_LAYERS[-1]}). Projection layers are "
            f"deliberately not offered: the kit refuses a forward hook on a "
            f"folded projection because the L2 fold changes its output layout"
        )
    if len(records) != 1:
        raise ValueError(
            f"embedding takes one sequence per request; this one holds "
            f"{len(records)} records"
        )
    name, seq = records[0]
    decimals = max(1, min(8, int(opts.get("decimals", 5))))

    input_ids = (
        torch.tensor(MODEL.tokenizer.tokenize(seq), dtype=torch.long)
        .unsqueeze(0)
        .to(DEVICE)
    )
    t = time.time()
    returned, embeddings = MODEL.forward(
        input_ids, return_embeddings=True, layer_names=[layer]
    )
    if DEVICE == "cuda":
        torch.cuda.synchronize()
    forward_s = time.time() - t

    # NESTED ON PURPOSE, and this cost a reading of three files to get right.
    # `vortex.model.model.StripedHyena.forward` returns
    # `(x, inference_params_dict_out)`; `evo2.models.Evo2.forward` assigns that
    # whole tuple to its own name `logits` and hands it back unchanged, so what
    # arrives here is ((logits, inference_params), embeddings). Upstream's
    # scoring.py is where the shape is visible -- `logits, _ = model(input_ids)`.
    logits = returned[0] if isinstance(returned, (tuple, list)) else returned

    hidden = embeddings[layer][0].float()  # (L, hidden)
    if hidden.shape[0] != len(seq):
        raise RuntimeError(
            f"the model returned {hidden.shape[0]} positions for a {len(seq)} bp "
            f"sequence; the tokenizer is byte-level and they should match"
        )
    width = int(hidden.shape[1])
    mean_vec = hidden.mean(dim=0)

    body = {
        "task": "embed",
        "ids": [name],
        "sequence_lengths": [len(seq)],
        "layer_name": layer,
        "embedding_dim": width,
        "pooling": "mean over positions",
        "mean_embedding": _floats(mean_vec, decimals),
        "mean_embedding_norm": round(float(mean_vec.norm()), 6),
        # The whole point of returning this alongside: the embedding is only
        # interpretable next to how surprising the model found the sequence.
        "timing": {"forward_s": round(forward_s, 3)},
        # A hooked forward is a stock-path forward; see this function's
        # docstring. Stated per reply so nobody reads a kit mode on the ready
        # line and concludes the levers ran for this call.
        "kit_path": (
            "route-dependent: the kit sends a hooked forward down the stock path "
            "on its Transformer-Engine routes, and down the kit path on "
            "bf16-projections, which installs no gate -- read kit_route below"
        ),
    }

    # A score alongside, from the same logits, so an embed reply satisfies the
    # same [runtime] output_keys contract a score reply does. The shift is
    # upstream's own (evo2/scoring.py logits_to_logprobs): position i's logits
    # predict base i+1, so the last row of the logits and the first token are
    # dropped.
    if logits.shape[0] != 1:
        raise RuntimeError(
            f"the model returned a batch of {logits.shape[0]}; this request sent one"
        )
    log_probs = torch.log_softmax(logits[0].float(), dim=-1)[:-1]
    observed = log_probs.gather(1, input_ids[0, 1:].long().unsqueeze(1)).squeeze(1)
    mean_ll = float(observed.mean())
    body["scores"] = [round(mean_ll, 6)]
    body["scores_hex"] = [float(mean_ll).hex()]
    body["perplexity"] = [round(math.exp(-mean_ll), 4)]
    body["reduce"] = "mean"

    window = opts.get("position_range")
    if window:
        start, end = int(window[0]), int(window[1])
        if not (1 <= start <= end <= len(seq)):
            raise ValueError(
                f"position_range {[start, end]} is outside 1..{len(seq)} "
                f"(1-based and inclusive)"
            )
        count = (end - start + 1) * width
        if count > MAX_INLINE_VALUES:
            raise ValueError(
                f"position_range {[start, end]} is {count} floats, over the "
                f"{MAX_INLINE_VALUES} an inline reply may carry; narrow it (at "
                f"width {width} that is {MAX_INLINE_VALUES // max(1, width)} "
                f"positions) or ask for per_position_file"
            )
        body["position_embeddings"] = {
            "start": start,
            "end": end,
            "values": [_floats(hidden[i], decimals) for i in range(start - 1, end)],
        }

    if opts.get("per_position_log_prob"):
        if len(seq) > MAX_POSITIONS_INLINE:
            raise ValueError(
                f"per_position_log_prob was asked for a {len(seq)} bp sequence; "
                f"the inline limit is {MAX_POSITIONS_INLINE} positions"
            )
        body["per_position_log_prob"] = [round(float(x), decimals) for x in observed]
        # L-1 numbers, not L, and whoever plots them needs to know which: the
        # first base has no preceding context to be predicted from, so these are
        # 1-based positions 2..L.
        body["per_position_log_prob_positions"] = [2, len(seq)]

    if opts.get("per_position_file"):
        out_dir = Path(req_out_dir(opts))
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{opts.get('_name') or 'evo2'}_{layer}_embeddings.npy"
        # float32 on purpose: the model computes in bfloat16 and float32 is the
        # smallest format that carries every bit of it without a dtype a
        # downstream reader may not have.
        np.save(path, hidden.cpu().numpy().astype(np.float32))
        body["per_position_file"] = {
            "path": str(path),
            "format": "numpy .npy",
            "dtype": "float32",
            "shape": [int(hidden.shape[0]), width],
            "bytes": path.stat().st_size,
        }
    return body


def _predict_one(req: dict) -> dict:
    """One forward pass: score (the default) or embed."""
    records = _records(req.get("input") or req.get("sequence") or "")
    opts = dict(req.get("options") or {})
    task = str(opts.get("task", "score")).lower()
    opts["_out_dir"] = req.get("out_dir") or "."
    opts["_name"] = req.get("name") or "evo2"

    if DEVICE == "cuda":
        torch.cuda.reset_peak_memory_stats()
    if task == "score":
        body = _score(records, opts)
    elif task == "embed":
        body = _embed(records, opts)
    else:
        raise ValueError(f"unknown task {task!r}: this worker serves score | embed")

    body.update(
        {
            "model": "Evo 2",
            "model_name": MODEL_NAME,
            "weights_held_by": HOLDER,
            "kit_mode": MODE,
            "kit_route": ROUTE,
            "levers_applied": LEVERS,
        }
    )
    if DEVICE == "cuda":
        body["peak_reserved_gib"] = round(torch.cuda.max_memory_reserved() / 2**30, 2)
    return body


def _ready() -> dict:
    return {
        "build_s": round(BUILD_S, 1),
        "device": DEVICE,
        "model_name": MODEL_NAME,
        "hidden_size": HIDDEN,
        "num_layers": N_LAYERS,
        "default_embedding_layer": DEFAULT_LAYER,
        "weights_held_by": HOLDER,
        "kit_mode": MODE,
        "kit_route": ROUTE,
        "levers_applied": LEVERS,
        "max_bp": MAX_BP,
        "ptxas": PTXAS_WORD,
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
