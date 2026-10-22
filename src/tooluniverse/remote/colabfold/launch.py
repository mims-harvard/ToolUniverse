"""Build the command line that starts ColabFold's resident worker.

This is the third provider in ``remote/`` that does not use
``tooluniverse.remote_resident.kit_launch:build_command`` (af3_torch and
af3_jax are the others), and the reasons are properties of the kit rather than
preferences of this provider.

**1. The hook refuses on names it does not recognise, not only on a mode.**
``colabfold_opt/_autoload.py`` installs its meta-path finder when

    (a kit mode in COLABFOLD_OPT) or (any undeclared COLABFOLD_OPT* name)
    or (MODEL_OPT_LEVERS_OFF set while the mode is off or unset)

and the second and third conditions fire with the mode unset. The finder then
waits for ``colabfold.batch`` -- which this worker must import -- and exits the
process 3 at that import. So a stray ``COLABFOLD_OPT_MODE=fast`` (a typo this
kit explicitly names as its example) or a ``MODEL_OPT_LEVERS_OFF`` left over
from an operator's last ablation is enough to kill the worker after the
supervisor has committed to the process. This module therefore PRUNES the
inherited environment rather than merely declining to add to it.
``kit_launch`` adds names; it removes none.

**2. The kit's own environment row is spelled ``kit_env``.**
``kit_launch.ask_kit`` reads ``resolve(...)``'s ``env`` or ``exports``; this
kit's ``modes.resolve(mode)`` returns ``{"mode", "levers", "kit_env", "tier"}``.
The probe's call would succeed and its row would come back empty, for a reason
that has nothing to do with the mode. Under ``off`` the row IS empty
(``TABLE["off"] = ((), {}, "stock")``), so nothing is lost here -- but a reader
comparing providers deserves to know which of the two reasons applies, and
``provider.toml``'s ``env_row_reason`` says so.

**3. ``[kit.env]`` is applied here.** ``kit_launch`` is what normally reads that
table, so a provider with its own launcher has to apply it itself or the
settings are inert. On this provider that is not a detail:
``XLA_PYTHON_CLIENT_PREALLOCATE = "false"`` is the difference between a reported
peak of 0.14 GiB and one of 91.22.

**Where the kit is asked for its own parameters.** Nowhere, and that is a
property of ``mode = "off"`` rather than an omission. ``modes.TABLE["off"]``
carries no lever and no variable, and the kit's own ``stock_pred.proof()``
asserts that no ``COLABFOLD_OPT*`` or ``AF_PALLAS_ATTN*`` name survives into the
stock model process before it launches one. This function enforces the same
thing for the resident worker, which is the stock model process in all but its
lifetime. If this provider ever moves to ``exact`` or ``fast``, the lever row
must be READ from ``modes.resolve(mode)["kit_env"]`` in a subprocess rather than
copied here; a hard-coded copy drifts the first time the kit moves.

**Exercised on the host without starting a model**: with
``COLABFOLD_OPT=fast``, ``COLABFOLD_OPT_MODE=1`` and
``MODEL_OPT_LEVERS_OFF=TRIMUL_PALLAS`` deliberately exported in the parent, this
function produced an argv and a child environment carrying no ``COLABFOLD_OPT*``
name except the two it sets on purpose, and no ``MODEL_OPT_LEVERS_OFF`` at all.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Tuple

from tooluniverse.remote_resident.kit_launch import KitUnavailable
from tooluniverse.remote_resident.setup import kit_checkout

# The kit's own declared names (colabfold_opt/_autoload.py ENV_NAMES). Any
# COLABFOLD_OPT* name outside this set makes the start-up hook refuse the first
# `import colabfold.batch`, so the child's environment is filtered against it.
DECLARED_ENV = (
    "COLABFOLD_OPT",
    "COLABFOLD_OPT_DATA_DIR",
    "COLABFOLD_OPT_HOME",
    "COLABFOLD_OPT_KIT",
    "COLABFOLD_OPT_LAUNCH_ID",
    "COLABFOLD_OPT_WORK_DIR",
    "COLABFOLD_OPT_JIT_ROOT",
    "COLABFOLD_OPT_N_GPU",
)
# The prefixes the kit insists must be absent from a stock model process
# (stock/PINS.json stock_proof.must_be_absent_prefixes, which is also
# colabfold_opt/stack.py PACKAGE_ENV_PREFIXES).
STOCK_ABSENT_PREFIXES = ("COLABFOLD_OPT", "AF_PALLAS_ATTN")
# The ablation switch. Set with no kit mode it installs the refusing finder, so
# it is stripped rather than left: under `off` there is nothing to ablate and
# the kit says so by exiting 3 at the trigger import.
LEVERS_OFF_ENV = "MODEL_OPT_LEVERS_OFF"
# The kit's own name for the compile-cache root. `MODEL_OPT_JIT_ROOT` stands in
# for it when unset, which is the kit's own rule (`run.sh`: "the kit's own
# cache-root variable follows the seeded root when nothing set it"), so the same
# default is used here.
CACHE_ENV = "COLABFOLD_OPT_JIT_ROOT"


def build_command(worker) -> Tuple[List[str], Dict[str, str]]:
    """``(argv, environment)`` for ``worker``. The supervisor calls this."""
    manifest = worker.manifest

    python = manifest.python_executable()
    if not Path(python).is_file():
        raise KitUnavailable(
            f"[env] python points at {python}, which is not a file -- it must "
            f"be the interpreter of {manifest.slug}'s own environment "
            f"(set TOOLUNIVERSE_COLABFOLD_PYTHON)"
        )

    root = manifest.weights_root()
    if manifest.weights and root is None:
        raise KitUnavailable(f"no weights directory: set {manifest.weights_root_env}")
    problems = manifest.verify_weights()
    if problems:
        # Nothing is fetched here. A short or altered parameter file is named
        # and the launch stops -- and for this provider the alternative is
        # worse than a refusal: upstream's own CLI treats a missing marker file
        # as licence to download 2 GB at request time.
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

    cache_dir = (
        os.environ.get(CACHE_ENV)
        or os.environ.get("MODEL_OPT_JIT_ROOT")
        or os.path.expanduser(f"~/.cache/tooluniverse/{manifest.slug}-jit")
    )
    os.makedirs(cache_dir, exist_ok=True)

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
        "cache_dir": cache_dir,
        "python": python,
    }
    worker_py = manifest.resolve(manifest.worker)
    argv = [python, os.fspath(worker_py)] + [
        str(a).format(**fields) for a in (manifest.worker_args or ())
    ]

    env: Dict[str, str] = {}
    # The kit's tree, for stack.home(). Harmless under `off` and correct if the
    # worker ever needs to ask the kit something in process.
    env["MODEL_OPT"] = os.fspath(kit_home)
    # Two of the kit's own DECLARED names, so that anything the worker runs that
    # consults the kit sees the same deployment this manifest describes.
    env[CACHE_ENV] = cache_dir
    if root is not None and manifest.weights_root_env:
        env[manifest.weights_root_env] = os.fspath(root)

    # [kit.env] -- applied HERE because kit_launch, which normally applies it,
    # is not on this provider's path. XLA_PYTHON_CLIENT_PREALLOCATE = "false" is
    # the one that keeps this provider a good co-tenant; see provider.toml.
    for name, value in (manifest.kit.get("env") or {}).items():
        env[str(name)] = str(value)

    off = manifest.kit.get("levers_off") or ()
    if off:
        # Not reachable under `off` -- the kit refuses an ablation with no mode
        # by name, which is exactly why the inherited variable is stripped below
        # -- but a future mode here needs a working door, and the kit does read
        # this name (ablation.py ENV).
        env[LEVERS_OFF_ENV] = ",".join(str(x) for x in off)

    # DELIBERATELY NOT SET: COLABFOLD_OPT. Absent is what the hook treats as
    # inert; "off" would also be inert, and setting neither is one fewer thing
    # that can be wrong. The mode reaches the worker as `--mode`.

    # Both shared files are found by path: this package is not importable from
    # the model's environment, and must not be.
    env["TOOLUNIVERSE_REMOTE_PROTOCOL"] = os.fspath(shared / "protocol.py")
    env["TOOLUNIVERSE_REMOTE_WORKER_BASE"] = os.fspath(shared / "worker_base.py")

    # Our own names, checked against the kit's list rather than assumed: a typo
    # in one of the two set above would arm the very refusal this function
    # exists to avoid, and it would arm it at `import colabfold.batch` in a
    # process the supervisor has already committed to.
    undeclared = sorted(
        k for k in env if k.startswith("COLABFOLD_OPT") and k not in DECLARED_ENV
    )
    if undeclared:
        raise KitUnavailable(
            f"{manifest.slug}: this launcher would set {', '.join(undeclared)}, "
            f"which colabfold_opt/_autoload.py does not declare; its start-up "
            f"hook refuses the first `import colabfold.batch` under any "
            f"undeclared COLABFOLD_OPT* name. Declared: {', '.join(DECLARED_ENV)}"
        )

    # THE STRIP HAS TO HAPPEN IN THE ARGV, NOT IN THE RETURNED ENVIRONMENT, and
    # that is a measured property of the layer rather than a style choice.
    # `supervisor._start` does
    # A REMOVAL IS A None VALUE. `supervisor.child_env` builds the child's
    # environment from `os.environ` and then applies this mapping over it, and
    # it pops every name mapped to None -- so removal IS expressible through the
    # return value, as of the fix recorded in STANDARD section 12.
    #
    # It was not when this provider was built. `_start` then did
    # `env = dict(os.environ)` followed by `env.update(extra_env)`, so a name
    # pruned from a returned copy came straight back, and this launcher worked
    # around it by putting `env -u NAME` in the ARGV. That workaround is gone
    # now that the mechanism exists: one mechanism beats two, and the argv form
    # hid the intent from anything reading `build_command`'s return value --
    # which is how the same defect survived in three sibling providers.
    #
    # Every COLABFOLD_OPT* and AF_PALLAS_ATTN* name the operator exported must be
    # REMOVED, not merely overwritten: an undeclared one makes the start-up hook
    # exit the worker 3 at `import colabfold.batch`, and a declared one
    # (COLABFOLD_OPT=fast, say) would either arm the same refusal or contradict
    # this manifest. The kit's own stock route does exactly this and then asserts
    # the result is empty (`stock_pred.proof()`), which is the behaviour this
    # reproduces for a worker that is the stock model process in all but its
    # lifetime. LEVERS_OFF_ENV goes too: under `off` it installs the refusing
    # finder all by itself, so not setting it is not enough.
    removals = {
        name: None
        for name in os.environ
        if (
            any(name.startswith(prefix) for prefix in STOCK_ABSENT_PREFIXES)
            or name == LEVERS_OFF_ENV
        )
        and name not in env
    }
    return argv, {**removals, **env}
