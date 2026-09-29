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

Three orderings in this file are load-bearing rather than stylistic:

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
import tempfile
import time
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="openfold3", help="provider slug, echoed in ping")
args = ap.parse_args()

T0 = time.time()


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
        raise SystemExit(
            f"[openfold3-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

MODE = (os.environ.get("OPENFOLD3_OPT") or "off").strip().lower()

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
        raise SystemExit(
            "[openfold3-resident] no checkpoint: set OPENFOLD3_CKPT, or install "
            "the kit so its pin table can name the file under OPENFOLD_CACHE"
        )
    return root / CKPT_NAME


CKPT = _checkpoint()
if not CKPT.is_file():
    raise SystemExit(f"[openfold3-resident] the checkpoint is not at {CKPT}")


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
    t = time.time()
    RUNNER.run(query_set)
    if DEVICE == "cuda":
        torch.cuda.synchronize()
    timing = {"predict_s": round(time.time() - t, 2)}

    files = sorted(str(p) for p in out_dir.rglob("*") if p.is_file())
    body = {
        "out_dir": str(out_dir),
        "files": files,
        "structures": [f for f in files if f.endswith((".cif", ".pdb"))],
        "seeds": list(RUNNER.seeds),
        "timing": timing,
        "weights_held_by": HOLDER,
        "kit_mode": MODE,
        "loader_workers": 0,
    }
    scores = _scores(out_dir)
    if scores:
        body["scores"] = scores
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
