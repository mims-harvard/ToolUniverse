"""ef2inv held resident on the GPU, answering one binder-design request at a time.

Run by the model's own interpreter::

    <model python> ef2inv_resident_worker.py --socket … --slug … --kit <kit>/ef2inv --mode fast

**This worker is the kit's ARM PROCESS.** ef2inv is an argv-only kit: it ships
no autoload ``.pth`` and patches nothing on import (``opt/pyproject.toml``: "No
autoload .pth: the upstream is a script, the kit's switch is an environment
variable the launcher sets per arm"). Its own launcher runs
``python -I -m ef2inv_opt.stock_design --mode <m> --cookbook <file> …`` once per
design, with ``EF2_FAST_KIT`` set, the design kit's ``k/`` on ``sys.path`` and
the kit installed on the imported cookbook module from outside. This file is a
different script in exactly that position: it calls the same kit functions in
the same order and then holds what the arm process throws away.

Every step below cites the part of ``ef2inv_opt/stock_design.py`` it mirrors.
Nothing in the kit is patched, copied or shadowed; the kit is asked for its own
values (the mode's switch, the allocator setting, the JIT cache key) rather than
told them.

**What residency buys.** ``ESMFold2Design.load()`` reads 28.0 GiB of fp32
weights -- ESMC-6B once, shared by every model (the cookbook's REUSE_ESMC), plus
six ESMFold2 models (two inversion models and four hero critics) -- and then the
cookbook torch.compile's the inversion models' MSA encoder and pair-update
blocks (its own COMPILE=True). An arm process pays all of it per design. This
one pays it once.

**What a request is, and what it is not.** One request is one specification and
N designs: ``n_designs`` is a request parameter, like rfdiffusion3's, and N
designs are N sequential 150-step loops in this process at seeds ``seed+k``.
Two things are NOT request parameters, and both are the kit's doing rather than
ours:

* the step count. ``STEPS = 150`` is a module constant of the cookbook file and
  ``settings.check_shipped`` makes a changed loop constant a REFUSAL, not a
  deviation. There is no knob, which is why the smoke is the warm pass.
* ``batch_size``. ``settings.batch_size_problem`` refuses ``batch_size > 1`` on
  every kit mode -- a kit arm's memory plan and graph pools are sized for one
  trajectory -- so the count costs time, never memory.

**What is per-BUILD here cannot be rebuilt in process, and the worker says so.**
rfdiffusion3 keys its engine on its build-time settings and rebuilds visibly
when a request asks for another key. That is the right answer there and the
wrong one here: a rebuild would mean re-reading 28 GiB, re-importing the
cookbook module, and -- the part with no API -- UN-applying ``patches.apply()``
and ``upstream_fix.apply()``, which rebind methods on the installed fork's own
classes process-wide. The kit offers no inverse for either. So the build key is
fixed when the worker starts (``--mode``, ``--det``, ``--chunk-size``,
``--kernel-backend``, ``--upstream-fix``, ``--use-scaling-critics``: all of them
``[runtime] worker_args``), and a request that names a different value is
refused BY NAME with the restart that would serve it. Nothing is silently
ignored and nothing is silently rebuilt.

The complex SIZE is free, and that is the kit's design rather than luck.
``fastkit.enable`` is documented as "Idempotent: a second call for the same size
re-installs nothing (one named line); a new size in the same process first
returns the previous size's shape-bound graph pools and memoised hidden states,
then re-plans", and the kit's own ``design`` wrapper calls it with the complex's
token count on every design. So a held worker serves any target and any binder
length without rebuilding, and a repeated shape is the case the kit optimises
for -- which is the failure openfold3 hit on the second request of one shape,
and the one this kit names and handles.

**What is retained between designs.** This is the first provider on the standard
that runs backward passes, so the question is new:

* the design loop never calls ``.backward()``. The cookbook takes
  ``torch.autograd.grad(loss, logits)`` for the structure term and again for the
  pseudo-perplexity term, so no graph outlives the step that built it.
* the worker keeps no tensor from a request. ``_CALLS`` holds floats and strings;
  the trajectory, the critic structures and the designed sequences are written
  to disk by the kit's own ``outputs`` module and then dropped, and
  ``gc.collect()`` runs between designs so that a dropped autograd graph is
  actually released rather than merely unreachable.
* the cross-request state that DOES persist is the kit's own and is listed on
  the ready line: the featurisation cache, the memoised ESM-C hidden states, and
  the CUDA-graph pools. The kit releases the shape-bound ones by name when the
  token count changes (``ef2_stepgraph.disable``, ``ef2_esmc_graph.release``,
  ``ef2_esmc_hoist.release``, ``ef2_pppl_graph.release``,
  ``ef2_loop_prep.release``) and reuses them when it does not.
* ``torch.cuda.empty_cache()`` is NOT called between designs. It would hand the
  allocator's cache back and make the kit's next memory plan -- which reads the
  device's free memory -- choose a different checkpoint policy for the same
  input. It IS called after a failed design, where releasing is the point.
* grad is left ENABLED globally. Every worker before this one begins with
  ``torch.set_grad_enabled(False)``; here that would disable the recipe. The
  kit's own state guard (``ef2_state_guard``) snapshots the process's global
  numeric state before it touches anything and checks it at every design step,
  so a worker that changed such state between requests would be named rather
  than quietly wrong.

**Who holds the weights.** The worker does: ``weights_held_by=worker:ESMFold2Design``.
That is safe here where it would not be under chai1's kit, because this kit
replaces no loader. Its hooks, from its own ``fastkit.HOOKS`` and confirmed on
this host, are ``prepare_esmfold2_tensors`` (the featurisation cache), the
``_enable_fast_kit`` method it adds to the cookbook's app class, that class's
``design``, ``fold_and_get_distogram``,
``compute_esmc_pseudoperplexity_nll`` and ``build_gradient_mask`` -- six
wrappers, and not one of them loads a checkpoint. There is no loader to race it
for, so memoising the load is ours to do and turns nothing off.
"""

from __future__ import annotations

import argparse
import dataclasses
import gc
import json
import math
import os
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="ef2inv", help="provider slug, echoed in ping")
ap.add_argument("--kit", required=True, help="the kit tree: <checkout>/ef2inv")
ap.add_argument(
    "--mode",
    default="fast",
    help="the kit mode: off | exact | fast | big (modes.MODES). Per BUILD.",
)
# The rest of the build key. Every one of these is applied before or at load and
# cannot be changed without rebuilding, so they are worker arguments rather than
# request fields; a request naming a different value is refused by name.
ap.add_argument("--det", type=int, default=0, help="the kit's --det level. Per BUILD.")
ap.add_argument(
    "--chunk-size",
    default=None,
    help="upstream's set_chunk_size on every loaded model: none | N. Per BUILD.",
)
ap.add_argument(
    "--kernel-backend",
    default=None,
    help="upstream's set_kernel_backend: fused | cuequivariance | None. Per BUILD.",
)
ap.add_argument(
    "--upstream-fix",
    default=None,
    help="the kit's --upstream-fix IDs, comma separated. Per BUILD.",
)
ap.add_argument(
    "--use-scaling-critics",
    type=int,
    default=0,
    help="load the 15 scaling critics (not among the pinned weights). Per BUILD.",
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
    print(f"[ef2inv-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds ef2inv's pinned stack and
    nothing of ToolUniverse, and importing the package would defeat that."""
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
            f"[ef2inv-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

KIT = Path(args.kit).expanduser().resolve()
PINS_PATH = KIT / "stock" / "PINS.json"
if not PINS_PATH.is_file():
    raise _refuse(
        f"[ef2inv-resident] {PINS_PATH} is not there: --kit must be the kit's "
        f"own directory (<checkout>/ef2inv)"
    )
PINS = json.loads(PINS_PATH.read_text())

# ---------------------------------------------------------------- the kit asks
# The kit's own core gate, which is statement one of every verb of this kit
# (cli.py main): it refuses by name unless an opt_core of at least the version
# pinned in opt/pyproject.toml [tool.opt_core] is importable.
import ef2inv_opt  # noqa: E402
from ef2inv_opt import _core_gate  # noqa: E402

CORE = _core_gate.gate(ef2inv_opt.__file__)

# modes and envproof import nothing of the stack -- no torch, no transformers,
# no esm -- which matters because the environment proof below requires that
# none of the three is loaded yet.
from ef2inv_opt import envproof  # noqa: E402
from ef2inv_opt import modes as M  # noqa: E402
from ef2inv_opt.launch import (  # noqa: E402
    DET_PINS,
    KIT_ALLOCATOR,
    LEVERS_OFF_VAR,
)

if args.mode not in M.MODES:
    raise _refuse(
        f"[ef2inv-resident] --mode {args.mode!r} is not one of {sorted(M.MODES)}"
    )
MODE = M.MODES[args.mode]
DET = int(args.det or 0)

# The arm's ONE allowed variable, with the value the KIT's own mode table gives
# it (exact -> "exact", fast -> "agk3", big -> "big"). A copy of that mapping
# here would drift the first time the kit moved a mode; launch.py deliberately
# does not set it for the same reason.
if MODE.kit_switch:
    os.environ[M.KIT_SWITCH] = MODE.kit_switch
    # The allocator setting the kit gives every kit arm, from the kit's own
    # launcher constant, and only when the operator has not set it: expandable
    # segments remove the fragmentation between the loop's eager activations and
    # the CUDA-graph pools. Set before torch is imported, so before any
    # allocation can have made it too late.
    os.environ.setdefault(*KIT_ALLOCATOR)
if DET >= 1:
    os.environ.update(DET_PINS)

# The Triton and Inductor caches, keyed by the running stack under the shared
# root -- what configs/<card>.env does, done with the kit's own functions
# because this card has no config. A key that cannot be computed is reported and
# the caches keep their own defaults, as the kit's own row says.
STACK_KEY = None
_jit_root = (os.environ.get(M.JIT_SHARED_ROOT_VAR) or "").rstrip("/")
if _jit_root:
    try:
        STACK_KEY = M.jit_cache_key()
    except Exception as exc:  # noqa: BLE001 - recorded, never fatal
        say(f"jit cache: no stack key ({type(exc).__name__}: {exc}); Triton defaults")
    if STACK_KEY:
        os.environ.setdefault("MODEL_OPT_STACK_KEY", STACK_KEY)
        for name, value in M.jit_cache_dirs(
            "shared", key=STACK_KEY, shared_root=_jit_root
        ).items():
            os.environ.setdefault(name, value)
            os.makedirs(value, exist_ok=True)
        say(f"jit cache: {_jit_root}/{STACK_KEY}/" + "{triton,inductor}")

# stock_design imports the kit's own modules and none of the stack.
from ef2inv_opt import attention as AT  # noqa: E402
from ef2inv_opt import det as D  # noqa: E402
from ef2inv_opt import evidence as EV  # noqa: E402
from ef2inv_opt import fastkit as FK  # noqa: E402
from ef2inv_opt import hardware as HW  # noqa: E402
from ef2inv_opt import outputs as O  # noqa: E402
from ef2inv_opt import patches as PT  # noqa: E402
from ef2inv_opt import report as R  # noqa: E402
from ef2inv_opt import settings as S  # noqa: E402
from ef2inv_opt import stock_design as SD  # noqa: E402
from ef2inv_opt import upstream_fix as UF  # noqa: E402

CHUNK = (
    S.CHUNK_SHIPPED if args.chunk_size is None else S.parse_chunk_size(args.chunk_size)
)
BACKEND = (
    S.KERNEL_BACKEND_SHIPPED
    if args.kernel_backend is None
    else S.parse_kernel_backend(args.kernel_backend)
)
USE_SCALING_CRITICS = bool(int(args.use_scaling_critics or 0))
FIX_IDS = UF.parse(args.upstream_fix)
# The build key, echoed on the ready line and in every reply, and the thing a
# request may not contradict.
BUILD_KEY = {
    "mode": MODE.name,
    "det": DET,
    "chunk_size": S.user_switch_word("chunk_size", CHUNK)
    if hasattr(S, "user_switch_word")
    else str(CHUNK),
    "kernel_backend": S.user_switch_word("kernel_backend", BACKEND)
    if hasattr(S, "user_switch_word")
    else str(BACKEND),
    "upstream_fix": list(FIX_IDS),
    "use_scaling_critics": USE_SCALING_CRITICS,
}

# -------------------------------------------------- the arm's import surface
# stock_design.main l.277-281: the cookbook's `import modal` resolves to the
# kit's no-op stand-in and, on a kit arm, the design kit's k/ goes first on
# sys.path. Before the proof and before any upstream import.
KIT_PATHS = M.kit_paths(os.fspath(KIT))
SD.prepare_arm_process(MODE, KIT_PATHS["k_dir"] if MODE.is_kit else None)

# stock_design.main l.282-290: the environment proof, in this process, before
# torch. A kit arm's allowed exceptions are EF2_FAST_KIT with exactly the mode's
# value and the ablation word as the operator set it.
_allowed = {M.KIT_SWITCH: MODE.kit_switch} if MODE.kit_switch else None
if _allowed is not None and (os.environ.get(LEVERS_OFF_VAR) or "").strip():
    _allowed[LEVERS_OFF_VAR] = os.environ[LEVERS_OFF_VAR]
PROOF = envproof.prove(
    PINS["stock_environment"]["must_be_absent_prefixes"], _allowed, arm=MODE.name
)
say(envproof.line(PROOF))
if not PROOF["clean"]:
    raise _refuse(
        "[ef2inv-resident] the kit's environment proof failed in this process: "
        + "; ".join(PROOF["problems"])
        + ". launch.py strips every forbidden prefix from the inherited "
        "environment, so a failure here means something else set one."
    )


def _cookbook_path() -> Path:
    """The pinned cookbook file, from the editable esm checkout's own metadata.

    ``check_pins.direct_url`` does exactly this: PEP 610 ``direct_url.json``
    with ``dir_info.editable`` locates the checkout, and the recipe lives at
    ``<checkout>/cookbook/tutorials/binder_design.py`` -- the file ships in the
    repository, not in any wheel. Metadata only: ``esm`` is not imported here,
    because the proof above requires that it is not yet loaded.

    The kit's own ``EF2INV_COOKBOOK_STOCK`` override is not read: its prefix is
    forbidden in an arm process, so an arm cannot be told the path this way.
    """
    import importlib.metadata as md

    try:
        dist = md.distribution("esm")
    except md.PackageNotFoundError:
        raise _refuse(
            "[ef2inv-resident] esm is not installed in this environment: it must "
            "be the editable checkout of github.com/Biohub/esm at "
            + PINS["upstream"]["commit"][:12]
            + " (run `tu remote setup ef2inv --only kit`)"
        ) from None
    raw = None
    try:
        raw = dist.read_text("direct_url.json")
    except OSError:
        raw = None
    info = json.loads(raw) if raw else {}
    url = str(info.get("url") or "")
    editable = bool((info.get("dir_info") or {}).get("editable"))
    if not url.startswith("file://") or not editable:
        raise _refuse(
            "[ef2inv-resident] esm is installed but not as the editable checkout "
            "the pin requires (PEP 610 dir_info.editable); the cookbook file "
            "ships in the repository, not in a wheel"
        )
    return Path(url[len("file://") :]) / "cookbook" / "tutorials" / "binder_design.py"


COOKBOOK = _cookbook_path()
# stock_design.main l.292-298: both files hashed here, no stored digest.
_REF = KIT / "stock" / "src" / "cookbook" / "tutorials" / "binder_design.py"
_got, _want = SD.sha256_file(os.fspath(COOKBOOK)), SD.sha256_file(os.fspath(_REF))
if _got != _want:
    raise _refuse(
        f"[ef2inv-resident] REFUSED cookbook file {COOKBOOK} sha256 {_got} != "
        f"tree copy {_REF} sha256 {_want}"
    )

# ------------------------------------------------------------------- the build
_LOG = EV.LogCapture()
import logging  # noqa: E402

logging.getLogger().addHandler(_LOG)
_t = time.time()
BD = SD.import_cookbook(os.fspath(COOKBOOK), "binder_design")
logging.getLogger().addHandler(_LOG)  # the cookbook's basicConfig resets handlers
import torch  # noqa: E402

IMPORT_S = round(time.time() - _t, 3)
say(f"cookbook imported t={time.time() - T0:.1f}s torch={torch.__version__}")

_bad = S.check_shipped(BD)
if _bad:
    raise _refuse(
        f"[ef2inv-resident] REFUSED the cookbook module's constants differ from "
        f"the shipped ones: {_bad}"
    )

USER_SWITCHES = S.user_switches(MODE, CHUNK, BACKEND)
try:
    KIT_REC = (
        FK.install(BD, MODE, user_switches=USER_SWITCHES)
        if MODE.is_kit
        else FK.record_off()
    )
except FK.LeversOffError as exc:
    raise _refuse(f"[ef2inv-resident] REFUSED {exc}") from None
say(
    f"PATCH {KIT_REC['name']} applied={KIT_REC['applied']}"
    + (
        f" kit={KIT_REC['kit']} hooks={','.join(KIT_REC['hooks'])}"
        if KIT_REC["applied"]
        else ""
    )
    + (
        f" levers_off={','.join(KIT_REC['levers_off'])}"
        if KIT_REC.get("levers_off")
        else ""
    )
)
if not torch.cuda.is_available():
    raise _refuse(
        "[ef2inv-resident] REFUSED no CUDA device (the recipe folds on cuda, "
        "stock file l.215/701)"
    )
DEVICE_NAME = torch.cuda.get_device_name(0)
SMI_NAME, SMI_MIB, _ = HW.card()
# stock_design.main l.318-324: the named upstream fixes, before any model is
# built. [] = the library as installed.
FIX_RECS = UF.apply(FIX_IDS, os.fspath(KIT), log=lambda m: say(m))

_t = time.time()
APP = BD.ESMFold2Design()
APP.load(use_scaling_critics=USE_SCALING_CRITICS)
# stock_design.main l.396-403: the mode's (or the user's) two switches on every
# loaded model, then the mode's critic-scope pair on the hero critics, each read
# back before anything else touches the models.
CMODE = (
    dataclasses.replace(
        MODE,
        critic_chunk_size=S.CHUNK_SHIPPED,
        critic_kernel_backend=S.KERNEL_BACKEND_SHIPPED,
    )
    if FK.ablated(BD, FK.CRITIC_LEVER)
    else MODE
)
CRITIC_SWITCHES = CMODE.critic_switches(CHUNK, BACKEND)
try:
    MODEL_SWITCHES = SD.apply_model_switches(
        APP,
        CHUNK,
        BACKEND,
        MODE.name,
        critic_chunk_size=CMODE.critic_chunk_size,
        critic_kernel_backend=CMODE.critic_kernel_backend,
    )
except SD.ModelSwitchError as exc:
    raise _refuse(f"[ef2inv-resident] NOT ACTIVE: {exc}") from None
torch.cuda.synchronize()
LOAD_S = round(time.time() - _t, 3)

DET_REC = D.apply(D.level(DET))
# stock_design.main l.406-408: upstream bug 0002, applied unconditionally on
# every arm -- the unpatched file cannot run on this stack at all.
PATCH_REC = PT.apply()
say(f"PATCH {PATCH_REC['name']} applied={PATCH_REC['applied']}")
_ROPE_REC = next((r for r in FIX_RECS if r.get("name") == PT.ESMC_ROPE_NAME), None)
_esmcs = {
    id(m): m
    for m in [getattr(APP, "esmc_model", None)]
    + [
        getattr(m, "_esmc", None)
        for m in list(APP.inversion_models.values())
        + list(getattr(APP, "hf_critic_models", {}).values())
    ]
    if m is not None
}
ATTN = AT.read(esmc_models=list(_esmcs.values()), det=DET_REC)
ATTN["require_fast_env"] = False
ATTN["esmc_rope_pin"] = _ROPE_REC["impl"] if _ROPE_REC else None
ATTN["upstream_fix"] = UF.ids_of(FIX_RECS)
say(R.attn_line(AT.words(ATTN), ATTN, False))

AGK = None
BEFORE: dict = {}
COUNTER = None
if MODE.is_kit:
    try:
        import ef2_autograd_kernels as agk  # noqa: E402
    except Exception as exc:  # noqa: BLE001 - the kit's own refusal wording
        raise _refuse(
            f"[ef2inv-resident] REFUSED the kit's lever module does not import: {exc!r}"
        ) from None
    AGK = agk
    BEFORE = EV.probe_before(MODE.name, agk=AGK, torch=torch)
    if BEFORE["refusals"]:
        raise _refuse(
            f"[ef2inv-resident] REFUSED before the loop: {BEFORE['refusals']}"
        )
    # ONE counter for the life of the worker: its install rebinds the kit's
    # kernel entry points and registers a forward pre-hook on every pair block,
    # so installing it per request would stack wrappers and multiply the counts.
    # The consequence is stated rather than worked around: its totals are
    # cumulative, so the kit's activation report is collected on the FIRST
    # design only, where this process is in exactly the state an arm process is
    # in (see _evidence_after).
    COUNTER = EV.KernelCounter()
    COUNTER.install(AGK, list(APP.inversion_models.values()), torch)

_CALLS: list = []
_STATE = {"designs": 0, "evidence": None, "observer": False, "tokens": None}


def _install_fold_observer(n_tokens_ref: dict) -> None:
    """stock_design.main l.423-437: the per-call fold observer.

    Installed once, LAZILY -- after the first ``_enable_fast_kit``, so that it
    wraps the kit's own outermost fold wrapper rather than being wrapped by it,
    which is the order the arm process gets. The kit's guard installer is
    idempotent per module object, so a later size change re-enters ``enable``
    without re-wrapping anything.
    """
    if _STATE["observer"]:
        return
    orig_fold = BD.fold_and_get_distogram
    names_by_id = {id(m): n for n, m in APP.inversion_models.items()}
    names_by_id.update({id(m): n for n, m in APP.hf_critic_models.items()})

    def fold_observed(model, *a, **kw):
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        out = orig_fold(model, *a, **kw)
        torch.cuda.synchronize()
        wall = time.perf_counter() - t0
        conf = bool(kw.get("calculate_confidence", False))
        loops = kw.get("num_loops", 0)
        _CALLS.append(
            {
                "k": len(_CALLS),
                "kind": "critic" if (conf and loops == 3) else "design",
                "wall_s": round(wall, 6),
                "tokens": n_tokens_ref.get("n"),
                "confidence": conf,
                "num_loops": loops,
                "num_sampling_steps": kw.get("num_sampling_steps"),
                "model": names_by_id.get(id(model)),
            }
        )
        return out

    BD.fold_and_get_distogram = fold_observed
    _STATE["observer"] = True


_TOKENS: dict = {"n": None}


def _check_build_key(doc: dict) -> None:
    """Refuse a request that asks for another BUILD, naming the restart that serves it."""
    clashes = []
    for field, held in (
        ("mode", MODE.name),
        ("det", DET),
        ("use_scaling_critics", USE_SCALING_CRITICS),
        ("upstream_fix", list(FIX_IDS)),
    ):
        if field in doc and doc[field] != held:
            clashes.append(f"{field}={doc[field]!r} (this worker holds {held!r})")
    for field in ("chunk_size", "kernel_backend"):
        if field in doc:
            clashes.append(
                f"{field}={doc[field]!r} is a load-time switch of this build "
                f"({BUILD_KEY[field]})"
            )
    if clashes:
        raise ValueError(
            "this request asks for a different BUILD: "
            + "; ".join(clashes)
            + ". The build cannot change in process -- the 28 GiB load could be "
            "repeated, but patches.apply() and upstream_fix.apply() rebind "
            "methods on the installed fork's classes and the kit offers no "
            "inverse -- so restart the worker with the matching "
            "[runtime] worker_args instead. Per-request fields are: target_name, "
            "target_sequence, binder_len, binder_sequence, n_designs, seed, "
            "target_hotspot_ids, epitope_contact_distance, is_antibody, pass."
        )


def _case(doc: dict) -> dict:
    """The case of a request: the cookbook's own target and binder rules.

    Mirrors stock_design.main l.340-392 -- the target rule first (a built-in
    TARGET_SEQUENCES name alone, or a label plus its sequence), then the binder
    (a fixed length registered as a PromptFactory, the cookbook's own factory,
    or a starting sequence), then the pair-bias int32 guard, which refuses a
    plane too large for the stock fused kernel BEFORE anything runs.
    """
    binder_len = doc.get("binder_len")
    binder_sequence = doc.get("binder_sequence")
    binder_name_in = doc.get("binder_name")
    stock_factory = None
    seed = int(doc.get("seed", 0))
    if binder_len is None and binder_sequence is None:
        stock_factory = binder_name_in or S.STOCK_BINDER_NAME
        if stock_factory not in BD.BINDER_PROMPT_FACTORIES:
            raise ValueError(
                f"binder_name {stock_factory!r} is not a registered "
                f"BINDER_PROMPT_FACTORIES entry of the cookbook "
                f"({sorted(BD.BINDER_PROMPT_FACTORIES)})"
            )
        binder_len = len(
            BD.BINDER_PROMPT_FACTORIES[stock_factory].sample(seed=seed).replace("|", "")
        )
    elif binder_len is None:
        binder_len = len(binder_sequence)
    st = S.for_run(
        binder_len,
        binder_name=stock_factory,
        batch_size=1,
        is_antibody=doc.get("is_antibody"),
        epitope_contact_distance=float(doc.get("epitope_contact_distance", 12.0)),
        use_scaling_critics=int(USE_SCALING_CRITICS),
        binder_sequence=binder_sequence,
    )
    target_name, target_sequence, target_route, target_seq = SD.resolve_target(
        doc.get("target_name"), doc.get("target_sequence"), BD.TARGET_SEQUENCES
    )
    if stock_factory is not None:
        binder_name = stock_factory
    elif binder_sequence is None:
        binder_name = f"mb{st.binder_len}"
        BD.BINDER_PROMPT_FACTORIES[binder_name] = BD.PromptFactory(
            name=binder_name,
            template="{seq}",
            length_ranges={"seq": (st.binder_len, st.binder_len)},
            is_antibody=bool(st.is_antibody),
        )
    else:
        binder_name = f"seq{st.binder_len}"
        BD.BINDER_PROMPT_FACTORIES.pop(binder_name, None)
    hotspots = (
        [str(h) for h in doc["target_hotspot_ids"]]
        if doc.get("target_hotspot_ids")
        else None
    )
    n_tokens = len(target_seq) + st.binder_len
    problem = S.pair_bias_int32_problem(MODE.name, BACKEND, st.batch_size, n_tokens)
    if problem:
        raise ValueError(problem)
    return {
        "st": st,
        "target_name": target_name,
        "target_sequence": target_sequence,
        "target_route": target_route,
        "target_seq": target_seq,
        "binder_name": binder_name,
        "binder_sequence": binder_sequence,
        "hotspots": hotspots,
        "n_tokens": n_tokens,
    }


def _evidence_after(case: dict, n_steps: int) -> dict:
    """The kit's own activation report, on the FIRST design of this worker only.

    stock_design.main l.515-530 collects it once per arm process, and two of its
    checks count calls against bookkeeping (F9) -- totals that this worker's one
    shared KernelCounter accumulates across requests. Collecting it per design
    would turn an honest count into a false refusal on design two, so it is
    collected where the process state matches an arm's and reported as a fact
    about this worker's first design.
    """
    if not MODE.is_kit or _STATE["evidence"] is not None:
        return _STATE["evidence"] or {}
    try:
        import ef2_pppl_graph

        pppl = ef2_pppl_graph.stats
    except Exception:  # noqa: BLE001 - the kit's own optional lever
        pppl = None
    after = EV.collect_after(
        MODE.name,
        BD,
        APP,
        COUNTER,
        _LOG.text(),
        agk=AGK,
        n_tokens=case["n_tokens"],
        pppl_stats_fn=pppl,
        n_steps=n_steps,
        critic_switches=CRITIC_SWITCHES,
        user_switches=USER_SWITCHES,
        batch_size=1,
    )
    for rec in after.get("levers") or []:
        say(R.lever_line(rec))
    say(R.evidence_line(after, MODE.name))
    _STATE["evidence"] = {
        "collected_on": "the first design of this worker",
        "refusals": list(after.get("refusals") or []),
        "asides": list(after.get("asides") or []),
        "ablated": list(after.get("ablated") or []),
        "mode_off": list(after.get("mode_off") or []),
        "levers": [
            {k: rec.get(k) for k in ("name", "state", "reason", "served") if k in rec}
            for rec in (after.get("levers") or [])
        ],
    }
    return _STATE["evidence"]


def _write_outputs(out_dir: Path, case: dict, seqs, trajectory, results) -> dict:
    """The kit's own output set, written with the kit's own writers (outputs.py)."""
    steps = BD.STEPS
    tmin = BD.TEMPERATURE_MIN
    temps = {
        s: tmin + (1 - tmin) * (0.5 * (1 + math.cos(math.pi * ((s + 1) / steps))))
        for s in range(steps)
    }
    design_calls = [c for c in _CALLS if c["kind"] == "design"]
    reps = {i: c["model"] for i, c in enumerate(design_calls)}
    n_traj = O.write_trajectory(
        os.fspath(out_dir / "trajectory.jsonl"), trajectory, temps, reps
    )
    O.write_steps(os.fspath(out_dir / "steps.jsonl"), _CALLS)
    binder_seq = seqs[0].split("|")[-1]
    O.write_fasta(
        os.fspath(out_dir / "design.fasta"),
        case["target_name"],
        case["target_seq"],
        binder_seq,
    )
    crit_rows = O.write_critics(
        os.fspath(out_dir / "critics.json"), results, os.fspath(out_dir)
    )
    first = results[0] if results else None
    if first is None or first.get("complex") is None:
        raise RuntimeError("the first hero critic returned no complex")
    O.write_complex(
        os.fspath(out_dir / "design.pdb"),
        os.fspath(out_dir / "design.cif"),
        first["complex"],
    )
    (out_dir / "run.log").write_text(_LOG.text() + "\n")
    return {
        "binder_sequence": binder_seq,
        "n_steps": n_traj,
        "critics": crit_rows,
        "n_design_folds": len(design_calls),
        "n_critic_folds": len(_CALLS) - len(design_calls),
    }


def _one_design(out_dir: Path, case: dict, seed: int) -> dict:
    """One trajectory: the cookbook's own recipe, as the arm process runs it."""
    out_dir.mkdir(parents=True, exist_ok=True)
    _CALLS.clear()
    _TOKENS["n"] = case["n_tokens"]
    st = case["st"]
    # stock_design.main l.411-421: enabled HERE rather than left to the kit's
    # own design wrapper, so the kit's loop-level levers and its per-step guard
    # sit inside the fold observer; the wrapper's own call is then the kit's
    # documented no-op ("already enabled for N tokens").
    if MODE.is_kit:
        APP._enable_fast_kit(case["n_tokens"])
    _install_fold_observer(_TOKENS)
    torch.cuda.reset_peak_memory_stats()
    t = time.time()
    seqs, trajectory, results = APP.design(
        target_name=case["target_name"],
        target_sequence=case["target_sequence"],
        binder_name=case["binder_name"],
        binder_sequence=case["binder_sequence"],
        seed=seed,
        target_hotspot_ids=case["hotspots"],
        **st.design_kwargs(),
    )
    torch.cuda.synchronize()
    design_s = round(time.time() - t, 2)
    alloc_b, reserved_b = R.cuda_peaks(torch)
    body = _write_outputs(out_dir, case, seqs, trajectory, results)
    per_step = [v.get("time") for v in trajectory.values()]
    body.update(
        {
            "seed": seed,
            "out_dir": os.fspath(out_dir),
            "timing": {
                "design_s": design_s,
                "step_time_median_s": (
                    sorted(p for p in per_step if p is not None)[len(per_step) // 2]
                    if per_step
                    else None
                ),
            },
            "peak_allocated_gib": round(alloc_b / 2**30, 2),
            "peak_reserved_gib": round(reserved_b / 2**30, 2),
            "files": sorted(os.fspath(p) for p in out_dir.rglob("*") if p.is_file()),
        }
    )
    for line in R.peak_lines(case["target_name"], seed, alloc_b, reserved_b):
        say(line)
    body["kit_evidence"] = _evidence_after(case, body["n_steps"])
    # Drop every reference the design produced before the next one starts. The
    # loop takes autograd.grad rather than .backward, so nothing is retained
    # past a step; this releases the finished trajectory and the critic
    # structures, and the collector is what actually frees a dropped graph.
    del seqs, trajectory, results
    gc.collect()
    _STATE["designs"] += 1
    return body


def _warm(out_dir: Path, case: dict, seed: int) -> dict:
    """The kit's ``warm`` work: the one-time costs and ONE design-step-shaped
    grad pass per inversion model.

    stock_design.main l.439-478, which is the ``--warm-only`` branch: a no-grad
    fold of the case per inversion model, then -- the part this provider's smoke
    exists for -- the loop's own grad pass: the fold under grad, the structure
    loss's backward with respect to the logits, and the pseudo-perplexity term's
    forward and backward. It is the smallest thing that exercises the gradient
    path end to end, and it is the smoke because the design loop's length is the
    cookbook's own pinned constant (STEPS = 150) rather than a parameter.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    _CALLS.clear()
    _TOKENS["n"] = case["n_tokens"]
    st = case["st"]
    if MODE.is_kit:
        APP._enable_fast_kit(case["n_tokens"])
    _install_fold_observer(_TOKENS)
    orig_fold = BD.fold_and_get_distogram
    torch.cuda.reset_peak_memory_stats()
    target_one_hot = BD.sequence_to_one_hot(case["target_seq"])
    logits = BD.build_initial_soft_sequence_logits("#" * st.binder_len, 1)
    design_soft = torch.softmax(logits.detach().cuda(), dim=-1)
    firsts = {}
    for name, m in APP.inversion_models.items():
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        orig_fold(
            m,
            case["target_seq"],
            target_one_hot,
            design_soft,
            num_loops=1,
            num_sampling_steps=1,
            calculate_confidence=False,
            seed=seed,
        )
        torch.cuda.synchronize()
        firsts[name] = round(time.perf_counter() - t0, 3)
    with torch.device("cuda"):
        score_mask = BD.build_gradient_mask("#" * st.binder_len, 1).sum(dim=-1) > 0
    steps = {}
    for name, m in APP.inversion_models.items():
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        lg = logits.detach().to("cuda").requires_grad_(True)
        fr = orig_fold(
            m,
            case["target_seq"],
            target_one_hot,
            torch.softmax(lg, dim=-1),
            num_loops=1,
            num_sampling_steps=1,
            calculate_confidence=False,
            seed=seed,
        )
        sl = BD.compute_structure_losses(
            fr["distogram_logits"],
            st.binder_len,
            target_sequence=case["target_seq"],
            target_hotspot_ids=case["hotspots"],
            epitope_contact_distance=st.epitope_contact_distance,
        )["total_loss"]
        torch.autograd.grad(sl.mean(), lg)
        with BD.seed_context(seed):
            pl = BD.compute_esmc_pseudoperplexity_nll(
                esmc_model=APP.esmc_model,
                binder_design=torch.softmax(lg, dim=-1),
                score_mask=score_mask,
                batch_size=BD.LM_LOSS_BATCH_SIZE,
                n_passes=BD.LM_MASK_PASSES,
            )
        torch.autograd.grad(pl.mean(), lg)
        del fr, sl, pl, lg
        torch.cuda.synchronize()
        steps[name] = round(time.perf_counter() - t0, 3)
    alloc_b, reserved_b = R.cuda_peaks(torch)
    record = {
        "arm": MODE.name,
        "import_s": IMPORT_S,
        "load_s": LOAD_S,
        "first_folds_s": firsts,
        "first_steps_s": steps,
        "n_tokens": case["n_tokens"],
        "peak_allocated_gib": round(alloc_b / 2**30, 2),
        "peak_reserved_gib": round(reserved_b / 2**30, 2),
        "device": DEVICE_NAME,
    }
    (out_dir / "warm_result.json").write_text(json.dumps(record, indent=1) + "\n")
    (out_dir / "run.log").write_text(_LOG.text() + "\n")
    O.write_steps(os.fspath(out_dir / "steps.jsonl"), _CALLS)
    say(
        f"WARM import_s={record['import_s']} load_s={record['load_s']} "
        f"first_folds_s={firsts} first_steps_s={steps}"
    )
    del target_one_hot, logits, design_soft, score_mask
    gc.collect()
    body = dict(record)
    body.update(
        {
            "out_dir": os.fspath(out_dir),
            "timing": {"first_steps_s": steps, "first_folds_s": firsts},
            "files": sorted(os.fspath(p) for p in out_dir.rglob("*") if p.is_file()),
        }
    )
    body["kit_evidence"] = _evidence_after(case, 0)
    return body


def _read_request(req: dict) -> dict:
    """``doc`` from one request: a JSON object, or the request's own fields.

    The smoke step sends the text of ``smoke/input.json`` under ``input``; the
    MCP server sends the same shape. Keys beginning with ``_`` are ignored so a
    document can carry a comment, and the request's ``seed`` serves when the
    document names none.
    """
    text = req.get("input")
    doc: dict = {}
    if isinstance(text, (dict, list)):
        doc = dict(text) if isinstance(text, dict) else {}
    elif text:
        loaded = json.loads(text)
        if not isinstance(loaded, dict):
            raise ValueError(
                "a design request is a JSON object, not " + type(loaded).__name__
            )
        doc = loaded
    doc = {k: v for k, v in doc.items() if not str(k).startswith("_")}
    doc.update({k: v for k, v in (req.get("options") or {}).items()})
    doc.setdefault("seed", int(req.get("seed", 0)))
    if not doc.get("target_name"):
        raise ValueError(
            "a request needs 'target_name': one of the cookbook's built-in "
            f"TARGET_SEQUENCES names ({sorted(BD.TARGET_SEQUENCES)}), or any "
            "label together with 'target_sequence'"
        )
    known = {
        "pass",
        "target_name",
        "target_sequence",
        "binder_len",
        "binder_name",
        "binder_sequence",
        "n_designs",
        "seed",
        "target_hotspot_ids",
        "epitope_contact_distance",
        "is_antibody",
        "mode",
        "det",
        "chunk_size",
        "kernel_backend",
        "upstream_fix",
        "use_scaling_critics",
    }
    unknown = sorted(set(doc) - known)
    if unknown:
        raise ValueError(
            f"unknown key(s) {unknown}; this provider takes {sorted(known)}"
        )
    _check_build_key(doc)
    return doc


def _handle(req: dict) -> dict:
    doc = _read_request(req)
    which = str(doc.get("pass", "design")).strip().lower()
    if which not in ("design", "warm"):
        raise ValueError("'pass' is 'design' (the 150-step loop) or 'warm'")
    case = _case(doc)
    seed = int(doc["seed"])
    n_designs = int(doc.get("n_designs", 1))
    if n_designs < 1:
        raise ValueError("'n_designs' must be at least 1")
    root = Path(req["out_dir"]) / (req.get("name") or "ef2inv")
    stamp = f"{int(time.time() * 1000):013d}"
    root = root / f"{which}-{stamp}"
    t = time.time()
    designs = []
    try:
        if which == "warm":
            designs.append(_warm(root / "warm", case, seed))
        else:
            for k in range(n_designs):
                designs.append(
                    _one_design(root / f"design-{k}-seed{seed + k}", case, seed + k)
                )
    except Exception:
        # A failed design is the one place the allocator's cache is handed back:
        # whatever the failure was, this process goes on serving and should not
        # hold the dead request's blocks while it does.
        gc.collect()
        torch.cuda.empty_cache()
        raise
    body = {
        "pass": which,
        "n_tokens": case["n_tokens"],
        "target_name": case["target_name"],
        "target_route": case["target_route"],
        "target_len": len(case["target_seq"]),
        "binder_len": case["st"].binder_len,
        "n_designs": len(designs),
        "designs": designs,
        "seed": seed,
        "mode": MODE.name,
        "weights_held_by": "worker:ESMFold2Design",
        "build_key": dict(BUILD_KEY),
        "build_rebuilt": False,
        "designs_served_by_this_worker": _STATE["designs"],
        "timing": {"request_s": round(time.time() - t, 2)},
        "files": sorted(f for d in designs for f in (d.get("files") or [])),
        "peak_reserved_gib": max((d.get("peak_reserved_gib") or 0.0) for d in designs),
        "peak_allocated_gib": max(
            (d.get("peak_allocated_gib") or 0.0) for d in designs
        ),
        "kit_evidence": designs[-1].get("kit_evidence") or {},
    }
    refusals = (body["kit_evidence"] or {}).get("refusals") or []
    if refusals:
        # The arm process exits 3 here. This worker does not discard a design
        # that already ran: the refusal is returned with it, named, and the
        # caller decides. `evidence_ok` is the field that says which happened.
        body["warning"] = (
            "the kit's activation report carries refusals -- a lever of the "
            "composition did not install or confirm without a declared reason. "
            "The arm process would have exited 3 here; the designs above ran "
            "anyway and are returned with the refusal rather than thrown away."
        )
    body["evidence_ok"] = not refusals
    return body


def _ready() -> dict:
    return {
        "build_s": round(time.time() - T0, 1),
        "device": DEVICE_NAME,
        "nvidia_smi": {"name": SMI_NAME, "memory_total_mib": SMI_MIB},
        "mode": MODE.name,
        "kit_switch": MODE.kit_switch,
        "weights_held_by": "worker:ESMFold2Design",
        "build_key": dict(BUILD_KEY),
        "stack_key": STACK_KEY,
        "core": {"version": (CORE or {}).get("version")}
        if isinstance(CORE, dict)
        else None,
        "timing": {"import_s": IMPORT_S, "load_s": LOAD_S},
        "designs_served": _STATE["designs"],
        "held_between_requests": (
            "the six loaded models and the shared ESMC-6B trunk; the kit's "
            "featurisation cache, memoised ESM-C hidden states and CUDA-graph "
            "pools, which the kit releases by name when the token count changes"
        ),
    }


if __name__ == "__main__":
    say(
        f"ready t={time.time() - T0:.1f}s mode={MODE.name} "
        f"kit_switch={MODE.kit_switch} weights_held_by=worker:ESMFold2Design "
        f"load_s={LOAD_S} import_s={IMPORT_S} "
        f"(the kit replaces no loader: its hooks are the featurisation cache, "
        f"_enable_fast_kit and the design wrapper, so memoising the load is "
        f"ours to do and turns nothing off)"
    )
    say(R.ready_line(time.time() - T0, None, LOAD_S))
    sys.exit(
        WB.serve(
            slug=args.slug,
            socket_path=args.socket,
            on_predict=_handle,
            ready=_ready,
            log=say,
        )
    )
