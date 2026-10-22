"""Build the command line that starts af2ig's resident worker.

This is the third provider in ``remote/`` that does not use
``tooluniverse.remote_resident.kit_launch:build_command``, and as with the
other two the reason is a property of the kit.

**1. The probe has nothing to find.** ``kit_launch.ask_kit`` looks for the
kit's mode variable at ``modes.ENV`` and then at ``_autoload.ENV``.
``af2ig_opt`` has neither, and not because it hides them somewhere else: this
kit applies its modes as COMMAND-LINE FLAGS on ``predict_pdb.py``, which its
own CLI appends to an argv it then runs as a subprocess. Its
``opt/pyproject.toml`` states it -- "Every lever of this kit is a command-line
flag of the kit's driver, so there is no import-time hook and no .pth" -- and
``opt/_build_backend.py`` confirms it from the build side, globbing for a
``*_autoload.pth`` that does not exist. ``mode_env`` would come back empty and
``build_command`` would raise ``KitUnavailable`` before anything else could
happen.

**2. ``[kit.env]`` is applied here.** ``kit_launch`` is what normally reads
that table, so a provider with its own launcher has to apply it itself or the
settings are inert. Both entries matter and both are argued in
``provider.toml``: ``XLA_PYTHON_CLIENT_PREALLOCATE = "false"`` is the
difference between reporting the model's footprint and reporting JAX's
default claim on the card, and ``OMP_NUM_THREADS = "1"`` keeps TensorFlow's
feature-pipeline thread pool from existing in a process that has CUDA up.

**3. The pruning, and why it is here when no hook will punish an omission.**
af3_jax had to strip ``AF3_JAX_*`` from the child because its ``.pth`` ends
any process that imports ``alphafold3`` under an undeclared one -- a hard
failure three frames into the first import. This kit installs no ``.pth`` at
all, so an inherited ``AF2IG_OPT=fast`` cannot kill this worker. It can do
something quieter and worse. The names under ``stock_environment
.must_be_absent_prefixes`` in the kit's own ``stock/PINS.json`` are the ones
the kit REMOVES before it runs the stock driver, and it asserts the removal
(``ENV-CLEAN ok:``) rather than trusting it:

    AF2IG_OPT, JAX_COMPILATION_CACHE_DIR,
    JAX_PERSISTENT_CACHE_MIN_COMPILE_TIME_SECS,
    JAX_PERSISTENT_CACHE_ENABLE_XLA_CACHES, AF2_SUBBATCH_SIZE, CUDA_MPS_

A resident worker under ``mode = "off"`` is the stock model process in all but
its lifetime, so it gets the same environment the kit's own stock caller
builds. Two of those six would otherwise change what this provider MEASURES
without changing what it answers: a ``JAX_COMPILATION_CACHE_DIR`` inherited
from an operator's shell would silently load executables compiled by some
other session, and the first-request timings this provider's residency claim
rests on would be timings of a cache hit.

**How a name is removed, and the one thing that does not work.** Mapping it to
``None`` in the returned mapping. A pruned copy of ``os.environ`` does NOT
work and looks exactly as though it does: ``supervisor._start`` builds the
child's environment with ``child_env(extra, os.environ)``, which starts from
``os.environ`` and applies the mapping over it, so a name merely left out
comes straight back. That defect shipped in af3_jax's launcher and passed a
review that read the return value, which is the one place a pruned copy looks
correct. ``child_env`` now honours ``None`` as a removal; this launcher uses
that, and the removal is verified by inspecting the CHILD's environment rather
than this function's return value -- see provider.toml's verified_on.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from tooluniverse.remote_resident.kit_launch import KitUnavailable
from tooluniverse.remote_resident.setup import kit_checkout

# The kit's own name for the patched upstream tree's `af2_initial_guess`
# directory (stock/PINS.json `checkout.env`). An operator who laid the tree out
# elsewhere -- or who ran the kit's own `run.sh install` in tree before this
# provider existed -- points this at it and nothing else changes.
TREE_ENV = "AF2IG_DIR"

# Where [kit] install puts the tree when nobody says otherwise. The two have to
# agree, and this is the only place they are written down twice; a mismatch
# surfaces as the named refusal below rather than as an import error.
DEFAULT_TREE = "~/.cache/tooluniverse/af2ig-stock/dl_binder_design/af2_initial_guess"

# JAX's persistent compilation cache root, if the operator wants one. NOT set
# by default, and the omission is deliberate: see _cache_dir().
CACHE_ENV = "AF2IG_JIT_ROOT"

# Every name the kit's own stock caller removes before it runs the stock
# driver (stock/PINS.json `stock_environment.must_be_absent_prefixes`). Read
# from the kit when the checkout is in hand, because a hard-coded copy drifts
# the first time the kit moves; this is the fallback and the two are compared.
STOCK_MUST_BE_ABSENT = (
    "AF2IG_OPT",
    "JAX_COMPILATION_CACHE_DIR",
    "JAX_PERSISTENT_CACHE_MIN_COMPILE_TIME_SECS",
    "JAX_PERSISTENT_CACHE_ENABLE_XLA_CACHES",
    "AF2_SUBBATCH_SIZE",
    "CUDA_MPS_",
)


def _prefixes_from_kit(kit_home: Optional[Path]) -> Tuple[str, ...]:
    """The kit's own must-be-absent prefix list, or this module's copy."""
    if kit_home is None:
        return STOCK_MUST_BE_ABSENT
    pins = kit_home / "stock" / "PINS.json"
    try:
        import json

        with open(pins, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        row = doc.get("stock_environment", {}).get("must_be_absent_prefixes")
        if row:
            return tuple(str(x) for x in row)
    except Exception:  # noqa: BLE001 - the fallback is the same list, pinned
        pass
    return STOCK_MUST_BE_ABSENT


def _tree(manifest) -> str:
    """The patched `af2_initial_guess` directory, refusing by name without it."""
    given = os.environ.get(TREE_ENV, "")
    path = Path(given or DEFAULT_TREE).expanduser()
    if not (path / "predict_pdb.py").is_file():
        raise KitUnavailable(
            f"{manifest.slug}: {path} holds no predict_pdb.py, so it is not the "
            f"patched af2_initial_guess tree. That tree is PRODUCED by the kit "
            f"step -- the pinned dl_binder_design archive unpacked and the "
            f"kit's 13-diff series applied -- and it is not the installed "
            f"af2ig_opt package.\n"
            f"  tu remote setup {manifest.slug} --only kit\n"
            f"lays it out at {DEFAULT_TREE}; export {TREE_ENV} to use one "
            f"somewhere else."
        )
    if not (path / "alphafold" / "model" / "modules.py").is_file():
        raise KitUnavailable(
            f"{manifest.slug}: {path} holds predict_pdb.py but no "
            f"alphafold/model/modules.py -- the vendored AlphaFold package is "
            f"missing, so the tree is incomplete. Remove it and re-run "
            f"`tu remote setup {manifest.slug} --only kit`."
        )
    return os.fspath(path)


def _cache_dir(manifest) -> str:
    """JAX's persistent compilation cache root for this worker.

    DEFAULT: a per-provider directory under ~/.cache/tooluniverse, which this
    function CREATES but which the worker only enables when the operator asked
    for it. The distinction matters and is the reason this is a function
    rather than a constant.

    Every distinct residue count costs one XLA compilation of the whole
    AlphaFold-2 forward pass, 2-4 minutes by the kit's own measurement, and
    nothing in this stack persists it: a worker restart recompiles every
    length it is asked for. JAX's own persistent compilation cache would fix
    that across restarts, and it is one `jax.config.update` away.

    It is off by default anyway, for one reason: the kit's stock caller lists
    JAX_COMPILATION_CACHE_DIR among the names it REMOVES before running the
    stock driver, so a cache is a deviation from the stock route however
    harmless it looks, and this provider's residency measurements are quoted
    against the stock one. An operator who wants it across restarts exports
    AF2IG_JIT_ROOT and the worker says so on its ready line, which is the
    shape a deviation should have: opt-in, named, and visible in the
    transcript rather than inferred from a wall time that got faster.
    """
    root = os.environ.get(CACHE_ENV) or os.path.expanduser(
        f"~/.cache/tooluniverse/{manifest.slug}-jit"
    )
    os.makedirs(root, exist_ok=True)
    return root


def build_command(worker) -> Tuple[List[str], Dict[str, Optional[str]]]:
    """``(argv, environment)`` for ``worker``. The supervisor calls this."""
    manifest = worker.manifest

    python = manifest.python_executable()
    if not Path(python).is_file():
        raise KitUnavailable(
            f"[env] python points at {python}, which is not a file -- it must "
            f"be the interpreter of {manifest.slug}'s own environment "
            f"(set TOOLUNIVERSE_AF2IG_PYTHON)"
        )

    root = manifest.weights_root()
    if manifest.weights and root is None:
        raise KitUnavailable(f"no weights directory: set {manifest.weights_root_env}")
    problems = manifest.verify_weights()
    if problems:
        # Nothing is fetched here. A short or altered parameter file is named
        # and the launch stops -- the whole reason [[weights.files]] exists is
        # that a 28.5 MB truncation of a 2,286 MB checkpoint served
        # predictions for a month.
        raise KitUnavailable(
            f"{manifest.slug}: the weights under {root} are not at their pins:\n  "
            + "\n  ".join(problems)
            + f"\n  run `tu remote setup {manifest.slug}` after removing the named file"
        )

    checkout = kit_checkout(manifest)
    kit_home = checkout / manifest.kit.get("subdir", "") if checkout else None
    if kit_home is None or not kit_home.is_dir():
        raise KitUnavailable(
            f"{manifest.slug}: the kit checkout is not at {kit_home} -- "
            f"run `tu remote setup {manifest.slug} --only kit`"
        )

    tree = _tree(manifest)
    cache_dir = _cache_dir(manifest)

    shared = (
        Path(
            __import__(
                "tooluniverse.remote_resident.worker_base", fromlist=["worker_base"]
            ).__file__
        )
        .resolve()
        .parent
    )

    fields = {
        "socket": worker.socket_path,
        "slug": manifest.slug,
        "kit": os.fspath(kit_home),
        "kit_mode": manifest.kit.get("mode", "off"),
        "weights_root": os.fspath(root) if root else "",
        "af2ig_dir": tree,
        "cache_dir": cache_dir,
        "python": python,
    }
    worker_py = manifest.resolve(manifest.worker)
    argv = [python, os.fspath(worker_py)] + [
        str(a).format(**fields) for a in (manifest.worker_args or ())
    ]

    env: Dict[str, Optional[str]] = {}
    # The kit's tree, for anything in af2ig_opt that asks stack.home(). Inert
    # under `off` and correct if the worker ever asks the kit something.
    env["MODEL_OPT"] = os.fspath(kit_home)
    # The kit's own two required names, set to exactly what this manifest
    # describes so that anything consulting the kit sees this deployment.
    env[TREE_ENV] = tree
    if root is not None and manifest.weights_root_env:
        env[manifest.weights_root_env] = os.fspath(root)

    # [kit.env] -- applied HERE because kit_launch, which normally reads that
    # table, is not on this provider's path. Both entries are argued in
    # provider.toml; the one that must not be missed is
    # XLA_PYTHON_CLIENT_PREALLOCATE = "false".
    for name, value in (manifest.kit.get("env") or {}).items():
        env[str(name)] = str(value)

    off = manifest.kit.get("levers_off") or ()
    if off:
        # Unused under `off` (there are no levers to remove) and declared
        # anyway, because the kit does read MODEL_OPT_LEVERS_OFF -- README.md
        # Notes -- so a future mode here has a working door.
        env["MODEL_OPT_LEVERS_OFF"] = ",".join(str(x) for x in off)

    # DELIBERATELY NOT SET: AF2IG_OPT. Unset is what the kit treats as "no mode
    # named"; "off" would also be accepted by its CLI, which this provider does
    # not run. Setting neither is one fewer thing that can be wrong, and the
    # mode reaches the worker as `--mode` where the worker can refuse it.

    # Both shared files are found by path: this package is not importable from
    # the model's environment, and must not be.
    env["TOOLUNIVERSE_REMOTE_PROTOCOL"] = os.fspath(shared / "protocol.py")
    env["TOOLUNIVERSE_REMOTE_WORKER_BASE"] = os.fspath(shared / "worker_base.py")

    # STRIP, do not merely omit. Every name under the kit's own
    # must-be-absent prefixes is REMOVED from the child, by mapping it to None
    # -- the only form the supervisor acts on and the only form that can be
    # checked by reading this return value. The list is read from the kit's
    # stock/PINS.json rather than copied, so it cannot drift from the kit's
    # own stock caller.
    #
    # One name is in the prefix list and is also set above: AF2IG_OPT is
    # covered by the AF2IG_OPT prefix, and `name not in env` keeps anything
    # this launcher set on purpose. Nothing this launcher sets starts with one
    # of these prefixes today; the guard is there so that adding one later
    # does not silently delete it.
    removals: Dict[str, Optional[str]] = {}
    for prefix in _prefixes_from_kit(kit_home):
        for name in os.environ:
            if name.startswith(prefix) and name not in env:
                removals[name] = None
    return argv, {**removals, **env}
