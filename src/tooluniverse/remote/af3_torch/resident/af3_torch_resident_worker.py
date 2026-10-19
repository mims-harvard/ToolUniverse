"""AF3-torch held resident on the GPU, answering one request at a time.

Run by the model's own interpreter, with the kit's mode variable DELIBERATELY
ABSENT from the environment::

    <model python> af3_torch_resident_worker.py --socket … --slug … --mode fast \\
        --kit <checkout>/af3_torch --params-dir <dir holding of3_ported_weights.bin.zst>

Everything unusual about this worker follows from one sentence in the kit's own
``_autoload.py``:

    On this model the hook applies nothing: the levers are arguments of the
    kit's own ``build_model`` in a model process the wrapper launches (cli.py /
    forward.py), not an in-process patch of an import.

So there is no mode variable to set here, and setting one is fatal rather than
useless: with ``AF3_TORCH_OPT`` non-``off`` the kit's ``.pth`` arms a meta-path
finder on ``xfold`` and ``af3_torch_api`` and calls ``os._exit(3)`` at the first
import of either. This worker imports both. ``launch.py`` strips the variable
and this file refuses to start if one survived.

**Which position this worker occupies.** The kit's prediction is a chain of
three processes -- ``featurise.py`` (the sokrypton/alphafold3 fork, CPU, under
``AF3_TORCH_JAX_PY``) -> ``forward.py`` (the model, GPU, under
``AF3_TORCH_PY``) -> ``postprocess.py`` (the fork's writers, CPU, under
``AF3_TORCH_JAX_PY``). This worker is a different script in the position
``forward.py`` occupies, exactly as Boltz-2's worker is a different script in
the position that kit's batch worker occupies. Nothing in the kit is patched,
copied or shadowed: the kit's own module is imported and its own helpers
(``kit_sys_path``, ``route_kernels``, ``apply_fastnn``, ``warm_core_imports``,
``swap_in_dtk``, ``_np_out``, ``_model_id``) do the work they do there. The two
CPU stages are launched as the kit's own ``cli.py`` launches them, with the
kit's own environment row (``stack.model_process_env(jax=True)``).

**Who holds the weights: this worker.** ``af3_torch_api.build_model`` reads the
converted OpenFold3 parameter records through ``xfold.params`` and the kit
replaces no loader under any mode -- its contribution is the ``levers`` tuple
passed to that same constructor. The ready line and every reply therefore say
``weights_held_by = "worker"``, and would under ``mode = "off"`` too. This is
the opposite of Chai-1, where the kit owns the load path and a worker that
memoised it would silently turn the kit off.

**What is asked of the kit rather than written down.** The mode's lever
composition (``modes.resolve``), the routed kernel names
(``stack.kernel_routes``), the shared core's directory, the kit and DTK trees,
the cache directories and the JAX-side environment row. A hard-coded copy of
any of them drifts the first time the kit moves. Unlike the other providers
this needs no subprocess probe: ``af3_torch_opt`` imports neither torch nor
jax, and this process already runs in the interpreter where it is installed.

**What is fixed for the worker's life.** ``num_recycles``, ``num_samples`` and
``diffusion_steps`` are arguments of the constructor, not of a call, so they
are set once at start and reported on the ready line. A request cannot change
them without rebuilding the model, and a resident worker that rebuilt on
request would give up the thing it exists for; a deployment that needs other
values starts a worker with other values.

**Untested.** No prediction has run through this file. It is written against
the kit's documented entry points and its own source at the pinned commit, and
the first smoke on real hardware should be read as the first execution, not as
a regression check.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="af3_torch", help="provider slug, echoed in ping")
ap.add_argument("--mode", default="fast", help="the kit mode: off | exact | fast | big")
ap.add_argument("--kit", default=None, help="the kit checkout's af3_torch directory")
ap.add_argument(
    "--params-dir",
    default=None,
    help="the directory holding of3_ported_weights.bin.zst (else AF3_TORCH_PARAMS_DIR)",
)
ap.add_argument("--num-recycles", type=int, default=None)
ap.add_argument("--num-samples", type=int, default=None)
ap.add_argument("--diffusion-steps", type=int, default=None)
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
    print(f"[af3_torch-resident] {msg}", flush=True)


def refuse(name: str, message: str) -> "None":
    """A named refusal that carries the fix, and exit 3 as the kit's own do."""
    print(f"[af3_torch-resident] NOT ACTIVE reason={name} {message}", file=sys.stderr)
    sys.stderr.flush()
    raise SystemExit(3)


def _load_worker_base():
    """The shared runtime, by path: this process holds AF3-torch's pinned stack
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
            f"[af3_torch-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

# ----------------------------------------------------------------- the kit
# Before anything else: the kit's hook kills this process at `import xfold` if
# a mode variable is set. launch.py strips them; an operator running this
# script by hand from a shell that exported one gets the reason instead of a
# bare exit 3 from inside site.py.
_LEAKED = sorted(k for k in os.environ if k.startswith("AF3_TORCH_OPT"))
if _LEAKED:
    refuse(
        "mode_variable_present",
        f"{', '.join(_LEAKED)} is set in this process. This kit's autoload hook "
        f"cannot apply a mode in-process and terminates any interpreter that "
        f"imports xfold or af3_torch_api while it is set (af3_torch_opt/"
        f"_autoload.py). The mode reaches this worker as --mode and its levers "
        f"go to build_model; unset the variable and start again.",
    )

if args.kit:
    os.environ.setdefault("MODEL_OPT", args.kit)

try:
    from af3_torch_opt import cli as KCLI
    from af3_torch_opt import modes as KMODES
    from af3_torch_opt import stack as KSTACK
except ImportError as exc:
    refuse(
        "kit_missing",
        f"af3_torch_opt is not importable on {sys.executable} ({exc}); run "
        f"`tu remote setup af3_torch --only kit`",
    )

try:
    RESOLVED = KMODES.resolve(args.mode)
except Exception as exc:  # noqa: BLE001 - the kit's own refusal is the answer
    refuse("mode_refused", f"{args.mode}: {type(exc).__name__}: {exc}")

LEVERS = tuple(RESOLVED["levers"])
PACKAGE_LEVERS = tuple(RESOLVED["package_levers"])
BIG = RESOLVED["big"]
PADDING = RESOLVED["padding"] or "none"

# The two CPU stages. This is the standard's one-interpreter assumption meeting
# a kit that needs two, and there is nowhere in the manifest to declare the
# second, so it is read from the environment and refused by name when absent.
JAX_PY = KSTACK.jax_python()
JAX_REPO = KSTACK.jax_repo()
if not JAX_PY or not Path(JAX_PY).is_file():
    refuse(
        "jax_interpreter_unset",
        "AF3_TORCH_JAX_PY does not name an interpreter. This kit featurises and "
        "writes its mmCIF with the sokrypton/alphafold3 fork in a SECOND, "
        "CPU-only environment; the model half this worker holds cannot produce "
        "an input or an output on its own. Build that environment with the kit's "
        "own recipe (STOCK.md, section Stack: a Python 3.12 venv from "
        "environment/requirements-jax.lock plus the fork at commit bc32b22f "
        "patched with stock/patches/04_of3_empty_template_restype_gap.diff, "
        "built and build_data-ed) and export AF3_TORCH_JAX_PY and "
        "AF3_TORCH_JAX_REPO before `tu remote run af3_torch`.",
    )
if not JAX_REPO or not Path(JAX_REPO).is_dir():
    refuse(
        "jax_repo_unset",
        "AF3_TORCH_JAX_REPO does not name the sokrypton/alphafold3 fork "
        "checkout (it holds run_alphafold.py and convert_of3_weights.py); "
        "export it alongside AF3_TORCH_JAX_PY.",
    )

PARAMS_DIR = Path(
    args.params_dir or os.environ.get("AF3_TORCH_PARAMS_DIR") or "~/.af3_torch"
).expanduser()
CKPT = PARAMS_DIR / "of3_ported_weights.bin.zst"
if not CKPT.is_file():
    refuse(
        "weights_absent",
        f"{CKPT} is not a file. It is the OpenFold3-preview2 checkpoint "
        f"converted into AlphaFold 3's parameter-record layout; it is produced, "
        f"not downloaded. Run `tu remote setup af3_torch --only weights` with "
        f"AF3_TORCH_JAX_PY and AF3_TORCH_JAX_REPO set.",
    )

# The kit's own environment row for a model process: the cache directories and
# the routed kernels' exports, with every AF3_TORCH_OPT* name stripped. Applied
# to this process before torch is imported, because Triton's cache directory
# and the allocator policy are read at import and at first allocation.
for _k, _v in KSTACK.model_process_env().items():
    os.environ[_k] = _v
JAX_ENV = KSTACK.model_process_env(jax=True)

# The kit's own model-process module. Its helpers are used as they are; nothing
# in it is patched or copied.
sys.path.insert(0, str(Path(KCLI.FORWARD).parent))
import forward as KFWD  # noqa: E402  (the kit's forward.py, by its own import route)

for _p in reversed(KFWD.kit_sys_path(KSTACK.kit_home(), KSTACK.dtk_home())):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Triton's autotune-result cache must be switched on before any kernel module
# is imported -- an Autotuner reads the knob when it is declared.
AUTOTUNE = KFWD._autotune_cache_on() if "autotune_cache" in PACKAGE_LEVERS else None

ROUTES = KSTACK.kernel_routes()
KERNEL_ROUTES, ROUTE_ERROR = KFWD.route_kernels(ROUTES, KSTACK.core_dir())
if ROUTE_ERROR:
    refuse("kernel_route_refused", ROUTE_ERROR)

import numpy as np  # noqa: E402
import torch  # noqa: E402

import af3_torch_api as A  # noqa: E402

if not torch.cuda.is_available():
    refuse("no_cuda_device", "torch reports no CUDA device; this provider is GPU-only")

WARM = KFWD.warm_core_imports(KSTACK.core_dir())
say(
    f"imports done t={time.time() - T0:.1f}s torch={torch.__version__} "
    f"device={torch.cuda.get_device_name(0)} mode={args.mode}"
)

if hasattr(A, "set_provider_tier"):
    # The shared core's providers ask for this pred's tier word where a cell
    # row wants one; the kit's forward.py picks it the same way.
    A.set_provider_tier("big" if BIG else "fast")

FASTNN = KFWD.apply_fastnn(1 if RESOLVED["fastnn"] else 0)

_CTOR = {
    k: v
    for k, v in (
        ("num_recycles", args.num_recycles),
        ("num_samples", args.num_samples),
        ("diffusion_steps", args.diffusion_steps),
    )
    if v is not None
}

_t = time.time()
MODEL = A.build_model(str(CKPT), levers=LEVERS, **_CTOR)
BUILD_S = time.time() - _t
LEVERS_APPLIED = tuple(getattr(MODEL, "_af3t_levers", ()) or ())
say(f"model built in {BUILD_S:.1f}s levers={','.join(LEVERS_APPLIED) or 'none'}")

# The mode's package levers, attached by the kit's own installers, in the
# kit's own order. The names come from modes.resolve(); the three scheduling
# levers of the kit's streamed process chain do not apply to a worker that
# serves one request at a time over a socket, and are declined BY NAME rather
# than quietly dropped.
_STREAM_LEVERS = {"prefetch", "write_behind", "feat_par"}
PACKAGE_APPLIED = []
PACKAGE_DECLINED = {}
for _pl in PACKAGE_LEVERS:
    if _pl in _STREAM_LEVERS:
        PACKAGE_DECLINED[_pl] = (
            "resident:one_request_at_a_time -- these levers overlap the kit's "
            "own multi-item process chain, which a socket worker does not run"
        )
        continue
    if _pl == "autotune_cache":
        if AUTOTUNE and AUTOTUNE.get("knob"):
            PACKAGE_APPLIED.append(_pl)
        else:
            PACKAGE_DECLINED[_pl] = (AUTOTUNE or {}).get(
                "reason"
            ) or "triton_knob_absent"
        continue
    try:
        _mod = __import__(f"af3_torch_opt.{_pl}", fromlist=["install"])
        _mod.install(MODEL)
        PACKAGE_APPLIED.append(_pl)
    except Exception as exc:  # noqa: BLE001 - a lever that cannot attach is fatal
        # The kit's own rule: never a silent stock path running under a lever's
        # name. forward.py fails the whole run here and so does this.
        refuse("package_lever_failed", f"{_pl}: {type(exc).__name__}: {exc}")

DTK_STATE = None
if RESOLVED["dtk"]:
    try:
        KFWD.swap_in_dtk(MODEL, torch)
        DTK_STATE = "on"
    except Exception as exc:  # noqa: BLE001 - the kit's own wording
        MODEL._af3t_dtk_dead = f"swap_failed: {type(exc).__name__}: {exc}"
        DTK_STATE = "dead:swap_failed"
        say(f"lever_dead name=dtk reason={MODEL._af3t_dtk_dead!r}")

BUCKETS = KCLI.bucket_row(PADDING)
HOLDER = "worker"


# ------------------------------------------------------------------ requests
def _run_stage(name: str, argv: list, work: Path) -> None:
    """One CPU stage of the kit's chain, under the JAX interpreter."""
    log = work / f"{name}.log"
    with open(log, "wb") as fh:
        out = subprocess.run(
            argv, env=JAX_ENV, stdout=fh, stderr=subprocess.STDOUT, cwd=str(work)
        )
    if out.returncode != 0:
        tail = ""
        try:
            tail = log.read_text(errors="replace")[-2000:]
        except OSError:
            pass
        raise RuntimeError(f"{name} exited {out.returncode}; its words:\n{tail}")


def _seeds_from(report: Path, name: str) -> list:
    data = json.loads(report.read_text())
    for item in data.get("items") or ():
        if item.get("name") == name:
            if not item.get("ok"):
                raise RuntimeError(
                    f"featurise refused {name}: {item.get('error') or 'no reason given'}"
                )
            return list(item.get("seeds") or ())
    raise RuntimeError(f"featurise wrote no report entry for {name}")


def _predict_one(req: dict) -> dict:
    """One prediction: featurise (CPU) -> the held model (GPU) -> write (CPU)."""
    text = req.get("input") or req.get("json") or req.get("fold_input")
    if not text:
        raise ValueError(
            "a request needs 'input': an AlphaFold 3 fold-input JSON "
            "(dialect 'alphafold3', with each chain's MSAs inline)"
        )
    name = str(req.get("name") or "fold")
    root = Path(req["out_dir"])
    work = root / "work"
    out_dir = root / "out" / name
    work.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    fold_json = work / f"{name}.json"
    fold_json.write_text(text if text.endswith("\n") else text + "\n")

    timing = {}

    # 1. featurise -- the fork under the JAX interpreter, CPU only. No data
    #    pipeline: --run_data_pipeline 0, so the fold input must carry its own
    #    MSAs and templates. A resident GPU worker is the wrong place to run
    #    HMMER against genetic databases, and nothing here has them.
    t = time.time()
    feat_report = work / "featurise.json"
    _run_stage(
        "featurise",
        [
            JAX_PY,
            KCLI.FEATURISE,
            "--buckets",
            BUCKETS,
            "--report",
            str(feat_report),
            "--run_data_pipeline",
            "0",
            "--run_inference",
            "1",
            "--item",
            f"{name}={fold_json}={work / name}",
        ],
        work,
    )
    seeds = _seeds_from(feat_report, name)
    timing["featurise_s"] = round(time.time() - t, 2)
    if not seeds:
        raise RuntimeError(f"featurise produced no seed for {name}")

    # 2. forward -- this process, the held model.
    torch.cuda.reset_peak_memory_stats()
    t = time.time()
    per_seed = {}
    for seed in seeds:
        d = work / name / f"seed-{seed}"
        batch = A.batch_from_npz(str(d / "batch.npz"))
        ts = time.time()
        with A.inference():
            result = A.forward(MODEL, batch, seed=int(seed))
        torch.cuda.synchronize()
        arrays = KFWD._np_out(result, np, torch)
        arrays["seed"] = np.asarray(seed)
        arrays["model_id"] = KFWD._model_id(MODEL, np, torch)
        np.savez(str(d / "result.npz"), **arrays)
        del result
        per_seed[str(seed)] = round(time.time() - ts, 2)
    timing["forward_s"] = round(time.time() - t, 2)
    timing["per_seed_s"] = per_seed

    # 3. postprocess -- the fork's own writers under the JAX interpreter.
    t = time.time()
    post_report = work / "postprocess.json"
    _run_stage(
        "postprocess",
        [
            JAX_PY,
            KCLI.POSTPROCESS,
            "--repo_dir",
            JAX_REPO,
            "--report",
            str(post_report),
            "--opt_core",
            KSTACK.core_dir(),
            "--item",
            f"{name}={work / name}={out_dir}",
        ],
        work,
    )
    timing["postprocess_s"] = round(time.time() - t, 2)

    files = sorted(str(p) for p in out_dir.rglob("*") if p.is_file())
    body = {
        "out_dir": str(out_dir),
        "files": files,
        "structures": [f for f in files if f.endswith(".cif")],
        "seeds": [int(s) for s in seeds],
        "timing": timing,
        "weights_held_by": HOLDER,
        "kit_mode": args.mode,
        "levers": list(LEVERS_APPLIED),
        "package_levers": list(PACKAGE_APPLIED),
        "peak_reserved_gib": round(torch.cuda.max_memory_reserved() / 2**30, 2),
    }
    ranking = out_dir / f"{name}_ranking_scores.csv"
    if ranking.is_file():
        body["ranking_scores_csv"] = ranking.read_text()[:64_000]
    summary = out_dir / f"{name}_summary_confidences.json"
    if summary.is_file():
        try:
            body["summary_confidences"] = json.loads(summary.read_text())
        except ValueError:
            pass
    return body


def _on_reset() -> None:
    torch.cuda.reset_peak_memory_stats()


def _ready() -> dict:
    return {
        "build_s": round(BUILD_S, 1),
        "device": torch.cuda.get_device_name(0),
        "weights_held_by": HOLDER,
        "kit_mode": args.mode,
        "levers": list(LEVERS_APPLIED),
        "levers_requested": list(LEVERS),
        "package_levers": list(PACKAGE_APPLIED),
        "package_levers_declined": PACKAGE_DECLINED,
        "dtk": DTK_STATE,
        "padding": PADDING,
        "buckets": BUCKETS,
        "fastnn": FASTNN,
        "kernel_routes": {k: bool(v.get("ok")) for k, v in KERNEL_ROUTES.items()},
        "warm_imports": WARM,
        "checkpoint": str(CKPT),
        "constructor": _CTOR or "the kit's build_model defaults",
        "jax_python": JAX_PY,
        "jax_repo": JAX_REPO,
        "status": "untested: no prediction has ever run through this provider",
    }


if __name__ == "__main__":
    raise SystemExit(
        WB.serve(
            slug=args.slug,
            socket_path=args.socket,
            on_predict=_predict_one,
            ready=_ready,
            on_reset=_on_reset,
            log=say,
        )
    )
