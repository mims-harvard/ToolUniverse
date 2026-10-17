"""GPN-Star held resident on the GPU, answering one request at a time.

Run by the model's own interpreter with the kit's mode variable in the
environment::

    GPNSTAR_OPT=exact <model python> gpnstar_resident_worker.py --socket ... --slug ... --model v100-200m

**What one request is.** A list of single-nucleotide variants -- chrom, 1-based
pos, ref, alt -- scored against an alignment store this host holds. GPN-Star is
a masked language model over a window of a multiple-species alignment, not over
a bare DNA string: for each variant the window around it is read from the store
(``--msa-path`` upstream: a zarr, one array per chromosome, one column per
species), the variant's column is masked in the target row, and the score is the
mean over the forward and reverse-complement windows of logit(alt) - logit(ref)
at that column. Negative: the alternate base is less likely than the reference
given what the alignment shows. There is no genome FASTA; the reference base is
the alignment's own target column, and a ``ref`` that disagrees is an error
upstream, which this worker passes on by name.

**What is held.** Upstream's own ``MLMforVEPModel`` (the model, fp32, eval), the
kit's levers on it, and one open ``GenomeMSA`` over the alignment store. What a
request still pays is tokenizing the windows and the forward pass. The scores
come out of upstream's own ``create_inference_runner`` and ``Trainer.predict`` --
the pass ``gpn star vep`` runs -- not out of a reimplementation of the forward,
which is what lets a request be compared byte for byte with the kit's CLI. The
one thing done differently from ``run_inference`` is how the tokenizing transform
is registered; see ``_Transform``.

**Activation** is the common form (30 of 36 kits): the kit installs
``gpnstar_opt_autoload.pth`` and, with ``GPNSTAR_OPT=exact`` set, a finder waits
for the first import of ``gpn.star.inference`` and arms the three wrapper
constructors, so every model one of them builds is placed on the GPU with the
levers applied. Nothing is modified, copied or shadowed. The variable's name is
read off the kit by ``kit_launch``'s probe (``_autoload.ENV``), never derived
from the slug.

**Who holds the weights: this worker.** The kit does not replace the loader; it
patches the model the wrapper's constructor returns. So the weights are read by
upstream's ``from_pretrained`` from the snapshot directory the weights step
certified, and this process holds the result.

**What a request may ask for is bounded in this file as well as in the tool**,
and the bound that matters is a PRODUCT. Peak memory follows the batch shape
(batch_size x window_size tokens), not the variant count, because the variants
are fed through in batches: ``MAX_VARIANTS`` bounds time and the reply, and
``MAX_BATCH_TOKENS`` bounds the product of the two axes that multiply. Each of
``MAX_BATCH`` and ``MAX_WINDOW`` is sane alone and the corner of both is not,
which is progen2's lesson (two sane ceilings, a 116.93 GiB product).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import struct
import sys
import time
from pathlib import Path

# The checkpoint this worker serves: the kit's own key, and the three facts the
# worker needs about it. stock/PINS.json variants.v100-200m / weights.*.
MODELS = {
    "v100-200m": {
        "repo": "songlab/gpn-star-hg38-v100-200m",
        "revision": "0c949f132d35619a3eb188b402848c998a3313ae",
        "n_species": 100,
        "native_window": 128,
    },
}

# ------------------------------------------------------------------ bounds
# Mirrored in gpnstar_tool.py and in provider.toml's [gpu] block. Raise them in
# all three together, after measuring: the budget is declared at the corner these
# admit TOGETHER, not at the smoke.
MAX_VARIANTS = 2048
MIN_WINDOW = 16
MAX_WINDOW = 512
MAX_BATCH = 64
DEFAULT_BATCH = 8
MAX_BATCH_TOKENS = 8192
# The second product, and the one that bounds TIME rather than memory: variants x
# window columns in one request. Measured on a contended card, 262,144 tokens took
# 165-211 s and 524,288 took 260-286 s (a flat ~0.5 ms a token), against a 900 s
# request timeout. Without it 2048 variants at window 512 is ~1M tokens, 520 s on
# a quiet-ish card and past the timeout on a busy one -- a request the supervisor
# would kill half done.
MAX_REQUEST_TOKENS = 524_288
NUCLEOTIDES = "ACGT"
CHROM_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,32}$")

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="gpnstar", help="provider slug, echoed in ping")
ap.add_argument(
    "--model",
    default="v100-200m",
    choices=sorted(MODELS),
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
    print(f"[gpnstar-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds GPN-Star's pinned stack and
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
            f"[gpnstar-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

MODEL_KEY = args.model
SPEC = MODELS[MODEL_KEY]
MODE = (os.environ.get("GPNSTAR_OPT") or "off").strip().lower() or "off"

# Before huggingface_hub is imported, which is when these are read. The snapshot
# is pinned and digest-checked by the weights step; a hub call from this process
# would mean something had gone wrong, and the honest outcome is an error rather
# than a silent 0.8 GB transfer at request time.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
# No .pyc into the shared kit checkout, which `tu remote setup` refuses when it
# has local modifications.
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def _snapshot() -> str:
    """The pinned snapshot directory under HF_HOME, or a named refusal.

    ``--model-path`` must be the SNAPSHOT DIRECTORY (kit README): given a repo id,
    upstream asks the Hub for the phylogenetic-distance files, which fails offline.
    """
    home = os.environ.get("HF_HOME")
    if not home:
        raise _refuse(
            "[gpnstar-resident] HF_HOME is not set: it must name the directory "
            "`tu remote setup gpnstar --only weights` filled. This worker will "
            "not let upstream fetch a checkpoint at request time"
        )
    snap = (
        Path(home).expanduser()
        / "hub"
        / f"models--{SPEC['repo'].replace('/', '--')}"
        / "snapshots"
        / SPEC["revision"]
    )
    for need in (
        "config.json",
        "model.safetensors",
        "phylo_dist/pairwise.npy",
        "phylo_dist/in_clade.npy",
    ):
        if not (snap / need).is_file():
            raise _refuse(
                f"[gpnstar-resident] {snap / need} is not there. Run "
                f"`tu remote setup gpnstar --only weights`"
            )
    return os.fspath(snap)


def _msa_root() -> tuple:
    """(path, kind): the operator's alignment store, else the kit's sparse example.

    The store is an INPUT, never fetched (42 GB zip, ~64 GB unpacked for the real
    hg38 100-way). The kit ships a 0.14 MiB sparse cut covering eight example
    windows; a provider pointed at nothing else answers for those and refuses the
    rest by name.
    """
    env = os.environ.get("TOOLUNIVERSE_GPNSTAR_MSA_ROOT")
    if env:
        p = Path(env).expanduser()
        if not p.is_dir():
            raise _refuse(
                f"[gpnstar-resident] TOOLUNIVERSE_GPNSTAR_MSA_ROOT={env} is not a "
                f"directory. It must hold <n_species>/all.zarr (upstream's "
                f"--msa-path), e.g. <root>/100/all.zarr"
            )
        return os.fspath(p), "operator"
    kit = os.environ.get("MODEL_OPT")
    if not kit:
        raise _refuse(
            "[gpnstar-resident] neither TOOLUNIVERSE_GPNSTAR_MSA_ROOT nor MODEL_OPT "
            "is set, so there is no alignment store to read"
        )
    p = Path(kit) / "examples" / "msa"
    if not p.is_dir():
        raise _refuse(
            f"[gpnstar-resident] the kit's example alignment {p} is absent; point "
            f"TOOLUNIVERSE_GPNSTAR_MSA_ROOT at an alignment store"
        )
    return os.fspath(p), "kit-example-sparse"


SNAPSHOT = _snapshot()
MSA_ROOT, MSA_KIND = _msa_root()

import numpy as np  # noqa: E402
import torch  # noqa: E402

torch.set_grad_enabled(False)

if not torch.cuda.is_available():
    raise _refuse(
        "[gpnstar-resident] CUDA is not available to this interpreter: the "
        "provider declares [gpu] policy = required"
    )
DEVICE = "cuda"

# The kit's trigger is `gpn.star.inference`: the finder fires on its import and
# arms the wrapper constructors. A mode that cannot engage prints one
# `[gpnstar-opt] NOT ACTIVE` line and exits 3 from inside this import --
# deliberately not caught, because a worker that swallowed it would serve stock
# under the name of the kit.
from datasets import Dataset, disable_caching  # noqa: E402
from transformers import TrainingArguments  # noqa: E402

from gpn.inference import create_inference_runner  # noqa: E402
from gpn.star.data import GenomeMSA  # noqa: E402
from gpn.star.inference import VEPInference  # noqa: E402
from gpn.star.utils import find_directory_sum_paths  # noqa: E402

disable_caching()

say(
    f"imports done t={time.time() - T0:.1f}s torch={torch.__version__} "
    f"device={DEVICE} model={MODEL_KEY} kit={MODE}"
)

_t = time.time()
MSA_PATHS = find_directory_sum_paths(MSA_ROOT)
if sum(MSA_PATHS) != SPEC["n_species"]:
    raise _refuse(
        f"[gpnstar-resident] the alignment store under {MSA_ROOT} holds "
        f"{sorted(MSA_PATHS)} species (summing to {sum(MSA_PATHS)}); "
        f"{MODEL_KEY} reads {SPEC['n_species']}"
    )
# Every chromosome the store names, lazily: `in_memory=False` keeps zarr arrays
# unread, so opening 25 of them costs listings and no data.
GENOME_MSA = [
    GenomeMSA(path, n_species=n, subset_chroms=None, in_memory=False)
    for n, path in MSA_PATHS.items()
]
CHROMS = set()
for g in GENOME_MSA:
    CHROMS |= set(g.data)
CHROM_LEN = {}
for g in GENOME_MSA:
    for c, arr in g.data.items():
        CHROM_LEN[c] = min(int(arr.shape[0]), CHROM_LEN.get(c, 1 << 62))

# Upstream's own constructor, and the kit's arm: MLMforVEPModel is built from
# the snapshot DIRECTORY, then the arm places `.model` on the GPU and applies the
# levers right there.
INFERENCE = VEPInference(
    SNAPSHOT,
    GENOME_MSA,
    SPEC["native_window"],
    model_revision=None,
)
BUILD_S = time.time() - _t
HOLDER = "worker"


def _kit_report() -> dict:
    """The kit's own account of what it did, or an empty one under `off`."""
    if MODE in ("", "off"):
        return {}
    try:
        import gpnstar_opt

        return dict(gpnstar_opt.status() or {})
    except Exception as exc:  # noqa: BLE001 - the kit's absence is not fatal here
        return {"status_error": f"{type(exc).__name__}: {exc}"}


# THE KIT'S `graph` LEVER IS TAKEN OUT HERE, BY THE KIT'S OWN FUNCTION, and the
# reason is a measurement rather than a preference. The lever captures one whole-
# forward CUDA graph per distinct (batch, window) shape up to 2048 tokens, and
# every captured graph keeps its activation pool: on this card 29 distinct small
# shapes walked `max_memory_reserved` from 1.0 to 24.3 GiB, ~0.8 GiB a shape, and
# nothing in the kit bounds the number of shapes. A request is allowed to pick its
# own batch_size and window_size, so the number of shapes is a caller's choice and
# the VRAM a held worker needs would be a function of how many different shapes
# anyone had ever asked for. No [gpu] vram_budget_gb can state that, and a budget
# that cannot be stated cannot be scheduled on. The other seven levers (device-side
# constants, the de-duplicated K/V projection, the column-attention rewrites) keep
# their memory inside the allocator's cache and are untouched.
# `unpatch_graphs` is public API (gpnstar_opt.accel.api) and puts `model.forward`
# back to the function the graph runner wrapped; nothing is patched or shadowed.
# TOOLUNIVERSE_GPNSTAR_GRAPHS=on keeps the lever for a host that wants the speed
# and has measured the memory.
GRAPHS = (os.environ.get("TOOLUNIVERSE_GPNSTAR_GRAPHS") or "off").strip().lower()
if GRAPHS not in ("on", "off"):
    raise _refuse(
        f"[gpnstar-resident] TOOLUNIVERSE_GPNSTAR_GRAPHS={GRAPHS!r} is not on|off"
    )
if MODE not in ("", "off") and GRAPHS == "off":
    from gpnstar_opt.accel.api import graph_report, unpatch_graphs

    if graph_report(INFERENCE.model.model) is not None:
        unpatch_graphs(INFERENCE.model.model)
        say("kit lever graph: declined (unpatch_graphs; see the comment above)")

REPORT = _kit_report()
LEVERS = [
    str(x)
    for x in (REPORT.get("levers") or [])
    if not (x == "graph" and GRAPHS == "off")
]
LEVERS_DECLINED = ["graph"] if (GRAPHS == "off" and MODE not in ("", "off")) else []
KIT_ACTIVE = bool(REPORT.get("active"))
if MODE not in ("", "off") and not KIT_ACTIVE:
    # The wrapper's engage is what activates the kit; a model built without it
    # would be stock. Say so rather than serve it under the kit's name.
    raise _refuse(
        f"[gpnstar-resident] GPNSTAR_OPT={MODE} but the kit reports no active "
        f"model after the build: {REPORT}"
    )
N_PARAMS = sum(p.numel() for p in INFERENCE.model.model.parameters())
say(
    f"model resident on {DEVICE} in {BUILD_S:.1f}s (model={MODEL_KEY} "
    f"params={N_PARAMS / 1e6:.0f}M weights_held_by={HOLDER} kit={MODE} "
    f"levers={len(LEVERS)} msa={MSA_KIND} species={SPEC['n_species']} "
    f"chroms={len(CHROMS)})"
)


# --------------------------------------------------------------- the request
class _Transform:
    """A dataset transform that hashes to a constant instead of to its owner.

    It calls the function it wraps and nothing else. ``__reduce__`` is what
    ``datasets``' fingerprinting pickles, and it returns no state -- not the
    function, whose ``self`` drags the model into the pickle. Caching is
    disabled (``disable_caching()``), so the fingerprint is never read back.
    """

    def __init__(self, fn):
        self.fn = fn

    def __call__(self, batch):
        return self.fn(batch)

    def __reduce__(self):
        return (_Transform, (None,))


def _int(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name!r} must be an integer, got {value!r}")
    return value


def _parse(text: str) -> dict:
    try:
        doc = json.loads(text)
    except ValueError as exc:
        raise ValueError(
            f"the input is not JSON ({exc}); it must be an object with a "
            f"'variants' list of {{chrom, pos, ref, alt}}"
        ) from None
    if not isinstance(doc, dict):
        raise ValueError("the input must be a JSON object with a 'variants' list")
    unknown = sorted(set(doc) - {"variants", "window_size", "batch_size"})
    if unknown:
        raise ValueError(
            f"unknown input field(s) {unknown}; this worker takes variants, "
            f"window_size and batch_size"
        )

    window = _int(doc.get("window_size", SPEC["native_window"]), "window_size")
    if window % 2:
        raise ValueError(
            f"window_size {window} is odd; upstream requires an even window "
            f"(the variant sits at index window/2 of the forward window)"
        )
    if not MIN_WINDOW <= window <= MAX_WINDOW:
        raise ValueError(
            f"window_size {window} is outside {MIN_WINDOW}..{MAX_WINDOW} (the "
            f"{MODEL_KEY} native window is {SPEC['native_window']})"
        )
    batch = _int(doc.get("batch_size", DEFAULT_BATCH), "batch_size")
    if not 1 <= batch <= MAX_BATCH:
        raise ValueError(f"batch_size {batch} is outside 1..{MAX_BATCH}")
    if batch * window > MAX_BATCH_TOKENS:
        raise ValueError(
            f"batch_size {batch} x window_size {window} = {batch * window} "
            f"tokens per forward; the limit is {MAX_BATCH_TOKENS}. Peak memory "
            f"follows that product, and it is what the declared VRAM budget "
            f"covers -- lower either one"
        )

    rows = doc.get("variants")
    if not isinstance(rows, list) or not rows:
        raise ValueError(
            "'variants' must be a non-empty list of {chrom, pos, ref, alt}"
        )
    if len(rows) > MAX_VARIANTS:
        raise ValueError(
            f"{len(rows)} variants; this worker takes {MAX_VARIANTS} at most per "
            f"request (split the list: requests queue on one held worker)"
        )
    if len(rows) * window > MAX_REQUEST_TOKENS:
        raise ValueError(
            f"{len(rows)} variants x window_size {window} = {len(rows) * window} "
            f"alignment columns in one request; the limit is {MAX_REQUEST_TOKENS} "
            f"(at window {window}, {MAX_REQUEST_TOKENS // window} variants). That "
            f"bounds the request's duration, not its memory -- split the list"
        )
    chrom, pos, ref, alt, ids = [], [], [], [], []
    half = window // 2
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {"chrom", "pos", "ref", "alt"}:
            raise ValueError(
                f"variant {i} must be an object with exactly chrom, pos, ref, alt; "
                f"got {row!r}"
            )
        c = row["chrom"]
        if isinstance(c, int) and not isinstance(c, bool):
            c = str(c)
        if not isinstance(c, str) or not CHROM_RE.match(c):
            raise ValueError(f"variant {i}: chrom {c!r} is not a chromosome name")
        # The store names its arrays as upstream's table must: `1`, no `chr`
        # prefix, for the hg38 stores. Accept either spelling and use the one
        # the store has, so a VCF's `chr1` is not an error about a name.
        key = None
        for cand in (c, c[3:] if c.lower().startswith("chr") else "chr" + c):
            if cand in CHROMS:
                key = cand
                break
        if key is None:
            raise ValueError(
                f"variant {i}: chromosome {c!r} is not in the alignment store "
                f"({len(CHROMS)} arrays: {', '.join(sorted(CHROMS)[:12])}"
                f"{'...' if len(CHROMS) > 12 else ''}). The kit's sparse example "
                f"store holds chromosomes 1, 2, 3 and 5 only"
            )
        p = _int(row["pos"], "pos")
        if p < 1:
            raise ValueError(f"variant {i}: pos {p} must be 1-based, so >= 1")
        if p - 1 - half < 0 or p - 1 + half > CHROM_LEN[key]:
            raise ValueError(
                f"variant {i}: the {window}-bp window around {c}:{p} runs off the "
                f"alignment's chromosome (0..{CHROM_LEN[key]})"
            )
        r, a = row["ref"], row["alt"]
        for label, v in (("ref", r), ("alt", a)):
            if not isinstance(v, str) or len(v) != 1 or v.upper() not in NUCLEOTIDES:
                raise ValueError(
                    f"variant {i}: {label} {v!r} must be one of A C G T -- this is "
                    f"a single-nucleotide-variant model, not an indel scorer"
                )
        r, a = r.upper(), a.upper()
        if r == a:
            raise ValueError(f"variant {i}: ref and alt are both {r}")
        chrom.append(key)
        pos.append(p)
        ref.append(r)
        alt.append(a)
        ids.append(f"{c}:{p}:{r}>{a}")
    return {
        "window": window,
        "batch": batch,
        "chrom": chrom,
        "pos": pos,
        "ref": ref,
        "alt": alt,
        "ids": ids,
    }


def _score(req: dict) -> dict:
    spec = _parse(req.get("input") or "")
    opts = dict(req.get("options") or {})
    decimals = max(1, min(8, int(opts.get("decimals", 5))))
    n = len(spec["pos"])

    columns = {k: list(spec[k]) for k in ("chrom", "pos", "ref", "alt")}
    # A ONE-ROW table makes upstream's own `gpn star vep` fail -- stock, no kit,
    # any batch size: "Error: Must pass 2-d input. shape=()". The Trainer hands
    # back a 0-d array for a single prediction and `postprocess` builds a frame
    # from it. Every other size works, including a final batch of one (9 rows at
    # batch 8 is fine), so the defect is the dataset's total row count and not
    # the batch shape. The variant is therefore sent TWICE and the first score is
    # kept; the reply says so. This feeds upstream a valid input rather than
    # changing upstream, and what it costs is one extra window in a batch of two.
    padded = n == 1
    if padded:
        columns = {k: v * 2 for k, v in columns.items()}
    dataset = Dataset.from_dict(columns)
    # Upstream's own invariants are applied by create_inference_runner
    # (inference_training_arguments); what is set here is what the CLI's defaults
    # are, plus the three things a held worker must state:
    #   dataloader_num_workers=0  -- a forked loader child dies in a process that
    #       already holds CUDA and the kit's graph pool (openfold3), and the CLI's
    #       own default is 0, so this changes nothing about the result;
    #   report_to="none"          -- no tracker is installed and none is wanted;
    #   per_device_eval_batch_size -- the request's batch_size, which is the axis
    #       the declared VRAM budget is a function of.
    training = TrainingArguments(
        per_device_eval_batch_size=spec["batch"],
        dataloader_num_workers=0,
        report_to="none",
        disable_tqdm=True,
    )
    INFERENCE.window_size = spec["window"]
    t = time.time()
    try:
        # The two public calls upstream's own `run_inference` makes -- a runner,
        # then `runner.predict` -- and its `postprocess`, with ONE difference:
        # the transform is registered through `_Transform` below. `run_inference`
        # calls `dataset.set_transform(inference.tokenize_function)`, and `datasets`
        # fingerprints a transform by pickling it with dill; a bound method pickles
        # its `self`, which is the whole VEPInference -- model, alignment handles,
        # tokenizer -- so every request walked ~66,000 objects for ~4-10 s to
        # compute a cache key that `disable_caching()` then throws away. Measured
        # here: 4.8 s of a 5.4 s call, against 0.4 s for the forward itself. In a
        # CLI that runs once per process and nobody sees it; in a held worker it
        # is paid per request, and it is the one cost residency was not saving.
        dataset.set_transform(_Transform(INFERENCE.tokenize_function))
        runner = create_inference_runner(
            INFERENCE.model, training, output_prefix="gpn-star-vep-"
        )
        predictions = runner.predict(dataset)
        frame = INFERENCE.postprocess(predictions)
    except ValueError as exc:
        text = str(exc)
        if "Reference allele mismatch" in text and "genome has '-'" in text:
            raise ValueError(
                f"{text}. The alignment holds no data at that position: the store "
                f"is sparse or the position lies outside it "
                f"({MSA_KIND} store; the kit's example store covers only the "
                f"windows of its eight example variants)"
            ) from None
        raise
    torch.cuda.synchronize()
    forward_s = time.time() - t

    raw = [float(x) for x in frame["score"].tolist()][:n]
    if len(raw) != n or any(not math.isfinite(v) for v in raw):
        raise RuntimeError(
            f"{n} variants went in, {len(raw)} scores came out and "
            f"{sum(not math.isfinite(v) for v in raw)} of them are not finite"
        )
    digest = hashlib.sha256(b"".join(struct.pack(">d", v) for v in raw)).hexdigest()
    body = {
        "task": "vep",
        "n_variants": n,
        "window_size": spec["window"],
        "batch_size": spec["batch"],
        "n_batches": math.ceil((2 if padded else n) / spec["batch"]),
        "ids": spec["ids"],
        "single_variant_sent_twice": padded,
        "scores": [round(v, decimals) for v in raw],
        "scores_sha256": digest,
        "timing": {"vep_s": round(forward_s, 3)},
    }
    return body


def _predict_one(req: dict) -> dict:
    body = _score(req)
    kit = _kit_report()
    body.update(
        {
            "model": "GPN-Star",
            "model_name": MODEL_KEY,
            "weights_held_by": HOLDER,
            "kit_mode": MODE,
            "levers_applied": LEVERS,
            "levers_declined": LEVERS_DECLINED,
            "alignment": MSA_KIND,
            # The kit's own route tally -- how many batch shapes ran on the
            # unified-K/V, de-dup or stock projection route -- which is the
            # engine-key evidence: a new (batch, window) shape moves it.
            "kit_kv_routes": kit.get("kv"),
            "peak_reserved_gib": round(torch.cuda.max_memory_reserved() / 2**30, 2),
        }
    )
    return body


def _ready() -> dict:
    return {
        "build_s": round(BUILD_S, 1),
        "device": DEVICE,
        "model_name": MODEL_KEY,
        "n_params": N_PARAMS,
        "weights_held_by": HOLDER,
        "kit_mode": MODE,
        "levers_applied": LEVERS,
        "levers_declined": LEVERS_DECLINED,
        "alignment": MSA_KIND,
        "limits": {
            "max_variants": MAX_VARIANTS,
            "window": [MIN_WINDOW, MAX_WINDOW],
            "max_batch": MAX_BATCH,
            "max_batch_tokens": MAX_BATCH_TOKENS,
            "max_request_tokens": MAX_REQUEST_TOKENS,
        },
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
