"""RoseTTAFold3 held resident on the GPU, answering one request at a time.

Run by the model's own interpreter with the kit's mode variable in the
environment::

    ROSETTAFOLD3_OPT=fast <model python> rosettafold3_resident_worker.py \
        --socket … --slug … --weights-root …

That is the whole activation, and it is the form 30 of the 36 kits offer: the
kit installs ``rosettafold3_opt_autoload.pth``, which imports
``rosettafold3_opt._autoload`` at interpreter start; with ``ROSETTAFOLD3_OPT``
naming a mode, a meta-path finder waits for the first import of ``rf3`` and
calls ``rosettafold3_opt.enable(mode, strict=True)`` **before that package's
body executes**. The variable's name is the kit's own -- this kit spells
``ENV = "ROSETTAFOLD3_OPT"`` in both ``modes.py`` and ``_autoload.py`` -- read
off the kit by ``kit_launch``'s probe rather than guessed from the slug.

**Who holds the weights: this worker.** The kit replaces no loader. Its levers
are switches read when ``rf3.graph_flags`` is imported plus an adapter applied
right after ``rf3.model.RF3_structure`` executes; its own ``pred`` verb drives
inference by spawning ``python -m rf3.cli fold`` as a CHILD PROCESS per seed
(``rosettafold3_opt/fold.py``), so nothing in the kit holds a checkpoint
between folds -- a kit run pays the load every time, exactly as a per-request
subprocess would. Upstream's ``BaseInferenceEngine.initialize()`` is memoised
on ``self.initialized_``, so an engine built once and kept holds the network,
the 3,038,876,446-byte checkpoint and the Lightning Fabric device context
across requests. This worker builds it once and keeps it, under every mode,
and the ready line says ``weights_held_by=worker`` with the kit word beside it
so the record never reads as a claim about the kit.

What that buys is what the kit's own README declines to hide: "Every call also
pays ~25 s of start-up and checkpoint load plus each input's CPU featurization
in any mode, so the four-tile example gains less end to end than its prediction
time does." A held worker pays the start-up and the checkpoint once. On top of
that, ``fast`` and ``exact`` capture CUDA graphs of the sampler and the
pairformer stack, and a graph captured on one request is collectable only by a
process that survives to the next.

**Three orderings in this file are load-bearing rather than stylistic.**

*``import rf3`` comes before anything that could initialise CUDA.* That import
is the kit's trigger, and the kit's memory policy (``rosettafold3_opt/mem.py``)
exports ``PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,
garbage_collection_threshold:0.5`` during activation through the shared core's
``opt_core.mem.torch_alloc.export``, which REFUSES BY NAME when torch's CUDA
allocator is already initialised -- and one refused lever takes the whole mode
to NOT ACTIVE and the process to exit 3. Chai-1's provider hit that exact wall
from the other side. Nothing here touches ``torch.cuda`` before the trigger.

*No submodule of ``rf3`` is imported before the package itself.* The finder
arms on the package name; ``rf3.graph_flags`` imported first would have read
its switches before the row was exported, and ``stack.activate`` refuses that
by name (``LateActivationError``: "its switches were read at import").

*The checkpoint path is put in the environment before the trigger, under the
kit's own declared name.* ``_autoload.undeclared()`` refuses the process for
ANY ``ROSETTAFOLD3_OPT_*`` / ``ROSETTAFOLD3_BIG_*`` variable the kit does not
declare, so nothing else of ours may be spelled under that prefix, and
``ROSETTAFOLD3_OPT_CKPT`` -- which is declared -- is the right place for it.

**The tree state is a precondition this worker does not create.** The kit
modes run only on an interpreter whose five ``rf3`` files are the add-on's
(``rosettafold3_opt/tree.py``). ``tu remote setup``'s kit step is what applies
them, through the kit's own ``install.sh --rebind``; if it has not, the
activation refuses at ``import rf3`` and this process exits 3 before the socket
is bound. That is the right failure: it is loud, it is named, and it happens at
start rather than in the middle of a fold.

**Sampling settings are fixed at build, and that is upstream's shape rather
than a limitation invented here.** ``n_recycles``, ``diffusion_batch_size``,
``num_steps`` and ``early_stopping_plddt_threshold`` are ``__init__``
parameters of ``RF3InferenceEngine``: they feed the transform pipeline that
``initialize()`` builds, so changing one per request would mean rebuilding the
engine and re-reading the checkpoint -- which is the cost residency exists to
avoid. They are therefore set once, from ``--`` options at start, and default
to upstream's own (the kit's settings.py: "pred states NOTHING of its own").
What a request may change is everything ``run()`` takes: the inputs, the output
directory and the dump/annotation switches.

**The seed is applied per request, and what that does and does not cover is
stated.** Upstream applies a seed by calling ``lightning.fabric.seed_everything``
in the engine's ``__init__`` and by writing ``trainer.seed`` into the config the
trainer is built from. This worker re-applies the first of those before every
fold and sets ``engine.seed`` so the output file names carry it; the second is
fixed at the trainer built at start. Sampling draws come from the global RNG
state that ``seed_everything`` sets, so a request's seed does reproduce its
fold; what it does not do is rebuild the trainer, and a run that depended on
``trainer.seed`` being re-read would not see it.

One request at a time: two inside one CUDA context would interleave their
allocations and make an out-of-memory attributable to neither.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# stock/PINS.json "weights"."rf3"."filename" -- the one checkpoint every mode
# uses. The weights step verifies it against its pin before this process runs.
CKPT_NAME = "rf3_foundry_01_24_latest_remapped.ckpt"

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="rosettafold3", help="provider slug, echoed in ping")
ap.add_argument(
    "--weights-root",
    default="",
    help=f"directory holding {CKPT_NAME}; ROSETTAFOLD3_OPT_CKPT wins over it",
)
# Upstream's own inference defaults (models/rf3/configs/inference_engine/rf3.yaml,
# copied into stock/PINS.json "settings"."cli_defaults"). Fixed for the life of
# the process because they are engine __init__ parameters; see the docstring.
ap.add_argument("--n-recycles", type=int, default=10)
ap.add_argument("--diffusion-batch-size", type=int, default=5)
ap.add_argument("--num-steps", type=int, default=50)
ap.add_argument(
    "--early-stopping-plddt-threshold",
    type=float,
    default=0.5,
    help="upstream's default; 0 disables early stopping, which writes no structure",
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
    print(f"[rosettafold3-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds RoseTTAFold3's pinned
    stack and nothing of ToolUniverse, and importing the package would defeat
    that."""
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
            f"[rosettafold3-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

MODE = (os.environ.get("ROSETTAFOLD3_OPT") or "off").strip().lower() or "off"

# The checkpoint, before the trigger import. ROSETTAFOLD3_OPT_CKPT is one of
# the six names the kit declares (stack.ENV_NAMES), so setting it is safe;
# anything else under that prefix would take the process to NOT ACTIVE.
CKPT = os.environ.get("ROSETTAFOLD3_OPT_CKPT") or (
    os.path.join(os.path.expanduser(args.weights_root), CKPT_NAME)
    if args.weights_root
    else ""
)
if not CKPT or not os.path.isfile(CKPT):
    raise _refuse(
        f"[rosettafold3-resident] the pinned checkpoint is not at {CKPT or '<unset>'}: "
        f"pass --weights-root <dir> holding {CKPT_NAME}, or set "
        f"ROSETTAFOLD3_OPT_CKPT; `tu remote setup rosettafold3` fetches it"
    )
os.environ["ROSETTAFOLD3_OPT_CKPT"] = CKPT

# THE TRIGGER. Everything above this line is standard library. `import rf3`
# fires the kit's finder, which activates the mode and exports the row --
# including the allocator configuration, which must land before CUDA is
# initialised. Under ROSETTAFOLD3_OPT unset or "off" no finder was installed
# and this is an ordinary import.
import rf3  # noqa: E402,F401  -- imported for its side effect on the kit

import torch  # noqa: E402

torch.set_grad_enabled(False)

# What rf3/cli.py does first when it is not run with --verbose, and the engine
# repeats in its own __init__. Called here so the worker's transcript is the
# fold's lines and the kit's, not atomworks' and hydra's DEBUG stream -- a
# transcript nobody can read is the one nobody reads when a smoke fails. After
# the trigger import, never before it.
from foundry.utils.logging import (  # noqa: E402
    configure_minimal_inference_logging,
)

configure_minimal_inference_logging()

from hydra import compose, initialize_config_dir  # noqa: E402
from hydra.utils import instantiate  # noqa: E402
from lightning.fabric import seed_everything  # noqa: E402
from omegaconf import OmegaConf  # noqa: E402

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
say(
    f"imports done t={time.time() - T0:.1f}s torch={torch.__version__} "
    f"device={DEVICE} mode={MODE} ckpt={os.path.basename(CKPT)}"
)

# The kit says whether it engaged; ask it rather than assume. Under mode "off"
# the package exports nothing and status() reports inactive, which is correct.
try:
    import rosettafold3_opt

    _status = rosettafold3_opt.status()
except Exception as exc:  # noqa: BLE001 - the kit's absence is not fatal here
    _status = {"active": False, "reason": f"{type(exc).__name__}: {exc}"}
KIT_ACTIVE = bool(_status.get("active"))
KIT_LEVERS = list(_status.get("levers") or ())
TREE_STATE = _status.get("tree_state")
say(
    f"kit mode={MODE} active={KIT_ACTIVE} tree={TREE_STATE} "
    f"levers={len(KIT_LEVERS)} reason={_status.get('reason')}"
)

# Upstream's own config directory. rf3/cli.py picks it the same way: installed
# mode puts configs beside the package, a source checkout two levels up.
_RF3_DIR = Path(rf3.__file__).resolve().parent
CONFIG_DIR = _RF3_DIR / "configs"
if not CONFIG_DIR.is_dir():
    CONFIG_DIR = _RF3_DIR.parent.parent / "configs"

# run_inference()'s own split (rf3/inference.py): these keys are arguments of
# engine.run(), everything else in the composed config builds the engine.
_RUN_PARAM_KEYS = (
    "inputs",
    "out_dir",
    "dump_predictions",
    "dump_trajectories",
    "one_model_per_file",
    "annotate_b_factor_with_plddt",
    "sharding_pattern",
    "skip_existing",
    "template_selection",
    "ground_truth_conformer_selection",
    "cyclic_chains",
    "add_missing_atoms",
)
# Of those, the ones a request may set. `inputs` and `out_dir` come from the
# request itself; `sharding_pattern` is left out because the reply reports the
# files it found and a caller-chosen layout only makes that harder to read.
PASSTHROUGH = (
    "dump_predictions",
    "dump_trajectories",
    "one_model_per_file",
    "annotate_b_factor_with_plddt",
    "skip_existing",
    "template_selection",
    "ground_truth_conformer_selection",
    "cyclic_chains",
    "add_missing_atoms",
)

_t = time.time()
with initialize_config_dir(config_dir=str(CONFIG_DIR), version_base="1.3"):
    _cfg = compose(
        config_name="inference",
        overrides=[
            "inference_engine=rf3",
            f"ckpt_path={CKPT}",
            f"n_recycles={args.n_recycles}",
            f"diffusion_batch_size={args.diffusion_batch_size}",
            f"num_steps={args.num_steps}",
            f"early_stopping_plddt_threshold={args.early_stopping_plddt_threshold}",
        ],
    )
_cfg_dict = OmegaConf.to_container(_cfg, resolve=True)
assert isinstance(_cfg_dict, dict)
_init_cfg = OmegaConf.create(
    {k: v for k, v in _cfg_dict.items() if k not in _RUN_PARAM_KEYS}
)
ENGINE = instantiate(_init_cfg, _convert_="partial", _recursive_=False)
# The load, here rather than inside the first request: this is what residency
# means for this model. initialize() is memoised on self.initialized_, so every
# later run() finds the network and the checkpoint already in place.
ENGINE.initialize()
BUILD_S = time.time() - _t
HOLDER = "worker"
SETTINGS = {
    "n_recycles": args.n_recycles,
    "diffusion_batch_size": args.diffusion_batch_size,
    "num_steps": args.num_steps,
    "early_stopping_plddt_threshold": args.early_stopping_plddt_threshold,
}
say(
    f"model resident on {DEVICE} in {BUILD_S:.1f}s "
    f"(weights_held_by={HOLDER} kit={MODE} kit_active={KIT_ACTIVE})"
)


def _write_input(text: str, out_dir: Path) -> Path:
    """The request's input text on disk, as ``rf3 fold``'s ``inputs=`` wants it.

    Upstream takes a JSON specification, a CIF/PDB structure, a directory or a
    list of paths. A request carries text, so the two single-file forms are
    what this covers: JSON when it parses as JSON, otherwise a structure file.
    """
    stripped = text.lstrip()
    try:
        json.loads(text)
        suffix = ".json"
    except ValueError:
        if not stripped:
            raise ValueError("the request's 'input' is empty")
        suffix = ".cif"
    path = out_dir / f"input{suffix}"
    path.write_text(text, encoding="utf-8")
    return path


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _collect(out_dir: Path) -> tuple:
    """(files, predictions) from what upstream wrote.

    Upstream's layout per example (rf3/inference_engines/rf3.py, dump_* and
    RF3Output.dump): ``<out_dir>/<example_id>/`` holds
    ``<example_id>_model.cif`` and ``<example_id>_summary_confidences.json``,
    which are a COPY of the top-ranked sample, plus
    ``<example_id>_ranking_scores.csv``; every sample is also written whole to
    ``seed-<s>_sample-<i>/<example_id>_seed-<s>_sample-<i>_model.cif``. Both
    are reported, with ``top_ranked`` saying which is the copy, so a caller
    can take one file without reading the csv and a caller that wants all
    five is not made to guess the naming.
    """
    files = sorted(str(p) for p in out_dir.rglob("*") if p.is_file())
    predictions = []
    for summary in sorted(out_dir.rglob("*_summary_confidences.json")):
        body = _read_json(summary) or {}
        stem = summary.name.split("_summary_confidences")[0]
        cif = next(
            (
                str(c)
                for c in sorted(summary.parent.glob("*.cif"))
                if c.stem.startswith(stem)
            ),
            None,
        )
        if cif is None:
            cif = next((str(c) for c in sorted(summary.parent.glob("*.cif"))), None)
        predictions.append(
            {
                "name": stem,
                # The example-level pair is the copy upstream makes of the
                # best sample; the per-sample ones live one directory down.
                "top_ranked": not summary.parent.name.startswith("seed-"),
                "cif": cif,
                "summary_confidences": str(summary),
                "ptm": body.get("ptm"),
                "iptm": body.get("iptm"),
                "ranking_score": body.get("ranking_score"),
                "has_clash": body.get("has_clash"),
            }
        )
    predictions.sort(key=lambda p: (not p.get("top_ranked"), p["name"]))
    # An early-stopped fold writes a ranking_scores.csv saying so and no
    # structure at all. Say that rather than report an empty prediction list
    # and let the caller guess.
    if not predictions:
        for csv_path in sorted(out_dir.rglob("*_ranking_scores.csv")):
            head = csv_path.read_text(encoding="utf-8", errors="replace")[:400]
            if "early_stopped" in head:
                predictions.append(
                    {
                        "name": csv_path.name.split("_ranking_scores")[0],
                        "cif": None,
                        "early_stopped": True,
                        "ranking_scores_csv": str(csv_path),
                        "note": head.strip(),
                    }
                )
    return files, predictions


def _predict_one(req: dict) -> dict:
    """One fold. The request carries the input text, not a path."""
    text = req.get("input") or req.get("json")
    if not text:
        raise ValueError(
            "a request needs 'input': RoseTTAFold3's input specification as "
            'text -- JSON ([{"name": ..., "components": [{"seq": ..., '
            '"chain_id": ..., "chain_type": ...}]}]) or a CIF/PDB structure'
        )
    out_dir = Path(req["out_dir"]) / (req.get("name") or "rosettafold3")
    out_dir.mkdir(parents=True, exist_ok=True)
    input_path = _write_input(text, out_dir)
    results_dir = out_dir / "predictions"
    results_dir.mkdir(parents=True, exist_ok=True)

    opts = dict(req.get("options") or {})
    run_kwargs = {k: opts[k] for k in PASSTHROUGH if k in opts}

    seed = req.get("seed")
    if seed is not None:
        # The call upstream's engine makes in __init__, re-made here so a
        # request's seed reproduces its fold; engine.seed feeds the output
        # names (``<id>_seed-<s>_sample-<i>``).
        seed = int(seed)
        seed_everything(seed, workers=True, verbose=False)
    ENGINE.seed = seed

    if DEVICE == "cuda":
        torch.cuda.reset_peak_memory_stats()
    t = time.time()
    ENGINE.run(inputs=str(input_path), out_dir=str(results_dir), **run_kwargs)
    if DEVICE == "cuda":
        torch.cuda.synchronize()
    fold_s = time.time() - t

    files, predictions = _collect(results_dir)
    body = {
        "out_dir": str(results_dir),
        "input_file": str(input_path),
        "files": files,
        "predictions": predictions,
        "seed": seed,
        "settings": SETTINGS,
        "timing": {"fold_s": round(fold_s, 2)},
        "weights_held_by": HOLDER,
        "kit_mode": MODE,
        "kit_active": KIT_ACTIVE,
    }
    if DEVICE == "cuda":
        # The kit captures a CUDA graph of the diffusion step per fold and
        # warms it up on a fresh side stream, which its own comment says is
        # there to fill the "cuBLAS/cuDNN workspace"
        # (rf3_xattempt_addon/.../inference_sampler.py, the
        # `torch.cuda.Stream()` in `_sample_diffusion_predrawn`). Every fold
        # therefore abandoned a stream and left torch holding a 32 MiB
        # workspace for it: measured at +32.0 MiB a fold over five identical
        # folds, with no plateau, and a clear at the end giving back exactly
        # 7 x 32 MiB. Released, the same five folds hold flat.
        #
        # `WB.serve` gives them back after every request now and reports the
        # figure as `cublas_workspaces_freed_mib`; this worker briefly did it
        # itself. It is safe here although this provider's `fast` mode DOES
        # keep captured graphs across folds -- up to FPF_RF3_TG_MAX
        # pairformer-stack graphs in the FPF add-on's cache, replayed on later
        # requests. A workspace a capture allocates belongs to that graph's
        # private memory pool, so clearing hands the block back to a pool
        # nothing but a capture into the same pool draws from; see
        # `release_cublas_workspaces` for what was measured, on this torch and
        # on the other seven in the fleet.
        body["peak_reserved_gib"] = round(torch.cuda.max_memory_reserved() / 2**30, 2)
    return body


def _ready() -> dict:
    return {
        "build_s": round(BUILD_S, 1),
        "device": DEVICE,
        "weights_held_by": HOLDER,
        "kit_mode": MODE,
        "kit_active": KIT_ACTIVE,
        "kit_levers": KIT_LEVERS,
        "tree_state": TREE_STATE,
        "settings": SETTINGS,
        "ckpt": CKPT,
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
