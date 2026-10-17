"""Build the command line that starts AlphaProtein Novo's resident worker.

This provider does not use `remote_resident.kit_launch:build_command`, and the
reason is structural rather than a preference: `kit_launch` asks the kit for its
own parameters by reading `modes.ENV` and then `_autoload.ENV` out of a
`<slug>_opt` package. There is no such package here. AP Novo is not an
Anthropic optimization kit -- `[kit]` points at upstream's own Apache-2.0
repository -- so the probe would be reading a module that does not exist and
would raise `KitUnavailable` before anything else could happen.

What that absence buys is a launcher with almost nothing in it. There is no
import hook to appease, so no inherited environment has to be stripped (the
whole second half of af3_jax's launcher); there is no lever row to read, because
`mode = "off"` means there are no levers; and `[kit.env]` carries one setting.

Two things this function will NOT do, both deliberate:

**It does not fetch weights.** A short or altered parameter file is named and
the launch stops. `tu remote setup apnovo --only weights` is the only thing that
downloads, and it refuses until the operator has accepted the non-commercial
terms -- an acceptance this code cannot make for anyone.

**It does not put the model's interpreter on ToolUniverse's path, or the
reverse.** The two shared files reach the worker as paths in its environment,
because `tooluniverse` is not importable from the model's environment and must
not be.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Tuple

from tooluniverse.remote_resident.kit_launch import KitUnavailable
from tooluniverse.remote_resident.setup import kit_checkout

# LigandMPNN's checkout and its own interpreter. Upstream's
# `run_ligandmpnn.py` reads the same two names, so an operator who has been
# driving it by hand already has them exported.
LIGANDMPNN_DIR_ENV = "LIGANDMPNN_DIR"
LIGANDMPNN_PYTHON_ENV = "TOOLUNIVERSE_LIGANDMPNN_PYTHON"


def build_command(worker) -> Tuple[List[str], Dict[str, str]]:
    """``(argv, environment)`` for ``worker``. The supervisor calls this."""
    manifest = worker.manifest

    python = manifest.python_executable()
    if not Path(python).is_file():
        raise KitUnavailable(
            f"[env] python points at {python}, which is not a file -- it must "
            f"be the interpreter of {manifest.slug}'s own environment "
            f"(set TOOLUNIVERSE_APNOVO_PYTHON)"
        )

    root = manifest.weights_root()
    if manifest.weights and root is None:
        raise KitUnavailable(f"no weights directory: set {manifest.weights_root_env}")
    problems = manifest.verify_weights()
    if problems:
        raise KitUnavailable(
            f"{manifest.slug}: the weights under {root} are not at their pins:\n  "
            + "\n  ".join(problems)
            + f"\n  run `tu remote setup {manifest.slug} --only weights` after "
            f"removing the named file"
        )

    checkout = kit_checkout(manifest)
    # Upstream's repository root IS the package, so `[kit]` declares no subdir
    # and the checkout is the directory holding run_generator.py.
    kit_home = checkout / manifest.kit.get("subdir", "") if checkout else None
    if kit_home is None or not (kit_home / "run_generator.py").is_file():
        raise KitUnavailable(
            f"{manifest.slug}: the pinned checkout is not at {kit_home}, or "
            f"holds no run_generator.py -- run "
            f"`tu remote setup {manifest.slug} --only kit`"
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
        "kit_mode": manifest.kit.get("mode", "off"),
        "weights_root": os.fspath(root) if root else "",
        "python": python,
    }
    worker_py = manifest.resolve(manifest.worker)
    argv = [python, os.fspath(worker_py)] + [
        str(a).format(**fields) for a in (manifest.worker_args or ())
    ]

    # The resequencing stage's two per-machine paths. They are APPENDED rather
    # than put in `worker_args` because either may be absent: a deployment that
    # never resequences should still start, and the operation then refuses by
    # name instead of the whole provider failing to launch. Same reasoning as
    # af3_jax's AF3_JAX_REPO -- a checkout and an interpreter are properties of
    # the machine, and `[env]` has one `python` key, not two.
    lmp_dir = os.environ.get(LIGANDMPNN_DIR_ENV, "")
    lmp_python = os.environ.get(LIGANDMPNN_PYTHON_ENV, "")
    if lmp_dir:
        argv += ["--ligandmpnn-dir", os.fspath(Path(lmp_dir).expanduser())]
    if lmp_python:
        argv += ["--ligandmpnn-python", os.fspath(Path(lmp_python).expanduser())]

    env: Dict[str, str] = {}
    if root is not None and manifest.weights_root_env:
        env[manifest.weights_root_env] = os.fspath(root)

    # [kit.env] is applied HERE because kit_launch, which normally reads that
    # table, is not on this provider's path -- so without this the settings
    # would be inert. XLA_PYTHON_CLIENT_PREALLOCATE = "false" is the one that
    # keeps this provider a good co-tenant: JAX otherwise takes most of the
    # card, and the measured 2.0 GiB budget would be a fiction.
    for name, value in (manifest.kit.get("env") or {}).items():
        env[str(name)] = str(value)

    # Both shared files are found by path: this package is not importable from
    # the model's environment, and must not be.
    env["TOOLUNIVERSE_REMOTE_PROTOCOL"] = os.fspath(shared / "protocol.py")
    env["TOOLUNIVERSE_REMOTE_WORKER_BASE"] = os.fspath(shared / "worker_base.py")
    return argv, env
