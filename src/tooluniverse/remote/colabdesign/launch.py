"""Build the command line that starts ColabDesign's resident worker.

This provider has its own launcher, as af3_jax, af2ig and colabfold do, for the
reasons that are properties of the kit rather than preferences:

**1. The kit's start-up hook refuses on names it does not recognise.**
``colabdesign_opt_autoload.pth`` imports ``colabdesign_opt._autoload`` at every
interpreter start. With ``COLABDESIGN_OPT`` set to a mode word it arms a
meta-path finder on ``import colabdesign``; with it set to a word the kit does
not know, the finder exits the process 3 at that import. A resident worker must
import ``colabdesign``, so a ``COLABDESIGN_OPT`` left in an operator's shell is
enough to kill it after the supervisor has committed to the process. The mode
reaches the worker as ``--mode`` and the worker activates it through the kit's
own ``colabdesign_opt.enable()``; the variable itself is REMOVED from the child.

**2. Removal is expressed as ``None`` in the returned mapping.** The supervisor
builds the child's environment from the operator's own (``supervisor.child_env``)
and applies this mapping over it, so a pruned copy of ``os.environ`` removes
nothing: af3_jax's launcher did that and its stripping was inert. A name this
function wants gone is therefore mapped to ``None``, which ``child_env`` honours,
and the end-to-end test of that is to export a hostile name, start a real worker
and read ``/proc/<pid>/environ``.

**3. The names removed are the kit's own list, read from the kit.** ``stock/PINS.json``
``stock_environment.must_be_absent_prefixes`` is what the kit's stock arm
asserts is absent from a stock process (``AF2M_``, ``AF_PALLAS_``,
``COLABDESIGN_OPT``, ``KEEP_XLA_DEFAULTS``); a hard-coded copy drifts the first
time the kit moves, so this module reads the file and falls back to its own copy.

**4. [kit.env] is applied here**, because the generic ``kit_launch`` that
normally reads it is not on this provider's path. On this provider one entry is
the difference between measuring the model and measuring a preallocation:
``XLA_PYTHON_CLIENT_PREALLOCATE = "false"`` (see provider.toml).

**5. JAX's persistent compilation cache directory is this launcher's to set, and
only for a kit mode.** ``JAX_COMPILATION_CACHE_DIR`` is jax's own variable and the
kit's ``compilecache`` lever adopts it when set. Under ``--mode off`` the kit's own
stock arm REMOVES it (``stock_arm_absent_prefixes``) so that stock compiles cold;
this launcher removes it under ``off`` for the same reason and sets it under any
other mode.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from tooluniverse.remote_resident.kit_launch import KitUnavailable
from tooluniverse.remote_resident.setup import kit_checkout

# stock/PINS.json `stock_environment.must_be_absent_prefixes`: the fallback copy.
MUST_BE_ABSENT = ("AF2M_", "AF_PALLAS_", "COLABDESIGN_OPT", "KEEP_XLA_DEFAULTS")
# `stock_arm_absent_prefixes`: removed under `off` only.
STOCK_ARM_ABSENT = ("JAX_COMPILATION_CACHE_DIR", "JAX_PERSISTENT_CACHE_")
# The ablation switch the shared core reads (`opt_core`): not a declared name of
# this kit, and under a mode word with levers it would drop levers this manifest
# did not choose, so it is removed rather than inherited.
LEVERS_OFF_ENV = "MODEL_OPT_LEVERS_OFF"
CACHE_ENV = "COLABDESIGN_JIT_ROOT"


def _prefixes_from_kit(kit_home: Optional[Path]) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """(must_be_absent, stock_arm_absent) from the kit's own PINS.json, else this module's copy."""
    if kit_home is not None:
        try:
            with open(kit_home / "stock" / "PINS.json", "r", encoding="utf-8") as fh:
                se = json.load(fh).get("stock_environment", {})
            both = tuple(se.get("must_be_absent_prefixes") or ())
            stock = tuple(se.get("stock_arm_absent_prefixes") or ())
            if both:
                return both, stock or STOCK_ARM_ABSENT
        except (OSError, ValueError):
            pass
    return MUST_BE_ABSENT, STOCK_ARM_ABSENT


def _cache_dir(manifest) -> str:
    where = os.environ.get(CACHE_ENV) or os.path.expanduser(
        f"~/.cache/tooluniverse/{manifest.slug}-jit"
    )
    os.makedirs(where, exist_ok=True)
    return where


def build_command(worker) -> Tuple[List[str], Dict[str, Optional[str]]]:
    """``(argv, environment)`` for ``worker``. The supervisor calls this."""
    manifest = worker.manifest

    python = manifest.python_executable()
    if not Path(python).is_file():
        raise KitUnavailable(
            f"[env] python points at {python}, which is not a file -- it must "
            f"be the interpreter of {manifest.slug}'s own environment "
            f"(set TOOLUNIVERSE_COLABDESIGN_PYTHON)"
        )

    root = manifest.weights_root()
    if manifest.weights and root is None:
        raise KitUnavailable(f"no weights directory: set {manifest.weights_root_env}")
    problems = manifest.verify_weights()
    if problems:
        # Nothing is fetched here. A short or altered parameter file is named
        # and the launch stops.
        raise KitUnavailable(
            f"{manifest.slug}: the parameters under {root} are not at their pins:\n  "
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

    cache_dir = _cache_dir(manifest)
    kit_mode = manifest.kit.get("mode", "off")

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
        "kit_mode": kit_mode,
        "weights_root": os.fspath(root) if root else "",
        "cache_dir": cache_dir,
        "python": python,
    }
    worker_py = manifest.resolve(manifest.worker)
    argv = [python, os.fspath(worker_py)] + [
        str(a).format(**fields) for a in (manifest.worker_args or ())
    ]

    env: Dict[str, Optional[str]] = {}
    # The kit's tree, which `stack.tree_home()` reads to find stock/PINS.json and
    # the vendored BindCraft design step.
    env["MODEL_OPT"] = os.fspath(kit_home)
    if root is not None and manifest.weights_root_env:
        env[manifest.weights_root_env] = os.fspath(root)

    # [kit.env] -- applied HERE, see the module docstring.
    for name, value in (manifest.kit.get("env") or {}).items():
        env[str(name)] = str(value)

    # PYTHONHASHSEED=0: the kit says it runs "in every arm" (STOCK.md, 'How stock
    # is run'; its Dockerfile sets it) and the reason is reproducibility rather
    # than speed -- CPython salts str hashing per interpreter, so the iteration
    # order of any set of strings differs from one process to the next and a
    # trajectory seeded identically need not repeat. The kit's CLI outside its
    # image does NOT set it, so a bare `run.sh design` on a host is not the
    # kit's own arm; this worker is, in that respect.
    env["PYTHONHASHSEED"] = "0"
    # BindCraft reports a trajectory with bare print()s. Block-buffered into a log
    # file they arrive minutes late, which is the difference between a transcript
    # that shows a worker is on step 40 and one that looks hung.
    env["PYTHONUNBUFFERED"] = "1"

    # jax's persistent compilation cache: a kit mode's, not stock's.
    if kit_mode != "off":
        env["JAX_COMPILATION_CACHE_DIR"] = os.path.join(cache_dir, "xla")

    env["TOOLUNIVERSE_REMOTE_PROTOCOL"] = os.fspath(shared / "protocol.py")
    env["TOOLUNIVERSE_REMOTE_WORKER_BASE"] = os.fspath(shared / "worker_base.py")

    # REMOVE, by mapping to None, every name under the kit's own must-be-absent
    # prefixes (and the stock-arm ones under `off`, and the ablation switch). A
    # name this launcher sets on purpose is kept: nothing it sets starts with one
    # of these prefixes today, and the guard stops a later addition from being
    # silently deleted.
    must, stock = _prefixes_from_kit(kit_home)
    prefixes = tuple(must) + (tuple(stock) if kit_mode == "off" else ())
    removals: Dict[str, Optional[str]] = {}
    for name in os.environ:
        if name in env:
            continue
        if name == LEVERS_OFF_ENV or any(name.startswith(p) for p in prefixes):
            removals[name] = None
    return argv, {**removals, **env}
