"""OpenFold3 held resident on the GPU, answering one request at a time.

Run by the model's own interpreter with the kit's mode variable in the
environment::

    OPENFOLD3_OPT=fast <model python> openfold3_resident_worker.py --socket … --slug …

Why holding matters here. Stock OpenFold3's only entry point is
``run_openfold predict``, which builds an ``InferenceExperimentRunner``, reads
2,287,928,519 bytes of fp32 checkpoint into it, calls ``Trainer.predict`` once
and exits. The kit measures the model construction alone at 68 s stock and 14 s
with its ``fast_init`` lever, and that is before the checkpoint read, the CUDA
context, the Triton compiles and the CUDA graphs the sampler captures on its
first pass. All of it is identical for every request, so this worker pays it
once: the runner, its ``lightning_module`` and its weights stay in this process
between requests, and only the output directory, the query set, the callbacks
and the Lightning trainer are rebuilt per call.

**Who holds the weights.** Unlike Chai-1, OpenFold3 has no loader called
repeatedly inside a fold -- ``InferenceExperimentRunner.setup()`` loads the
checkpoint once -- so there is nothing here for a worker to memoise, and this
worker memoises nothing of upstream. What it must not do is take over the load
path, because under a kit mode the kit already owns it: the ``ckpt_mmap`` lever
replaces ``openfold3.core.utils.checkpoint_loading_utils.load_checkpoint`` with
a memory-mapping call of its own, and ``fast_init`` replaces the model
construction that precedes it. Patching either from here would be a second
route into a process the kit allows only one of, and the kit's own
``late_activation_gate`` refuses exactly that. Under ``[kit] mode = "off"``
nothing replaces them and the plain upstream path runs. The ready line and
every reply say which of the two it was, as Chai-1's worker does.

**The featurisation loader runs in-process, and it has to.** Upstream
configures ``data_module_args.num_workers = 10`` (``entry_points/validator.py``
``DataModuleArgs``) and the kit's ``loader_workers`` lever caps that at the
item count -- ``max(1, min(items, configured))``, never 0, because zero moves
featurisation's RNG draws into the main process. One query therefore still
forks one DataLoader child, and the first smoke on a GB10 died there::

    [openfold3-opt/loader_workers] predict loader: 1 item(s), workers 10 -> 1
    RuntimeError: DataLoader worker (pid(s) 778073) exited unexpectedly

with no traceback from the child, which is torch's wording for a worker killed
by a signal rather than raising. Host memory was not short (61 GB free) and
``/dev/shm`` is 61 GB, so neither of the usual two causes applies; nothing in
``openfold3/core/data/`` touches CUDA, so the child did not kill itself with a
CUDA call either. What is left is the fork itself: a resident worker is a
long-lived process that has already built the model and initialised CUDA
(``cuda_max_reserved_mib=1408`` before the request arrived), and ``fork()``
copies only the calling thread while the kit's hooks, cuEquivariance, DeepSpeed
and Triton leave threads and handles behind it. This repository already carries
the shape: ``boltz_tool.py`` -- "Multiprocessing data-loader workers can
deadlock when Boltz is launched from a long-lived MCP worker process" -- and
Boltz-2's provider passes ``--num_workers 0`` for exactly this.

So this worker sets the count to 0. That is not a patch of the kit and not a
setting tried at random: the kit's own ``plan()`` short-circuits on it --
``if configured <= 0: return configured  # 0 workers configured: the engine
featurises in-process; as configured`` -- so the lever stays on and steps aside
by its own rule, and ``DataModuleConfig.num_workers`` defaults to 0 in the data
module itself. The honest cost is the one the kit names: with no worker
processes, ``worker_init_fn`` never runs and featurisation's random draws come
from the DataLoader's own generator in this process instead. Featurisation-level
randomness is therefore not bit-comparable with a forked run at the same seed;
the model seeds, which ``RankSpecificSeedCallback`` owns, are untouched.

**What residency here does not buy, stated rather than discovered.** Lightning
moves the module back to the CPU at the end of every ``predict``
(``Strategy.teardown``: "moving model to CPU"), so the ~2.1 GiB of weights are
re-uploaded host to device on each request. What a held worker saves is
everything upstream of that -- the 2,287,928,519-byte checkpoint read, the
model construction, the CUDA context, the Triton compiles and the sampler's
captured graphs -- and that is the large half. Pinning the module to the device
would mean patching Lightning's teardown, which also releases what the kit's
``post_release`` lever expects to release, so it is left alone until a
measurement says it is worth the argument.

**The second request in a held worker, and why the first one proves nothing.**
A single smoke passes on a provider that cannot serve twice. This one did: the
first request folded, the second raised ``Offset increment outside graph
capture encountered unexpectedly`` from the ``torch.randint`` in the kit's
``sync_hoist`` cell, deterministically, for every repeat of a shape already
folded. ``sync_hoist`` is the messenger, not the cause; the chain, each step
read from a log line rather than inferred:

1. Lightning moves the module to the CPU at the end of every ``predict`` and
   back to the device at the next one, so every parameter's address changes
   between requests. The kit's ``trunk_graph`` cell checks exactly that
   (``_storage_signature``) and refuses to replay a graph over moved storage:
   the second request's first trunk call is counted ``storage_moved`` and the
   captured graph is dropped -- correctly.
2. Dropping it deletes the only CUDA graph in the cell's process-wide graph
   pool, but the cell keeps the pool HANDLE (``release()`` clears it; the
   ``storage_moved`` path does not). The re-capture two calls later hands that
   handle to ``torch.cuda.graph(...)``, the allocator finds the pool with a use
   count of zero and the capture dies inside ``capture_begin``::

       [openfold3-opt/trunk_graph] capture FAILED for n_tok=35 (RuntimeError:
       it->second->use_count > 0 INTERNAL ASSERT FAILED at
       ".../c10/cuda/CUDACachingAllocator.cpp":2731 ...) — this key runs eager

3. ``trunk_graph`` catches that, marks the key uncapturable and runs the call
   eagerly, so nothing raises YET. But a capture that began and never ended
   leaves the default CUDA generator with its ``capturing_`` flag set, and the
   next eager draw from it is the one that reports the damage. The kit names
   this failure itself, in
   ``opt_core.capture.graphs.reset_generator_capture_state``: "clearing the
   'capturing' flag a failed capture leaves behind ('Offset increment outside
   graph capture' on every later eager draw)". ``trunk_graph`` does not call
   that recovery, so the exception surfaces at the next request's first MSA
   depth draw -- ``sync_hoist.py``'s ``torch.randint`` -- and upstream catches
   it per query, which is why it arrives as "wrote no structure".

A length ladder hides all of this: a new token count makes ``trunk_graph``
call its own ``release()``, which clears the pool, so consecutive requests of
DIFFERENT shapes never reach step 2. Only a repeated shape does.

**So this worker forces the kit's item boundary.** ``post_release`` already
drops every between-items resident of the graph machinery -- ``of3_graphs``'s
generation and pool, ``of3t_paircache``'s static buffers, ``trunk_graph``'s
graphs (through the ``release()`` that clears the pool handle) -- and already
states that above its gate "every item re-captures by design" and that the
result is "bitwise with the gate forced on every item". It simply never fires
here: its gate is ``n_tok >= 2400`` or free memory below 16 GB, and a 35- or
800-residue fold on a 128 GB card is neither (measured: ``pre_confidence=0
post_forward=0 kept=1``). ``OPENFOLD3_OPT_POST_RELEASE_NTOK = 0`` puts the
gate on every item. That is the kit's own knob, not a patched cell and not an
ablation: the fast line exports ``OPENFOLD3_OPT_POST_RELEASE``, and the kit's
conflict rule says in so many words that the line carrying a cell lever leaves
the family's parameters -- "size gates, caps, core pins" -- to the caller
(``modes.resolve`` under this setting returns no conflicts). What it costs is
one re-capture per request instead of a replayed graph; see ``[gpu]`` in
``provider.toml`` for the measurement.

**Where upstream puts the exception.** ``predict_step`` catches everything a
fold raises, logs one ``ERROR`` line and appends the traceback to
``<log_dir>/predict_err_rank0.log`` (``_log_predict_exception``); the writer
callback then counts the query failed, writes its summary and the run returns
normally. ``log_dir`` is ``<output_dir>/logs`` and the lightning module is
handed it once, at construction -- so in a resident worker every traceback
lands under ``_BIRTH_DIR`` below, not under the request's own output
directory. That is the file to read when a request comes back with
``structures: []``; the module docstring of ``provider.toml`` records what it
held the first time.

Four orderings in this file are load-bearing rather than stylistic:

* ``_reconcile_kit_row()`` comes before the trigger import, because the kit's
  conflict check reads ``os.environ`` at activation and the row this process
  inherited was resolved without the manifest's ablation. Its own docstring
  has the refusal it prevents.

* ``_force_item_boundary_release()`` comes before the trigger import too: the
  ``post_release`` cell reads its gate out of ``os.environ`` once, at
  activation, and activation is what the trigger import runs.
* ``import openfold3`` comes before anything that could touch the GPU. That
  import is the kit's trigger: the ``.pth`` installed at interpreter start arms
  a finder which patches the package the moment its body has run, and the
  kit's ``alloc_expandable`` lever wants to export
  ``PYTORCH_CUDA_ALLOC_CONF`` while CUDA is still uninitialised.
* No submodule of ``openfold3`` is imported before the package itself, for the
  same reason: the kit's gate refuses a late activation by name, naming the
  target that was already imported.
* The runner's configuration -- the runner YAML that carries the mode's
  precision and kernel settings -- is asked of the kit rather than copied from
  it (``openfold3_opt.cli.member_yaml``). A hard-coded copy drifts the first
  time the kit moves.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="openfold3", help="provider slug, echoed in ping")
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
    print(f"[openfold3-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds OpenFold3's pinned stack
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
            f"[openfold3-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

MODE = (os.environ.get("OPENFOLD3_OPT") or "off").strip().lower()

# The kit's gate knob for `post_release`, the one setting that makes a held
# worker able to serve the same shape twice. See _force_item_boundary_release.
_POST_RELEASE_NTOK = "OPENFOLD3_OPT_POST_RELEASE_NTOK"


def _reconcile_kit_row() -> None:
    """Make this process's environment agree with the line the kit will run.

    The launcher reads the kit's mode row in a probe interpreter
    (``kit_launch._PROBE`` -> ``modes.resolve(mode, home)``) and exports it, and
    it reads that row *before* it adds ``MODEL_OPT_LEVERS_OFF``. So under an
    ablation the two disagree: the inherited row still names every lever of the
    unablated line, and the kit's own conflict rule -- "the modes set their own
    switches" -- refuses the whole activation on the difference::

        [openfold3-opt] NOT ACTIVE: OPENFOLD3_OPT_PAIR='trimul_v4:triatt_block:
        pair_transition' preset, the fast line sets 'trimul_v4:triatt_block'
        (mode=fast)

    and the process exits 3 before it binds its socket. This provider declares
    ``[kit] levers_off = ["pair_transition"]`` (see ``provider.toml`` for why),
    so it meets that refusal on every start.

    Nothing here decides anything. The resolution is the kit's own, computed in
    this process, where ``MODEL_OPT_LEVERS_OFF`` is set; applying its
    ``exports`` and ``unsets`` is what ``openfold3_opt.stack.activate`` does a
    moment later anyway. Doing it before the trigger import only means the
    conflict check, which reads ``os.environ``, sees the row this process will
    actually run instead of the stale one it inherited. A conflict that
    survives is a real one and is said out loud rather than left for the
    NOT ACTIVE line.

    ``openfold3_opt.modes`` imports neither ``torch`` nor ``openfold3``
    (measured: both absent from ``sys.modules`` after it), so this runs ahead of
    the trigger without arming or disarming anything.
    """
    if MODE == "off":
        return
    try:
        from openfold3_opt import env as kit_env
        from openfold3_opt import modes as kit_modes
    except ImportError as exc:  # noqa: BLE001 - a kitless environment still serves
        say(f"the optimization kit is not importable ({exc}); nothing to reconcile")
        return
    resolution = kit_modes.resolve(MODE, kit_env.tree_home())
    before = dict(os.environ)
    for name in resolution.unsets:
        os.environ.pop(name, None)
    os.environ.update(resolution.exports)
    changed = sorted(
        k for k in set(before) | set(os.environ) if before.get(k) != os.environ.get(k)
    )
    off = os.environ.get("MODEL_OPT_LEVERS_OFF") or "none"
    say(
        f"kit row reconciled for levers_off={off}: "
        f"{', '.join(changed) if changed else 'the inherited row already agreed'}"
    )
    if resolution.conflicts:
        say(f"the kit still reports conflicts: {'; '.join(resolution.conflicts)}")


_reconcile_kit_row()


def _force_item_boundary_release() -> None:
    """Put the kit's ``post_release`` gate on every item, which is what makes
    this worker able to answer a second request at a shape it has already
    folded.

    The module docstring has the chain in full. In one line: a resident worker
    hands the same shape to ``trunk_graph`` twice with a Lightning CPU round
    trip in between, the cell drops its graph for the moved storage but keeps
    the emptied pool handle, the re-capture into that handle trips the
    allocator's use-count assertion, and a capture that began and never ended
    leaves the CUDA generator flagged as capturing -- so the NEXT eager draw
    raises ``Offset increment outside graph capture encountered unexpectedly``.

    ``post_release`` releases ``trunk_graph``'s graphs through the cell's own
    ``release()``, which clears the pool handle with them, so a forced gate
    means no request ever meets a pool its graphs have left. The kit calls the
    forced gate exact ("bitwise with the gate forced on every item") and leaves
    the knob to the caller (the fast line carries the lever; its parameters are
    then ours). ``setdefault`` so an operator who has set it keeps their value
    -- and the ready line says which value is in force, because a worker
    running with the kit's 2400 default is a worker that fails on request two.
    """
    if MODE == "off":
        return
    os.environ.setdefault(_POST_RELEASE_NTOK, "0")
    say(
        f"{_POST_RELEASE_NTOK}={os.environ[_POST_RELEASE_NTOK]}: the kit's "
        f"item-boundary release fires on every item, so each request captures "
        f"its own trunk graph instead of meeting the last request's emptied "
        f"graph pool (see the module docstring)"
    )


_force_item_boundary_release()

# The kit's trigger package, first and whole. Everything the kit patches lives
# under it, and the finder disarms once this import returns.
import openfold3  # noqa: E402,F401

import torch  # noqa: E402

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
say(f"imports done t={time.time() - T0:.1f}s torch={torch.__version__} device={DEVICE}")


def _ask_kit() -> tuple[str, str]:
    """``(runner yaml, checkpoint file name)``, both asked of the kit.

    The mode's runner YAML carries its precision and kernel settings, and the
    checkpoint's name is in the kit's own pin table. Neither is written down
    here: a kit that moves either would otherwise take this worker with it,
    silently. With no kit installed, upstream's own defaults apply and the
    checkpoint is whatever ``OPENFOLD3_CKPT`` names.
    """
    try:
        from openfold3_opt import cli as kit_cli
        from openfold3_opt import env as kit_env
        from openfold3_opt import modes as kit_modes
        from openfold3_opt import weights as kit_weights
    except ImportError as exc:  # noqa: BLE001 - a kitless environment still serves
        say(f"the optimization kit is not importable ({exc}); upstream defaults apply")
        return "", ""
    home = kit_env.tree_home()
    _line_name, line = kit_modes.line_of(MODE)
    resolution = kit_modes.resolve(MODE, home)
    yaml_path = kit_cli.member_yaml(
        home, line, getattr(resolution, "precision", None), MODE, 0
    )
    pinned = kit_weights.pinned_files(home)
    return yaml_path, (pinned[0]["local"] if pinned else "")


RUNNER_YAML, CKPT_NAME = _ask_kit()


def _checkpoint() -> Path:
    """The weights file, from ``OPENFOLD3_CKPT`` or from the weights root the
    manifest declares plus the name the kit pins. Nothing is fetched here: the
    setup step verified every declared file against its digest, and a worker
    that reached for a CDN mid-request would undo that."""
    named = os.environ.get("OPENFOLD3_CKPT")
    if named:
        return Path(named).expanduser()
    root = Path(os.environ.get("OPENFOLD_CACHE") or "~/.openfold3").expanduser()
    if not CKPT_NAME:
        raise _refuse(
            "[openfold3-resident] no checkpoint: set OPENFOLD3_CKPT, or install "
            "the kit so its pin table can name the file under OPENFOLD_CACHE"
        )
    return root / CKPT_NAME


CKPT = _checkpoint()
if not CKPT.is_file():
    raise _refuse(f"[openfold3-resident] the checkpoint is not at {CKPT}")


def _weights_held_by() -> str:
    """The word for the ready line: who owns the load path this process ran."""
    if MODE and MODE != "off":
        # ckpt_mmap replaced load_checkpoint and fast_init replaced the model
        # construction; this worker holds the runner they filled and touches
        # neither function.
        return f"kit:{MODE}"
    return "worker"


HOLDER = _weights_held_by()

from openfold3.core.config import config_utils  # noqa: E402
from openfold3.entry_points.experiment_runner import (  # noqa: E402
    InferenceExperimentRunner,
)
from openfold3.entry_points.import_utils import _torch_gpu_setup  # noqa: E402
from openfold3.entry_points.validator import (  # noqa: E402
    InferenceExperimentConfig,
    generate_seeds,
)
from openfold3.projects.of3_all_atom.config.inference_query_format import (  # noqa: E402
    InferenceQuerySet,
)

# Upstream's own CLI calls this before it imports the runner; it sets the
# float32 matmul precision the pinned configuration was measured with.
_torch_gpu_setup()

# The runner insists on an output directory at construction and creates it.
# Requests bring their own, so the one it is born with is a scratch directory
# that nothing is written to.
_BIRTH_DIR = Path(tempfile.mkdtemp(prefix="openfold3-resident-"))

_runner_args = config_utils.load_yaml(RUNNER_YAML) if RUNNER_YAML else {}
say(
    f"mode={MODE} weights_held_by={HOLDER} ckpt={CKPT} "
    f"runner_yaml={RUNNER_YAML or 'upstream defaults'}"
)

RUNNER = InferenceExperimentRunner(
    InferenceExperimentConfig(inference_ckpt_path=CKPT, **_runner_args),
    None,  # num_diffusion_samples: upstream's configured default
    None,  # num_model_seeds: the configuration's seed list
    False,  # use_msa_server: a held worker does not call out per request
    False,  # use_templates: likewise, and templates need files it has none of
    _BIRTH_DIR,
)
# See the module docstring: the one upstream setting a resident worker must
# overrule. `data_module_args` is the same object as
# `experiment_config.data_module_args`, and `data_module_config` re-reads it on
# every request, so setting it once here holds for all of them. Both counts are
# set although predict only reads the first, so that a future upstream moving
# predict onto the validation branch cannot quietly restore the fork.
LOADER_WORKERS_CONFIGURED = int(RUNNER.data_module_args.num_workers)
RUNNER.data_module_args.num_workers = 0
RUNNER.data_module_args.num_workers_validation = 0
say(
    f"loader workers: {LOADER_WORKERS_CONFIGURED} -> 0 (featurisation in this "
    f"process; a DataLoader child forked from a CUDA-initialised resident "
    f"worker dies by signal -- see the module docstring)"
)

RUNNER.setup()  # reads the checkpoint into the module: the expensive half
BUILD_S = time.time() - T0
say(f"model built t={BUILD_S:.1f}s")

# Everything the runner memoises that belongs to ONE request. The rest -- the
# model config, the lightning module, the checkpoint path, the strategy -- is
# what residency is for and is never dropped.
_PER_REQUEST = (
    "output_dir",
    "log_dir",
    "callbacks",
    "trainer",
    "data_module_config",
    "lightning_data_module",
)

# Options a caller may set per request. Anything else is refused by name rather
# than silently ignored, because a misspelt knob that reads as a default is how
# a prediction quietly stops being the one that was asked for.
PASSTHROUGH = (
    "num_diffusion_samples",
    "num_model_seeds",
    "use_msa_server",
    "use_templates",
)


def _apply_options(opts: dict, seed: int | None) -> None:
    unknown = sorted(set(opts) - set(PASSTHROUGH))
    if unknown:
        raise ValueError(
            f"unknown option(s) {unknown}; this provider takes {list(PASSTHROUGH)}"
        )
    settings = RUNNER.experiment_config.experiment_settings
    if "num_diffusion_samples" in opts:
        # model_config is the same ConfigDict the built module holds, so this
        # reaches the rollout; the memoised count has to go with it.
        RUNNER.set_num_diffusion_samples(int(opts["num_diffusion_samples"]))
        RUNNER.__dict__.pop("num_diffusion_samples", None)
    for flag in ("use_msa_server", "use_templates"):
        if flag in opts:
            setattr(settings, flag, bool(opts[flag]))
            RUNNER.__dict__.pop(flag, None)
    start = 42 if seed is None else int(seed)
    if "num_model_seeds" in opts:
        RUNNER.seeds = generate_seeds(start, int(opts["num_model_seeds"]))
    elif seed is not None:
        RUNNER.seeds = [start]


def _scores(out_dir: Path) -> dict:
    """The confidence JSONs upstream writes beside each structure, parsed.

    They are what a caller ranks samples on, and returning a directory listing
    without them makes every caller re-read the disk this process just wrote.
    """
    found = {}
    for path in sorted(out_dir.rglob("*.json")):
        name = path.name.lower()
        if "confidence" not in name and "summary" not in name:
            continue
        if path.stat().st_size > 1 << 16:
            continue
        try:
            found[str(path.relative_to(out_dir))] = json.loads(path.read_text())
        except (OSError, ValueError):  # a score we cannot read is not fatal
            continue
    return found


def _upstream_failure(out_dir: Path, from_byte: int) -> str:
    """Why a fold that returned normally produced nothing, in upstream's words.

    ``predict_step`` catches every exception a fold raises, appends the
    traceback to ``<log_dir>/predict_err_rank<rank>.log`` and lets the run
    finish; the writer then records the query as failed in ``summary.txt``. A
    resident worker's ``log_dir`` is fixed at construction, so that file is
    under ``_BIRTH_DIR`` and grows across requests -- ``from_byte`` is where
    this request started writing, so only its own traceback is quoted.

    This exists because the alternative is what this provider shipped with: a
    reply of ``structures: []`` and a timing, from a call that raised.
    """
    parts = []
    summary = out_dir / "summary.txt"
    if summary.is_file():
        try:
            parts.append(summary.read_text().strip())
        except OSError:
            pass
    log = _BIRTH_DIR / "logs" / "predict_err_rank0.log"
    if log.is_file():
        try:
            with open(log, "r", errors="replace") as handle:
                handle.seek(from_byte)
                fresh = handle.read().strip()
            if fresh:
                parts.append(f"{log}:\n{fresh}")
        except OSError:
            pass
    return "\n\n".join(parts)


def _err_log_size() -> int:
    log = _BIRTH_DIR / "logs" / "predict_err_rank0.log"
    try:
        return log.stat().st_size
    except OSError:
        return 0


def _predict_one(req: dict) -> dict:
    """One prediction. The request carries the query JSON text."""
    text = req.get("input") or req.get("query_json")
    if not text:
        raise ValueError(
            "a request needs 'input' (or 'query_json'): an OpenFold3 query JSON"
        )
    name = req.get("name") or "input"
    item = Path(req["out_dir"]) / name
    item.mkdir(parents=True, exist_ok=True)
    query_path = item / f"{name}.json"
    query_path.write_text(text if text.endswith("\n") else text + "\n")
    out_dir = item / "predictions"
    out_dir.mkdir(parents=True, exist_ok=True)

    _apply_options(dict(req.get("options") or {}), req.get("seed"))
    query_set = InferenceQuerySet.from_json(query_path)

    RUNNER.experiment_config.experiment_settings.output_dir = out_dir
    for cached in _PER_REQUEST:
        RUNNER.__dict__.pop(cached, None)

    if DEVICE == "cuda":
        torch.cuda.reset_peak_memory_stats()
    err_from = _err_log_size()
    t = time.time()
    RUNNER.run(query_set)
    if DEVICE == "cuda":
        torch.cuda.synchronize()
    timing = {"predict_s": round(time.time() - t, 2)}

    files = sorted(str(p) for p in out_dir.rglob("*") if p.is_file())
    structures = [f for f in files if f.endswith((".cif", ".pdb"))]
    if not structures:
        # A fold that raises returns normally from RUNNER.run: upstream caught
        # it per query. Answering with an empty list would make the caller's
        # success the caller's problem, so the reason is raised instead, in
        # upstream's own words.
        detail = _upstream_failure(out_dir, err_from) or (
            "upstream left neither a summary nor a traceback; the worker "
            "transcript is the only record"
        )
        raise RuntimeError(
            f"OpenFold3 wrote no structure for {name!r}: the fold raised and "
            f"upstream caught it per query.\n\n{detail}"
        )
    body = {
        "out_dir": str(out_dir),
        "files": files,
        "structures": structures,
        "seeds": list(RUNNER.seeds),
        "timing": timing,
        "weights_held_by": HOLDER,
        "kit_mode": MODE,
        "loader_workers": 0,
    }
    scores = _scores(out_dir)
    if scores:
        body["scores"] = scores
    if _err_log_size() > err_from:
        # Some query of this set failed while others produced structures. The
        # reply says so rather than letting the short list speak for itself.
        body["failed"] = _upstream_failure(out_dir, err_from)
    if DEVICE == "cuda":
        body["peak_reserved_gib"] = round(torch.cuda.max_memory_reserved() / 2**30, 2)
    return body


def _ready() -> dict:
    return {
        "build_s": round(BUILD_S, 1),
        "device": DEVICE,
        "weights_held_by": HOLDER,
        "kit_mode": MODE,
        "runner_yaml": RUNNER_YAML or "upstream defaults",
        "checkpoint": str(CKPT),
        "loader_workers": 0,
        "loader_workers_configured": LOADER_WORKERS_CONFIGURED,
        "post_release_ntok": os.environ.get(_POST_RELEASE_NTOK, "kit default"),
    }


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
