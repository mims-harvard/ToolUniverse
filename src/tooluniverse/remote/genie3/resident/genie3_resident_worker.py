"""Genie 3 held resident on the GPU, answering one design request at a time.

Run by the model's own interpreter with the kit's mode variable in the
environment AND its autoload hook disarmed::

    GENIE3_OPT=exact GENIE3_OPT_AUTOLOAD=0 \
        <model python> genie3_resident_worker.py --socket … --slug …

**Why the second variable is not optional, and why it loses nothing.**

This kit activates through a ``.pth`` -- the common form, 30 of the 36 -- but
what its hook does is not what the other twenty-nine do. It does not patch
upstream in place. Under a kit mode its meta-path finder waits for the first
``import genie3`` and then:

* if the process is upstream's console script at ``genie3 generate …``, it
  ``os.execv``s itself into ``python -m genie3_opt design --mode <m> …``;
* **otherwise it prints ``NOT ACTIVE: env-route`` and ends the process with
  exit 3** (``opt/genie3_opt/_autoload.py``), naming ``GENIE3_OPT_AUTOLOAD=0``
  as the route for "a tool that imports genie3 on purpose".

A resident worker is exactly such a tool, so with the mode variable set and the
hook armed this file would die at its first import. Measured, in this
provider's own interpreter::

    $ GENIE3_OPT=exact python -c 'import genie3'
    [genie3-opt] NOT ACTIVE: env-route: GENIE3_OPT='exact' is set at `python -c …`
    … refused (exit 3), nothing of upstream ran: … or GENIE3_OPT_AUTOLOAD=0 to
    leave a tool that imports genie3 untouched                       # rc 3

Disarming it costs nothing because **the hook is not where this kit's levers
live.** For ``exact`` and ``fast`` the mode table's ``attach`` is ``"driver"``
(``opt/genie3_opt/modes.py``): the mode IS a script,
``opt/genie3_opt/g3batch.py``, which imports the kit's three carried library
modules and applies every lever itself. The autoload is only a CLI shim that
re-execs into the verb that launches that script. So this worker takes the
script's position -- the same shape as boltz2's ``worker_launch``, reached
through a different door -- and the kit's levers are applied by calling the
kit's own functions, nothing patched, copied or shadowed.

**What this worker holds, and what it rebuilds.**

``g3fast.build_everything(request, device, seed, …)`` is one call that does all
of: read the request, construct the network (which consumes the global numpy
RNG through scipy truncnorm inits), read the 331 MiB checkpoint, build the
diffusion sampler and build the data module. It is per-request by construction,
because the sampler's ``eta`` / ``n_sample_step`` / ``direction_scale`` and the
whole dataset come out of the request.

So the engine is held keyed on the request itself -- the request bytes, the
seed and the shard -- and a request that changes any of them rebuilds, once,
visibly, on the ready line and in every reply (``engine_rebuilt``).

**The RNG order is the part a held engine has to get right.** The kit copies
the stock CLI's order of RNG-relevant events and says so in g3fast.py's own
comment: ``seed_everything(seed)`` -> network construction (numpy draws) ->
checkpoint load -> per-design featurisation, whose binder-length draw is
``np.random.randint``. A held engine SKIPS the network construction on the
second request of a key, so its numpy stream would start in the wrong place and
the designs would not be stock's. This worker therefore snapshots the four
generator states (python ``random``, numpy, torch CPU, the torch CUDA default
generator) at the instant ``build_everything`` returns and restores them before
every later request of the same key, which is precisely the state a fresh
process has when featurisation begins. ``rng_restored`` says which path a reply
came from.

That is a reasoned reconstruction and not yet a measurement, and the test for
it is the one STANDARD.md already demands: four consecutive IDENTICAL requests.
Under ``exact`` their PDB files must be byte-identical to each other -- which
is a stronger acceptance check than "it answered four times", and it is the
check to run before this provider claims ``verified``.

**What residency buys.** The kit's README puts process start-up and model
set-up at 10-15 s "in every mode", against sampling time that scales with
designs x steps. A held engine pays that once per key rather than once per
request, and the kit's CUDA-graph capture (0.7-2.6 s per batch shape) once per
request rather than once per process. Graphs are NOT kept across requests by
default: the kit's own ``--reuse-graphs`` documentation says "nothing is cached
ACROSS requests -- the cache lives inside one process / request only", and
openfold3 is on record failing deterministically on the second request of a
shape because a kept graph outlived the state it was captured against. Set
``GENIE3_RESIDENT_KEEP_GRAPHS=1`` to keep them and measure; the reply's
``graph_cache`` counters are what shows whether it paid.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import os
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="genie3", help="provider slug, echoed in ping")
args = ap.parse_args()

T0 = time.time()
TAG = "genie3-resident"


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
    print(f"[{TAG}] {msg}", flush=True)


class Refused(SystemExit):
    """A named refusal, at the kits' own exit code.

    STANDARD.md section 8 fixes the vocabulary -- 0 ok, 1 failed, 2 usage, 3
    refused -- and every refusal in this file is of the third kind: a fact
    about this deployment that is named and has a fix, not a fault. A bare
    ``SystemExit("message")`` exits 1, which is what the four resident workers
    written before this one do; a caller that branches on the code cannot then
    tell a refusal from a crash.
    """

    def __init__(self, message: str):
        sys.stderr.write(message.rstrip("\n") + "\n")
        sys.stderr.flush()
        super().__init__(3)


def refuse(reason: str) -> "Refused":
    return Refused(f"[{TAG}] NOT ACTIVE: {reason}")


def _load_worker_base():
    """The shared runtime, by path: this process holds Genie 3's pinned stack
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
            f"[{TAG}] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

if (os.environ.get("GENIE3_OPT_AUTOLOAD") or "").strip() != "0":
    # Refused here rather than discovered three frames into the first import,
    # where it arrives as a bare exit 3 with no mention of this worker.
    raise refuse(
        f"GENIE3_OPT_AUTOLOAD is not '0'. Under a kit mode "
        f"this kit's .pth hook ends any process that imports genie3 for any "
        f"reason other than upstream's `genie3 generate` console script "
        f"(opt/genie3_opt/_autoload.py), and a resident worker is such a "
        f'process. Declare it: [kit.env] GENIE3_OPT_AUTOLOAD = "0".'
    )

# --------------------------------------------------------------------- the mode
# Read out of the kit, never derived from the slug: the variable's name is
# _autoload.ENV_MODE / stack.ENV_MODE and kit_launch's probe sets it.
from genie3_opt import modes as KM  # noqa: E402
from genie3_opt import stack as KS  # noqa: E402

MODE = (os.environ.get("GENIE3_OPT") or "").strip().lower()
if not MODE:
    raise refuse(
        f"GENIE3_OPT is unset, so no mode is named. This "
        f"worker applies the kit's levers itself and will not run upstream "
        f"unpatched while calling it a mode: set GENIE3_OPT to one of "
        f"{'|'.join(KM.MODE_NAMES)}."
    )
try:
    RES0 = KM.resolve(MODE)
except KM.ModeError as exc:
    raise refuse(f"{exc}") from exc
if RES0.attach != "driver":
    raise refuse(
        f"mode {MODE!r} attaches as {RES0.attach!r}, not "
        f"'driver'. The kit's stock route (`--mode off`) is upstream's console "
        f"script in a clean subprocess that proves its own environment "
        f"(opt/genie3_opt/stock_cli.py); it is not a thing this process can be, "
        f"and pretending would report the kit's patches as stock. A deployment "
        f"that wants stock runs the kit's own `run.sh design --mode off`."
    )


def _flag_table(res) -> dict:
    """The mode's driver flags as a mapping -- read from the kit's own table.

    Every switch this worker knows how to honour is listed here with how to
    read its value. A flag the kit's table grows that is NOT listed refuses the
    start, because the alternative is a worker that silently runs an ablation
    of the mode and reports the mode's name. (That is the failure boltzgen's
    ``levers_off`` taught: a setting that does not reach the kit is worse than
    saying so.)
    """
    takes_value = {
        "--batch-size": int,
        "--reuse-graphs": int,
        "--pt-chunk": str,
        "--alloc": str,
        "--trimul": str,
    }
    bare = (
        "--cuda-graphs",
        "--hoist",
        "--lean-pair",
        "--wide-capture",
        "--tf32",
        "--compile",
    )
    out: dict = {}
    rest = list(res.flags)
    while rest:
        flag = rest.pop(0)
        if flag in takes_value:
            if not rest:
                raise refuse(f"the kit's line ends with {flag}, which takes a value")
            out[flag] = takes_value[flag](rest.pop(0))
        elif flag in bare:
            out[flag] = True
        else:
            raise refuse(
                f"the kit's mode table passes {flag!r} on "
                f"the {MODE} line and this worker does not know how to honour "
                f"it. The worker takes the position of "
                f"opt/genie3_opt/g3batch.py and must apply every switch that "
                f"script applies; a mode is all of its levers. Add it here "
                f"(and in _request) or run the kit's own `run.sh design`."
            )
    return out


FLAGS = _flag_table(RES0)

if FLAGS.get("--alloc") == "expandable":
    # L19, and set HERE -- before this process imports torch at all -- because
    # the caching allocator reads it at CUDA initialisation and the mode
    # preflight below asks torch for the card's compute capability, which
    # initialises CUDA. The kit's own driver sets the same string after
    # importing torch and refuses if CUDA is already up; doing it first makes
    # that refusal unreachable instead of ordering-dependent.
    _conf = os.environ.get("PYTORCH_CUDA_ALLOC_CONF", "")
    if "expandable_segments" not in _conf:
        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = (
            _conf + "," if _conf else ""
        ) + "expandable_segments:True"


def _triton_minor() -> tuple:
    try:
        from importlib.metadata import version

        return tuple(int(p) for p in version("triton").split(".")[:2])
    except Exception:  # noqa: BLE001 - absent or unparseable is "unknown"
        return ()


def _mode_preflight() -> None:
    """Refuse a mode whose kernels cannot run on this card -- before the pass.

    The kit's own policy is to name a hardware uncertainty and proceed, and to
    refuse only AFTER the pass when a planned lever left no evidence
    (``stack.lever_notes``, ``design.run`` -> ``levers_missing``, exit 3). Two
    of this card's facts turn that into a wasted pass or a dead process, and
    both were measured in this interpreter rather than read:

    * ``--trimul fpf`` (L7, mode fast) is served only from a row of
      ``opt/genie3_opt/fpf_cells.json``, and that file has rows for compute
      capability 9.0 and 8.0 only. On a card without a row every call is a
      counted ``no_cell:`` fallback, which is not in L7's
      ``EXPECTED_FALLBACKS``, so the lever's gate refuses and mode fast refuses
      by name after the whole pass has run.
    * ``--compile`` (L16) hands the denoiser core to inductor, which emits
      Triton. On triton 3.3.x this card cannot lower a cross-lane reduction at
      all: ``LLVM ERROR: Cannot select: intrinsic
      %llvm.nvvm.shfl.sync.bfly.i32`` -- an ``abort()`` no worker can catch.
      Measured here with ``torch.compile`` on a bare ``nn.LayerNorm``: rc 134.
      The carried kernel is in the same position (``tl.sum`` in
      ``opt_core/kernels/fpf_trimul_v4/kernels.py:46``).
    """
    cc = KS.gpu_probe().get("cc")
    if cc is None:
        # nvidia-smi reports memory.total as [N/A] on unified memory, which
        # makes the kit's whole probe return None fields (it parses the three
        # queried columns together and swallows the ValueError). Read the
        # capability from torch instead -- which is also what the pass itself
        # will use.
        major, minor = torch.cuda.get_device_capability(0)
        cc = f"{major}.{minor}"
    if FLAGS.get("--trimul") == "fpf":
        from genie3_opt import trimul as KT

        if KT.cell_row(cc) is None:
            raise refuse(
                f"mode {MODE} plans lever L7 (--trimul fpf) "
                f"and opt/genie3_opt/fpf_cells.json has no row for compute "
                f"capability {cc} (it has 9.0 and 8.0). Every call would be a "
                f"counted no_cell fallback, which L7 does not expect, so the "
                f"lever's gate refuses and the kit refuses the mode by name "
                f"after the pass has run. Refused before it, which costs "
                f'nothing and saves the pass. Use GENIE3_OPT="exact".'
            )
    if FLAGS.get("--compile") and _triton_minor() < (3, 4):
        raise refuse(
            f"mode {MODE} plans lever L16 (--compile) and "
            f"triton {'.'.join(str(p) for p in _triton_minor()) or '?'} cannot "
            f"lower a cross-lane reduction for compute capability {cc}: "
            f"inductor's generated LayerNorm kernel aborts the process with "
            f"'LLVM ERROR: Cannot select: intrinsic "
            f"%llvm.nvvm.shfl.sync.bfly.i32' (measured, rc 134). An abort is "
            f'not catchable, so it would take the worker down. Use GENIE3_OPT="exact".'
        )


# ---------------------------------------------------------------- the process
import torch  # noqa: E402

_mode_preflight()

from genie3_opt import design as KD  # noqa: E402  compose_request / write_request / request_record
from genie3_opt import det as KDET  # noqa: E402  the deterministic recipe's levels
from genie3_opt import g3batch as GB  # noqa: E402  the kit's driver, as a library
from genie3_opt import jitdirs as KJ  # noqa: E402
from genie3_opt import kernels as KK  # noqa: E402
from genie3_opt import outputs as KO  # noqa: E402  what the pass actually wrote
from genie3_opt import sampling as SMP  # noqa: E402
from genie3_opt import trimul as KT  # noqa: E402
from opt_core.precision import policy as P  # noqa: E402

_hits = P.tf32_override_env()
if _hits:
    # The kit's own gate: a TF32 library override in the environment moves every
    # line off its mode's numerics, and cuBLAS reads it rather than torch.
    raise refuse(P.tf32_override_refusal(_hits))

GENIE3_ROOT = KS.genie3_root()
if not GENIE3_ROOT or not os.path.isdir(GENIE3_ROOT):
    raise refuse(
        f"no Genie 3 checkout. The kit resolves it from "
        f"GENIE3_ROOT, else pip's recorded editable location; neither names a "
        f"directory. Run `tu remote setup genie3`."
    )
# cwd = $GENIE3_ROOT: the cwd of every kit line, and what the relative paths
# inside a request (paths.dataset, paths.rootdir) resolve against.
os.chdir(GENIE3_ROOT)

_KITDRV, _CAPDIR = GB.kit_dirs()  # refuses by name when a carried driver is absent
sys.path.insert(0, _KITDRV)
import g3fast as G  # noqa: E402
import g3fast_patches  # noqa: E402

sys.path.insert(0, _CAPDIR)
import g3cap as C  # noqa: E402
import g3lean as L  # noqa: E402

import logging  # noqa: E402

logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s"
)

# --------------------------------------------------- upstream's one-shot config
# UPSTREAM CAN BUILD EXACTLY ONE SAMPLING CONFIG PER PROCESS, and this is the
# single thing that makes a resident worker for this model different from one
# for any of the fourteen providers before it.
#
# `genie3.generation.config.default.default_config` is a MODULE-LEVEL mutable
# `ml_collections.ConfigDict`, and `registry.get_config()` -- which
# `build_sample_config_from_dict` calls, which `build_everything` calls -- walks
# all over it:
#
#     default_config.update({"common": common_config, "data": ..., ...})
#     default_config.update(config)
#
# `common_config` holds module-level `FieldReference` objects (common.py:
# `batch_size = mlc.FieldReference(1, field_type=int)` and eleven more), so
# after the first call `default_config.common.batch_size` IS that shared
# FieldReference. The second call's `update({"common": common_config})` then
# tries to update a FieldReference with a FieldReference, and ml_collections
# refuses:
#
#     TypeError: Cannot update a FieldReference from another FieldReference:
#     'batch_size'
#
# Measured: the first `build_sample_config_from_dict` of a process succeeds and
# EVERY later one raises, for the identical document. It has nothing to do with
# the request -- not its length, not its batch size, not its seed. The kit never
# meets it because the kit runs one process per request, which its own det.py
# states as point (4) of the byte-identity contract ("one process per request:
# every design of the request is sampled in that process"). A held engine meets
# it on the first REBUILD.
#
# So before every build this worker restores upstream's own interpreter-start
# state from a deep copy taken before the first one. That is a state reset, not
# a patch: nothing of upstream or of the kit is modified, and what each build
# sees is exactly what the first build in a fresh process sees -- which is the
# fidelity property the whole provider rests on. The kits do this sort of thing
# for themselves and name it (opt_core/capture/graphs.py's
# `reset_generator_capture_state`); nobody names this one.
import copy as _copy  # noqa: E402

import genie3.generation.config as _UP_CFG_PKG  # noqa: E402
import genie3.generation.config.default as _UP_DEFAULT  # noqa: E402
import genie3.generation.config.registry as _UP_REGISTRY  # noqa: E402

if hasattr(_UP_DEFAULT.default_config, "common"):
    # The snapshot would already be polluted, which can only mean something
    # built a config before this line ran. Refused rather than snapshotted,
    # because a polluted "pristine" copy is worse than no copy at all.
    raise refuse(
        "genie3.generation.config.default.default_config already carries a "
        "`common` section at worker start-up, so a sampling config has already "
        "been built in this process and the pristine snapshot this worker needs "
        "cannot be taken. Nothing may build a config before this point."
    )
_PRISTINE_DEFAULT_CONFIG = _copy.deepcopy(_UP_DEFAULT.default_config)


def _reset_upstream_config() -> None:
    """Rebind upstream's module-level default config to a fresh deep copy.

    All three modules that hold the name are rebound: the object is reached as
    `registry.default_config` (a `from ... import`, so a name in registry's own
    namespace), as `default.default_config`, and as
    `genie3.generation.config.default_config`, which the package re-exports.
    """
    fresh = _copy.deepcopy(_PRISTINE_DEFAULT_CONFIG)
    _UP_DEFAULT.default_config = fresh
    _UP_REGISTRY.default_config = fresh
    _UP_CFG_PKG.default_config = fresh


DEVICE = torch.device("cuda:0")
if not torch.cuda.is_available():
    raise refuse("no CUDA device visible to torch")
torch.cuda.set_device(DEVICE)

# The line's numerics policy, through the shared core (the one home of the
# switches): the fp32 line PROVES upstream's policy is live and sets nothing;
# --tf32 applies the preset. The READBACK, not the flag, is the fact.
if FLAGS.get("--tf32"):
    PRECISION = P.apply(GB.POLICY_TF32, torch)
else:
    PRECISION = P.expect(GB.POLICY_FP32, torch)
READBACK = P.live(torch)
if bool(READBACK["matmul_tf32"]) is not bool(FLAGS.get("--tf32")):
    raise refuse(
        f"numerics readback matmul_tf32={READBACK['matmul_tf32']} "
        f"matmul={READBACK['matmul']} contradicts the {MODE} line "
        f"(--tf32={bool(FLAGS.get('--tf32'))}); nothing runs"
    )

# L2: the five value-identical forward patches. Class-level, so once per
# process; the kit's own marker check is what says they took.
g3fast_patches.apply(verbose=False)
MARKERS = KS.kit_levers_applied()
if len(MARKERS) != 2:
    raise refuse(
        f"the kit's forward patches left {len(MARKERS)} of "
        f"2 markers ({MARKERS}); mode {MODE} plans L2 and a mode is all of its "
        f"levers"
    )
if FLAGS.get("--hoist"):
    C.install_hoist()  # L8, idempotent by its own guard
LEAN = None
if FLAGS.get("--lean-pair"):  # L17
    LEAN = {
        "lt_release": L.install_lt_release(),
        # The fused-kernel provider replaces the forward outright, so there is
        # nothing to lean on a `fast` line.
        "trimul_lean": L.install_trimul_lean()
        if FLAGS.get("--trimul", "stock") == "stock"
        else 0,
    }
if FLAGS.get("--wide-capture") and not (
    FLAGS.get("--cuda-graphs") and FLAGS.get("--hoist") and FLAGS.get("--lean-pair")
):
    raise refuse("--wide-capture needs --cuda-graphs --hoist --lean-pair")
if FLAGS.get("--reuse-graphs") and not FLAGS.get("--cuda-graphs"):
    raise refuse("--reuse-graphs needs --cuda-graphs (a graph cache of no graphs)")
if FLAGS.get("--trimul") == "fpf":
    # L7 patches the class BEFORE any capture, so the graphs record the
    # kernel's launches. Unreachable on this card -- _mode_preflight refused it
    # -- and kept because the switch is the kit's, not this card's.
    KT.enable()

KEEP_GRAPHS = (os.environ.get("GENIE3_RESIDENT_KEEP_GRAPHS") or "0").strip() == "1"
# The one deviation from the kit's own determinism contract, and the one knob
# that undoes it. det.py point (4) is "one process per request: every design of
# the request is sampled in that process", and the kit's byte-identity claim is
# scoped to that. A held engine serves a second request in the same process, so
# this worker reconstructs the state a fresh process would be in (see the
# module docstring) rather than inheriting it. Set GENIE3_RESIDENT_HOLD=0 to
# rebuild the engine for every request, which is the kit's contract exactly and
# gives up only the checkpoint read and the network construction -- residency
# still keeps the imports, the CUDA context and the compile caches.
HOLD_ENGINE = (os.environ.get("GENIE3_RESIDENT_HOLD") or "1").strip() != "0"
WEIGHTS_DIR = KS.weights_dir()
say(
    f"imports done t={time.time() - T0:.1f}s torch={torch.__version__} "
    f"triton={'.'.join(str(p) for p in _triton_minor()) or '?'} mode={MODE} "
    f"flags={' '.join(RES0.flags)}"
)

# --------------------------------------------------------------- held engine
_ENGINE: dict = {
    "key": None,
    "parts": None,
    "rng": None,
    "setup_s": None,
    "builds": 0,
    "graphs": None,
    "probe_seen": None,
    "svec": None,
}


def _rng_snapshot() -> dict:
    import random

    import numpy as np

    return {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch_cpu": torch.get_rng_state(),
        "torch_cuda": torch.cuda.default_generators[DEVICE.index or 0].get_state(),
    }


def _rng_restore(snap: dict) -> None:
    import random

    import numpy as np

    random.setstate(snap["python"])
    np.random.set_state(snap["numpy"])
    torch.set_rng_state(snap["torch_cpu"])
    torch.cuda.default_generators[DEVICE.index or 0].set_state(snap["torch_cuda"])


def _engine_key(composed: dict, shard_id: int, num_shards: int) -> str:
    """A digest of everything in the COMPOSED request that decides what the
    engine is, with the two keys that only decide where files land removed:
    ``paths.rootdir`` (this pass's output directory) and ``experiment.name``
    (which compose_request defaults to that directory's basename). Nothing else
    is excluded, so a different checkpoint, sampler, dataset, seed or shard is
    a different engine and rebuilds."""
    import copy

    import yaml

    doc = copy.deepcopy(composed)
    if isinstance(doc.get("paths"), dict):
        doc["paths"].pop("rootdir", None)
    if isinstance(doc.get("experiment"), dict):
        doc["experiment"].pop("name", None)
    h = hashlib.sha256()
    h.update(yaml.safe_dump(doc, sort_keys=True).encode("utf-8"))
    h.update(f"\x00{shard_id}\x00{num_shards}".encode("utf-8"))
    return h.hexdigest()[:32]


def _engine_for(key: str, request_path: str, shard_id: int, num_shards: int):
    """The held engine for ``key``, rebuilt only when the key changes.

    One at a time: two networks on one card would hold two copies of the
    weights, and the supervisor serialises requests, so nobody is waiting on
    the one being dropped.
    """
    if HOLD_ENGINE and _ENGINE["parts"] is not None and _ENGINE["key"] == key:
        _rng_restore(_ENGINE["rng"])
        return _ENGINE["parts"], False
    if _ENGINE["parts"] is not None:
        say(f"rebuilding: the request's key {key} is not the held {_ENGINE['key']}")
        _drop_graphs()
        _ENGINE["parts"] = None
        _ENGINE["rng"] = None
        # Dropping the reference is not enough to give the card back: the
        # network stays reachable until the collector runs and the caching
        # allocator keeps its blocks until told to release them.
        gc.collect()
        torch.cuda.empty_cache()
    t = time.time()
    # Upstream can build one sampling config per process; this gives it the
    # state a fresh process would have. See _reset_upstream_config above.
    _reset_upstream_config()
    # The kit's own set-up, unchanged and whole: seed_everything in the stock
    # order, the network, the checkpoint, the sampler, the data module.
    # outdir=None on purpose -- the request keeps its own `paths.rootdir` and
    # this worker hands each request's real directory to the kit's writer, so
    # the engine key does not have to carry a path that changes every call.
    # seed_override is None on purpose: the seed travels in the composed
    # request copy's `experiment.seed`, which is where the kit puts it
    # ("the deterministic recipe adds no driver flag", stack.driver_command).
    parts = G.build_everything(
        request_path,
        DEVICE,
        None,
        None,
        shard_id=int(shard_id),
        num_shards=int(num_shards),
    )
    exp, config, model, diffusion, sampler, dm, setup_s, seed_used = parts
    beyond = [k for k in ("predict_sidechain",) if getattr(sampler, k, False)]
    if (
        getattr(sampler, "_beam_search", None) is not None
        or getattr(getattr(config, "inference", None), "search", None) is not None
    ):
        beyond.append("inference.search")
    if beyond:
        raise ValueError(
            f"the request sets {', '.join(beyond)} -- outside the kit's batched "
            f"capture line, which refuses it by name rather than running it in "
            f"part. Upstream's stock route (`run.sh design --mode off`) runs it."
        )
    tab = G.StepTables(sampler, DEVICE)
    torch.cuda.synchronize()
    _ENGINE.update(
        {
            "key": key,
            "parts": (exp, config, model, diffusion, sampler, dm, tab, seed_used),
            # Snapshotted HERE: the state a fresh `genie3 generate` process has
            # at the instant featurisation begins.
            "rng": _rng_snapshot(),
            "setup_s": round(setup_s, 3),
            "builds": _ENGINE["builds"] + 1,
            "graphs": None,
            "probe_seen": {},
            "svec": {},
        }
    )
    say(
        f"engine built in {time.time() - t:.1f}s (model_setup_s={_ENGINE['setup_s']}) "
        f"key={key} seed={seed_used} n_designs={len(dm.dataset)}"
    )
    return _ENGINE["parts"], True


def _graph_cache():
    """The kit's graph cache (L9). Per request by default; see the module
    docstring for why, and for the one variable that keeps it."""
    if not FLAGS.get("--cuda-graphs"):
        return None
    if _ENGINE["graphs"] is None or not KEEP_GRAPHS:
        _ENGINE["graphs"] = C.GraphCache(int(FLAGS.get("--reuse-graphs", 0)))
    return _ENGINE["graphs"]


def _drop_graphs() -> None:
    cache = _ENGINE.get("graphs")
    if cache is not None:
        cache.clear()
    _ENGINE["graphs"] = None


# -------------------------------------------------------------- one request
def _design(req: dict) -> dict:
    """One design request: one experiment YAML, N designs, one directory."""
    text = req.get("input") or req.get("request")
    if not text:
        raise ValueError(
            "a request needs 'input': the text of upstream's own experiment "
            "YAML (examples/unconditional/experiment.yaml is the smallest one)"
        )
    if isinstance(text, (dict, list)):
        import yaml

        text = yaml.safe_dump(text, sort_keys=False)
    opts = dict(req.get("options") or {})
    known = {
        "batch_size",
        "limit",
        "shard_id",
        "num_shards",
        "n_sample",
        "selections",
        "det",
    }
    unknown = sorted(set(opts) - known)
    if unknown:
        raise ValueError(
            f"unknown option(s) {unknown}; this provider takes {sorted(known)} "
            f"-- the kit's own `design` flags (--batch_size, --n, "
            f"--selections, --det, --limit) plus upstream's dataset shards. "
            f"Everything else about a pass is a key of the request YAML, which "
            f"is upstream's own file."
        )
    shard_id = int(opts.get("shard_id", 0))
    num_shards = int(opts.get("num_shards", 1))
    if not (num_shards >= 1 and 0 <= shard_id < num_shards):
        raise ValueError(
            f"shard_id {shard_id} num_shards {num_shards}: the shard index is 0 <= K < M"
        )
    limit = opts.get("limit")
    limit = None if limit is None else int(limit)
    det_level = int(opts.get("det", KDET.DEFAULT_LEVEL))
    if det_level not in KDET.LEVELS:
        raise ValueError(f"det {det_level}: the kit's levels are {list(KDET.LEVELS)}")

    import yaml

    raw = yaml.safe_load(text)
    if not isinstance(raw, dict) or "generation" not in raw:
        raise ValueError(
            "the request is upstream's experiment YAML -- a mapping with a "
            "`generation` section (examples/unconditional/experiment.yaml)"
        )
    # B is `batch_size` in the options, else the request's own
    # generation.dataset.batch_size, else the mode table's -- the kit's own
    # precedence (modes.with_batch), and the kit changes no workload key.
    batch = opts.get("batch_size")
    batch = None if batch is None else int(batch)
    res = KM.effective(MODE, batch if batch is not None else KM.request_batch(raw))
    B = int(KM.batch_size(res))
    if B < 1:
        raise ValueError("batch_size is an integer >= 1")

    name = str(req.get("name") or "design")
    item = Path(req["out_dir"]) / name
    item.mkdir(parents=True, exist_ok=True)
    stamp = f"{int(time.time() * 1000):013d}"
    out_dir = item / f"designs-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=False)

    seed = req.get("seed")
    seed = None if seed is None else int(seed)
    n_sample = opts.get("n_sample")
    # The kit's OWN request composition, not this worker's: paths.rootdir, the
    # seed under the deterministic recipe's rule, the two weight files from
    # GENIE3_WEIGHTS (a request that names its own keeps them), n_sample,
    # selections and the batch size. The caller's file is never edited; this is
    # the package's copy, written where the kit writes it.
    composed_req, composed = KD.compose_request(
        raw,
        os.fspath(out_dir),
        WEIGHTS_DIR,
        seed=seed,
        n_sample=None if n_sample is None else int(n_sample),
        selections=opts.get("selections"),
        det_level=det_level,
        batch=batch,
    )
    request_path = Path(KD.write_request(composed_req, os.fspath(out_dir)))
    problems = KD.request_problems(composed_req, GENIE3_ROOT)
    record = KD.request_record(
        composed_req,
        composed,
        problems,
        os.fspath(request_path),
        shard_id=shard_id if num_shards > 1 else None,
        num_shards=num_shards if num_shards > 1 else None,
    )

    key = _engine_key(composed_req, shard_id, num_shards)
    builds_before = _ENGINE["builds"]
    parts, built = _engine_for(key, os.fspath(request_path), shard_id, num_shards)
    exp, config, model, diffusion, sampler, dm, tab, seed_used = parts
    predict_sequence = bool(getattr(sampler, "predict_sequence", False))

    cache = _graph_cache()
    svec_by_b = _ENGINE["svec"]
    probe_seen = _ENGINE["probe_seen"]
    gen = torch.cuda.default_generators[DEVICE.index or 0]
    n_designs = GB.n_designs_of(dm, limit)
    n_batches = -(-n_designs // B)
    per_batch: list = []
    capacity: list = []
    lines: list = []
    ev = {
        "graph_captures": 0,
        "graph_reuses": 0,
        "graph_evictions": 0,
        "hoist_fills": 0,
        "hoist_anomalies": 0,
    }
    t_all = time.time()
    since = t_all
    featurize_s = 0.0
    write_s = 0.0

    with torch.inference_mode():
        state0 = G.global_numerics_state()
        feed = GB.featurize_batches(dm, DEVICE, B, limit)
        for bi in range(n_batches):
            t_f = time.time()
            names, bd, raw_cpu = next(feed)
            featurize_s += time.time() - t_f
            b = int(bd["gt_atom_positions"].shape[0])
            n_tok = int(bd["token_mask"].shape[1])
            if FLAGS.get("--pt-chunk") == "design":  # L12
                GB.chunk_pair_transition_per_design(model, n_tok)
            if b not in svec_by_b:
                svec_by_b[b] = GB.step_vectors(tab, b, DEVICE)
            SB = svec_by_b[b]
            t_b = time.time()
            # L19: the capacity probe's answer is a function of the feature
            # shape, so it is memoised per shape (per engine here, which is the
            # kit's "per process" with the engine's lifetime).
            saved = gen.get_state()
            psig = (C.feat_signature(bd), b) if FLAGS.get("--alloc") else None
            if psig is not None and psig in probe_seen:
                probe_gb = probe_seen[psig]
            else:
                probe_gb = GB.probe_forward_gb(model, bd, b, SB[0], tab.n_timestep)
                if psig is not None:
                    probe_seen[psig] = probe_gb
            torch.cuda.synchronize()
            gen.set_state(saved)
            regime = GB.capacity_regime(bool(FLAGS.get("--cuda-graphs")))
            need, fits, b_ok, resident_gb, total_gb, evicted = (
                GB.capacity_verdict_yielding(b, probe_gb, regime, cache)
            )
            ev["graph_evictions"] += evicted
            probe_s = time.time() - t_b
            line = GB.capacity_line(
                b, n_tok, regime, probe_gb, need, resident_gb, total_gb, fits, b_ok
            )
            print(line, file=sys.stderr, flush=True)
            lines.append(line)
            capacity.append(
                {
                    "batch": b,
                    "n_token": n_tok,
                    "regime": regime,
                    "probe_gb": round(probe_gb, 3),
                    "need_gb": round(need, 2),
                    "resident_gb": round(resident_gb, 2),
                    "total_gb": round(total_gb, 1),
                    "fits": fits,
                    "evicted_graphs": evicted,
                }
            )
            if not fits:
                # The kit's guard refuses; it never reduces the batch.
                raise RuntimeError(
                    f"the kit's capacity guard refused this batch before it ran: "
                    f"{line} -- pass options.batch_size <= {b_ok} or lower"
                )
            mask = bd["gt_atom_mask"]
            if FLAGS.get("--hoist"):
                bd["_g3cap_hoist"] = True
            hoist_pre = "_g3cap_static" in bd
            gd, how, sig = None, "eager", None
            if FLAGS.get("--cuda-graphs"):
                sig = C.feat_signature(bd)
                gd = cache.take(sig)
                if gd is None:
                    saved = gen.get_state()
                    gd = G.GraphedDenoiser(
                        model,
                        bd,
                        tab.n_timestep,
                        pool=None,
                        compile=("inductor" if FLAGS.get("--compile") else None),
                        wide=bool(FLAGS.get("--wide-capture")),
                    )
                    torch.cuda.synchronize()
                    gen.set_state(saved)
                    ev["graph_captures"] += 1
                    how = "capture"
                else:
                    C.rebind_graph(gd, bd)
                    how = "reuse"
            live = gd.batch if gd is not None else bd
            if how == "reuse":
                hoist_pre = hoist_pre or "_g3cap_static" in live
            xs = SMP.sample_batch(gd, model, bd, tab, SB, mask, G.ddim_math)
            ai, seq_s = None, 0.0
            if predict_sequence:
                t_q = time.time()
                seq = {k: v for k, v in live.items() if not str(k).startswith("_g3cap")}
                ai = sampler._sample_sequence(model, seq, xs)
                del seq
                torch.cuda.synchronize()
                seq_s = time.time() - t_q
            hoist_how = "off"
            if FLAGS.get("--hoist"):
                filled = "_g3cap_static" in live
                hoist_how = (
                    "fill"
                    if (filled and not hoist_pre)
                    else ("stale" if hoist_pre else "miss")
                )
                ev["hoist_fills"] += int(hoist_how == "fill")
                ev["hoist_anomalies"] += int(hoist_how != "fill")
            if gd is not None:
                cache.give(sig, gd)
                gd = None
            ev["graph_reuses"] += int(how == "reuse")
            torch.cuda.synchronize()
            wall = time.time() - t_b
            row = {
                "names": names,
                "n_token_pad": n_tok,
                "n_token_real": [int(v) for v in bd["token_mask"].sum(dim=1).tolist()],
                "wall_s": round(wall, 3),
                "probe_s": round(probe_s, 3),
                "graph": how,
                "hoist": hoist_how,
            }
            G.assert_global_state(state0, f"after batch {bi + 1}")
            t_w = time.time()
            GB.write_batch(config, raw_cpu, names, xs, os.fspath(out_dir), ai=ai)
            G.assert_global_state(state0, f"after PDB writing, batch {bi + 1}")
            row["write_s"] = round(time.time() - t_w, 3)
            write_s += row["write_s"]
            if predict_sequence:
                row["sequence_s"] = round(seq_s, 3)
            per_batch.append(row)
            print(
                f"[genie3-opt] BATCH {bi + 1}/{n_batches} designs={len(names)} "
                f"n_token={n_tok} graph={how} hoist={hoist_how} wall_s={wall:.3f}",
                flush=True,
            )
            bd.pop("_g3cap_static", None)
            del bd, raw_cpu, live, ai
        readback_end = P.live(torch)

    graph_cache = None
    if cache is not None:
        graph_cache = {
            "capacity": cache.capacity,
            "hits": cache.hits,
            "misses": cache.misses,
            "kept": cache.n,
            "captures": ev["graph_captures"],
            "evictions": ev["graph_evictions"],
            "kept_across_requests": KEEP_GRAPHS,
        }
        if not KEEP_GRAPHS:
            _drop_graphs()

    # What this pass wrote, counted by the KIT's own reader: the
    # <problem>/pdbs/<name>.pdb files produced at or after this request started
    # AND among the design names the request record expects. An exit code is
    # not evidence that a model ran, and a file an earlier pass left in the
    # same directory is not this pass's.
    produced = KO.list_outputs(
        os.fspath(out_dir), problems, since=since, names=record.get("names_expected")
    )
    # Per design: upstream writes one PDB per design name and no metrics file,
    # so the per-design record is what the pass itself knows -- the name, the
    # file, the real and padded token counts, and which batch it came in.
    by_name: dict = {}
    for index, row in enumerate(per_batch):
        for i, nm in enumerate(row["names"]):
            by_name[nm] = {
                "name": nm,
                "batch_index": index,
                "n_token_real": row["n_token_real"][i],
                "n_token_pad": row["n_token_pad"],
                "batch_wall_s": row["wall_s"],
            }
    designs = []
    for problem, found in sorted((produced.get("problems") or {}).items()):
        for nm in found:
            pdb = Path(KO.pdb_dir(os.fspath(out_dir), problem)) / f"{nm}.pdb"
            entry = dict(by_name.get(nm, {"name": nm}))
            entry["problem"] = problem
            entry["structure"] = os.fspath(pdb)
            entry["bytes"] = pdb.stat().st_size if pdb.is_file() else 0
            designs.append(entry)

    total_s = time.time() - t_all
    timing = {
        "total_s": round(total_s, 2),
        "model_setup_s": _ENGINE["setup_s"],
        "featurize_s": round(featurize_s, 3),
        "write_s": round(write_s, 3),
        "sampling_loop_s": round(sum(r["wall_s"] for r in per_batch), 3),
    }
    if designs:
        timing["s_per_design"] = round(total_s / len(designs), 3)
    if len(per_batch) > 1:
        rest = per_batch[1:]
        timing["s_per_design_steady"] = round(
            sum(r["wall_s"] for r in rest) / max(1, sum(len(r["names"]) for r in rest)),
            3,
        )

    kernels = KK.census(KT.evidence(), tf32=bool(READBACK["matmul_tf32"]))
    kernels_line = KK.line(kernels)
    print(kernels_line, file=sys.stderr, flush=True)
    body = {
        "out_dir": os.fspath(out_dir),
        "request_file": os.fspath(request_path),
        "designs": designs,
        "n_designs": len(designs),
        "n_designs_requested": n_designs,
        "designs_expected": record.get("designs_expected"),
        "problems": problems,
        "composed": composed,
        "batch_size": B,
        "seed": seed_used,
        "det": det_level,
        "shard": f"{shard_id}/{num_shards}",
        "files": sorted(os.fspath(p) for p in out_dir.rglob("*") if p.is_file()),
        "timing": timing,
        "per_batch": per_batch,
        "capacity": capacity,
        "graph_cache": graph_cache,
        "levers": list(res.levers),
        "lever_line": " ".join(res.flags),
        "mode": MODE,
        "tier": res.tier,
        "kernels": kernels,
        "kernels_line": kernels_line,
        "kernels_verdict": KK.verdict(kernels, KM.trimul_of(res)),
        "numerics": {
            "policy": PRECISION.get("policy"),
            "readback": READBACK,
            "readback_end": readback_end,
        },
        "weights_held_by": f"engine:{MODE}",
        "engine_rebuilt": _ENGINE["builds"] != builds_before,
        "engine_key": key,
        # False means the designs came off a held engine whose generator states
        # were restored to the point a fresh process reaches before
        # featurisation. True means this request built the engine itself, which
        # is the stock order by construction.
        "rng_restored": not built,
        "kit_lines": lines,
    }
    expected = record.get("designs_expected")
    if expected is not None and limit is not None:
        expected = min(int(expected), int(limit))
    if expected is not None and len(designs) != int(expected):
        body["warning"] = (
            f"{len(designs)} PDB files of the {expected} design names this "
            f"request expects -- the pass is incomplete; read the worker log "
            f"for the kit's CAPACITY / BATCH / KERNELS lines"
        )
    elif len(designs) != n_designs:
        body["warning"] = (
            f"{len(designs)} PDB files for {n_designs} designs sampled -- the "
            f"pass is incomplete; read the worker log for the kit's own lines"
        )
    # The kit warms up each capture on a fresh side stream (g3fast.py), so
    # every request left torch holding a cuBLAS workspace for a stream nothing
    # would use again: 0.040 GiB a request, and the wall time climbed with it
    # (6.7 s by the eighth request against 2.2 s flat once released).
    # `WB.serve` gives them back after every request now, including under
    # KEEP_GRAPHS, which this worker used to refuse. The refusal was for a
    # hazard that has since been measured on this provider's own torch
    # (2.7.1+cu128, where the workspace is 8.12 MiB and not 32) and does not
    # exist: a workspace a capture allocates belongs to that graph's private
    # memory pool, so clearing hands it back to a pool no ordinary allocation
    # draws from, held graph or not. See `release_cublas_workspaces`.
    body["peak_reserved_gib"] = round(torch.cuda.max_memory_reserved() / 2**30, 2)
    return body


def _reset() -> None:
    """Make ``peak_reserved_gib`` this request's peak rather than the session's.

    Without this the figure was ``max_memory_reserved`` over the whole life of
    the worker -- a high-water mark that can only ever rise, which reads as
    per-request growth whether or not any is happening and is not what the
    other providers on this standard report. The acceptance suite runs its
    ladder ascending precisely because some workers report a session mark, and
    this one should not be among them.
    """
    torch.cuda.reset_peak_memory_stats()


def _ready() -> dict:
    return {
        "build_s": round(time.time() - T0, 1),
        "device": torch.cuda.get_device_name(0),
        "mode": MODE,
        "tier": RES0.tier,
        "levers": list(RES0.levers),
        "lever_line": " ".join(RES0.flags),
        "weights_held_by": f"engine:{MODE}",
        "weights_dir": WEIGHTS_DIR,
        "genie3_root": GENIE3_ROOT,
        "engine_key": _ENGINE["key"],
        "engine_builds": _ENGINE["builds"],
        "keep_graphs_across_requests": KEEP_GRAPHS,
        "lean_pair": LEAN,
        "patches": MARKERS,
        "jit_root": KJ.jit_root(),
    }


if __name__ == "__main__":
    # No engine is built here, and that is a property of the kit rather than a
    # shortcut: build_everything takes the REQUEST as its first argument, and
    # the sampler and the dataset it constructs both come out of that file. The
    # first request pays the build; every later request of the same key does
    # not. [runtime] start_timeout_s therefore only has to cover imports.
    say(
        f"ready t={time.time() - T0:.1f}s mode={MODE} tier={RES0.tier} "
        f"weights_held_by=engine:{MODE} engine=none-until-first-request "
        f"levers={','.join(RES0.levers)} keep_graphs={int(KEEP_GRAPHS)}"
    )
    sys.exit(
        WB.serve(
            slug=args.slug,
            socket_path=args.socket,
            on_predict=_design,
            ready=_ready,
            on_reset=_reset,
            log=say,
        )
    )
