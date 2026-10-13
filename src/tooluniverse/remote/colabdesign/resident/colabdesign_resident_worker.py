#!/usr/bin/env python
"""ColabDesign resident worker -- one process holding BindCraft's design step.

Runs in the MODEL's environment (CPython 3.10.18, jax/jaxlib 0.6.0 +
jax-cuda12-plugin, ColabDesign 1.1.3 at commit e31a56fe, the kit's
``colabdesign_opt`` and its shared core). It imports nothing from ToolUniverse:
``protocol.py`` and ``worker_base.py`` are loaded by path, which is the whole
reason the two environments can hold conflicting stacks.

WHAT THIS PROVIDER DOES, AND THAT IT NEEDS NO ALIGNMENT
-------------------------------------------------------
BindCraft's design step is *binder hallucination*: AlphaFold-Multimer is run
BACKWARDS from a loss to optimise the sequence of a new chain bound to a given
target structure. The input is a target PDB, a chain, a binder length and
(optionally) hotspot residues. There is no MSA anywhere in it -- the model is fed
the target's backbone as a template and a single sequence for the binder -- so
this provider has nothing to fetch at request time, and nothing to refuse for
that reason. (Unlike ColabFold, whose usual route is a remote MMseqs2 server,
there is no external service on any route of this kit's design step.) The only
things this provider ever downloaded were the 1.86 GB of parameters and BindCraft's
DSSP executable, both by ``tu remote setup`` and both digest-checked.

WRAP, DO NOT PATCH
------------------
The worker calls the kit's own driver, ``colabdesign_opt.bindcraft``:
``prepare()`` (settings, BindCraft's modules imported unmodified from the pinned
vendored tree, BindCraft's derivation, the named refusals) and ``run_design()``
(``binder_hallucination`` itself, then ``design.pdb`` / ``design.fasta`` /
``trajectory.jsonl``). Nothing of upstream or of the kit is modified, copied or
shadowed. This is the same code the kit's CLI runs in its subprocess.

WHO HOLDS THE MODEL: NOBODY, AND THAT IS UPSTREAM'S DESIGN
----------------------------------------------------------
``binder_hallucination`` begins with ``clear_mem()`` (which DELETES every live
device buffer) and then builds a fresh ``mk_afdesign_model`` -- reading the
parameter files and tracing the model again -- for every trajectory. So unlike
the providers that hold weights, there is no model here for a worker to keep, and
a worker that tried would have its buffers deleted by the next request. What a
held process DOES keep is everything around the model: the interpreter, jax,
ColabDesign and BindCraft's imports, the CUDA context, the kit's levers (under a
kit mode) and, with them, the cache of compiled executables. The ready line says
``weights_held_by=nobody``.

THE ENGINE KEY
--------------
What is compile-time here is the trajectory's SHAPES and its recycle count: the
target's residue count, the binder length and ``num_recycles_design``. A request
that changes any of them is a different set of XLA programs. The worker records
the keys it has seen, and the reply says ``engine_key`` and whether it was new
(``first_of_engine_key``), so a long first request is not mistaken for a hang.
Upstream's builder was called three times in one process, with three different
keys, BEFORE this worker was written (the genie3 check: a module-level mutable
config that permits one build per process). It has no such state.

TWO SETTINGS THE WORKER FIXES, AND WHY EACH IS WRITTEN DOWN
-----------------------------------------------------------
Both are BindCraft's OWN advanced-settings keys, handed to it through the kit's
``--advanced FILE`` route -- configuration, not a patch.

* ``optimise_beta``: BindCraft's default is true, which runs DSSP on the stage-1
  structure. The DSSP executable the kit fetches is BindCraft's prebuilt
  ``functions/dssp``, an x86-64 static ELF; on an aarch64 host exec fails with
  ``Exec format error``. The worker PROBES that executable at start-up and sets
  the key false only when it cannot run, so on a host where DSSP runs the default
  is kept. The reply and the ready line say which (``optimise_beta``).
* ``save_design_animations`` / ``save_design_trajectory_plots``: false. Neither
  artefact is returned, and the animation is written through matplotlib's ffmpeg
  writer, which needs an ``ffmpeg`` that is not on this host's PATH. Neither feeds
  design.pdb, design.fasta or trajectory.jsonl.

NOTHING OF OURS FORKS
---------------------
With animations, plots, DSSP, MPNN and PyRosetta all off the request path, it
contains no ``multiprocessing``, no ``os.fork`` and no subprocess. XLA assembles
PTX with ``ptxas`` processes it ``exec``s, which hold no CUDA context.

PEAK MEMORY UNDER JAX
---------------------
``peak_reserved_gib`` is ``jax.local_devices()[0].memory_stats()["peak_pool_bytes"]``
(``peak_bytes_reserved`` is a trap that reads 0) and ``peak_in_use_gib`` is
``peak_bytes_in_use``. Neither is reset between requests: a host adding budgets up
needs the worker's worst case, and JAX offers no reset for the pool figure.
``XLA_PYTHON_CLIENT_PREALLOCATE=false`` is set in the launch; left at jax's default
the figure reports the preallocation rather than the model.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SLUG = "colabdesign"

# The advanced-settings keys a caller may change, with the bounds the worker
# enforces. They are bounds on WORK, not on shape: BindCraft's default is
# 75 / 45 / 5 / 15, and `design_logits(iters=50)` in stage 1 is hard-coded
# upstream, so fewer than 50 soft iterations does not make stage 1 shorter.
ITERATION_BOUNDS = {
    "soft_iterations": (50, 200),
    "temporary_iterations": (0, 100),
    "hard_iterations": (0, 50),
    "greedy_iterations": (0, 50),
}
RECYCLE_BOUNDS = (1, 3)
# The shape ceiling, TOTAL TOKENS = target residues + binder length, which is the
# row the VRAM budget was measured at (provider.toml [gpu]). Checked here as well
# as in the MCP server because a socket caller does not go through it.
MAX_TOKENS = 400
MIN_BINDER, MAX_BINDER = 8, 250
MAX_PDB_BYTES = 8 * 1024 * 1024
MAX_CHAINS_REQUESTED = 4
OMIT_AA_LETTERS = set("ACDEFGHIKLMNPQRSTVWY")

# The three files `run_design` writes, in the order it writes them; the first is
# what [runtime] outputs matches.
OUTPUT_FILES = ("design.pdb", "design.fasta", "trajectory.jsonl")
TMP_PREFIX = "colabdesign-in-"


def _refuse(message: str) -> SystemExit:
    """A refusal exits 3, per STANDARD section 8; its message goes to stderr.

    `raise SystemExit("text")` would print the text and exit **1**, which the
    standard reserves for "failed" -- a distinction a caller branches on.
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


def _number(value):
    """A JSON-safe float from a numpy scalar, bool or NaN."""
    if value is None:
        return None
    try:
        out = float(value)
        return None if math.isnan(out) or math.isinf(out) else round(out, 5)
    except (TypeError, ValueError):
        return None


def _jsonable(obj):
    """Numpy scalars and arrays to plain Python, recursively."""
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if hasattr(obj, "tolist"):
        return _jsonable(obj.tolist())
    if isinstance(obj, float):
        return _number(obj)
    if isinstance(obj, (int, str, bool)) or obj is None:
        return obj
    return str(obj)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def sweep_stale_temp() -> int:
    """Remove temp trees left by a worker that died without cleaning up.

    The orphan watchdog exits through ``os._exit``, which skips ``atexit`` by
    design, so a worker must sweep at START-UP as well as removing its own tree at
    the end of each request. The pid is in the name and is checked: a directory
    belonging to a live worker is never touched.
    """
    removed = 0
    base = Path(tempfile.gettempdir())
    for p in base.glob(f"{TMP_PREFIX}*"):
        m = re.match(rf"{re.escape(TMP_PREFIX)}(\d+)-", p.name)
        if not m or not p.is_dir():
            continue
        if int(m.group(1)) != os.getpid() and not _pid_alive(int(m.group(1))):
            shutil.rmtree(p, ignore_errors=True)
            removed += 1
    return removed


def _target_residues(pdb_text: str, chains: list) -> dict:
    """Residues with a CA atom per requested chain, the way the kit counts them
    (``colabdesign_opt.inputs.ca_residues``): ATOM records, altloc blank or 'A'."""
    seen = {c: set() for c in chains}
    for line in pdb_text.splitlines():
        if len(line) < 27 or not line.startswith("ATOM"):
            continue
        if line[12:16].strip() != "CA" or line[16] not in (" ", "A"):
            continue
        c = line[21]
        if c in seen:
            seen[c].add(line[22:27])
    return {c: len(v) for c, v in seen.items()}


class Engine:
    """Everything held between requests."""

    def __init__(self, args):
        self.args = args
        self.mode = args.mode
        self.tree = os.path.abspath(os.path.expanduser(args.kit))
        self.params_dir = os.path.abspath(os.path.expanduser(args.params_dir))
        self.cache_dir = os.path.abspath(os.path.expanduser(args.cache_dir))
        self.build_s = None
        self.requests = 0
        self.config_rebuilds = 0
        self.keys_seen = []
        self.shapes_seen = []
        self._device = None
        self._bindcraft = None
        self._report = None
        self._settings = None
        self._default_advanced = None
        self.activation = None
        self.optimise_beta_default = None
        self.dssp_runnable = None

    # -------------------------------------------------------------- building
    def build(self) -> None:
        t0 = time.time()
        if not os.path.isdir(os.path.join(self.tree, "stock")):
            raise _refuse(
                f"[{SLUG}-resident] --kit {self.tree} is not the colabdesign kit "
                f"(no stock/ under it). Run `tu remote setup {SLUG} --only kit`"
            )
        missing = [
            n
            for n in [
                f"params/params_model_{i}_multimer_v3.npz" for i in range(1, 6)
            ]
            if not os.path.isfile(os.path.join(self.params_dir, n))
        ]
        if missing:
            raise _refuse(
                f"[{SLUG}-resident] the AlphaFold-Multimer v3 parameters are "
                f"incomplete under {self.params_dir}: {', '.join(missing)}. "
                f"Run `tu remote setup {SLUG} --only weights`"
            )
        # Before jax is imported: jax reads this at its first allocation.
        os.environ.setdefault("XLA_PYTHON_CLIENT_PREALLOCATE", "false")
        # The kit's own variable for "this tree"; the launcher sets it too.
        os.environ.setdefault("MODEL_OPT", self.tree)
        for name in ("COLABDESIGN_OPT", "MODEL_OPT_LEVERS_OFF"):
            if os.environ.get(name):
                raise _refuse(
                    f"[{SLUG}-resident] {name} is set in this process's "
                    f"environment ({os.environ[name]!r}); the launcher removes "
                    f"it, so this worker was started some other way. The kit's "
                    f"start-up hook would act on it at `import colabdesign`."
                )

        try:
            import colabdesign_opt  # noqa: E402
        except ImportError as exc:
            raise _refuse(
                f"[{SLUG}-resident] colabdesign_opt is not importable "
                f"({type(exc).__name__}: {exc}). Run "
                f"`tu remote setup {SLUG} --only kit`"
            ) from None

        if self.mode != "off":
            # The kit's own in-process route (README: `colabdesign_opt.enable`):
            # the mode's levers are installed BEFORE the first mk_afdesign_model,
            # which is where the kit's late-activation refusal puts the line.
            try:
                self.activation = colabdesign_opt.enable(self.mode, strict=True)
            except colabdesign_opt.ActivationError as exc:
                raise _refuse(
                    f"[{SLUG}-resident] the kit refused mode {self.mode!r}: {exc}"
                ) from None
            if not self.activation.get("active"):
                raise _refuse(
                    f"[{SLUG}-resident] mode {self.mode!r} did not activate: "
                    f"{self.activation.get('reason')}"
                )

        from colabdesign_opt import bindcraft, report, settings  # noqa: E402
        import jax  # noqa: E402

        devices = jax.local_devices(backend="gpu")
        if not devices:
            raise _refuse(
                f"[{SLUG}-resident] jax reports no GPU device "
                f"(default_backend={jax.default_backend()!r}); this provider "
                f'declares [gpu] policy = "required"'
            )
        self._device = devices[0]
        self._bindcraft, self._report, self._settings = bindcraft, report, settings

        # BindCraft's own modules, imported once, unmodified, from the vendored tree.
        bindcraft.functions(self.tree)
        self._default_advanced = dict(settings.load(self.tree)["advanced"])
        self.optimise_beta_default = bool(self._default_advanced.get("optimise_beta"))
        self.dssp_runnable = self._probe_dssp()

        self.build_s = round(time.time() - t0, 2)
        levers = (self.activation or {}).get("levers") or []
        skipped = (self.activation or {}).get("skipped") or {}
        _say(
            f"ready device={self._device.device_kind} cc={self.compute_capability} "
            f"jax={jax.__version__} mode={self.mode} "
            f"levers={'+'.join(levers) or 'none'} "
            f"skipped={','.join(sorted(skipped)) or 'none'} weights_held_by=nobody "
            f"params={self.params_dir} dssp_runnable={self.dssp_runnable} "
            f"optimise_beta={self._optimise_beta()} build_s={self.build_s}"
        )

    def _probe_dssp(self) -> bool:
        """Can BindCraft's DSSP executable run on this machine?

        The kit fetches a prebuilt ``functions/dssp``. It is an x86-64 static ELF,
        so on an aarch64 host the exec fails with ENOEXEC. Asked by running it,
        not by reading a header: the question is whether it executes.
        """
        dssp = os.path.join(self.tree, "stock", "src", "bindcraft", "functions", "dssp")
        if not os.path.isfile(dssp):
            return False
        self._bindcraft.executable(dssp)
        try:
            subprocess.run([dssp, "--version"], capture_output=True, timeout=30)
        except OSError:
            return False
        except subprocess.SubprocessError:
            return True  # it started, which is the question
        return True

    def _optimise_beta(self) -> bool:
        return bool(self.optimise_beta_default and self.dssp_runnable)

    @property
    def compute_capability(self) -> str:
        try:
            return str(self._device.compute_capability)
        except Exception:  # noqa: BLE001 - informational only
            return "?"

    # ------------------------------------------------------------- measuring
    def memory(self) -> dict:
        try:
            stats = self._device.memory_stats() or {}
        except Exception:  # noqa: BLE001 - a missing stat must not fail a design
            return {}
        gib = 1024.0**3
        out = {}
        if stats.get("peak_pool_bytes") is not None:
            out["peak_reserved_gib"] = round(stats["peak_pool_bytes"] / gib, 2)
        if stats.get("peak_bytes_in_use") is not None:
            out["peak_in_use_gib"] = round(stats["peak_bytes_in_use"] / gib, 2)
        if stats.get("bytes_limit") is not None:
            out["bytes_limit_gib"] = round(stats["bytes_limit"] / gib, 2)
        out["peak_bytes_reserved"] = stats.get("peak_bytes_reserved")
        out["memory_source"] = "jax.local_devices()[0].memory_stats()"
        return out

    # --------------------------------------------------------------- request
    def _parse(self, req: dict) -> dict:
        raw = req.get("input")
        doc = raw if isinstance(raw, dict) else None
        if doc is None:
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError(
                    "'input' must be a JSON document: {\"target_pdb\": <PDB text>, "
                    "\"chain\": \"A\", \"binder_len\": <int>, \"hotspot\": \"56\", ...}."
                )
            try:
                doc = json.loads(raw)
            except ValueError as exc:
                raise ValueError(f"'input' is not valid JSON: {exc}") from None
        if not isinstance(doc, dict):
            raise ValueError("'input' must be a JSON object.")
        known = {
            "target_pdb", "chain", "binder_len", "hotspot", "seed", "name",
            "num_recycles_design", *ITERATION_BOUNDS,
        }
        unknown = sorted(set(doc) - known)
        if unknown:
            raise ValueError(
                f"unknown field(s) {unknown}; this provider accepts {sorted(known)}. "
                f"BindCraft's other advanced settings are not exposed: each one would "
                f"change the work or the shapes the VRAM budget was measured at."
            )

        pdb = doc.get("target_pdb")
        if not isinstance(pdb, str) or "ATOM" not in pdb:
            raise ValueError("'target_pdb' must be PDB text with ATOM records.")
        if len(pdb.encode("utf-8", "ignore")) > MAX_PDB_BYTES:
            raise ValueError(f"'target_pdb' exceeds {MAX_PDB_BYTES // (1024 * 1024)} MB.")

        chain = str(doc.get("chain", "A")).strip()
        chains = [c.strip() for c in chain.replace("+", ",").split(",") if c.strip()]
        if not chains or any(len(c) != 1 or not c.isalnum() for c in chains):
            raise ValueError(
                "'chain' is one or more single-character chain ids, e.g. 'A' or 'A,B'."
            )
        if len(chains) > MAX_CHAINS_REQUESTED:
            raise ValueError(f"at most {MAX_CHAINS_REQUESTED} target chains.")
        counts = _target_residues(pdb, chains)
        empty = [c for c, n in counts.items() if n == 0]
        if empty:
            raise ValueError(
                f"chain(s) {','.join(empty)} have no CA atom in 'target_pdb'."
            )

        binder_len = doc.get("binder_len")
        if not isinstance(binder_len, int) or isinstance(binder_len, bool):
            raise ValueError("'binder_len' must be an integer.")
        if not MIN_BINDER <= binder_len <= MAX_BINDER:
            raise ValueError(f"'binder_len' must be between {MIN_BINDER} and {MAX_BINDER}.")
        target_res = int(sum(counts.values()))
        tokens = target_res + binder_len
        if tokens > MAX_TOKENS:
            raise ValueError(
                f"{tokens} tokens ({target_res} target residues + a binder of "
                f"{binder_len}) exceeds this provider's {MAX_TOKENS}, the row its "
                f"VRAM budget was measured at. Peak memory and time both grow with "
                f"the token count, so a larger request needs the budget "
                f"re-measured, not the limit raised."
            )

        hotspot = doc.get("hotspot")
        if hotspot is not None:
            if not isinstance(hotspot, str) or not re.fullmatch(r"[A-Za-z0-9,\-\s]*", hotspot):
                raise ValueError(
                    "'hotspot' is BindCraft's target_hotspot_residues grammar, e.g. "
                    "'56', '31,33,57', 'A31,A33' or 'A1-10'."
                )
            hotspot = hotspot.strip() or None

        seed = doc.get("seed", req.get("seed", 0))
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
            raise ValueError("'seed' must be a non-negative integer.")

        recycles = doc.get("num_recycles_design")
        if recycles is not None:
            if not isinstance(recycles, int) or isinstance(recycles, bool):
                raise ValueError("'num_recycles_design' must be an integer.")
            if not RECYCLE_BOUNDS[0] <= recycles <= RECYCLE_BOUNDS[1]:
                raise ValueError(
                    f"'num_recycles_design' must be between {RECYCLE_BOUNDS[0]} and "
                    f"{RECYCLE_BOUNDS[1]}."
                )

        iters = {}
        for key, (lo, hi) in ITERATION_BOUNDS.items():
            if key not in doc:
                continue
            v = doc[key]
            if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
                raise ValueError(f"'{key}' must be an integer between {lo} and {hi}.")
            iters[key] = v

        name = re.sub(
            r"[^A-Za-z0-9_.-]", "_", str(doc.get("name") or req.get("name") or "design")
        )[:48] or "design"
        return {
            "pdb": pdb, "chain": ",".join(chains), "chains": chains,
            "binder_len": binder_len, "hotspot": hotspot, "seed": seed,
            "recycles": recycles, "iters": iters, "name": name,
            "target_res": target_res, "tokens": tokens,
        }

    def predict(self, req: dict) -> dict:
        t0 = time.time()
        self.requests += 1
        p = self._parse(req)
        out_dir = req.get("out_dir") or tempfile.mkdtemp(prefix=f"{SLUG}-out-")
        os.makedirs(out_dir, exist_ok=True)

        # An output left by an EARLIER request is not this request's output. A
        # re-run into a directory that still holds a design.pdb would otherwise
        # pass the outputs check after failing to produce one -- the false pass
        # that check exists to catch -- and a stale failure census would be read
        # as this trajectory's verdict.
        for stale in (*OUTPUT_FILES, "failure_csv.csv"):
            try:
                os.remove(os.path.join(out_dir, stale))
            except FileNotFoundError:
                pass

        # BindCraft's own directory tree is also an earlier request's: its design
        # step MOVES a trajectory into Trajectory/Clashing or /LowConfidence and
        # refuses (shutil.Error "Destination path ... already exists") when a
        # file of that name is already there -- measured, by re-running into a
        # directory a previous run had used. The worker owns these directories.
        for sub in ("Accepted", "Rejected", "Trajectory", "MPNN"):
            shutil.rmtree(os.path.join(out_dir, sub), ignore_errors=True)

        bindcraft, report = self._bindcraft, self._report
        engine_key = (
            p["target_res"], p["binder_len"], p["recycles"] or self._default_advanced["num_recycles_design"],
            len(p["chains"]),
        )
        first_of_key = engine_key not in self.keys_seen
        if first_of_key:
            self.keys_seen.append(engine_key)
            if len(self.keys_seen) > 1:
                self.config_rebuilds += 1

        work = tempfile.mkdtemp(prefix=f"{TMP_PREFIX}{os.getpid()}-")
        try:
            target_path = os.path.join(work, "target.pdb")
            with open(target_path, "w", encoding="utf-8") as fh:
                fh.write(p["pdb"])

            advanced = dict(self._default_advanced)
            advanced.update(p["iters"])
            if p["recycles"] is not None:
                advanced["num_recycles_design"] = p["recycles"]
            advanced["optimise_beta"] = self._optimise_beta()
            advanced["save_design_animations"] = False
            advanced["save_design_trajectory_plots"] = False
            advanced_path = os.path.join(work, "advanced.json")
            with open(advanced_path, "w", encoding="utf-8") as fh:
                json.dump(advanced, fh)

            t_start = time.perf_counter()
            try:
                prep = bindcraft.prepare(
                    self.tree, params_dir=self.params_dir, out_dir=out_dir,
                    binder_len=p["binder_len"], seed=p["seed"], tag=p["name"],
                    advanced=advanced_path,
                )
            except (bindcraft.Refusal, self._settings.SettingsError) as exc:
                raise ValueError(
                    f"refused by the kit: {getattr(exc, 'kind', 'settings')}: {exc}"
                ) from None
            try:
                run = bindcraft.run_design(
                    prep, target=target_path, chain=p["chain"],
                    binder_len=p["binder_len"], hotspot=p["hotspot"],
                    seed=p["seed"], out_dir=out_dir, t_start=t_start, report=report,
                )
            except bindcraft.Refusal as exc:
                raise ValueError(f"refused by the kit: {exc.kind}: {exc}") from None
        finally:
            shutil.rmtree(work, ignore_errors=True)

        files = [
            os.path.join(out_dir, n)
            for n in OUTPUT_FILES
            if os.path.isfile(os.path.join(out_dir, n))
        ]
        if os.path.join(out_dir, "design.pdb") not in files:
            # `run_design` writes design.pdb after the design returns; reaching
            # here without one means the kit returned without writing it. An
            # exit-0 style reply is not a result, so this is a failure.
            raise RuntimeError(
                "the design step returned but wrote no design.pdb: nothing was "
                "produced. The request is reported failed rather than empty."
            )

        terminate = run.get("terminate") or {}
        verdict = terminate.get("verdict") or ""
        gate = terminate.get("gate")
        final = run.get("final") or {}
        timing = run.get("timing") or {}
        sequences = [s for s in (run.get("seq_best") or []) if isinstance(s, str)]
        body = {
            "model": "BindCraft binder hallucination on ColabDesign 1.1.3 / AlphaFold-Multimer v3",
            "kit_mode": self.mode,
            "levers": list((self.activation or {}).get("levers") or []),
            "weights_held_by": "nobody",
            "msa_source": "none (binder hallucination uses no alignment)",
            "design_name": run.get("tag"),
            "sequences": sequences,
            "files": files,
            "accepted_by_stage_gates": not verdict and not gate,
            "terminate": verdict or None,
            "gate_fired": gate,
            "final": _jsonable({k: final.get(k) for k in (
                "loss", "plddt", "ptm", "i_ptm", "pae", "i_pae", "con", "i_con")}),
            "best_metric": _number(run.get("best_metric")),
            "best_metric_name": run.get("best_metric_name"),
            "n_steps": run.get("n_steps"),
            "phases_run": run.get("phases_run"),
            "tokens": run.get("tokens"),
            "lengths": run.get("lengths"),
            "target_residues": p["target_res"],
            "binder_len": p["binder_len"],
            "chains": p["chains"],
            "hotspot": p["hotspot"],
            "seed": p["seed"],
            "num_recycles_design": advanced["num_recycles_design"],
            "iterations": {k: advanced[k] for k in ITERATION_BOUNDS},
            "optimise_beta": advanced["optimise_beta"],
            "dssp_runnable": self.dssp_runnable,
            "save_design_animations": False,
            "engine_key": list(engine_key),
            "first_of_engine_key": first_of_key,
            "config_rebuilds": self.config_rebuilds,
            "requests_served": self.requests,
            "output_sha256": {
                n: (run.get("files") or {}).get(n, {}).get("sha256") for n in OUTPUT_FILES
            },
            "timing": _jsonable({
                "design_s": timing.get("total_s"),
                "steady_s_per_step": timing.get("steady_s"),
                "first_calls_s": timing.get("first_calls_s"),
                "total_s": round(time.time() - t0, 2),
            }),
        }
        body.update(self.memory())
        # One line per request in the transcript, so that a log shows what each
        # request cost and which engine key it ran, whoever asked.
        _say(
            f"request {self.requests} done tokens={body['tokens']} "
            f"engine_key={body['engine_key']} first_of_engine_key={first_of_key} "
            f"accepted_by_stage_gates={body['accepted_by_stage_gates']} "
            f"design_s={body['timing'].get('design_s')} "
            f"peak_pool_gib={body.get('peak_reserved_gib')} "
            f"peak_in_use_gib={body.get('peak_in_use_gib')}"
        )
        return body


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="ColabDesign resident worker")
    parser.add_argument("--socket", required=True)
    parser.add_argument("--slug", default=SLUG)
    parser.add_argument("--mode", default="off")
    parser.add_argument("--params-dir", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--kit", required=True)
    args = parser.parse_args(argv)

    base = _load_worker_base()
    removed = sweep_stale_temp()
    if removed:
        _say(f"swept {removed} stale temp tree(s) from a worker that did not clean up")
    engine = Engine(args)
    engine.build()

    def ready():
        body = {
            "build_s": engine.build_s,
            "kit_mode": engine.mode,
            "levers": list((engine.activation or {}).get("levers") or []),
            "weights_held_by": "nobody",
            "compute_capability": engine.compute_capability,
            "requests_served": engine.requests,
            "engine_keys_seen": len(engine.keys_seen),
            "config_rebuilds": engine.config_rebuilds,
            "optimise_beta": engine._optimise_beta(),
            "dssp_runnable": engine.dssp_runnable,
            "msa_source": "none",
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
