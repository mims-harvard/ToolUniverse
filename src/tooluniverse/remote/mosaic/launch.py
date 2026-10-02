"""Build the command line that starts mosaic's resident worker.

mosaic is the second provider here whose kit cannot use
``tooluniverse.remote_resident.kit_launch:build_command`` as it stands (af3_jax
is the first), and the reason is a property of this kit, not a preference.

**kit_launch reads the kit's environment row with ``modes.resolve(mode)`` and
refuses to start when it comes back empty.** mosaic_opt's fast row is
``JAX_COMPILATION_CACHE_DIR=$C1 ...`` and ``resolve`` substitutes ``$C1`` from a
cache directory the CALLER must supply; called bare it raises ``ValueError: row
needs $C1 but none was given``. kit_launch records that as ``row_error``, finds
no environment, and raises ``KitUnavailable`` -- a refusal of a kit that is
perfectly able to start. The row is not needed here in any case: this provider
engages the kit through the route the kit documents for a program of one's own,
``MOSAIC_OPT=<mode>``, whose hook calls ``pcc.enable()`` and
``levers.install()`` in-process and takes the P1 directory from
``MOSAIC_OPT_CACHE_ROOT``. So the launcher states those two variables, which is
what the row would have said, and nothing else about the row.

**What it asks the kit, and what it states itself.** Asked, in the model's
interpreter, through ``kit_launch.ask_kit`` (so a container route would be asked
where the kit lives): the stack key (``modes.jit_cache_key()``, the (jax,
jaxlib, CUDA plugin, GPU product) the P1 files belong to) and the mode
variable's name (``_autoload.ENV``). Read from the kit's own ``stock/PINS.json``:
the environment-name prefixes its stock arm requires absent. Stated here: the
two variables above, and the manifest's ``[kit.env]``.

**It STRIPS, and says so the one way the supervisor acts on.** The kit's
``stock_environment`` lists names that must be absent from a process it runs:
``JAX_COMPILATION_CACHE_DIR``, ``JAX_PERSISTENT_CACHE_*``, ``XLA_FLAGS``,
``MOSAIC_OPT*``, and (for every arm, stock included) ``JAX_ENABLE_X64`` and
``JAX_DEFAULT_MATMUL_PRECISION``, which the kit refuses outright because it
never changes precision. An operator who has been running the kit by hand has
very likely exported one of them. Not setting a variable and removing it are
different operations, and only removal is safe against an environment this
function did not build; a name mapped to ``None`` is what
``supervisor.child_env`` removes. A pruned copy of ``os.environ`` would not be
(af3_jax shipped that and it did nothing), so the check that matters is
``/proc/<worker pid>/environ`` and not this function's return value.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from tooluniverse.remote_resident.kit_launch import KitUnavailable, ask_kit
from tooluniverse.remote_resident.setup import kit_checkout

# The kit's own names, from stack.py (ENV_MODE / ENV_CACHE_ROOT). The mode
# variable is READ from the kit (`_autoload.ENV`) and checked against this; the
# cache-root name has no accessor, and a wrong spelling would silently disable
# P1 ("p1=none(MOSAIC_OPT_CACHE_ROOT_unset)" on the kit's ACTIVE line).
CACHE_ROOT_ENV = "MOSAIC_OPT_CACHE_ROOT"
# Refused by the kit for every arm: it never changes precision
# (det.py MUST_BE_UNSET, PINS.json stock_environment.must_be_unset_every_arm).
MUST_BE_UNSET_FALLBACK = ("JAX_ENABLE_X64", "JAX_DEFAULT_MATMUL_PRECISION")


def _stock_environment(kit_home: Path) -> Tuple[List[str], List[str], List[str]]:
    """``(absent_prefixes, exceptions, unset_every_arm)`` as the kit's PINS state them."""
    pins = kit_home / "stock" / "PINS.json"
    try:
        doc = json.loads(pins.read_text()).get("stock_environment") or {}
    except (OSError, ValueError) as exc:
        raise KitUnavailable(f"mosaic: cannot read {pins}: {exc}") from exc
    absent = [str(p) for p in doc.get("must_be_absent_prefixes") or ()]
    if not absent:
        raise KitUnavailable(
            f"mosaic: {pins} names no stock_environment.must_be_absent_prefixes; "
            f"refusing to guess what the kit wants stripped"
        )
    return (
        absent,
        [str(p) for p in doc.get("allowed_exceptions") or ()],
        [str(p) for p in doc.get("must_be_unset_every_arm") or MUST_BE_UNSET_FALLBACK],
    )


def build_command(worker) -> Tuple[List[str], Dict[str, Optional[str]]]:
    """``(argv, environment)`` for ``worker``. ``None`` values REMOVE a name."""
    manifest = worker.manifest

    python = manifest.python_executable()
    if not Path(python).is_file():
        raise KitUnavailable(
            f"[env] python points at {python}, which is not a file -- it must "
            f"be the interpreter of {manifest.slug}'s own environment "
            f"(set TOOLUNIVERSE_MOSAIC_PYTHON)"
        )

    root = manifest.weights_root()
    if manifest.weights and root is None:
        raise KitUnavailable(f"no weights directory: set {manifest.weights_root_env}")
    problems = manifest.verify_weights()
    if problems:
        # Nothing is fetched here. A short or altered file is named and the
        # launch stops, rather than a model loading whatever is on disk.
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

    mode = str(manifest.kit.get("mode", "off"))
    absent, exceptions, unset_every_arm = _stock_environment(kit_home)

    env: Dict[str, Optional[str]] = {}
    env["MODEL_OPT"] = os.fspath(kit_home)
    if root is not None and manifest.weights_root_env:
        env[manifest.weights_root_env] = os.fspath(root)

    jit_root = os.environ.get("MODEL_OPT_JIT_ROOT") or os.path.expanduser(
        f"~/.cache/tooluniverse/{manifest.slug}-jit"
    )
    os.makedirs(jit_root, exist_ok=True)
    env["MODEL_OPT_JIT_ROOT"] = jit_root

    if mode != "off":
        # Asked of the kit, in its own interpreter. The row it returns is not
        # used (see the module docstring); the two facts that are used are the
        # stack key and the mode variable's name.
        row = ask_kit(python, str(manifest.kit.get("package", "mosaic_opt")), mode)
        mode_env = row.get("mode_env")
        if not mode_env:
            raise KitUnavailable(
                "mosaic_opt exposes no mode variable (modes.ENV / _autoload.ENV), "
                "so there is no way to engage it in our own process"
            )
        key = row.get("stack_key")
        if not key:
            raise KitUnavailable(
                f"mosaic_opt could not derive its stack key ({row.get('stack_key_error')}); "
                f"without it P1's cache directory cannot be named, and the kit's fast "
                f"mode would run without its persistent compilation cache"
            )
        env["MODEL_OPT_STACK_KEY"] = str(key)
        env[str(mode_env)] = mode
        # <root>/<stack key>/mosaic: the kit's own layout (configs/<card>.env),
        # so a cache made by the kit's CLI on this card is the same directory.
        cache_root = Path(jit_root) / str(key) / "mosaic"
        cache_root.mkdir(parents=True, exist_ok=True)
        env[CACHE_ROOT_ENV] = os.fspath(cache_root)

    # [kit.env] -- states settings for the kit that are not levers. Applied here
    # because this launcher replaces kit_launch, which is what reads the table.
    for name, value in (manifest.kit.get("env") or {}).items():
        env[str(name)] = str(value)

    off = manifest.kit.get("levers_off") or ()
    if off:
        env["MODEL_OPT_LEVERS_OFF"] = ",".join(str(x) for x in off)

    shared = (
        Path(
            __import__(
                "tooluniverse.remote_resident.worker_base", fromlist=["worker_base"]
            ).__file__
        )
        .resolve()
        .parent
    )
    env["TOOLUNIVERSE_REMOTE_PROTOCOL"] = os.fspath(shared / "protocol.py")
    env["TOOLUNIVERSE_REMOTE_WORKER_BASE"] = os.fspath(shared / "worker_base.py")

    fields = {
        "socket": worker.socket_path,
        "slug": manifest.slug,
        "kit_mode": mode,
        "kit": os.fspath(kit_home),
        "weights_root": os.fspath(root) if root else "",
        "python": python,
    }
    worker_py = manifest.resolve(manifest.worker)
    argv = [python, os.fspath(worker_py)] + [
        str(a).format(**fields) for a in (manifest.worker_args or ())
    ]

    # STRIP what the kit says must be absent, except what this function just
    # decided to set. Expressed as None, which supervisor.child_env removes.
    removals: Dict[str, Optional[str]] = {}
    for name in os.environ:
        if name in env or name in exceptions:
            continue
        if name in unset_every_arm or any(name.startswith(p) for p in absent):
            removals[name] = None
    return argv, {**removals, **env}
