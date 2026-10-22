"""Proteina-Complexa held resident on the GPU, answering one request at a time.

Run by the model's own interpreter with the kit's mode variable set::

    COMPLEXA_OPT=fast <model python> complexa_resident_worker.py \
        --socket ... --slug complexa --upstream <checkout> --weights-root <ckpts>

WHAT ONE REQUEST IS. A target protein's structure, a residue range cropping it,
a handful of hotspot residues on its surface, a binder length and a design
count. Per design the model integrates 400 flow-matching steps (default) over the
binder's CA coordinates and an 8-dimensional per-residue latent, conditioned on
the target, and a frozen autoencoder then decodes the binder's full atoms and
its amino-acid sequence. One PDB comes back per design: chain A the target
crop, chain B a protein that did not exist before.

WHY HOLDING IT HELPS, measured and stated at its true size (provider.toml has the
numbers). Upstream's only entry point is the console script ``complexa``, whose
``cli_runner`` execs ``python -m proteinfoundation.generate`` as a CHILD, so the
stock route pays per call: the interpreter and its import graph (jax, atomworks,
lightning: 12-25 s), the checkpoint read and model construction of a 415.2 M
parameter model (6.6 GiB on disk; 5-30 s) and the CUDA context. This worker pays
them once. What it does NOT save: Lightning's ``Strategy.teardown`` moves the
module back to the CPU at the end of every ``Trainer.predict``, so the weights
are uploaded again on each request -- which is also why an idle worker holds
almost no GPU memory. Nothing here compiles, so there is no compile trace to
keep: the gain is the process, not a cache.

THE SHAPE OF THE WRAP. Nothing of upstream is patched, copied or shadowed.
``generate.py``'s ``main()`` is a Hydra entry point that does the following in
order; this worker does the same, calling upstream's own functions, with the one
expensive step hoisted out of the loop:

    main()                                 this worker
    ---------------------------------      --------------------------------
    hydra composes the config              _compose(), per request
    validate_checkpoint_paths(cfg)         the same, per request
    check_cfg_validity(...)                the same, per request
    setup(cfg) -> root, seed_everything    the same, per request
    load_ckpt_n_configure_inference(cfg)   ONCE at start-up; per request only
                                           its last statement, configure_inference
    instantiate(dataloader); Trainer       the same, per request
    save_predictions(...)                  the same, per request

so the numerics, the seeding rule, the output layout and the file names are
upstream's. MEASURED to be the same thing, not argued: the held worker's design
for the smoke target, its second request, and the kit's own ``run.sh design`` in
a fresh process (same seed, same mode) are byte-identical, sha256 a37a8fd0...,
and so is a worker built from the lock in an empty venv.

WHAT WAS CHECKED BEFORE THIS FILE WAS TRUSTED, because STANDARD.md section 14
says a held engine built once cannot show that a SECOND can be built, and genie3
passed four identical requests and raised on the first rebuild. Each was run
against the real stack, in this process shape:

  * ``hydra.compose`` three times in one process: all three compose. Hydra's
    ``GlobalHydra`` is a singleton and ``initialize_config_dir`` raises on a
    second entry, which is the genie3 shape; ``GlobalHydra.instance().clear()``
    before each composition is what makes a rebuild possible, and it is in
    ``_compose`` for that reason.
  * ``model.configure_inference(...)`` a second and a third time on the held
    model. It is only an attribute assignment (``self.inf_cfg = ...``), so the
    "engine" a request changes is upstream's ``inf_cfg`` (``num_steps``, the
    model sampling block) plus what the KIT keeps between requests: one
    pair-bias buffer, replaced when the shape changes, and per-batch memos. The
    acceptance run therefore varies every one of those -- ``num_steps``,
    ``batch_size``, the target, the binder length, the seed -- and then returns to
    the first request, which must reproduce byte for byte.
  * the DataLoader's worker count. ``base_gen_data.yaml`` declares no
    ``num_workers``, so torch's default of 0 holds, but a resident worker that
    lets a loader fork is the recorded failure of openfold3 and boltz both, so
    this worker SETS it to 0 rather than inheriting a default an upstream edit
    could change. Every reply carries ``child_processes``, read from /proc, as
    the evidence nothing forked.
  * a CUDA probe that does something AFTERWARDS (protenix's LayerNorm passed and
    made the NEXT op raise): a GEMM, then a LayerNorm, then an SDPA call, then
    ``torch_scatter``'s ``scatter_mean`` on a CUDA tensor. That probe passed --
    and the first real request still failed, in ``torch.prod``, an op NOT in the
    probe, because torch 2.7.0+cu128's NVRTC does not know sm_121. See launch.py
    item 4. A probe proves the ops it ran.

THE KIT, AND WHAT IT DOES NOT NEED. ``complexa_opt`` activates the common way:
its ``.pth`` imports ``_autoload`` at interpreter start and, with
``COMPLEXA_OPT`` naming a kit mode, arms a finder on ``proteinfoundation.proteina``
that installs the mode's levers the moment that module's body has run. So
``import proteinfoundation.proteina`` is the FIRST import below, before torch
and before anything of ``generate``, and the levers attach to the model this
process then builds. Every lever of this kit is a torch-level class or function
patch -- a fused pair-bias LayerNorm+Linear, attention through
``scaled_dot_product_attention`` -- with no custom kernel anywhere, so none of
the kernel-versus-card failures of other providers has a surface here. All six
levers read ``state=on`` on the kit's own EXIT census after a held worker's
requests. (``state=partial`` appears in the transcript for the worker whose only
request failed before every lever had engaged; it is a record of that, not of
the provider.)

WHO HOLDS THE WEIGHTS: this worker, and the kit does not contest it.
``complexa_opt`` replaces no loader -- its levers patch the transformer, the
feature factories and the flow matchers, never ``Proteina.load_from_checkpoint``
-- so there is no second route into the load path and nothing here turns the
kit off by memoising. The ready line and every reply say so.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser(description="Proteina-Complexa resident worker")
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="complexa", help="provider slug, echoed in ping")
ap.add_argument(
    "--upstream", required=True, help="upstream's Proteina-Complexa checkout at the pin"
)
ap.add_argument(
    "--weights-root", required=True, help="directory holding the two checkpoints"
)
args = ap.parse_args()

T0 = time.time()


def _refuse(message: str) -> SystemExit:
    """A refusal exits 3, per STANDARD.md section 8; its message goes to stderr.

    ``raise SystemExit("text")`` prints the text and exits **1**, which the
    standard reserves for "failed". Fifty-four sites across eighteen workers
    got this wrong, every one with a correct message behind the wrong code, and
    the code is the half a caller branches on.
    """
    sys.stderr.write(str(message).rstrip("\n") + "\n")
    sys.stderr.flush()
    return SystemExit(3)


def say(msg: str) -> None:
    print(f"[complexa-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds Proteina-Complexa's
    pinned stack and nothing of ToolUniverse, and importing the package would
    defeat the separation the standard's section 2 is about."""
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
            f"[complexa-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

MODE = (os.environ.get("COMPLEXA_OPT") or "off").strip().lower()
UPSTREAM = Path(args.upstream).expanduser()
CFG_DIR = UPSTREAM / "configs"
CKPT_ROOT = Path(args.weights_root).expanduser()
PIPELINE = "search_binder_local_pipeline"
CKPT_NAME = "complexa.ckpt"
AE_NAME = "complexa_ae.ckpt"

if not (CFG_DIR / f"{PIPELINE}.yaml").is_file():
    raise _refuse(
        f"[complexa-resident] {CFG_DIR} holds no {PIPELINE}.yaml, so --upstream "
        f"is not Proteina-Complexa's checkout at the pin. The lock installs it "
        f"editable; `tu remote setup complexa --only environment` rebuilds it."
    )
for _name in (CKPT_NAME, AE_NAME):
    if not (CKPT_ROOT / _name).is_file():
        raise _refuse(
            f"[complexa-resident] {CKPT_ROOT / _name} is absent. "
            f"`tu remote setup complexa --only weights` fetches and verifies "
            f"both checkpoints through the kit's own fetcher."
        )

# THE KIT'S TRIGGER, first and whole. complexa_opt/_autoload.py arms a finder on
# this exact module and calls complexa_opt.enable(mode) the moment its body has
# executed; everything the levers patch is reachable from it. Importing any
# other proteinfoundation submodule first would mean patching after some of its
# targets were already bound.
import proteinfoundation.proteina  # noqa: E402,F401

import torch  # noqa: E402

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
if DEVICE != "cuda":
    # upstream's own setup() asserts this; saying it here names the provider
    # rather than surfacing as an AssertionError three frames in.
    raise _refuse(
        "[complexa-resident] no CUDA device: this provider declares "
        '[gpu] policy = "required" and upstream asserts torch.cuda.is_available()'
    )

import hydra  # noqa: E402
import lightning as L  # noqa: E402
from hydra import compose, initialize_config_dir  # noqa: E402
from hydra.core.global_hydra import GlobalHydra  # noqa: E402
from loguru import logger as _loguru  # noqa: E402

from proteinfoundation.generate import (  # noqa: E402
    check_cfg_validity,
    load_ag_ckpt,
    load_ckpt_n_configure_inference,
    save_predictions,
    setup as _upstream_setup,
    validate_checkpoint_paths,
)

say(
    f"imports done t={time.time() - T0:.1f}s torch={torch.__version__} "
    f"cuda={torch.version.cuda} device={torch.cuda.get_device_name(0)} "
    f"mode={MODE}"
)

# The kit's own Hydra override grammar, asked of the kit rather than copied.
# `inputs.overrides` renders the target entry as the two tokens upstream takes:
# `++generation.task_name=<item>` and ONE dictionary merge
# `++generation.target_dict_cfg={<item>:{...}}`. The dotted per-key form cannot
# be used -- Hydra's KEY grammar rejects a path element starting with a digit --
# and that is the kind of fact a hand-rolled copy gets wrong once and silently.
from complexa_opt import inputs as kit_inputs  # noqa: E402

# UPSTREAM'S OWN OVERRIDES FOR THE GENERATION STAGE, and nothing else.
#
# The shipped configuration runs a best-of-n search that scores every design
# with upstream's AlphaFold2 reward model, whose parameters live under $AF2_DIR
# and which the kit's weights step does not fetch. This provider runs the
# GENERATION STAGE ALONE, which is upstream's own documented pair of overrides
# -- `stock/PINS.json` names them under "generation_stage" and the kit's README
# puts the same two in its `$GEN` example -- not a setting invented here.
BASE_OVERRIDES = [
    f"++ckpt_path={CKPT_ROOT}",
    f"++ckpt_name={CKPT_NAME}",
    f"++autoencoder_ckpt_path={CKPT_ROOT / AE_NAME}",
    "++generation.search.algorithm=single-pass",
    "++generation.reward_model=null",
    # A resident worker must not let a loader fork: the parent has CUDA and the
    # kit's patched modules long before a request arrives, and fork() copies
    # only the calling thread. 0 is also what the shipped configuration already
    # resolves to (base_gen_data.yaml declares no num_workers), so this changes
    # no behaviour -- it pins it against an upstream edit.
    "++generation.dataloader.num_workers=0",
]

_ITEM_SAFE = re.compile(r"[^A-Za-z0-9_]+")


def _compose(extra):
    """One composed Hydra config.

    ``GlobalHydra.instance().clear()`` is the load-bearing line. Hydra keeps a
    process-wide singleton and ``initialize_config_dir`` raises on a second
    entry, so without this a held worker composes exactly once and every later
    request raises -- the genie3 failure, which four identical requests cannot
    see because they would all reuse one composition if one were cached.
    Measured here before the worker was written: three consecutive composes in
    one process, all three succeeding.
    """
    GlobalHydra.instance().clear()
    with initialize_config_dir(version_base=None, config_dir=str(CFG_DIR)):
        return compose(
            config_name=PIPELINE, overrides=list(BASE_OVERRIDES) + list(extra)
        )


def _seed_and_root(cfg, item, run_name):
    """Upstream's ``setup()``, with the one thing a resident process must undo.

    ``setup()`` computes the run's root directory, asserts CUDA and calls
    ``lightning.seed_everything(cfg.seed + job_id)`` -- the seeding rule that
    makes a run reproducible, and the reason ``++root_path`` is NOT used here
    (``generate.py`` skips ``setup()`` entirely when it is set, and the seeding
    with it).

    It also calls ``loguru.logger.add(sys.stdout, ...)``. In upstream's
    one-shot process that happens once; in a held worker it happens per request
    and loguru accumulates a sink every time, so by the tenth request every log
    line is printed ten times. The handler ids added by the call are removed
    afterwards. Nothing else of ``setup()`` is changed, and the seeding and the
    path rule stay upstream's.
    """
    before = set(_loguru._core.handlers)
    root = _upstream_setup(
        cfg,
        create_root=True,
        config_name=PIPELINE,
        job_id=0,
        task_name=item,
        run_name=run_name,
    )
    for handler_id in set(_loguru._core.handlers) - before:
        try:
            _loguru.remove(handler_id)
        except ValueError:
            pass
    return root


# ---------------------------------------------------------------- build once
_BUILD_CFG = _compose([])
validate_checkpoint_paths(_BUILD_CFG)
say("reading 6.6 GiB of checkpoint and constructing the model ...")
MODEL = load_ckpt_n_configure_inference(_BUILD_CFG)
torch.set_float32_matmul_precision("high")  # upstream's own line (generate.py:596)
BUILD_S = time.time() - T0
N_PARAMS = sum(p.numel() for p in MODEL.parameters())
GIB = 2**30
# Two peaks, kept apart on purpose. The BUILD has a high-water mark of its own
# (upstream's Lightning loader restores the checkpoints' CUDA tensors onto the
# card), and a held worker's worst case is the larger of that and any request's,
# so `peak_reserved_gib` -- what a host adds up -- is the running maximum of
# both and never goes down. But a ladder wants to know what an INPUT costs, and a
# running maximum that opens at the build's figure hides every request smaller
# than it. So each request resets torch's counter, reads its own peak, and folds
# it into the running one.
HIGH_RESERVED = torch.cuda.max_memory_reserved()
BUILD_PEAK_GIB = HIGH_RESERVED / GIB
# The loader's transient is still cached when it returns; release it so the first
# request's own figure is its own (it read 7.93 GiB for a 36-residue binder when
# the cache was left in place, which is the build, not the request).
torch.cuda.empty_cache()
torch.cuda.reset_peak_memory_stats()
say(
    f"model built t={BUILD_S:.1f}s params={N_PARAMS / 1e6:.1f}M "
    f"build_peak_reserved={BUILD_PEAK_GIB:.2f} GiB "
    f"held_allocated={torch.cuda.memory_allocated() / GIB:.2f} GiB "
    f"held_reserved={torch.cuda.memory_reserved() / GIB:.2f} GiB"
)

HOLDER = "worker"  # the kit replaces no loader; see the module docstring

# three-letter to one-letter, for reporting the decoded binder sequence back to
# the caller. Reading it off the PDB this run just wrote is independent of how
# upstream orders its residue-type integers.
_AA3 = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLN": "Q",
    "GLU": "E",
    "GLY": "G",
    "HIS": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
}


def _chain_sequence(pdb_path: Path, chain: str) -> str:
    """The one-letter sequence of ``chain`` in ``pdb_path``, read off its CA atoms.

    Raises when the file cannot be read: an empty string here once stood for
    "unreadable" and "no such chain" at once, and a caller cannot tell them apart.
    """
    out = []
    with open(pdb_path, "r", errors="replace") as handle:
        for line in handle:
            if not line.startswith("ATOM"):
                continue
            if line[21] != chain or line[12:16].strip() != "CA":
                continue
            out.append(_AA3.get(line[17:20].strip().upper(), "X"))
    return "".join(out)


def _child_count() -> int:
    """Live child processes of this worker, read from /proc (no dependency)."""
    try:
        with open(f"/proc/{os.getpid()}/task/{os.getpid()}/children") as handle:
            return len(handle.read().split())
    except OSError:
        return -1


def _triton_cache_files() -> int:
    """Files in this worker's private Triton cache; -1 when none was set."""
    directory = os.environ.get("TRITON_CACHE_DIR")
    if not directory:
        return -1
    return sum(len(files) for _root, _dirs, files in os.walk(directory))


def _kit_record() -> dict:
    """The kit's own activation record for this process, if it wrote one.

    ``activate.py`` writes ``<COMPLEXA_OPT_RECORD>/kit_<pid>.json`` carrying the
    lever census and, at exit, the TALLY state. Reading it back is how a reply
    can say the mode actually engaged rather than that the variable was set --
    "the model started" is not evidence it did what the manifest says.
    """
    directory = os.environ.get("COMPLEXA_OPT_RECORD")
    if not directory:
        return {}
    path = Path(directory) / f"kit_{os.getpid()}.json"
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return {
        "mode": doc.get("mode"),
        "tier": doc.get("tier"),
        "levers": {k: v.get("state") for k, v in (doc.get("levers") or {}).items()},
        "gpu": (doc.get("gpu") or {}).get("label"),
    }


# ------------------------------------------------------------- one request
# THE CEILINGS, and the tool (complexa_tool.py) repeats them so a refusal costs
# milliseconds; a test reads both files and fails if they differ. They bound the
# PRODUCT, because progen2 allowed 16 sequences of 1024 tokens -- each sane, the
# product 116.93 GiB -- and this architecture's pair track is N^2 in
# (target crop + binder) with the batch multiplying it, so the same trap is
# available here. The corner the three ceilings admit together is
# (300 + 200)^2 x 16 = 4,000,000, which is the number MAX_PAIR_CELLS_X_BATCH
# states: it is redundant today and is there so raising any one ceiling alone
# cannot admit an unmeasured request. provider.toml carries the ladder the product was measured
# against and the row [gpu] vram_budget_gb is declared at.
MIN_BINDER_LENGTH = 20
MAX_BINDER_LENGTH = 200
MAX_TARGET_RESIDUES = 300
MAX_DESIGNS = 16
MAX_PAIR_CELLS_X_BATCH = 4_000_000
MIN_STEPS = 10
MAX_STEPS = 400
MAX_PDB_BYTES = 4 * 1024 * 1024


def _int_field(spec: dict, key: str, default: int, low: int, high: int) -> int:
    value = spec.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"'{key}' must be an integer")
    if not low <= value <= high:
        raise ValueError(f"'{key}' must be {low}..{high}")
    return value


def _spec(req) -> dict:
    raw = req.get("input")
    if raw is None:
        raise ValueError("a request needs 'input': a Proteina-Complexa design spec")
    spec = json.loads(raw) if isinstance(raw, (str, bytes)) else dict(raw)

    pdb_text = spec.get("target_pdb")
    if not isinstance(pdb_text, str) or not pdb_text.strip():
        raise ValueError(
            "a request needs 'target_pdb': the target structure as PDB text"
        )
    if len(pdb_text.encode("utf-8", "replace")) > MAX_PDB_BYTES:
        raise ValueError(f"'target_pdb' is larger than {MAX_PDB_BYTES} bytes")
    target_input = str(spec.get("target_input") or "").strip()
    match = re.fullmatch(r"([A-Za-z0-9])(-?\d+)-(-?\d+)", target_input)
    if not match:
        raise ValueError(
            f"'target_input' must be a chain and residue range like 'A1-115'; "
            f"got {target_input!r}"
        )
    chain, lo, hi = match.group(1), int(match.group(2)), int(match.group(3))
    target_residues = hi - lo + 1
    if not 1 <= target_residues <= MAX_TARGET_RESIDUES:
        raise ValueError(
            f"'target_input' crops {target_residues} residues; this provider "
            f"accepts 1..{MAX_TARGET_RESIDUES}"
        )
    hotspots = spec.get("hotspot_residues") or []
    if not isinstance(hotspots, list) or not hotspots:
        raise ValueError(
            "'hotspot_residues' must be a non-empty list like ['A37','A39']: "
            "they are what the binder is designed against"
        )
    for h in hotspots:
        if not isinstance(h, str) or not re.fullmatch(r"[A-Za-z0-9]-?\d+", h.strip()):
            raise ValueError(f"hotspot {h!r} must be <chain><residue number>, e.g. A37")

    binder_length = _int_field(
        spec, "binder_length", 80, MIN_BINDER_LENGTH, MAX_BINDER_LENGTH
    )
    designs = _int_field(spec, "num_designs", 1, 1, MAX_DESIGNS)
    batch = min(_int_field(spec, "batch_size", designs, 1, MAX_DESIGNS), designs)
    steps = _int_field(spec, "num_steps", MAX_STEPS, MIN_STEPS, MAX_STEPS)
    default_seed = req.get("seed") if isinstance(req.get("seed"), int) else 5
    seed = _int_field(spec, "seed", default_seed, 0, 2**31 - 1)

    tokens = target_residues + binder_length
    if tokens * tokens * batch > MAX_PAIR_CELLS_X_BATCH:
        raise ValueError(
            f"(target {target_residues} + binder {binder_length})^2 x batch "
            f"{batch} = {tokens * tokens * batch} exceeds this provider's "
            f"{MAX_PAIR_CELLS_X_BATCH}, which is the envelope its VRAM budget was "
            f"measured at. Peak grows as N^2 in the pair track and linearly in "
            f"the batch; lower 'batch_size' to split the same design count into "
            f"more forward passes, or re-measure the budget."
        )
    return {
        "pdb_text": pdb_text,
        "target_input": f"{chain}{lo}-{hi}",
        "target_residues": target_residues,
        "hotspots": [h.strip() for h in hotspots],
        "binder_length": binder_length,
        "designs": designs,
        "batch": batch,
        "steps": steps,
        "seed": seed,
    }


def _design_once(req: dict) -> dict:
    global HIGH_RESERVED
    spec = _spec(req)
    held_before = torch.cuda.memory_reserved()
    torch.cuda.reset_peak_memory_stats()
    name = str(req.get("name") or "design")
    item = "tu_" + (_ITEM_SAFE.sub("_", name).strip("_") or "target")
    run_name = item
    seed = spec["seed"]

    work = Path(req["out_dir"]) / name
    work.mkdir(parents=True, exist_ok=True)
    # The caller's structure, written into the request directory. It is a .pdb
    # that a failed run also leaves behind, which is why [runtime] outputs is
    # not `*.pdb`.
    target = work / "target.pdb"
    target.write_text(spec["pdb_text"])

    entry = {
        "source": "tooluniverse",
        "target_filename": target.stem,
        "target_path": str(target),
        "target_input": spec["target_input"],
        "hotspot_residues": list(spec["hotspots"]),
        # [L, L] -- equal ends mean a fixed binder length and no RNG draw
        # (gen_dataset.UniformInt). A range would also make the kit's
        # `pair_assembly` lever idle by its declared `padded_batches` gate.
        "binder_length": [spec["binder_length"], spec["binder_length"]],
        "pdb_id": None,
    }
    target_tokens = kit_inputs.overrides(item, entry)

    overrides = target_tokens + [
        f"++generation.dataloader.dataset.nres.nsamples={spec['designs']}",
        "++generation.dataloader.dataset.nrepeat_per_sample=1",
        f"++generation.dataloader.batch_size={spec['batch']}",
        f"++generation.search.max_batch_size={spec['batch']}",
        f"++generation.args.nsteps={spec['steps']}",
        f"++seed={seed}",
        f"++run_name={run_name}",
    ]

    t = time.time()
    cfg = _compose(overrides)
    validate_checkpoint_paths(cfg)
    check_cfg_validity(cfg.generation.dataloader.dataset, cfg.generation.args)
    # THE ENGINE KEY. What a caller varies -- num_steps, target, hotspots,
    # binder length, design count, seed -- reaches the model through this call
    # (upstream's `inf_cfg`) and through the dataloader instantiated below, on a
    # model whose checkpoints are read once. configure_inference is an attribute
    # assignment, so it is cheap and cannot itself fail twice; what could go stale
    # is the kit's per-shape state, and the acceptance run varies every axis
    # and returns to request one.
    MODEL.configure_inference(cfg.generation, nn_ag=load_ag_ckpt(cfg.generation.args))
    configure_s = time.time() - t

    previous = os.getcwd()
    os.chdir(work)  # upstream roots ./inference and ./logs at the working directory
    try:
        root_path = _seed_and_root(cfg, item, run_name)
        dataloader = hydra.utils.instantiate(cfg.generation.dataloader)
        if getattr(dataloader, "num_workers", 0):
            # A RuntimeError, not a refusal: this runs per request, and a
            # SystemExit here would take the held model down with it.
            raise RuntimeError(
                f"the composed dataloader asks for {dataloader.num_workers} "
                f"loader workers; a resident worker must not fork one (CUDA is "
                f"already initialised in this process). "
                f"++generation.dataloader.num_workers=0 is set in "
                f"BASE_OVERRIDES and should have held."
            )
        trainer = L.Trainer(
            accelerator="gpu",
            devices=1,
            logger=False,
            enable_checkpointing=False,
            enable_progress_bar=False,
            enable_model_summary=False,
            inference_mode=False,  # upstream's own value: refinement needs grad
        )
        t = time.time()
        predictions = trainer.predict(MODEL, dataloader)
        torch.cuda.synchronize()
        predict_s = time.time() - t

        t = time.time()
        pdb_paths, reward_df = save_predictions(
            root_path, predictions, job_id=0, cath_codes=None
        )
        save_s = time.time() - t
        # RESOLVED HERE, while the working directory is still the request's.
        # save_predictions returns paths relative to it ("./inference/..."), and
        # resolving them after the chdir below would point at the wrong tree --
        # which an earlier draft did, and which surfaced as a design with an
        # empty sequence and a path to nothing, because the sequence reader
        # swallowed the OSError. Both are checked now.
        root_abs = Path(root_path).resolve()
        pdb_paths = [str(Path(q).resolve()) for q in pdb_paths]
    finally:
        os.chdir(previous)

    designs = []
    for path in sorted(pdb_paths):
        p = Path(path)
        sequence = _chain_sequence(p, "B")
        if len(sequence) != spec["binder_length"]:
            # A reply is not a result. Upstream returned normally and wrote a
            # file; what the caller asked for was a binder of this length, and a
            # file without one is the openfold3 shape (success, nothing made).
            raise RuntimeError(
                f"{p.name}: chain B holds {len(sequence)} residues, not the "
                f"{spec['binder_length']} requested; the design is not a binder "
                f"of the requested length and is not returned"
            )
        designs.append(
            {
                "name": p.stem,
                "path": path,
                "binder_sequence": sequence,
                "binder_length": len(sequence),
            }
        )
    if not designs:
        # Upstream returns normally from a run that decoded nothing -- its own
        # timing CSV is written with nsamples=0 -- so an empty list here would
        # be a success reply for a failure, which is the openfold3 shape this
        # standard exists to prevent.
        wrote = sorted(q.name for q in root_abs.rglob("*") if q.is_file())[:8]
        raise RuntimeError(
            f"Proteina-Complexa wrote no design for {name!r}: the run returned "
            f"normally and save_predictions produced no PDB. What it wrote was "
            f"{wrote or 'nothing at all'}; the worker transcript is the record."
        )

    request_peak = torch.cuda.max_memory_reserved()
    HIGH_RESERVED = max(HIGH_RESERVED, request_peak)
    # Give the allocator's cache back. Lightning empties it once, inside
    # predict(), but what upstream then does with the batch's tensors regrows it,
    # and a reserve that is never returned ratchets with the batch: measured at
    # 0.16 GiB per design left cached after a request (5.01 GiB after 32). The
    # next request pays nothing for it -- the weights are re-uploaded either way
    # -- and an idle worker should not hold a co-tenant's memory.
    del predictions, dataloader, trainer
    import gc

    gc.collect()
    torch.cuda.empty_cache()
    files = sorted(str(q) for q in root_abs.rglob("*") if q.is_file())
    body = {
        "out_dir": str(root_abs),
        "files": files,
        "designs": designs,
        "n_designs": len(designs),
        "seed": seed,
        "num_steps": spec["steps"],
        "target_residues": spec["target_residues"],
        "binder_length": spec["binder_length"],
        "batch_size": spec["batch"],
        "timing": {
            "configure_s": round(configure_s, 2),
            "predict_s": round(predict_s, 2),
            "save_s": round(save_s, 2),
        },
        "weights_held_by": HOLDER,
        "kit_mode": MODE,
        "loader_workers": 0,
        # Direct evidence for "nothing forked": the processes this worker has as
        # children when the request is done. 0 is the only acceptable answer
        # (see STANDARD.md section 15: a resident worker that has run host-tensor
        # work must not let a library fork).
        "child_processes": _child_count(),
        # And for the Triton audit in provider.toml [env]: this stack's Triton
        # cannot lower a cross-lane reduction, so what matters is that nothing on
        # the path COMPILES a Triton kernel. `triton` is imported (torch._dynamo's
        # presence check, via lightning), which means nothing; the launcher gives
        # this worker a private empty cache, and a compiled kernel would leave
        # files in it.
        "triton_cache_files": _triton_cache_files(),
        # this request's own high-water mark; the running one is below
        "request_peak_reserved_gib": round(request_peak / GIB, 2),
        "reserved_before_gib": round(held_before / GIB, 2),
        "reserved_after_gib": round(torch.cuda.memory_reserved() / GIB, 2),
        "peak_reserved_gib": round(HIGH_RESERVED / GIB, 2),
    }
    record = _kit_record()
    if record:
        body["kit_record"] = record
    return body


def _predict_one(req: dict) -> dict:
    """``_design_once`` with its traceback written to the transcript.

    The supervisor carries back only the exception's message, which for a CUDA
    or NVRTC failure is a page of generated source with the Python frame nowhere
    in it. The transcript is the record, so the frame goes there.
    """
    global HIGH_RESERVED
    try:
        return _design_once(req)
    except Exception:
        import traceback

        # A request that died of memory is exactly the one whose peak a host
        # needs; fold it in before the next request resets the counter.
        HIGH_RESERVED = max(HIGH_RESERVED, torch.cuda.max_memory_reserved())
        say("request failed:\n" + traceback.format_exc())
        raise


def _ready() -> dict:
    body = {
        "build_s": round(BUILD_S, 1),
        "device": DEVICE,
        "gpu": torch.cuda.get_device_name(0),
        "weights_held_by": HOLDER,
        "kit_mode": MODE,
        "parameters_m": round(N_PARAMS / 1e6, 1),
        "build_peak_reserved_gib": round(BUILD_PEAK_GIB, 2),
        "held_allocated_gib": round(torch.cuda.memory_allocated() / GIB, 2),
        "held_reserved_gib": round(torch.cuda.memory_reserved() / GIB, 2),
        "upstream": str(UPSTREAM),
        "checkpoints": [str(CKPT_ROOT / CKPT_NAME), str(CKPT_ROOT / AE_NAME)],
        "loader_workers": 0,
        "max_binder_length": MAX_BINDER_LENGTH,
        "max_target_residues": MAX_TARGET_RESIDUES,
        "max_designs": MAX_DESIGNS,
        "max_pair_cells_x_batch": MAX_PAIR_CELLS_X_BATCH,
    }
    record = _kit_record()
    if record:
        body["kit_record"] = record
    return body


if __name__ == "__main__":
    raise SystemExit(
        WB.serve(
            slug=args.slug,
            socket_path=args.socket,
            on_predict=_predict_one,
            ready=_ready,
            log=say,
        )
    )
