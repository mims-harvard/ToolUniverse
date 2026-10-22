#!/usr/bin/env python
"""af2ig resident worker -- builds AlphaFold 2 once, re-predicts many complexes.

Runs in the MODEL's environment (CPython 3.11.5, jax/jaxlib 0.5.3 +
jax-cuda12-plugin, dm-haiku 0.0.16, tensorflow 2.21.0 CPU-only, and the pinned
dl_binder_design tree with the kit's patch series applied). It imports nothing
from ToolUniverse: ``protocol.py`` and ``worker_base.py`` are loaded by path,
which is the whole reason the two environments can hold conflicting stacks.

HOW THIS WRAPS THE KIT WITHOUT PATCHING IT, which is the one design decision
worth reading before anything else
------------------------------------------------------------------------------
``predict_pdb.py`` is a SCRIPT, not a library. ``args = parser.parse_args()``
sits at module level (line 113), the model is constructed at module level
(``af2_runner = AF2_runner(args, struct_manager)``, line 873), and the
prediction loop is the last statement in the file. There is no ``main()``, no
``if __name__ == "__main__"`` and nothing importable.

So this worker imports it anyway, with an argv of its own and an EMPTY input
directory. The module then runs exactly as upstream wrote it: it parses that
argv, builds ``StructManager`` and ``AF2_runner``, reads the 373 MB parameter
file, enumerates zero inputs, and the loop at the bottom iterates nothing. What
is left behind in the module namespace is a fully built AlphaFold 2 and
upstream's own I/O object, and this worker calls
``af2_runner.process_struct(path)`` on them once per request -- the same call
the loop makes, with the same objects, in the same process state.

Nothing of upstream is modified, shadowed, copied or reimplemented. The one
thing this worker does to the module between requests is rebind three paths on
``StructManager`` (``outpdbdir``, ``score_fn``, ``chkfn``) so each request
writes into its own directory, which is the same rebinding a second
``run.sh pred --out <dir>`` would do by starting a second process.

WHY THE EMPTY DIRECTORY RATHER THAN A DUMMY INPUT. ``StructManager.__init__``
asserts ``args.pdbdir != ''`` (silent files need PyRosetta and this front end
does not support them), so the directory must exist and be named. It must also
be EMPTY: anything in it would be folded during the import, before the socket
is bound, and the build time this worker reports would include a prediction.

WHAT IS HELD, AND WHAT IT IS WORTH
----------------------------------
* The 373 MB ``params_model_1_ptm.npz`` read and the haiku parameter tree
  built from it (``data.get_model_haiku_params``).
* TensorFlow's feature pipeline, imported and warm.
* **The compiled XLA programs**, which is the bulk of it. ``RunModel.apply``
  is ``jax.jit``-wrapped, so jax's own executable cache keeps one compiled
  program per input SHAPE for the life of the process.

AND THERE ARE NO BUCKETS HERE, which is the opposite of af3_jax and changes
what a repeat proves. The AF3 fork pads every input to a multiple of 64, so
near-by lengths share a program. This model does not pad at all: ``L =
len(feat_holder.seq)`` is the exact total residue count, ``self.seen_lengths``
is keyed on it, and the jit cache is keyed on the feature shapes, every one of
which is a pure function of that count. EVERY DISTINCT RESIDUE COUNT IS ITS OWN
COMPILATION, 2-4 minutes by the kit's own measurement. Four identical requests
therefore exercise exactly one program; a request one residue longer exercises
a new one.

NOTHING FORKS. The request path is `read_pdb_structure` (numpy) ->
`af2_util.generate_template_features` / `parse_initial_guess` (numpy + jnp) ->
`model_runner.process_features` (TensorFlow, on the CPU) -> `apply` (jax) ->
numpy post-processing -> two file writes. No ``multiprocessing``, no
``ProcessPoolExecutor``, no ``os.fork``. The kit levers that WOULD start
threads (L7 precompile's ``ThreadPoolExecutor``, L15 prefetch's worker, L16's
output writer) are declined in provider.toml, so not even a thread pool comes
up. ``OMP_NUM_THREADS=1`` is set by the launcher anyway, because TensorFlow
brings up its own intra-op pool in a process that already has CUDA initialised
and making the pool not exist is cheaper than reasoning about it.

PEAK MEMORY UNDER JAX -- READ THIS BEFORE COMPARING THE NUMBER
--------------------------------------------------------------
There is no torch here, so ``peak_reserved_gib`` cannot come from
``torch.cuda.max_memory_reserved``. It is
``jax.local_devices()[0].memory_stats()["peak_pool_bytes"]``, the high-water
mark of the BFC pool and the analogue of torch's *reserved*.
``peak_bytes_reserved`` is a TRAP: in XLA "reserved" means memory held OUTSIDE
the pool and it reads 0 on this host, so the field whose name matches would
report zero for every request forever. It is returned verbatim beside the real
one so a reader can see that for themselves.

``peak_pool_bytes`` is QUANTISED TO POWERS OF TWO. A JAX provider's
``vram_budget_gb`` is therefore a rounded-up ceiling sitting in the same column
as a torch provider's near-exact one; the gap between two rungs is not
headroom. ``peak_bytes_in_use`` -- the analogue of torch's *allocated*, and
what the kit's own instrument samples -- is returned beside it because it is
the tighter answer to "what did this input cost".

This worker does NOT reset peak statistics between requests, which is what the
standard asks of a new provider: a host adding budgets up needs the worker's
worst case. JAX offers no reset for ``peak_pool_bytes`` in any case.

ONE INPUT HAS ONE ANSWER
------------------------
Upstream fixes the seed: ``jax.random.PRNGKey(0)`` is a literal in
``process_struct`` and ``process_features(random_seed=0)`` is a literal in
``featurize``. There is no seed argument anywhere in ``predict_pdb.py``, so
this worker offers none -- a ``seed`` field that changed nothing would be a lie
in a schema. The useful side of that is that residency's effect on the ANSWER
is directly falsifiable: the same complex through a held worker must give a
byte-identical PDB every time. provider.toml's verified_on records the sha256s.
"""

from __future__ import annotations

import argparse
import atexit
import copy
import hashlib
import importlib.util
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

SLUG = "af2ig"
# Upstream's own defaults (predict_pdb.py argparse, lines 86-92; recorded in
# the kit's stock/PINS.json `settings`).
DEFAULT_RECYCLE = 3
DEFAULT_MAX_AMIDE_DIST = 3.0
# The kit's declared ceiling for one GPU is "up to 3,000 tokens" under `big`;
# this provider runs `off` and declares its budget at a measured row. The
# worker's own guard is the budget's envelope, not the kit's.
MAX_RESIDUES = 800
MAX_INPUT_BYTES = 32 * 1024 * 1024


def _refuse(message: str) -> SystemExit:
    """A refusal exits 3, per STANDARD section 8; its message goes to stderr.

    `raise SystemExit("text")` would print the text and exit **1**, which the
    standard reserves for "failed" -- a distinction a caller branches on, and
    the whole point of a named refusal is that a caller can. Fifty-four sites
    across eighteen workers got this wrong, every one with a correct message
    behind the wrong code.
    """
    sys.stderr.write(str(message).rstrip("\n") + "\n")
    sys.stderr.flush()
    return SystemExit(3)


def _load_worker_base():
    override = os.environ.get("TOOLUNIVERSE_REMOTE_WORKER_BASE")
    path = Path(override) if override else None
    if path is None or not path.is_file():
        raise _refuse(
            "TOOLUNIVERSE_REMOTE_WORKER_BASE must point at "
            "remote_resident/worker_base.py; this worker never imports "
            "tooluniverse"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _say(msg: str) -> None:
    print(f"[{SLUG}-resident] {msg}", flush=True)


_TAG_OK = re.compile(r"[^A-Za-z0-9_.-]+")


def _tag(name: str) -> str:
    """A filesystem-safe tag. It becomes a file name, so it is sanitised here.

    Upstream derives the tag from the input FILE name
    (``'.'.join(basename.split('.')[:-1])``) and uses it for the output PDB,
    the score line and the checkpoint line. A caller-supplied name reaches all
    three, so a `../` in it would reach outside the request's directory.
    """
    out = _TAG_OK.sub("_", (name or "query").strip()) or "query"
    return out[:64]


def _sweep_stale_work_dirs() -> None:
    """Remove `<tmpdir>/af2ig-worker-<pid>-*` trees whose pid is gone.

    Only this user's, only this slug's, and only ones whose pid no longer
    exists -- a live sibling worker's directory is left alone, because two
    workers of this provider can legitimately coexist for the seconds between
    one retiring and the next binding the socket.
    """
    root = tempfile.gettempdir()
    prefix = f"{SLUG}-worker-"
    try:
        names = os.listdir(root)
    except OSError:
        return
    for name in names:
        if not name.startswith(prefix):
            continue
        rest = name[len(prefix) :].split("-", 1)[0]
        if not rest.isdigit():
            continue
        path = os.path.join(root, name)
        try:
            if os.path.islink(path) or not os.path.isdir(path):
                continue
            if os.stat(path).st_uid != os.getuid():
                continue
            os.kill(int(rest), 0)
        except ProcessLookupError:
            shutil.rmtree(path, ignore_errors=True)
        except (OSError, PermissionError, ValueError):
            continue


class Engine:
    """Everything held between requests."""

    def __init__(self, args):
        self.args = args
        self.mode = args.mode
        self.tree = os.path.abspath(os.path.expanduser(args.af2ig_dir))
        self.params_dir = os.path.abspath(os.path.expanduser(args.params_dir))
        self.cache_dir = os.path.abspath(os.path.expanduser(args.cache_dir))
        self.build_s = None
        self.requests = 0
        self.config_rebuilds = 0
        self.compiled_lengths = []
        self._mod = None
        self._device = None
        self._runner_key = None
        self._work = None
        self._stage = None
        self._jit_cache = None

    # -------------------------------------------------------------- building
    def build(self) -> None:
        t0 = time.time()
        if self.mode != "off":
            # Every lever of this kit is a command-line flag of
            # `predict_pdb.py` that the kit's own CLI appends before running
            # it as a subprocess. A worker handed another mode would silently
            # run stock and report the mode, which is the one thing a mode
            # name must never do. provider.toml's [kit] section argues why
            # `off` is the right answer on this card rather than a retreat.
            raise _refuse(
                f"[{SLUG}-resident] --mode {self.mode!r}: this worker implements "
                f"the kit's stock route only. af2ig's levers are argparse flags "
                f"of predict_pdb.py applied by `af2ig-opt pred --mode M`, which "
                f"runs the driver as a batch subprocess; four of them overlap "
                f"work across a campaign's inputs and have no meaning for one "
                f"request, and the three kernel levers have no float32 tile row "
                f"for this compute capability. See provider.toml [kit]."
            )

        params = os.path.join(self.params_dir, "params", "params_model_1_ptm.npz")
        if not os.path.isfile(params):
            raise _refuse(
                f"[{SLUG}-resident] --params-dir {self.params_dir} holds no "
                f"params/params_model_1_ptm.npz. AF2_PARAMS names the DIRECTORY "
                f"THAT HOLDS params/, not the params directory and not the file "
                f"(the kit's own convention). Run "
                f"`tu remote setup {SLUG} --only weights`."
            )
        driver = os.path.join(self.tree, "predict_pdb.py")
        if not os.path.isfile(driver):
            raise _refuse(
                f"[{SLUG}-resident] --af2ig-dir {self.tree} holds no "
                f"predict_pdb.py. That file is CREATED by the kit's patch "
                f"series (patches/00_pdb_frontend_envport.diff) on the pinned "
                f"dl_binder_design tree, so this is the patched checkout and "
                f"not the installed af2ig_opt package. Run "
                f"`tu remote setup {SLUG} --only kit`."
            )

        # Set before jax is imported, in case the launcher did not. Left at its
        # default JAX takes 75% of the device at the first allocation, and
        # every peak this worker reported would be a measurement of that
        # preallocation rather than of the model (af3_jax: 91.22 GiB against a
        # real 2.0).
        os.environ.setdefault("XLA_PYTHON_CLIENT_PREALLOCATE", "false")
        os.environ.setdefault("OMP_NUM_THREADS", "1")

        # One staging directory for the module's import-time argv and one for
        # per-request inputs. The first MUST stay empty: `StructManager`
        # enumerates it at construction and anything in it would be folded
        # during the import.
        # Swept at START-UP, not only at exit, and the distinction is the whole
        # reason this is three lines instead of one. A resident worker has three
        # ways to die and only one of them runs `atexit`: a clean shutdown does,
        # an idle timeout that ends in SIGKILL does not, and the orphan watchdog
        # calls `os._exit(0)` -- which is correct there, because the serve loop
        # is blocked in `accept()` and there is nothing to unwind, and which
        # skips every handler. So the directory is named with this process's
        # pid and every sibling whose pid is gone is removed first. Without it,
        # one `/tmp/af2ig-worker-*` tree accumulates per worker lifetime, which
        # the first draft of this file did.
        _sweep_stale_work_dirs()
        self._work = tempfile.mkdtemp(prefix=f"{SLUG}-worker-{os.getpid()}-")
        atexit.register(shutil.rmtree, self._work, True)
        self._stage = os.path.join(self._work, "empty-at-import")
        os.makedirs(self._stage, exist_ok=True)
        boot = os.path.join(self._work, "boot")
        os.makedirs(boot, exist_ok=True)

        argv = [
            "predict_pdb.py",
            "-pdbdir",
            self._stage,
            "-outpdbdir",
            os.path.join(boot, "pdbs"),
            "-scorefilename",
            os.path.join(boot, "out.sc"),
            "-checkpoint_name",
            os.path.join(boot, "check.point"),
            "-af2_dir",
            self.params_dir,
            "-recycle",
            str(self.args.recycle),
            "-max_amide_dist",
            str(self.args.max_amide_dist),
            # Upstream's own per-design record stream: `proc_start`,
            # `params_loaded`, `runner_ready`, then one `design` record per
            # request carrying its own t_load / t_feat / t_tf / t_model and
            # `peak_bytes_in_use`. Kept because it is the kit's instrument
            # rather than ours, and a disagreement between the two is worth
            # being able to see.
            "-timers",
            os.path.join(self.cache_dir, "timers.jsonl"),
        ]
        # ABSENT FROM THAT ARGV, and checkable by reading this list, which is
        # the point of building the argv here rather than letting a default
        # decide: no -fast, no -device_params, no -precompile, no
        # -program_cache, no -prefetch, no -overlap_output, no -flash_attn, no
        # -fused_triattn, no -fused_trimul, no -opm_reassoc, no -subbatch, no
        # -tmpl_pointwise_sub, no -trimul_chunk. Exactly one lever flag is
        # added below, from an explicit switch the manifest passes.

        if self.args.device_params:
            # L1. Only reachable through an explicit --device-params, and the
            # manifest does NOT pass it: the per-call host->device transfer it
            # removes is 355.7 MiB over 338 arrays and costs 2.4-6.2 ms on this
            # card's unified memory, against a held request of tens of seconds.
            # The switch stays so the measurement can be repeated on a card
            # with a separate device pool behind a bus, where it would pay.
            argv.append("-device_params")
        if self.args.host_outputs:
            # L6, and the manifest DOES pass it -- the one kit lever this
            # provider engages. One jax.device_get of the output tree instead
            # of numpy and scipy pulling each device array lazily during
            # post-processing. On a held 195-residue request upstream's own
            # timers put t_output at 45-57 s against t_model at 14-17 s, so the
            # transfer, not the model, is most of a warm request; with this
            # flag the held request is 12.8-13.3 s instead of 60.6-75.5 s.
            # EXACT, checked rather than assumed: under the kit's own
            # deterministic recipe (XLA_FLAGS=--xla_gpu_autotune_level=0) a
            # stock worker, this worker, and the kit's own `run.sh pred --mode
            # off --det 1` all produce sha256
            # 81d69b99410824b7fad9ca5a9b9134d8e52f789580fe5202d1ce74ca8e70dc89.
            argv.append("-host_outputs")

        self._mod = self._import_driver(driver, argv)

        import jax  # noqa: E402  - after the driver, which configures sys.path

        devices = jax.local_devices(backend="gpu")
        if not devices:
            raise _refuse(
                f"[{SLUG}-resident] jax reports no GPU device "
                f"(default_backend={jax.default_backend()!r}); this provider "
                f'declares [gpu] policy = "required". Note the stack also '
                f"carries tensorflow, which is CPU-only on this architecture "
                f"by design -- a check that asked tensorflow about the card "
                f"would get the wrong answer."
            )
        self._device = devices[0]
        self._jax = jax
        self._runner_key = (self.args.recycle, not self.args.no_initial_guess)

        self.build_s = round(time.time() - t0, 2)
        _say(
            f"ready device={self._device.device_kind} cc={self.compute_capability} "
            f"jax={jax.__version__} mode={self.mode} weights_held_by=worker "
            f"recycle={self.args.recycle} initial_guess={not self.args.no_initial_guess} "
            f"device_params={self.args.device_params} "
            f"host_outputs={self.args.host_outputs} "
            f"jit_cache={self._jit_cache or 'off (process-local only)'} "
            f"tree={self.tree} params={self.params_dir} build_s={self.build_s}"
        )

    def _import_driver(self, driver: str, argv):
        """Import upstream's script with our argv, leaving its objects built.

        `sys.argv` is swapped for the duration because the module parses it at
        import. It is restored afterwards so that anything later in this
        process -- a traceback, an absl flag, upstream's own `proc_start`
        record -- does not read a line that is no longer true.
        """
        jit_root = os.environ.get("AF2IG_JIT_ROOT", "").strip()
        if jit_root:
            # OPT-IN ONLY. The kit's stock caller strips
            # JAX_COMPILATION_CACHE_DIR before running the stock driver, so a
            # persistent executable cache is a deviation from the stock route
            # however harmless it looks -- and this provider's residency
            # numbers are quoted against the stock one. An operator who wants
            # compiled programs to survive a restart exports AF2IG_JIT_ROOT
            # and it is named on the ready line, rather than inferred from a
            # wall time that got faster.
            import jax as _jax

            os.makedirs(jit_root, exist_ok=True)
            _jax.config.update("jax_compilation_cache_dir", jit_root)
            self._jit_cache = jit_root

        saved = sys.argv
        sys.argv = list(argv)
        try:
            spec = importlib.util.spec_from_file_location("predict_pdb", driver)
            module = importlib.util.module_from_spec(spec)
            # Registered before exec: the module imports `af2_util`, which
            # upstream expects to resolve from the same directory, and a
            # failure part-way through should leave a diagnosable entry rather
            # than a half-built anonymous module.
            sys.modules["predict_pdb"] = module
            spec.loader.exec_module(module)
        except SystemExit as exc:
            # argparse exits 2 on a bad flag. Upstream's words are already on
            # stderr; this says whose argv it was.
            raise _refuse(
                f"[{SLUG}-resident] upstream's predict_pdb.py exited "
                f"{exc.code} while this worker was importing it with "
                f"{' '.join(argv[1:])}"
            ) from exc
        finally:
            sys.argv = saved

        for attr in ("af2_runner", "struct_manager", "args", "AF2_runner"):
            if not hasattr(module, attr):
                raise _refuse(
                    f"[{SLUG}-resident] predict_pdb.py imported but has no "
                    f"{attr!r}: this worker stands in the position of its "
                    f"prediction loop and needs the objects that loop uses. "
                    f"The tree at {self.tree} is not the patched pin."
                )
        if module.struct_manager.struct_iterator:
            raise _refuse(
                f"[{SLUG}-resident] the import-time input directory "
                f"{self._stage} was not empty; upstream's loop would have "
                f"folded its contents before this worker bound its socket"
            )
        return module

    @property
    def compute_capability(self) -> str:
        try:
            return str(self._device.compute_capability)
        except Exception:  # noqa: BLE001 - informational only
            return "?"

    def _ensure_runner(self, recycle: int, initial_guess: bool) -> bool:
        """Hold an AF2_runner for (recycle, initial_guess); True when rebuilt.

        BOTH ARE COMPILE-TIME. `AF2_runner.__init__` bakes them into
        `model_config` (`data.common.num_recycle`, `model.num_recycle`,
        `embeddings_and_evoformer.initial_guess`) before `model.RunModel` is
        constructed, so neither can be changed on a held runner -- the jitted
        function closes over the config.

        THE SECOND BUILD IS THE DANGEROUS ONE and it is exercised rather than
        assumed. genie3 would have passed four identical requests and raised
        on the first that changed its engine key, because upstream's config
        was a module-level mutable permitting one build per process. The
        equivalent here is `alphafold.model.config.model_config`, which does
        `copy.deepcopy(CONFIG)` and `copy.deepcopy(CONFIG_DIFFS[name])` before
        touching anything -- so a second call cannot reach the first's object.
        Checked by calling it twice in one process before this worker was
        written, and exercised by the acceptance suite's recycle change.
        """
        key = (int(recycle), bool(initial_guess))
        if self._runner_key == key:
            return False
        mod = self._mod
        _say(f"config change {self._runner_key} -> {key}: rebuilding AF2_runner")
        args2 = copy.copy(mod.args)
        args2.recycle = int(recycle)
        args2.no_initial_guess = not initial_guess
        # Dropped before the new one is built: under `off` the parameters are
        # host numpy arrays, so this frees host memory rather than device
        # memory, but a 373 MB tree is worth not holding twice.
        mod.af2_runner = None
        mod.af2_runner = mod.AF2_runner(args2, mod.struct_manager)
        self._runner_key = key
        self.config_rebuilds += 1
        return True

    # ------------------------------------------------------------- measuring
    def memory(self) -> dict:
        try:
            stats = self._device.memory_stats() or {}
        except Exception:  # noqa: BLE001 - a missing stat must not fail a fold
            return {}
        gib = 1024.0**3
        out = {}
        if stats.get("peak_pool_bytes") is not None:
            out["peak_reserved_gib"] = round(stats["peak_pool_bytes"] / gib, 2)
        if stats.get("peak_bytes_in_use") is not None:
            out["peak_in_use_gib"] = round(stats["peak_bytes_in_use"] / gib, 2)
        if stats.get("bytes_limit") is not None:
            out["bytes_limit_gib"] = round(stats["bytes_limit"] / gib, 2)
        # Returned verbatim so a reader can see for themselves that the field
        # whose NAME says "reserved" is not the one to use.
        out["peak_bytes_reserved"] = stats.get("peak_bytes_reserved")
        out["memory_source"] = (
            "jax.local_devices()[0].memory_stats()['peak_pool_bytes'] "
            "(quantised to powers of two)"
        )
        return out

    # --------------------------------------------------------------- folding
    def predict(self, req: dict) -> dict:
        t0 = time.time()
        mod = self._mod

        text = req.get("input")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                "'input' must be the text of a PDB file holding the complex: "
                "chain 1 is the binder, every following chain is the target. "
                "This model re-predicts a STRUCTURE it is given; there is no "
                "sequence-only route, because without coordinates there is no "
                "initial guess and no template."
            )
        if len(text) > MAX_INPUT_BYTES:
            raise ValueError(
                f"the input PDB is {len(text)} bytes, over this provider's "
                f"{MAX_INPUT_BYTES} limit"
            )
        if not any(line.startswith("ATOM") for line in text.splitlines()):
            raise ValueError(
                "the input carries no ATOM records. upstream's parser reads "
                "ATOM lines only -- HETATM, waters and ligands are dropped by "
                "the kit's own public-input recipe -- so a file of HETATM "
                "records parses as an empty structure."
            )

        options = req.get("options") or {}
        recycle = int(options.get("num_recycle", self.args.recycle))
        initial_guess = bool(
            options.get("initial_guess", not self.args.no_initial_guess)
        )
        force_monomer = bool(options.get("force_monomer", False))
        max_amide_dist = float(options.get("max_amide_dist", self.args.max_amide_dist))

        out_dir = req.get("out_dir") or tempfile.mkdtemp(prefix=f"{SLUG}-out-")
        os.makedirs(out_dir, exist_ok=True)
        tag = _tag(req.get("name") or "query")

        in_dir = tempfile.mkdtemp(prefix="in-", dir=self._work)
        pdb_in = os.path.join(in_dir, f"{tag}.pdb")
        with open(pdb_in, "w", encoding="utf-8") as fh:
            fh.write(text if text.endswith("\n") else text + "\n")

        config_rebuilt = self._ensure_runner(recycle, initial_guess)
        runner = mod.af2_runner
        sm = mod.struct_manager

        # Per-request I/O, rebound on upstream's own object. `force_monomer`
        # and `max_amide_dist` are read per call (in `load_structure` and
        # `featurize`), unlike recycle and initial_guess, so they cost no
        # rebuild.
        pdbs_dir = os.path.join(out_dir, "pdbs")
        sm.outpdbdir = pdbs_dir
        sm.score_fn = os.path.join(out_dir, "out.sc")
        sm.chkfn = os.path.join(out_dir, "check.point")
        sm.force_monomer = force_monomer
        # A fresh set per request: upstream reads the checkpoint file at
        # construction to resume a campaign, and a tag it thinks is finished
        # is SKIPPED. Two requests with the same name in one worker would
        # otherwise silently return the first one's file.
        sm.finished_structs = set()
        runner.max_amide_dist = max_amide_dist

        # Upstream writes the score line through `record_scores`; capturing it
        # here means the reply carries the same numbers that reach out.sc,
        # from the same call, rather than a re-parse of the file.
        captured = {}
        original = sm.record_scores

        def _capture(scored_tag, score_dict, string_dict):
            captured.update(score_dict or {})
            captured["tag"] = scored_tag
            return original(scored_tag, score_dict, string_dict)

        sm.record_scores = _capture
        try:
            # THE SAME CALL UPSTREAM'S LOOP MAKES. `_run_one` wraps it in a
            # bare `except:` that prints and carries on, which is right for a
            # campaign of a thousand designs and wrong for one request: a
            # caller asked for this structure and an exception is the answer.
            runner.process_struct(pdb_in)
        finally:
            sm.record_scores = original
            shutil.rmtree(in_dir, ignore_errors=True)

        produced = os.path.join(pdbs_dir, f"{tag}_af2pred.pdb")
        if not os.path.isfile(produced):
            # An exit code is not evidence that a model ran, and here neither
            # is a returned call: `check.point` is appended for every tag the
            # loop finishes INCLUDING one that raised, so a directory can hold
            # upstream's own bookkeeping and no structure.
            raise RuntimeError(
                f"process_struct returned without writing {produced}. The "
                f"request is reported failed rather than empty; "
                f"{out_dir} holds whatever upstream did write."
            )
        n_res, n_chains, binderlen = _shape_of(text)
        with open(produced, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()

        if n_res > MAX_RESIDUES:
            _say(
                f"note: {n_res} residues is above the {MAX_RESIDUES} this "
                f"provider's VRAM budget was measured at"
            )

        body = {
            "model": "AlphaFold 2 model_1_ptm, initial guess (dl_binder_design cafa3853)",
            "kit_mode": self.mode,
            "weights_held_by": "worker",
            # `structures` is [runtime] output_keys and `files` is what the
            # smoke step's directory walk compares against [runtime] outputs.
            "structures": [produced],
            "files": [produced, sm.score_fn, sm.chkfn],
            "score_file": sm.score_fn,
            "tag": f"{tag}_af2pred",
            "sha256": digest,
            "scores": {k: _number(v) for k, v in captured.items() if k != "tag"},
            "n_residues": n_res,
            "n_chains": n_chains,
            "binder_length": binderlen,
            "monomer": n_chains == 1 or force_monomer,
            "num_recycle": recycle,
            "initial_guess": initial_guess,
            "force_monomer": force_monomer,
            "max_amide_dist": max_amide_dist,
            "config_rebuilt": config_rebuilt,
            "config_rebuilds": self.config_rebuilds,
            "requests_served": self.requests + 1,
            "new_length": n_res not in self.compiled_lengths,
            "compiled_lengths": sorted(set(self.compiled_lengths + [n_res])),
            "seed": "fixed upstream: jax.random.PRNGKey(0), no seed argument",
            "timing": {"total_s": round(time.time() - t0, 2)},
        }
        self.requests += 1
        if n_res not in self.compiled_lengths:
            self.compiled_lengths.append(n_res)
        body.update(self.memory())
        return body


def _shape_of(text: str):
    """(total residues, chains, binder length) from the input PDB's CA atoms.

    Read the same way upstream reads it -- ATOM records, chain id in column 22,
    residues in file order -- so the number reported is the number that sets
    the compiled shape rather than an independent count that could disagree.
    """
    chains = []
    seen = set()
    for line in text.splitlines():
        if not line.startswith("ATOM") or len(line) < 27:
            continue
        if line[12:16].strip() != "CA":
            continue
        key = (line[21], line[22:27])
        if key in seen:
            continue
        seen.add(key)
        if not chains or chains[-1][0] != line[21]:
            chains.append([line[21], 0])
        chains[-1][1] += 1
    total = sum(n for _, n in chains)
    return total, len(chains), (chains[0][1] if chains else 0)


def _number(value):
    """A JSON-safe float from a numpy scalar or NaN."""
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return value if isinstance(value, (str, int, bool)) else None
    return None if out != out else round(out, 4)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="af2ig resident worker")
    parser.add_argument("--socket", required=True)
    parser.add_argument("--slug", default=SLUG)
    parser.add_argument("--mode", default="off")
    parser.add_argument("--af2ig-dir", required=True)
    parser.add_argument("--params-dir", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--recycle", type=int, default=DEFAULT_RECYCLE)
    parser.add_argument("--max-amide-dist", type=float, default=DEFAULT_MAX_AMIDE_DIST)
    parser.add_argument("--no-initial-guess", action="store_true", default=False)
    # The kit's L1 and L6. Off: measured on this card and did not pay. See
    # provider.toml [kit].
    parser.add_argument("--device-params", action="store_true", default=False)
    parser.add_argument("--host-outputs", action="store_true", default=False)
    args = parser.parse_args(argv)

    base = _load_worker_base()
    engine = Engine(args)
    engine.build()

    def ready():
        body = {
            "build_s": engine.build_s,
            "kit_mode": engine.mode,
            "weights_held_by": "worker",
            "compute_capability": engine.compute_capability,
            "requests_served": engine.requests,
            "config_rebuilds": engine.config_rebuilds,
            "compiled_lengths": sorted(set(engine.compiled_lengths)),
            "padding": "none: one XLA program per exact total residue count",
            "device_params": args.device_params,
            "host_outputs": args.host_outputs,
        }
        body.update(engine.memory())
        return body

    return base.serve(
        slug=args.slug,
        socket_path=args.socket,
        on_predict=engine.predict,
        ready=ready,
        log=_say,
    )


if __name__ == "__main__":
    sys.exit(main())
