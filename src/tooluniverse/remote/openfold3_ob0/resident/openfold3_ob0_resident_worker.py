"""OpenFold3 0.5.0 (OpenBind-0) held resident on the GPU, one request at a time.

Run by the model's own interpreter with the kit's mode variable set::

    OPENFOLD3_OB0_OPT=fast <model python> openfold3_ob0_resident_worker.py --socket … --slug …

**What this is, and what it is not.** The parameters are OpenBind-0
(`of3-ob-2025-06-30-174k.pt`), the upstream is OpenFold3 0.5.0, and both are
version-locked to each other: `openfold3/entry_points/parameters.py` declares
`version_compatibility = ">=0.5.0"` for this checkpoint and lists the 0.4.x
preview checkpoints in `LEGACY_CHECKPOINTS`, which 0.5.0 refuses to download.
`provider.toml` has the full argument for why this is a second provider rather
than an option on the `openfold3` one; the short form is that both pin the
same distribution name at incompatible versions and each kit's `.pth` refuses
to share a process with the other's.

**Why holding matters.** Stock's only entry point is `run_openfold predict`,
which builds an `InferenceExperimentRunner`, reads 2,287,872,989 bytes of
checkpoint into it, calls `Trainer.predict` once and exits. All of that is
identical for every request, so this worker pays it once: the runner, its
`lightning_module` and its weights stay in this process between requests, and
only the output directory, the query set, the callbacks and the Lightning
trainer are rebuilt per call.

**Who holds the weights.** Nothing here memoises anything of upstream, and
that is deliberate rather than an omission. Under a kit mode the kit already
owns the load path -- the `ckpt_mmap` cell replaces upstream's
`load_checkpoint` and `fast_init` replaces the model construction that
precedes it -- and the kit's own late-activation gate refuses a process that
has had either replaced from somewhere else. Under `[kit] mode = "off"`
nothing replaces them and the plain upstream path runs. The ready line and
every reply say which of the two it was (`weights_held_by`).

**The checkpoint is checked to be the file the weights step certified**, by
size, before the model is built and again from the runner's own
`inference_ckpt_path` after. "The model started" is not evidence it read the
file you hashed: a staging that links into one directory while the loader
reads another reports success and downloads gigabytes behind your back. Here
the path is passed explicitly rather than resolved from a cache, which removes
the class -- and the check is still made, because an explicit path is only an
argument until something reads it.

**The featurisation loader runs in-process, and it has to.** Upstream
configures `data_module_args.num_workers = 10` (`entry_points/validator.py`
`DataModuleArgs`) and the kit's `loader_workers` cell caps that at the item
count -- `max(1, min(items, configured))`, never 0 -- so one query would still
start one child. 0.5.0 defaults that child's start method to **forkserver**
rather than fork (`data_module.safe_multiprocessing_context`), which is an
improvement on the 0.4.1 situation where a forked child of this worker died by
signal with no traceback. It is not a reason to allow it: the standard's rule
is a property of the resident route, not of one start method, and a forkserver
child of a worker holding a built model and a CUDA context re-imports the kit
hook to featurise one item. So the count is set to 0, which the kit's own
`plan()` short-circuits on::

    if configured <= 0: return configured   # the engine featurises in-process

so the cell stays on and steps aside by its own rule, and
`DataModuleConfig.num_workers` defaults to 0 in the data module itself. The
honest cost is the one the kit names: with no worker processes
`worker_init_fn` never runs and featurisation's random draws come from the
DataLoader's own generator in this process, so featurisation-level randomness
is not bit-comparable with a multi-worker run at the same seed. The model
seeds, which `RankSpecificSeedCallback` owns, are untouched.

**The second request, read out of the source rather than met on the card.**
The `openfold3` provider died deterministically on the SECOND request of a
shape it had already folded: Lightning moves the module to the CPU between
requests, the `trunk_graph` cell correctly refuses to replay a graph over
moved storage and deletes the entry -- but keeps the graph POOL handle the
deleted graph had emptied, the re-capture into that handle trips the
allocator's use-count assertion, and a capture that began and never ended
leaves the CUDA generator flagged as capturing, so the NEXT eager draw raises
`Offset increment outside graph capture encountered unexpectedly`.

This kit's `cells/trunk_graph.py` and `cells/post_release.py` are eighteen-line
binders over the SAME shared modules (`opt_core.of3_trunk.trunk_graph`,
`opt_core.of3_sampler.post_release`), and the defect is in the shared one:

    if e["storage_sig"] != _storage_signature(self):
        del _G["entries"][key]            # the pool handle is NOT cleared here
        return _fb("storage_moved", self, a, k)

against `release()`, three lines up, which does `_G["pool"] = None`. So the
hazard is inherited exactly, and the fix is the same knob:
`OPENFOLD3_OB0_OPT_POST_RELEASE_NTOK = 0` puts `post_release`'s item-boundary
release on every item, and that release goes through `trunk_graph.release()`,
which clears the pool with the graphs. It is declared in `[kit] env` in
`provider.toml` rather than set here, because it is a kit knob a reviewer
should find beside `levers_off` and not in a line of Python. This worker only
REPORTS which value is in force, and says so loudly when it is the kit's 2400
default -- because a worker running with that default is a worker that fails
on request two.

**A SECOND second-request defect, and this one is upstream's.** The kit's is
above. 0.5.0 also added `MsaComputationSettings`, whose per-run directory name
is fixed at construction and whose record root the runner binds once to the
directory it was BORN with -- and the no-MSA-server path every request here
takes then `mkdir`s that one path with `exist_ok=False`. Request one folds;
request two of ANY shape dies with `FileExistsError`, caught per query, so it
arrives as "wrote no structure". It is invisible to a one-request smoke AND to
a length ladder, which is how it was actually found: on rung two of the
acceptance run. `_rebind_msa_workspace` has the citation and the fix, which is
upstream's own public setter called per request. Two independent defects of the
same shape, in two different layers, in one provider: "the second request" is
not a kit hazard, it is a resident-worker hazard.

Three orderings in this file are load-bearing rather than stylistic:

* `import openfold3` comes before anything that could touch the GPU. That
  import is the kit's trigger: the `.pth` installed at interpreter start arms
  a finder which patches the package the moment its body has run, and the
  kit's `alloc_expandable` lever wants to export `PYTORCH_CUDA_ALLOC_CONF`
  while CUDA is still uninitialised.
* No submodule of `openfold3` is imported before the package itself, for the
  same reason: the kit's gate refuses a late activation by name, naming the
  target that was already imported.
* The runner's configuration -- the runner YAML carrying the mode's precision
  and kernel settings -- is asked of the kit (`openfold3_ob0_opt.cli.row_yaml`
  / `member_yaml`) rather than copied from it. A hard-coded copy drifts the
  first time the kit moves.

There is no `_reconcile_kit_row()` here, and its absence is deliberate. The
`openfold3` worker carries one because `kit_launch` used to read the kit's
environment row in a probe that did not know about `MODEL_OPT_LEVERS_OFF`, so
an ablated provider inherited the unablated row and the kit refused the whole
activation over the difference. `kit_launch.ask_kit` now sets `levers_off` in
the probe's own environment, so the row this process inherits is already the
one it will run.
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
ap.add_argument("--slug", default="openfold3_ob0", help="provider slug, echoed in ping")
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
    print(f"[openfold3_ob0-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds OpenFold3 0.5.0's pinned
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
            f"[openfold3_ob0-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

MODE = (os.environ.get("OPENFOLD3_OB0_OPT") or "off").strip().lower()

# The kit's gate knob for `post_release`: the one setting that makes a held
# worker able to serve the same shape twice. Declared in [kit] env, reported
# here -- see the module docstring for the chain it defuses.
_POST_RELEASE_NTOK = "OPENFOLD3_OB0_OPT_POST_RELEASE_NTOK"


def _check_item_boundary_release() -> str:
    """The value of the kit's `post_release` gate in force, and a loud line when
    it is the kit's default.

    This worker does not SET it. `[kit] env` in `provider.toml` does, because
    a kit's own documented knob belongs in the file a reviewer reads. What a
    worker can usefully do is refuse to be quiet about running without it.
    """
    value = os.environ.get(_POST_RELEASE_NTOK)
    if MODE == "off":
        return "n/a (kit mode off)"
    if value is None:
        say(
            f"WARNING: {_POST_RELEASE_NTOK} is unset, so the kit's item-boundary "
            f"release keeps its 2400-token / 16 GB-free default and will not fire "
            f"on an ordinary request. A held worker then meets the last request's "
            f"emptied trunk-graph pool on the second request of a shape it has "
            f"already folded, and raises `Offset increment outside graph capture`. "
            f"Set it through [kit] env in provider.toml."
        )
        return "kit default (2400)"
    say(
        f"{_POST_RELEASE_NTOK}={value}: the kit's item-boundary release fires on "
        f"every item, so each request captures its own trunk graph instead of "
        f"meeting the last request's emptied graph pool"
    )
    return value


POST_RELEASE_NTOK = _check_item_boundary_release()

# The kit's trigger package, first and whole. Everything the kit patches lives
# under it, and the finder disarms once this import returns.
import openfold3  # noqa: E402,F401

import torch  # noqa: E402

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
say(f"imports done t={time.time() - T0:.1f}s torch={torch.__version__} device={DEVICE}")


def _ask_kit() -> tuple:
    """``(runner yaml, checkpoint file name)``, both asked of the kit.

    The mode's runner YAML carries its precision and kernel settings, and the
    checkpoint's name is in the kit's own pin table (`stock/PINS.json`).
    Neither is written down here: a kit that moved either would otherwise take
    this worker with it, silently. With no kit installed, upstream's defaults
    apply and the checkpoint is whatever ``OPENFOLD3_OB0_CKPT`` names.

    THE API IS NOT THE openfold3 KIT'S, and that is the §10 warning about
    `resolve()` one layer out: `openfold3_opt.cli` exposes
    `member_yaml(home, line, precision, mode, det)`, this kit exposes
    `row_yaml(home, line, runner_yaml=None, mode=..., det=0)` and a separate
    `line_member`. Copying the sibling's call verbatim raises TypeError at the
    first start. Asked, not assumed.
    """
    try:
        from openfold3_ob0_opt import cli as kit_cli
        from openfold3_ob0_opt import env as kit_env
        from openfold3_ob0_opt import modes as kit_modes
    except ImportError as exc:  # noqa: BLE001 - a kitless environment still serves
        say(f"the optimization kit is not importable ({exc}); upstream defaults apply")
        return "", ""
    home = kit_env.tree_home()
    _line_name, line = kit_modes.line_of(MODE)
    # No `--runner-yaml` overlay and det level 0: the route's own member file,
    # untouched, which for `fast` is the kit's stock runner yaml (bf16-mixed,
    # cuEquivariance triangle kernels, the chunk plan pinned).
    yaml_path = kit_cli.row_yaml(home, line, mode=MODE)
    pin = (kit_env.pins(home) or {}).get("weights") or {}
    return yaml_path, str(pin.get("file") or "")


RUNNER_YAML, CKPT_NAME = _ask_kit()

# The pin, restated in one place so the check below has something to compare
# against without importing the manifest (which lives in ToolUniverse's
# environment, not this one). It is the `weights` entry of the kit's own
# stock/PINS.json and the [[weights.files]] entry of provider.toml.
CKPT_BYTES = 2287872989


def _checkpoint() -> Path:
    """The weights file, from ``OPENFOLD3_OB0_CKPT`` or from the weights root
    the manifest declares plus the name the kit pins. Nothing is fetched here:
    the setup step verified every declared file against its digest, and a
    worker that reached for a CDN mid-request would undo that."""
    named = os.environ.get("OPENFOLD3_OB0_CKPT")
    if named:
        return Path(named).expanduser()
    root = Path(os.environ.get("OPENFOLD_CACHE") or "~/.openfold3").expanduser()
    if not CKPT_NAME:
        raise _refuse(
            "[openfold3_ob0-resident] no checkpoint: set OPENFOLD3_OB0_CKPT, or "
            "install the kit so its pin table can name the file under OPENFOLD_CACHE"
        )
    return root / CKPT_NAME


CKPT = _checkpoint()
if not CKPT.is_file():
    raise _refuse(f"[openfold3_ob0-resident] the checkpoint is not at {CKPT}")
_SIZE = CKPT.stat().st_size
if _SIZE != CKPT_BYTES:
    raise _refuse(
        f"[openfold3_ob0-resident] {CKPT} is {_SIZE} bytes, the pin is "
        f"{CKPT_BYTES} ({100 * _SIZE / CKPT_BYTES:.1f}% of it). This is the file "
        f"the model would have loaded; remove it and re-run "
        f"`tu remote setup openfold3_ob0 --only weights`"
    )


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
from openfold3.entry_points.import_utils import (  # noqa: E402
    _configure_torch_backend,
    _enable_tf32,
)
from openfold3.entry_points.validator import (  # noqa: E402
    InferenceExperimentConfig,
    generate_seeds,
)
from openfold3.projects.of3_all_atom.config.inference_query_format import (  # noqa: E402
    InferenceQuerySet,
)

# Upstream's own CLI calls both of these before it builds the runner, and
# `predict`'s `use_tf32` defaults to True in 0.5.0 (it did not exist in 0.4.1).
# A held worker is the CLI here, so it makes the same two calls once.
_configure_torch_backend()
_enable_tf32()

# The runner insists on an output directory at construction and creates it.
# Requests bring their own, so the one it is born with is a scratch directory
# that nothing is written to -- except upstream's own per-run records
# (`experiment_config.json`, `model_config.json`) and, crucially, the
# per-rank traceback file. `log_dir` is bound to the lightning module once, at
# construction, so EVERY traceback this provider ever produces lands here and
# not under the request's own output directory. That is the file to read when
# a request comes back having written no structure.
_BIRTH_DIR = Path(tempfile.mkdtemp(prefix="openfold3_ob0-resident-"))

_runner_args = config_utils.load_yaml(RUNNER_YAML) if RUNNER_YAML else {}
say(
    f"mode={MODE} weights_held_by={HOLDER} ckpt={CKPT} ({_SIZE} bytes, at its pin) "
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
# predict onto the validation branch cannot quietly restore the child.
LOADER_WORKERS_CONFIGURED = int(RUNNER.data_module_args.num_workers)
RUNNER.data_module_args.num_workers = 0
RUNNER.data_module_args.num_workers_validation = 0
say(
    f"loader workers: {LOADER_WORKERS_CONFIGURED} -> 0 (featurisation in this "
    f"process; a resident worker holding a built model and a CUDA context does "
    f"not start loader children, whatever the start method -- see the module "
    f"docstring)"
)

RUNNER.setup()  # reads the checkpoint into the module: the expensive half
BUILD_S = time.time() - T0

# The second half of the "did it load what you certified" check: the path the
# runner actually used, re-resolved after the load rather than asserted before
# it. Under a kit mode `ckpt_mmap` has replaced `load_checkpoint`, so this is
# also the check that the replacement did not quietly change the file.
_LOADED = Path(str(RUNNER.ckpt_path)).resolve()
if _LOADED != CKPT.resolve() or _LOADED.stat().st_size != CKPT_BYTES:
    raise _refuse(
        f"[openfold3_ob0-resident] the runner loaded {_LOADED} "
        f"({_LOADED.stat().st_size if _LOADED.exists() else 'absent'} bytes), not "
        f"the certified {CKPT} ({CKPT_BYTES} bytes)"
    )
say(f"model built t={BUILD_S:.1f}s from {_LOADED}")

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


def _apply_options(opts: dict, seed) -> None:
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


# A reply has to fit through a socket, and upstream's per-residue confidence
# record does not scale: `<sample>_confidences.json` carries the full N x N PDE
# matrix, so it is 61 KB for the 35-residue smoke and **29 MB** at 800
# residues -- measured, five of them per request. Five 29 MB JSON documents in
# one reply is the shape that gets truncated in transit and arrives as a broken
# answer rather than a refused one.
_SCORE_BYTES = 1 << 16


def _scores(out_dir: Path) -> tuple:
    """``(scores, omitted)``: the confidence records upstream wrote, parsed.

    They are what a caller ranks samples on, and returning a directory listing
    without them makes every caller re-read the disk this process just wrote.

    Two records exist per sample and only one of them scales. Upstream writes
    `<sample>_confidences_aggregated.json` -- ~270 bytes, carrying `avg_plddt`,
    `ptm`, `iptm`, `sample_ranking_score`, `has_clash` and the per-chain PTMs,
    which is the whole of what ranking five diffusion samples needs -- beside
    `<sample>_confidences.json`, which carries the per-residue pLDDT and the
    full N x N PDE matrix and reaches 29 MB at 800 residues. So the size cap
    keeps the first at every input size and drops the second above ~400
    residues.

    The omission is REPORTED rather than silent, which is the point of
    returning a second value. A caller that asks for 800 residues and gets a
    short `scores` object should be told the large record is on disk and where,
    not left to infer that the model did not produce one.
    """
    found: dict = {}
    omitted: list = []
    for path in sorted(out_dir.rglob("*.json")):
        name = path.name.lower()
        if "confidence" not in name and "summary" not in name:
            continue
        size = path.stat().st_size
        if size > _SCORE_BYTES:
            omitted.append(
                f"{path.relative_to(out_dir)} ({size} bytes, over the "
                f"{_SCORE_BYTES}-byte reply cap; read it from out_dir)"
            )
            continue
        try:
            found[str(path.relative_to(out_dir))] = json.loads(path.read_text())
        except (OSError, ValueError) as exc:  # a score we cannot read is not fatal
            omitted.append(f"{path.relative_to(out_dir)} ({type(exc).__name__})")
    return found, omitted


def _upstream_failure(out_dir: Path, from_byte: int) -> str:
    """Why a fold that returned normally produced nothing, in upstream's words.

    `predict_step` catches every exception a fold raises, appends the traceback
    to `<log_dir>/predict_err_rank<rank>.log` (`_log_predict_exception`) and
    lets the run finish; the writer then records the query as failed in
    `summary.txt`. A resident worker's `log_dir` is fixed at construction, so
    that file is under `_BIRTH_DIR` and grows across requests -- `from_byte` is
    where this request started writing, so only its own traceback is quoted.
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


def _rebind_msa_workspace(out_dir: Path) -> None:
    """Point upstream's MSA record root at THIS request's output directory.

    THE SECOND-REQUEST DEFECT THAT IS UPSTREAM'S, NOT THE KIT'S, and the reason
    0.4.1's provider never met it: 0.5.0 added
    `MsaComputationSettings`, and `InferenceExperimentRunner.__init__` binds it
    once --

        msa_settings.set_saved_output_root(self.output_dir / "msas")

    -- where `self.output_dir` is the directory the runner was BORN with. The
    settings object also fixes its per-run directory name once, as a pydantic
    PrivateAttr with a `default_factory`:

        _run_directory_name: str = PrivateAttr(default_factory=_default_run_directory_name)

    So `saved_output_directory` is `<birth>/msas/<one fixed name>` for the whole
    life of the worker. Every request then goes through
    `augment_main_msa_with_query_sequence` -- which is the NO-MSA-SERVER path,
    the one this provider always takes, writing a single-sequence dummy
    alignment per chain -- and that function does

        output_directory.mkdir(parents=True,
                               exist_ok=compute_settings.msa_output_directory is not None)

    with `msa_output_directory` None, i.e. **exist_ok=False**. Measured: request
    one folds, and every request after it fails with

        FileExistsError: [Errno 17] File exists:
        '/tmp/openfold3_ob0-resident-XXXX/msas/msa-<user>-<timestamp>-<hex>'

    caught per query by upstream, so it arrives as "wrote no structure". It is
    invisible to a one-request smoke, and -- unlike the kit's graph-pool defect
    -- it is invisible to a LENGTH LADDER too, because it does not care what the
    shape is: the acceptance run showed it on ladder rung TWO.

    The fix is upstream's own public setter, called per request instead of once
    at construction, which is exactly what residency changes about this runner.
    Nothing is patched and nothing is reimplemented: a one-process-per-request
    CLI gets a fresh output directory each time and so gets this for free.
    `set_saved_output_root` re-runs `validate_output_paths()` itself, so an
    overlap with the temporary workspace would still be refused by upstream.

    It also puts the records where a caller looking at its own output directory
    would expect them, instead of accumulating them in the worker's birth
    directory for as long as the worker lives.
    """
    settings = RUNNER.experiment_config.msa_computation_settings
    settings.set_saved_output_root(out_dir / "msas")


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
    # After the pops, so RUNNER.output_dir is this request's. See the function:
    # without this, request two of any shape fails inside upstream.
    _rebind_msa_workspace(RUNNER.output_dir)

    if DEVICE == "cuda":
        torch.cuda.reset_peak_memory_stats()
    err_from = _err_log_size()
    t = time.time()
    try:
        RUNNER.run(query_set)
    finally:
        # Upstream's own post-run step, which its CLI makes once per process at
        # the end of `predict`. A held worker has to make it per request or the
        # temporary MSA workspace accumulates for the life of the worker; it is
        # in a `finally` because a failed request leaves one behind too.
        RUNNER.cleanup_msa_workspace()
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
            f"OpenFold3 (OpenBind-0) wrote no structure for {name!r}: the fold "
            f"raised and upstream caught it per query.\n\n{detail}"
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
    scores, omitted = _scores(out_dir)
    if scores:
        body["scores"] = scores
    if omitted:
        # Named, never silent: a short `scores` object on a large request is
        # the reply cap, not a model that produced no confidences.
        body["scores_omitted"] = omitted
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
        "checkpoint": str(_LOADED),
        "checkpoint_bytes": CKPT_BYTES,
        "loader_workers": 0,
        "loader_workers_configured": LOADER_WORKERS_CONFIGURED,
        "post_release_ntok": POST_RELEASE_NTOK,
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
