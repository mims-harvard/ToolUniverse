"""BoltzGen held resident on the GPU, answering one design request at a time.

Run by the model's own interpreter with the kit's mode variable in the
environment::

    BOLTZGEN_OPT=fast <model python> boltzgen_resident_worker.py --socket … --slug …

The kit engages through its own ``.pth`` -- the common form, 30 of the 36 kits
-- so this file is simply a script the model's interpreter runs. The variable's
name is read from the kit by ``kit_launch``'s probe, never guessed here; for
this kit ``modes.ENV`` and ``_autoload.ENV`` agree and both say
``BOLTZGEN_OPT``.

**What this worker is a replacement for.** Upstream's ``boltzgen run`` is
``configure`` followed by one interpreter per pipeline step, and the kit's
``inproc`` lever removes exactly that: its runner ``xa_run.py`` runs the GPU
steps of one configured job in ONE process and the two CPU steps (``analysis``,
``filtering``) afterwards as stock subprocesses. This file stands in
``xa_run.py``'s position -- a different script where the kit already serves one
-- and the only thing it changes is that the process is held across requests
instead of started per job. Nothing in the kit is patched, copied or shadowed;
the in-process pipeline itself is the kit's own ``bg_inproc.py``, executed by
path out of the kit tree exactly as ``xa_run.py`` executes it, so a change
upstream makes to the seeding recipe or the per-step torch-state restore
reaches this worker without anything here being edited.

**Who holds the weights: NOBODY, and that is a third answer.** Chai-1 had to
choose between the kit's loader and its own. RFdiffusion3 found upstream
already memoising. Here neither:

* upstream re-reads the step's checkpoint inside ``Predict.run``
  (``Boltz.load_from_checkpoint``), once per step of every job;
* the kit replaces no loader. ``boltzgen_opt`` is a set of environment-driven
  lever modules that patch upstream's classes in place, and one of them
  (``fastinit``) is already wrapping the parameter initialisation that load
  runs through.

So there is no loader here to memoise that would not mean patching upstream on
top of the kit, which the standard forbids and which would race ``fastinit``
for the same code. The ready line and every reply say
``weights_held_by=upstream-per-step``, and what residency buys is the PROCESS:
the interpreter, the torch / rdkit / hydra / biotite import graph, the CUDA
context and the Triton and cuEquivariance JIT caches, paid once rather than
once per step per request.

**There is no engine key, and there is a process key.** RFdiffusion3 keys a
held engine on the constructor arguments a request may not change for free.
Here nothing is held between requests, so every specification argument --
``num_designs``, ``diffusion_batch_size``, ``protocol``, ``steps``,
``sampling_steps`` -- is request-time and free; they are arguments of
upstream's ``configure``, which runs as a clean subprocess per request. What IS fixed for the life of this
process is the kit MODE: ``stack.activate`` refuses a second mode outright
("already active in mode 'fast'; a process has one mode"). A request naming
another mode is therefore a request for a different WORKER, and this file says
so by name rather than ignoring the field.

**One refusal is pre-checked rather than suffered.** Under ``exact`` and
``fast`` the kit's ``hoist`` lever cannot serve a diffusion batch of one design
unless the token count happens to be a multiple of 16, and a mode is all of its
levers -- so the kit ends the process with exit 3 (``stack.end_process`` calls
``os._exit``) before the step's model loads. In a resident worker that is the
whole worker dying on a bad request, which is precisely what the standard says
must not happen for a bad request. So the batch rule is checked here first and
returned as an ordinary named error, and the worker stays up.
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="boltzgen", help="provider slug, echoed in ping")
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
    print(f"[boltzgen-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds BoltzGen's pinned stack
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
            f"[boltzgen-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

MODE = (os.environ.get("BOLTZGEN_OPT") or "off").strip().lower() or "off"
# The weights directory. `tu remote setup`'s weights step verified every one of
# the six files against the kit's pins before the supervisor started this
# process, and kit_launch put the directory here under the kit's own name.
CACHE = (os.environ.get("BOLTZGEN_CACHE") or "").strip()
if not CACHE:
    raise _refuse(
        "[boltzgen-resident] BOLTZGEN_CACHE is unset: run "
        "`tu remote setup boltzgen --only weights`"
    )
# What the kit's own configs/<card>.env fills in when these are unset. Set
# BEFORE upstream is imported: nothing is fetched at request time, and
# huggingface_hub reads both at import.
os.environ.setdefault("HF_HOME", CACHE)
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ.setdefault("PYTHONUNBUFFERED", "1")


def _map_jit_cache() -> None:
    """Point the four compile caches under ``$MODEL_OPT_JIT_ROOT/<stack key>/``.

    ``kit_launch`` sets ``MODEL_OPT_JIT_ROOT`` and nothing else, which for THIS
    kit does nothing on its own: the root is only a root, and the mapping onto
    ``TRITON_CACHE_DIR`` / ``TORCH_EXTENSIONS_DIR`` / ``TORCHINDUCTOR_CACHE_DIR``
    / ``NUMBA_CACHE_DIR`` lives in the kit's ``run.sh``, which a resident worker
    does not go through (STOCK.md "Variables", the MODEL_OPT_JIT_ROOT row).
    Without it each cache falls back to its library's own default -- Triton to
    ``~/.triton/cache``, shared with this repository's five other stacks, and
    numba to a ``__pycache__`` inside site-packages -- so the kit's per-stack
    layout is not used and a worker restart may recompile.

    The stack key is asked of the kit (``stack.stack_key()``: torch + CUDA +
    compute capability) rather than composed here. A variable a deployment
    already set is left alone, as ``run.sh`` leaves it. This is the one thing
    in this file copied from the kit's shell launcher rather than called on the
    kit, and it belongs in ``kit_launch`` instead; see the provider's notes.
    """
    root = (os.environ.get("MODEL_OPT_JIT_ROOT") or "").strip()
    if not root:
        return
    from boltzgen_opt import stack as _stack

    key = os.environ.get("MODEL_OPT_STACK_KEY") or _stack.stack_key()
    if not key:
        say(
            "MODEL_OPT_STACK_KEY could not be derived: the compile caches stay "
            "at their libraries' own defaults"
        )
        return
    os.environ["MODEL_OPT_STACK_KEY"] = key
    for var, leaf in (
        ("TRITON_CACHE_DIR", "triton"),
        ("TORCH_EXTENSIONS_DIR", "torch_extensions"),
        ("TORCHINDUCTOR_CACHE_DIR", "inductor"),
        ("NUMBA_CACHE_DIR", "numba"),
    ):
        if os.environ.get(var):
            continue
        path = os.path.join(root, key, leaf)
        os.makedirs(path, exist_ok=True)
        os.environ[var] = path
    say(f"compile caches under {os.path.join(root, key)} (stack key {key})")


_map_jit_cache()

import torch  # noqa: E402

torch.set_grad_enabled(False)

# The kit's trigger is the first import of `boltzgen`; its meta-path finder
# lets that package's own body run and then activates the mode -- the lever
# directories onto sys.path, the lever modules imported, the step gate armed.
# Importing it here is what arms and fires it, before any step runs. A refusal
# is the kit's own NOT ACTIVE line and exit 3, which is the honest outcome: the
# supervisor reports a worker that would not start rather than a provider
# quietly serving stock.
import boltzgen  # noqa: E402,F401
import boltzgen_opt  # noqa: E402
from boltzgen_opt import design as kit_design  # noqa: E402
from boltzgen_opt import modes as kit_modes  # noqa: E402
from boltzgen_opt import stack as kit_stack  # noqa: E402

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
say(f"imports done t={time.time() - T0:.1f}s torch={torch.__version__} device={DEVICE}")

STATUS = boltzgen_opt.status()
RESOLUTION = kit_modes.resolve(MODE, kit_stack.opt_home())
# The kit's own in-process pipeline, found through the kit's own accessors so
# that a move of the file inside the kit cannot leave a stale path here. This
# is the file `xa_run.py` execs; its module body IS the run and it must never
# be imported as a module (the `analysis` step's multiprocessing pool would
# re-execute it).
BG_INPROC = os.path.join(
    kit_stack.kit_dir(kit_modes.KIT_PARTNER), "src", "bg_inproc.py"
)
GPU_STEPS = tuple(kit_stack.GPU_STEPS)

# Upstream's own configure options this provider exposes, and how each is
# spelled on `boltzgen configure`'s command line. Everything here is
# request-time: configure is a clean subprocess per request and nothing of it
# survives into the next one, so unlike RFdiffusion3 there is no engine key to
# separate these from.
_INT_OPTIONS = {
    "num_designs": "--num_designs",
    "diffusion_batch_size": "--diffusion_batch_size",
    "budget": "--budget",
}
_STR_OPTIONS = {"protocol": "--protocol"}
_LIST_OPTIONS = {"steps": "--steps"}

# The denoiser's step count, which is NOT a `configure` flag -- upstream
# exposes no `--sampling_steps`; it is a value of the step's resolved config,
# and `configure`'s own general override `--config <step> <key>=<value>` is how
# upstream sets one. That override is appended LAST of everything this builds
# (it is `nargs="+"`, so a flag after it would be swallowed) and it wins,
# because `configure_command` puts the caller's per-step overrides after its
# own (`config_args_by_step[...]` last in the design step's args list).
#
# Why it is exposed at all: upstream's design.yaml ships `sampling_steps: 500`,
# and 500 denoiser steps over two 60-residue designs does not finish in 40
# minutes on this card. The smallest honest end-to-end exercise of this path
# therefore has to be able to say a smaller number, and a caller who wants
# upstream's sampling asks for nothing and gets upstream's 500.
#
# The kit does not object. Its eight switches carry no step count; the only
# lever that reads one is the CUDA-graph sampler (`bg_graph_patch.sample_patched`),
# which takes `num_sampling_steps` as an argument, captures ONE graph of a
# single denoiser step and replays it S times -- so S is a loop bound there,
# not a shape, and a smaller S is fewer replays of the same captured graph.
# `stock/PINS.json` records `step_config_defaults.design.sampling_steps = 500`,
# but that is a record of what the wheel ships: no code in the kit reads it.
# The floor is the schedules' own: both `sample_schedule_af3` and
# `sample_schedule_dilated` divide by `S - 1`.
_CONFIG_STEP = "design"
MIN_SAMPLING_STEPS = 2
OPTION_NAMES = tuple(
    sorted({*_INT_OPTIONS, *_STR_OPTIONS, *_LIST_OPTIONS, "mode", "sampling_steps"})
)

# Upstream's own default is --num_designs 10000, which is a campaign rather
# than a request. A tool call that names no count gets a small one and the
# reply says which.
DEFAULT_NUM_DESIGNS = 4
DEFAULT_MAX_BATCH = 4
# The modes whose `hoist` lever cannot serve a one-design diffusion batch.
BATCH_TWO_MODES = ("exact", "fast")

STRUCTURE_SUFFIXES = (".cif", ".mmcif", ".pdb", ".cif.gz", ".pdb.gz")
MAX_METRIC_ROWS = 200


def _yaml():
    import yaml

    return yaml


def _read_request(text: str) -> tuple:
    """``(specification, options, files)`` from one request document.

    Two readings, because a design request carries more than a specification.
    Upstream's own file is a YAML mapping with an ``entities`` list, and that
    is accepted unchanged, so anything `boltzgen run` takes works here. But how
    many designs to make, in how large a diffusion batch, and which pipeline
    steps to run are not specification fields -- upstream's parser does not
    know them -- so the envelope form carries them beside it::

        {"specification": {...}, "options": {...}, "files": {"t.pdb": "..."}}

    A mapping with a top-level ``specification`` key is read as the envelope;
    anything else is read as upstream's own spec. YAML is a superset of JSON,
    so either notation works for either form. Keys beginning with ``_`` are
    ignored at the top level, so a document can carry a comment.

    ``files`` exists because a binder specification names its target by a
    RELATIVE path (``- file: {path: target.pdb}``) resolved against the spec
    file's own directory, and a caller reaching this worker over a socket has
    nowhere to put that file otherwise.
    """
    doc = _yaml().safe_load(text)
    if not isinstance(doc, dict):
        raise ValueError(
            "a design request is a YAML/JSON mapping, not " + type(doc).__name__
        )
    doc = {k: v for k, v in doc.items() if not str(k).startswith("_")}
    if "specification" in doc:
        spec = doc["specification"]
        opts = doc.get("options") or {}
        files = doc.get("files") or {}
        unknown = sorted(set(doc) - {"specification", "options", "files"})
        if unknown:
            raise ValueError(
                f"unknown key(s) {unknown} beside 'specification'; the envelope "
                f"takes 'specification', 'options' and 'files'"
            )
    else:
        spec, opts, files = doc, {}, {}
    if isinstance(spec, str):  # the envelope may carry the spec as YAML text
        spec = _yaml().safe_load(spec)
    if not isinstance(spec, dict) or not spec:
        raise ValueError(
            "the specification is a non-empty mapping -- upstream's own design "
            "spec, whose top-level key is 'entities'"
        )
    if "entities" not in spec:
        raise ValueError(
            "the specification has no 'entities' key; a BoltzGen design spec is "
            "a mapping with an 'entities' list (see the kit's pdl1_ref.yaml)"
        )
    if not isinstance(opts, dict):
        raise ValueError("'options' is a mapping")
    if not isinstance(files, dict) or any(
        not isinstance(v, str) for v in files.values()
    ):
        raise ValueError("'files' is a mapping of file name to text content")
    return spec, opts, files


def _configure_args(opts: dict) -> tuple:
    """``(argv for configure, the resolved counts)``, with every refusal this
    kit would make checked here first."""
    unknown = sorted(set(opts) - set(OPTION_NAMES))
    if unknown:
        raise ValueError(
            f"unknown option(s) {unknown}; this provider takes {list(OPTION_NAMES)}"
        )

    asked_mode = opts.get("mode")
    if asked_mode is not None and str(asked_mode).strip().lower() != MODE:
        # A process has one mode: stack.activate refuses a second one, and the
        # levers of this one are already installed on upstream's classes.
        raise ValueError(
            f"this worker is running the kit in mode {MODE!r} and a process has "
            f"one mode (boltzgen_opt.stack.activate); a request for mode "
            f"{asked_mode!r} is a request for a different worker -- change "
            f"[kit] mode in the provider manifest and restart it"
        )

    num_designs = int(opts.get("num_designs", DEFAULT_NUM_DESIGNS))
    if num_designs < 1:
        raise ValueError("num_designs must be at least 1")
    if "diffusion_batch_size" in opts:
        batch = int(opts["diffusion_batch_size"])
    else:
        batch = min(num_designs, DEFAULT_MAX_BATCH)
    if batch < 1:
        raise ValueError("diffusion_batch_size must be at least 1")
    if batch > num_designs:
        raise ValueError(
            f"diffusion_batch_size {batch} is larger than num_designs "
            f"{num_designs}: upstream would make {batch} designs per roll-out "
            f"and never fewer"
        )
    if batch == 1 and MODE in BATCH_TWO_MODES:
        # Pre-checked, not suffered: the kit would end this PROCESS with exit 3
        # rather than fail the request. CHANGES.md, the `hoist` entry.
        raise ValueError(
            f"mode {MODE!r} cannot run a diffusion batch of one design: the "
            f"kit's `hoist` lever disables itself at one design per structure "
            f"unless the token count is a multiple of 16, and a mode is all of "
            f"its levers, so the kit refuses the run (exit 3). Ask for "
            f"num_designs >= 2 with diffusion_batch_size >= 2, or run a worker "
            f'whose [kit] mode is "big" or "off"'
        )

    argv = ["--num_designs", str(num_designs), "--diffusion_batch_size", str(batch)]
    for name, flag in _INT_OPTIONS.items():
        if name in ("num_designs", "diffusion_batch_size") or name not in opts:
            continue
        argv += [flag, str(int(opts[name]))]
    for name, flag in _STR_OPTIONS.items():
        if name in opts:
            argv += [flag, str(opts[name])]
    for name, flag in _LIST_OPTIONS.items():
        if name not in opts:
            continue
        values = opts[name]
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, (list, tuple)) or not all(
            isinstance(v, str) for v in values
        ):
            raise ValueError(f"'{name}' is a list of step names")
        argv += [flag, *values]

    sampling_steps = None
    if opts.get("sampling_steps") is not None:
        sampling_steps = int(opts["sampling_steps"])
        if sampling_steps < MIN_SAMPLING_STEPS:
            raise ValueError(
                f"sampling_steps must be at least {MIN_SAMPLING_STEPS}: both of "
                f"upstream's noise schedules divide by (sampling_steps - 1)"
            )
        # LAST, and last for a reason: `--config` is `nargs="+"` and would
        # swallow a flag appended after it.
        argv += ["--config", _CONFIG_STEP, f"sampling_steps={sampling_steps}"]
    return argv, {
        "num_designs": num_designs,
        "diffusion_batch_size": batch,
        # None = upstream's own (design.yaml ships 500); the reply says which
        # rather than leaving a caller to guess what it got.
        "sampling_steps": sampling_steps,
    }


def _run_gpu_steps(run_dir: str, seed: int, steps: list) -> None:
    """The kit's own in-process pipeline over ``steps``, in THIS process.

    ``bg_inproc.py``'s module body is the run and it reads ``sys.argv``; it is
    executed by path under a name that is not ``__main__``, which is what
    ``xa_run.py`` does and for the reason ``xa_run.py`` gives: the ``analysis``
    step's multiprocessing pool re-imports the main script, and a main script
    that is a pipeline would run a second one.
    """
    if not os.path.isfile(BG_INPROC):
        raise RuntimeError(
            f"the kit's in-process pipeline is not at {BG_INPROC}; the checkout "
            f"is not the pinned one (run `tu remote setup boltzgen --only kit`)"
        )
    saved = sys.argv[:]
    sys.argv = [BG_INPROC, run_dir, str(seed), ",".join(steps)]
    try:
        with open(BG_INPROC, encoding="utf-8") as fh:
            code = compile(fh.read(), BG_INPROC, "exec")
        exec(code, {"__name__": "bg_inproc_exec", "__file__": BG_INPROC})  # noqa: S102
    finally:
        sys.argv = saved
    gc.collect()
    if DEVICE == "cuda":
        torch.cuda.empty_cache()


def _run_cpu_steps(run_dir: str, steps: list, log_path: str) -> list:
    """``analysis`` and ``filtering`` as stock subprocesses, as ``xa_run.py``
    runs them: no kit hook is needed for a CPU step and PYTHONPATH is dropped
    so none is loaded."""
    main_py = os.path.join(os.path.dirname(boltzgen.__file__), "resources", "main.py")
    configs = {s["name"]: s["config_file"] for s in kit_design.read_steps(run_dir)}
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    out = []
    with open(log_path, "a", encoding="utf-8") as log:
        for name in steps:
            env["BOLTZGEN_PIPELINE_STEP"] = name
            t = time.time()
            rc = subprocess.call(
                [sys.executable, main_py, os.path.join(run_dir, configs[name])],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            out.append({"step": name, "rc": rc, "wall_s": round(time.time() - t, 2)})
            say(f"step {name} (stock subprocess) rc={rc}")
            if rc != 0:
                raise RuntimeError(
                    f"the {name} step exited {rc}; its output is in {log_path}"
                )
    return out


def _collect(run_dir: Path) -> dict:
    """What the job produced: the structures, the ranked table when the
    filtering step ran, and every file."""
    files = sorted(p for p in run_dir.rglob("*") if p.is_file())
    structures = [
        os.fspath(p)
        for p in files
        # Not the top level: `configure` writes one mmCIF visualisation of the
        # specification itself into run_dir before any step runs, and counting
        # it as a design would make a job that generated nothing look like a
        # job that generated one.
        if p.name.endswith(STRUCTURE_SUFFIXES) and p.parent != run_dir
    ]
    out = {
        "structures": structures,
        "n_structures": len(structures),
        "files": [os.fspath(p) for p in files],
    }
    # `filtering` writes <run_dir>/final_ranked_designs/ with the ranked table
    # and the selected structures. It is the step a caller ranks N designs on,
    # and the reason for returning anything beyond a list of paths.
    ranked = run_dir / "final_ranked_designs"
    if ranked.is_dir():
        out["final_ranked_dir"] = os.fspath(ranked)
        tables = sorted(ranked.glob("final_designs_metrics_*.csv")) or sorted(
            ranked.glob("all_designs_metrics.csv")
        )
        if tables:
            out["metrics_file"] = os.fspath(tables[0])
            try:
                with open(tables[0], newline="", encoding="utf-8") as fh:
                    rows = list(csv.DictReader(fh))
                out["metrics"] = rows[:MAX_METRIC_ROWS]
                out["n_metric_rows"] = len(rows)
            except (OSError, UnicodeError, csv.Error) as exc:
                out["metrics_error"] = f"{type(exc).__name__}: {exc}"
    return out


def _resolved_sampling_steps(run_dir: Path) -> dict:
    """``{step: sampling_steps}`` as ``configure`` resolved it, read back out of
    ``<run_dir>/config/<step>.yaml``.

    This is the written file the provider's own override goes through, and
    reading it back is the cheap proof that the override landed: a value that
    did not take shows here as upstream's own, not as a silent 40-minute run.
    """
    out = {}
    try:
        steps = kit_design.read_steps(os.fspath(run_dir))
    except (OSError, ValueError, KeyError, TypeError):
        return out
    for s in steps:
        try:
            with open(run_dir / s["config_file"], encoding="utf-8") as fh:
                cfg = _yaml().safe_load(fh) or {}
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if "sampling_steps" in cfg:
            try:
                out[s["name"]] = int(cfg["sampling_steps"])
            except (TypeError, ValueError):
                pass
    return out


def _design_one(req: dict) -> dict:
    """One design request: one specification, N designs, one run directory."""
    text = req.get("input") or req.get("specification")
    if not text:
        raise ValueError(
            "a request needs 'input': the text of a BoltzGen design "
            "specification (upstream's own YAML, or the envelope form)"
        )
    if isinstance(text, (dict, list)):
        text = json.dumps(text)
    spec, file_opts, attachments = _read_request(text)
    # The request's own options win over the document's: the document is the
    # design, the request is the call.
    opts = {**file_opts, **(req.get("options") or {})}
    configure_argv, counts = _configure_args(opts)

    name = req.get("name") or "design"
    item = Path(req["out_dir"]) / name
    item.mkdir(parents=True, exist_ok=True)
    # A fresh directory per request. Upstream sets an old `config/` aside and
    # re-runs every step into an existing --output, so pointing two requests at
    # one directory would mix two jobs' outputs under one ranking.
    stamp = f"{int(time.time() * 1000):013d}"
    work = item / f"job-{stamp}"
    inputs = work / "inputs"
    inputs.mkdir(parents=True, exist_ok=False)
    run_dir = work / "run"
    # Relative `file: {path: …}` entries in a spec are resolved against the
    # spec file's own directory, so the attachments go beside it.
    for fname, content in attachments.items():
        safe = Path(fname).name
        if not safe or safe != fname:
            raise ValueError(
                f"attachment name {fname!r} must be a plain file name, not a path"
            )
        (inputs / safe).write_text(content)
    spec_path = inputs / "design_spec.yaml"
    spec_path.write_text(_yaml().safe_dump(spec, sort_keys=False))

    # The kit's own runner is seeded by construction -- step i runs with
    # seed + i -- and a kit mode without a seed is NOT ACTIVE. 0 when the
    # caller names none, and the reply says which was used.
    seed = int(req.get("seed", 0))
    if seed < 0:
        raise ValueError("seed must be a non-negative integer")

    timing = {}
    t = time.time()
    # `configure` in the kit's own words: a clean stock subprocess with every
    # kit variable stripped, cwd the output's parent, `--cache` filled from
    # BOLTZGEN_CACHE. Calling the kit's function rather than rebuilding the
    # command line is what keeps this in step with the kit.
    conf = kit_design.configure(
        os.fspath(spec_path), os.fspath(run_dir), configure_argv, CACHE
    )
    timing["configure_s"] = round(time.time() - t, 2)

    planned = [s["name"] for s in kit_design.read_steps(os.fspath(run_dir))]
    # What `configure` actually wrote, not what was asked: the reply states the
    # denoiser step count that the step will run, whether a caller named one or
    # took upstream's, so nobody has to know that design.yaml ships 500.
    resolved_steps = _resolved_sampling_steps(run_dir)
    gpu_steps = [s for s in planned if s in GPU_STEPS]
    cpu_steps = [s for s in planned if s not in GPU_STEPS]
    log_path = os.fspath(run_dir / "opt_run.log")

    if DEVICE == "cuda":
        torch.cuda.reset_peak_memory_stats()
    t = time.time()
    if gpu_steps:
        _run_gpu_steps(os.fspath(run_dir), seed, gpu_steps)
        if DEVICE == "cuda":
            torch.cuda.synchronize()
    timing["gpu_steps_s"] = round(time.time() - t, 2)
    cpu_results = (
        _run_cpu_steps(os.fspath(run_dir), cpu_steps, log_path) if cpu_steps else []
    )
    timing["cpu_steps_s"] = round(sum(r["wall_s"] for r in cpu_results), 2)
    timing["total_s"] = round(
        timing["configure_s"] + timing["gpu_steps_s"] + timing["cpu_steps_s"], 2
    )

    body = {
        "run_dir": os.fspath(run_dir),
        "specification_file": os.fspath(spec_path),
        "steps": planned,
        "gpu_steps": gpu_steps,
        "cpu_steps": cpu_results,
        "seed": seed,
        "seed_recipe": "step i of the pipeline runs with seed + i (the kit's own)",
        "num_designs": counts["num_designs"],
        "diffusion_batch_size": counts["diffusion_batch_size"],
        # What was asked for (None = upstream's own) and what every configured
        # step will actually run.
        "sampling_steps_requested": counts["sampling_steps"],
        "sampling_steps": resolved_steps,
        "configure_args": conf["cmd"],
        "timing": timing,
        "mode": MODE,
        "weights_held_by": "upstream-per-step",
        "levers_applied": STATUS.get("levers_applied"),
        "levers_unavailable": STATUS.get("levers_unavailable"),
    }
    # The kit's own per-step wall times, written by bg_inproc.py.
    inproc_times = run_dir / "inproc_times.json"
    if inproc_times.is_file():
        try:
            body["inproc_times"] = json.loads(inproc_times.read_text())
        except ValueError:
            pass
    body.update(_collect(run_dir))
    if not body["structures"]:
        body["warning"] = (
            "no structure was written; upstream skips a diffusion batch it "
            "cannot fit and still exits 0, so check the worker log for its own "
            "`ran out of memory, skipping batch` lines and the kit's KERNELS line"
        )
    if DEVICE == "cuda":
        body["peak_reserved_gib"] = round(torch.cuda.max_memory_reserved() / 2**30, 2)
    return body


def _ready() -> dict:
    return {
        "build_s": round(time.time() - T0, 1),
        "device": DEVICE,
        "mode": MODE,
        "weights_held_by": "upstream-per-step",
        "weights_root": CACHE,
        "kit_active": bool(STATUS.get("active")),
        "kit_form": STATUS.get("form"),
        "levers_applied": STATUS.get("levers_applied"),
        "levers_unavailable": STATUS.get("levers_unavailable"),
        "partial": STATUS.get("partial"),
        "boltzgen_version": STATUS.get("boltzgen_version"),
        "boltzgen_opt_version": STATUS.get("package_version"),
    }


if __name__ == "__main__":
    # Nothing is built here: every checkpoint this pipeline reads is read
    # inside the step that uses it, so there is no model to preload and
    # [runtime] start_timeout_s covers the import graph and the kit's
    # activation rather than a 2 GB load.
    #
    # `partial` is the kit's own word for "a lever of the mode could not run in
    # this process", which it treats as a refusal of the whole mode. The
    # activation already printed its NOT ACTIVE line and, under the .pth
    # route's strict activation, would have ended the process; if one ever
    # reaches here it is said out loud rather than served quietly.
    if STATUS.get("partial"):
        say(
            f"WARNING partial activation: levers {STATUS.get('levers_fallback')} "
            f"fell back -- this process's outputs are not mode {MODE}'s"
        )
    say(
        f"ready t={time.time() - T0:.1f}s mode={MODE} "
        f"weights_held_by=upstream-per-step "
        f"(upstream loads each pipeline step's own checkpoint inside the step "
        f"and the kit replaces no loader, so residency holds the process -- "
        f"imports, CUDA context, JIT caches -- and not the weights) "
        f"levers={','.join(STATUS.get('levers_applied') or []) or 'none'} "
        f"unavailable={','.join(STATUS.get('levers_unavailable') or []) or 'none'}"
    )
    # The kit registers an atexit verdict: a process that built a model and saw
    # a lever fall back ends with exit 3 and a NOT ACTIVE line, whatever this
    # loop returns. That is the kit's judgement on the run and is left alone.
    sys.exit(
        WB.serve(
            slug=args.slug,
            socket_path=args.socket,
            on_predict=_design_one,
            ready=_ready,
            log=say,
        )
    )
