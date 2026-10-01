"""Build the command line that starts AF3-JAX's resident worker.

This is the second provider in ``remote/`` that does not use
``tooluniverse.remote_resident.kit_launch:build_command`` (af3_torch is the
first), and the reasons are properties of the kit rather than preferences of
this provider.

**1. The probe cannot find this kit's mode variable.** ``kit_launch.ask_kit``
reads ``modes.ENV`` and then ``_autoload.ENV``. ``af3_jax_opt.modes`` has no
module-level ``ENV`` or ``ENV_MODE`` at all -- the only ENV-prefixed name in it
is ``ENV_N_GPU`` -- and the mode variable lives at
``af3_jax_opt._autoload.ENV_MODE == "AF3_JAX_OPT"``. So ``mode_env`` comes back
empty and ``build_command`` raises ``KitUnavailable`` on its autoload path
before anything else can happen.

**2. The hook refuses on names it does not recognise, not only on a mode.**
``af3_jax_opt/_autoload.py`` arms a meta-path finder on ``alphafold3`` when

    (_mode and _mode.lower() != "off") or _undeclared

where ``_undeclared`` is every environment name starting ``AF3_JAX_`` that is
not in its 18-name ``DECLARED_ENV`` tuple. The second half of that condition
fires with the mode unset. A resident worker must ``import alphafold3``, so a
stray ``AF3_JAX_ANYTHING`` inherited from an operator's shell -- the shell of
exactly the operator who has been running ``run.sh`` by hand -- would exit the
worker 3 at import, after the supervisor had committed to the process. Hence
this module PRUNES the inherited environment rather than merely declining to
add to it. ``kit_launch`` adds names; it removes none.

**3. ``[kit.env]`` is applied here.** ``kit_launch`` is what normally reads that
table, so a provider with its own launcher has to apply it itself or the
settings are inert. The two that matter are in ``provider.toml``:
``XLA_PYTHON_CLIENT_PREALLOCATE = "false"`` overrides the kit's own pinned
``"true"``, which on a shared card is the difference between measuring the model
and measuring a 75-95% preallocation.

**Where the kit is asked for its own parameters.** Nowhere, and that is a
property of ``mode = "off"`` rather than an omission. Under ``off`` the kit
contributes no lever, no switch and no row -- ``modes.mode_env("off")`` returns
``{}``, and the kit's own ``stock_pred.proof()`` asserts that no ``AF3_JAX_*``,
``AF3P_*``, ``AF3_FLASHPAIRFORMER`` or ``AF3_DIFFUSION_HOIST`` name survives
into the stock model process before it launches one. This function enforces the
same thing for the resident worker, which is the stock model process in all but
its lifetime. If this provider ever moves to ``exact`` or ``fast``, the lever
row must be READ from ``modes.resolve(mode)["env"]`` in a subprocess rather than
copied here; a hard-coded copy drifts the first time the kit moves.

**Exercised by starting a real worker, which is the only layer that can show
it.** An earlier version of this note said the function had been "exercised on
the host without starting a model" by inspecting the argv and mapping it
returned -- and that check passed while the stripping did nothing at all,
because `supervisor._start` built the child's environment as
``dict(os.environ)`` updated with this mapping, so every name pruned from the
returned copy came straight back. With ``AF3_JAX_BOGUS=1`` exported, the worker
exited 3 at ``import alphafold3``: precisely the failure the stripping exists to
prevent. The supervisor now honours a ``None`` value as a REMOVAL, this function
returns removals rather than a pruned copy, and the test is
``AF3_JAX_BOGUS=1 AF3_JAX_OPT=fast AF3P_WHATEVER=1`` exported with a worker that
starts and answers. The lesson is general enough to be worth the paragraph: a
launcher's intent has to be expressed in something the executor acts on, and a
check has to observe the thing that executes.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Tuple

from tooluniverse.remote_resident.kit_launch import KitUnavailable
from tooluniverse.remote_resident.setup import kit_checkout

# The kit's own declared names (af3_jax_opt/_autoload.py DECLARED_ENV). Any
# AF3_JAX_* name outside this set makes the start-up hook refuse the first
# `import alphafold3`, so the child's environment is filtered against it.
DECLARED_ENV = (
    "AF3_JAX_OPT",
    "AF3_JAX_VARIANT",
    "AF3_JAX_OPT_HOME",
    "AF3_JAX_REPO",
    "AF3_JAX_PY",
    "AF3_JAX_PARAMS_ROOT",
    "AF3_JAX_CACHE_ROOT",
    "AF3_JAX_N_GPU",
    "AF3_JAX_DATTN",
    "AF3_JAX_TTR",
    "AF3_JAX_TRIATT_XLA",
    "AF3_JAX_SAMPLER_BF16",
    "AF3_JAX_ATOM_ATTN",
    "AF3_JAX_TRIMUL_CD",
    "AF3_JAX_LNP",
    "AF3_JAX_HOIST_LOGITS",
    "AF3_JAX_COND_SHARE",
    "AF3_JAX_ATOM_COND_HOIST",
)

# The kit's own variable for the fork CHECKOUT -- not an installed package, and
# the one per-machine path `[env]` has no key for. `run_alphafold.py` and
# `convert_of3_weights.py` live there and nowhere else.
REPO_ENV = "AF3_JAX_REPO"
# Persistent XLA compilation cache + tokamax autotune table. The kit's own name
# for the root; `MODEL_OPT_JIT_ROOT` stands in for it when unset, which is the
# kit's rule, so the same default is used here.
CACHE_ENV = "AF3_JAX_CACHE_ROOT"


def _repo(manifest) -> str:
    repo = os.environ.get(REPO_ENV, "")
    if not repo:
        raise KitUnavailable(
            f"{manifest.slug}: {REPO_ENV} is not set. It names the "
            f"sokrypton/alphafold3 fork CHECKOUT -- the directory holding "
            f"run_alphafold.py -- which is not the installed package and which "
            f"[env] has no key for. Lay it out from the kit and export it:\n"
            f"  bash <kit>/af3_jax/stock/unpack_src.sh ~/af3_jax-repo\n"
            f"  export {REPO_ENV}=~/af3_jax-repo\n"
            f"The checkout must stay writable: the kit copies its own script "
            f"beside run_alphafold.py on a first non-stock run."
        )
    path = Path(repo).expanduser()
    if not (path / "run_alphafold.py").is_file():
        raise KitUnavailable(
            f"{manifest.slug}: {REPO_ENV}={repo} holds no run_alphafold.py, so "
            f"it is not the fork checkout. `bash <kit>/af3_jax/stock/"
            f"unpack_src.sh {repo}` lays the pinned source out, with the kit's "
            f"one declared stock patch applied."
        )
    return os.fspath(path)


def build_command(worker) -> Tuple[List[str], Dict[str, str]]:
    """``(argv, environment)`` for ``worker``. The supervisor calls this."""
    manifest = worker.manifest

    python = manifest.python_executable()
    if not Path(python).is_file():
        raise KitUnavailable(
            f"[env] python points at {python}, which is not a file -- it must "
            f"be the interpreter of {manifest.slug}'s own environment "
            f"(set TOOLUNIVERSE_AF3_JAX_PYTHON)"
        )

    root = manifest.weights_root()
    if manifest.weights and root is None:
        raise KitUnavailable(f"no weights directory: set {manifest.weights_root_env}")
    problems = manifest.verify_weights()
    if problems:
        # Nothing is fetched here. A short or altered parameter file is named
        # and the launch stops. That matters more than usual for this provider:
        # the file is PRODUCED by a converter rather than downloaded, so
        # "plausible but wrong" is a shape it can actually take.
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

    repo = _repo(manifest)

    # The variant's own directory under the parameters root. `--model_dir` in
    # this fork names the directory that HOLDS of3_ported_weights.bin.zst, not
    # the root above it (af3_jax_opt/variants.py params_dir).
    variant = "p2"
    params_dir = os.fspath(Path(root) / variant) if root else ""

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
        "params_dir": params_dir,
        "repo": repo,
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
    # Three of the kit's own DECLARED names, so that anything the worker runs
    # that consults the kit sees the same deployment this manifest describes.
    env[REPO_ENV] = repo
    env["AF3_JAX_PY"] = python
    env[CACHE_ENV] = cache_dir
    if root is not None and manifest.weights_root_env:
        env[manifest.weights_root_env] = os.fspath(root)

    # [kit.env] -- applied HERE because kit_launch, which normally applies it,
    # is not on this provider's path. XLA_PYTHON_CLIENT_PREALLOCATE = "false"
    # is the one that keeps this provider a good co-tenant; see provider.toml.
    for name, value in (manifest.kit.get("env") or {}).items():
        env[str(name)] = str(value)

    off = manifest.kit.get("levers_off") or ()
    if off:
        # Not used under `off` (there are no levers to remove), but the kit does
        # read MODEL_OPT_LEVERS_OFF -- ablation.py ENV, consumed by
        # stack.activate through modes.with_levers_off -- so a future mode here
        # has a working door.
        env["MODEL_OPT_LEVERS_OFF"] = ",".join(str(x) for x in off)

    # DELIBERATELY NOT SET: AF3_JAX_OPT. Absent is what the hook treats as
    # inert; "off" would also be inert, and setting neither is one fewer thing
    # that can be wrong. The mode reaches the worker as `--mode`.

    # Both shared files are found by path: this package is not importable from
    # the model's environment, and must not be.
    env["TOOLUNIVERSE_REMOTE_PROTOCOL"] = os.fspath(shared / "protocol.py")
    env["TOOLUNIVERSE_REMOTE_WORKER_BASE"] = os.fspath(shared / "worker_base.py")

    # Our own names, checked against the kit's list rather than assumed: a typo
    # in one of the three set above would arm the very refusal this function
    # exists to avoid, and it would arm it at `import alphafold3` in a process
    # the supervisor has already committed to.
    undeclared = sorted(
        k for k in env if k.startswith("AF3_JAX_") and k not in DECLARED_ENV
    )
    if undeclared:
        raise KitUnavailable(
            f"{manifest.slug}: this launcher would set {', '.join(undeclared)}, "
            f"which af3_jax_opt/_autoload.py does not declare; its start-up hook "
            f"refuses the first `import alphafold3` under any undeclared "
            f"AF3_JAX_* name. Declared: {', '.join(DECLARED_ENV)}"
        )

    # STRIP, do not merely omit -- and say it the one way the supervisor acts on.
    # Every AF3_JAX_* name the operator exported must be REMOVED from the child:
    # one outside the kit's DECLARED_ENV makes the start-up hook exit the worker
    # 3 at `import alphafold3`, and one that IS declared (AF3_JAX_OPT=fast, say)
    # would either arm the same refusal or contradict this manifest. The kit's
    # own model process does exactly this -- stack.model_process_env strips four
    # prefixes -- and stock_pred.proof() asserts the result is empty.
    #
    # This used to be written as a pruned copy of os.environ, which DID NOT
    # WORK: `supervisor._start` built the child's environment as
    # `dict(os.environ)` updated with this mapping, so a name left out of the
    # copy came straight back and an exported AF3_JAX_BOGUS killed the worker.
    # Mapping a name to None is the removal the supervisor now honours, and it
    # is also the only form that can be checked by reading this return value --
    # which is how the earlier version passed a test it should have failed.
    removals = {}
    for prefix in ("AF3_JAX_", "AF3P_", "AF3_FLASHPAIRFORMER", "AF3_DIFFUSION_HOIST"):
        for name in os.environ:
            if name.startswith(prefix) and name not in env:
                removals[name] = None
    return argv, {**removals, **env}
