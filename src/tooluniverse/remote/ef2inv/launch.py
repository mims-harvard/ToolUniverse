"""Build the command line that starts ef2inv's resident worker.

This is the second provider in ``remote/`` that does not use
``tooluniverse.remote_resident.kit_launch:build_command`` (af3_torch is the
first), and as there the reason is a property of the kit rather than a
preference of this provider. Two of them, and the second is the hard one:

**1. The kit spells its mode variable ``ENV_MODE``.** ``kit_launch``'s probe
reads ``modes.ENV`` and then ``_autoload.ENV``; ``ef2inv_opt.modes`` defines
``ENV_MODE = "EF2INV_OPT"`` and no ``ENV``, so the probe finds no name and
``build_command`` refuses with "exposes no modes.ENV". That alone would be
worth a two-line fix in the shared probe (af3_torch's provider.toml records the
same spelling, so it is now two kits of eleven).

**2. Setting that variable in the worker's environment would be WRONG.** This
kit does not activate through a ``.pth`` at all. It ships none -- its own
``opt/pyproject.toml`` says "No autoload .pth: the upstream is a script, the
kit's switch is an environment variable the launcher sets per arm" -- and
``EF2INV_OPT`` is the CLI-side variable that tells ``run.sh`` which mode to
*launch*, never a variable an arm process carries. The arm is launched with
every name under the prefixes in ``stock/PINS.json``
``stock_environment.must_be_absent_prefixes`` REMOVED, which includes
``EF2INV_``, and the arm proves that about its own environment before torch is
imported (``ef2inv_opt/envproof.py``). An ``EF2INV_OPT`` in the worker's
environment would therefore not activate anything; it would make the kit's own
proof fail and the worker exit 3.

So this function does what the kit's own ``launch.arm_env`` does: it STRIPS
those prefixes from the inherited environment rather than merely omitting them,
and passes the mode to the worker as ``--mode``.

**Where the kit is asked for its own parameters.** Not here, and for af3_torch's
reason: ``ef2inv_opt`` imports neither torch nor the model, and the worker
already runs in the interpreter where the kit is installed, so the worker asks
it directly, in process, before it imports anything of the stack. It reads

* ``modes.MODES[mode].kit_switch`` -- the arm's one allowed variable,
  ``EF2_FAST_KIT=exact|agk3|big``. The mapping from mode name to switch value
  is the kit's and a copy of it here would drift.
* ``launch.KIT_ALLOCATOR`` -- ``PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True``,
  which the kit gives every kit arm unless the operator set it.
* ``launch.DET_PINS`` -- the two Inductor variables of a ``--det`` arm.
* ``modes.jit_cache_key()`` and ``modes.jit_cache_dirs()`` -- the Triton and
  Inductor cache directories under ``MODEL_OPT_JIT_ROOT/<stack key>/``, which
  ``configs/<card>.env`` would have set and which this card has no config for.

What is left for this function is what has to be true before the process starts:
the interpreter, the argv, the weights verified, and the handful of names above
that are paths rather than policy.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

from tooluniverse.remote_resident.kit_launch import KitUnavailable
from tooluniverse.remote_resident.setup import kit_checkout

# Names the operator may supply that this provider passes straight through. They
# are the kit's own (STOCK.md, Variables) and are per-machine paths, so nothing
# here invents a default; the worker refuses by name when one it needs is
# missing. EF2INV_COOKBOOK_STOCK is deliberately NOT among them: it carries a
# forbidden prefix, so an arm process may not see it, and the worker resolves
# the cookbook file from the editable esm checkout's own metadata instead.
PASS_THROUGH = ("ESMCFOLD_CCD_PATH",)

# Fallback only. The prefixes are read from the kit's own PINS.json; this list
# is what a checkout too old to carry them would get, and it is the same list.
_FALLBACK_PREFIXES = (
    "EF2_",
    "EF2INV_",
    "ESMFOLD2_",
    "CUBLAS_WORKSPACE_CONFIG",
    "NVIDIA_TF32_OVERRIDE",
    "CUDA_MPS_",
    "TORCH_COMPILE_DISABLE",
    "TORCHDYNAMO_DISABLE",
    "MODEL_OPT_LEVERS_OFF",
)


def _must_be_absent(kit_home: Path) -> List[str]:
    """The kit's own list of variable prefixes an arm process may not carry."""
    pins = kit_home / "stock" / "PINS.json"
    try:
        doc = json.loads(pins.read_text())
        prefixes = doc["stock_environment"]["must_be_absent_prefixes"]
    except (OSError, ValueError, KeyError):
        return list(_FALLBACK_PREFIXES)
    return [str(p) for p in prefixes]


def build_command(worker) -> Tuple[List[str], Dict[str, str]]:
    """``(argv, environment)`` for ``worker``. The supervisor calls this."""
    manifest = worker.manifest

    python = manifest.python_executable()
    if not Path(python).is_file():
        raise KitUnavailable(
            f"[env] python points at {python}, which is not a file -- it must be "
            f"the interpreter of {manifest.slug}'s own environment "
            f"(set TOOLUNIVERSE_EF2INV_PYTHON)"
        )

    root = manifest.weights_root()
    if manifest.weights and root is None:
        raise KitUnavailable(f"no weights directory: set {manifest.weights_root_env}")
    problems = manifest.verify_weights()
    if problems:
        # Nothing is fetched here. A short or altered snapshot is named and the
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
        "kit_mode": manifest.kit.get("mode", "fast"),
        "weights_root": os.fspath(root) if root else "",
        "python": python,
    }
    worker_py = manifest.resolve(manifest.worker)
    argv = [python, os.fspath(worker_py)] + [
        str(a).format(**fields) for a in (manifest.worker_args or ())
    ]

    env: Dict[str, str] = {}
    # The kit tree the lever modules are resolved from (modes.kit_root reads it;
    # configs/<card>.env sets it). The package is installed editable from the
    # checkout so it would derive this itself; stating it keeps a non-editable
    # install working.
    env["MODEL_OPT"] = os.fspath(kit_home)
    if root is not None and manifest.weights_root_env:
        env[manifest.weights_root_env] = os.fspath(root)
    # The configs' own policy: nothing is fetched at run time -- the six pinned
    # snapshots are already under HF_HOME and the weights step verified them.
    env.setdefault("HF_HUB_OFFLINE", "1")
    env.setdefault("TRANSFORMERS_OFFLINE", "1")
    # configs/<card>.env and the kit's own arm_env both set this: the kit tree
    # is read-only to us and carries the kit's bytes only.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for name in PASS_THROUGH:
        if os.environ.get(name):
            env[name] = os.environ[name]

    off = manifest.kit.get("levers_off") or ()
    if off:
        # This kit DOES read it: the launcher documents MODEL_OPT_LEVERS_OFF as
        # a kit arm's second allowed variable and fastkit.install resolves it by
        # name, raising LeversOffError on a lever the mode does not compose.
        env["MODEL_OPT_LEVERS_OFF"] = ",".join(str(x) for x in off)
    for key, value in (manifest.kit.get("env") or {}).items():
        env[str(key)] = str(value)

    # Both shared files are found by path: this package is not importable from
    # the model's environment, and must not be.
    env["TOOLUNIVERSE_REMOTE_PROTOCOL"] = os.fspath(shared / "protocol.py")
    env["TOOLUNIVERSE_REMOTE_WORKER_BASE"] = os.fspath(shared / "worker_base.py")

    # Compiled kernels keyed by torch + CUDA + arch. The worker puts the Triton
    # and Inductor directories under <root>/<stack key>/ using the kit's own
    # modes.jit_cache_dirs, which is what configs/<card>.env does; keeping them
    # across worker lifetimes is what stops a restart recompiling, and this
    # recipe compiles both Inductor blocks (the cookbook's own COMPILE=True) and
    # the kit's Triton kernels.
    jit_root = os.environ.get("MODEL_OPT_JIT_ROOT") or os.path.expanduser(
        f"~/.cache/tooluniverse/{manifest.slug}-jit"
    )
    os.makedirs(jit_root, exist_ok=True)
    env["MODEL_OPT_JIT_ROOT"] = jit_root

    # A REMOVAL IS A None VALUE, not a pruned copy. `supervisor.child_env`
    # builds the child's environment from `os.environ` and then applies this
    # mapping over it, so a name merely left out of a copy comes straight back.
    # This launcher used to prune `dict(os.environ)` and its strip did nothing:
    # measured on a sibling provider, with the stray variable exported and the
    # worker exiting 3 at the very refusal the strip existed to prevent.
    # STANDARD section 12 has the general form -- a launcher's intent has to be
    # expressed in something the executor acts on.
    #
    # The list is the kit's own: an EF2INV_OPT or a stale EF2_FAST_KIT inherited
    # from an operator's shell would fail the kit's environment proof in the
    # worker and cost a confusing exit 3. EF2_FAST_KIT is set by the WORKER,
    # from the kit's own mode table.
    popen_env = {
        name: None
        for prefix in _must_be_absent(kit_home)
        for name in os.environ
        if (name.startswith(prefix) if prefix.endswith("_") else name == prefix)
    }
    popen_env.update(env)
    return argv, popen_env
