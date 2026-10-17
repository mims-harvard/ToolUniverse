"""Build the argv and environment for proteinmpnn's resident worker.

This provider carries its own launcher rather than using the shared
``kit_launch`` probe, for the same reason esm_if1 does and then one more.

**The kit is argv-only.** ``PROTEINMPNN_OPT`` is the environment route of the
mode and ``--mode`` is the command-line route; a worker that inherited the
first from an operator's shell would be taking its mode from the environment,
which is the class of mistake this module's siblings are full of. The mode is
passed as ``--mode`` and every ``PROTEINMPNN_*`` name is REMOVED from the
child's environment -- as a None value, not by pruning a copy, because the
supervisor rebuilds the child's environment from ``os.environ`` and applies
this mapping over it.

**And there is no mode row to probe.** ``proteinmpnn_opt.modes.DEFAULT_MODE``
is ``None`` on purpose -- the kit ships no ``fast`` tier, so a command that
names no mode is a usage error rather than a default. ``KIT_MODES['off']`` is
``{"route": "stock"}``: a dict with no ``env`` and no ``exports``, because mode
``off`` is "the upstream command line in a clean subprocess; nothing from the
kit on the path". There is nothing for a probe to read, which is the seventh
``resolve()`` shape for the record and the emptiest.

What a run of this kit normally gets instead is ``configs/<card>.env``, shipped
for h100, h200 and a100 and not for this machine. This provider runs on the
CPU, so the two variables those files set that matter here are supplied below
and ``MODEL_OPT_TARGET_GPU`` is deliberately left unset: every shipped value
names a card this is not, and the kit treats it as "a report, never a refusal".
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ...remote_resident.kit_launch import KitUnavailable
from ...remote_resident.setup import kit_checkout

# Names forwarded from the operator's environment when set: the kit's compile
# cache root and the thread caps an operator may want to hold down on a shared
# box. Nothing else crosses.
PASS_THROUGH = (
    "MODEL_OPT_JIT_ROOT",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "PROTEINMPNN_MAX_RESIDUES",
)


def build_command(worker) -> Tuple[List[str], Dict[str, Optional[str]]]:
    """``(argv, environment)`` for ``worker``. The supervisor calls this."""
    manifest = worker.manifest

    python = manifest.python_executable()
    if not Path(python).is_file():
        raise KitUnavailable(
            f"[env] python points at {python}, which is not a file -- it must be "
            f"the interpreter of {manifest.slug}'s own environment "
            f"(set TOOLUNIVERSE_PROTEINMPNN_PYTHON)"
        )

    root = manifest.weights_root()
    if manifest.weights and root is None:
        raise KitUnavailable(f"no weights directory: set {manifest.weights_root_env}")
    problems = manifest.verify_weights()
    if problems:
        # Nothing is fetched here. ProteinMPNN's weights ship INSIDE the clone,
        # so a mismatch means the clone is not at the pinned commit or a file
        # was edited; either way a model must not load whatever is on disk.
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
    # The one lever this provider keeps is a FILE, so its absence is a launch
    # failure rather than a silent fallback to the stock helper.
    parser = kit_home / "opt" / "forward" / "mpnn_pdb_parser" / "kit" / "fast_parse.py"
    if not parser.is_file():
        raise KitUnavailable(
            f"{manifest.slug}: the kit's read-once parser is not at {parser}. It is "
            f"the one lever this provider keeps ([kit] levers_kept) and the worker "
            f"refuses rather than reimplementing the stock helper -- "
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
        "kit_mode": manifest.kit.get("mode", "off"),
        "weights_root": os.fspath(root) if root else "",
        "python": python,
    }
    worker_py = manifest.resolve(manifest.worker)
    argv = [python, os.fspath(worker_py)] + [
        str(a).format(**fields) for a in (manifest.worker_args or ())
    ]

    env: Dict[str, Optional[str]] = {}
    env["MODEL_OPT"] = os.fspath(kit_home)
    env["MODEL_OPT_STATE"] = os.path.expanduser(
        f"~/.cache/tooluniverse/{manifest.slug}-state"
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # The kit's own variable for the stock clone. It names the DIRECTORY (the
    # clone holding protein_mpnn_run.py, .git and both *_model_weights/), and
    # both the kit's worker and this provider's read it at import to put the
    # clone on sys.path. It is also what the .fa header's git_hash comes from.
    if root is not None:
        env["MPNN_DIR"] = os.fspath(root)
    for name in PASS_THROUGH:
        if os.environ.get(name):
            env[name] = os.environ[name]

    off = manifest.kit.get("levers_off") or ()
    if off:
        env["MODEL_OPT_LEVERS_OFF"] = ",".join(str(x) for x in off)
    for key, value in (manifest.kit.get("env") or {}).items():
        env[str(key)] = str(value)

    env["TOOLUNIVERSE_REMOTE_PROTOCOL"] = os.fspath(shared / "protocol.py")
    env["TOOLUNIVERSE_REMOTE_WORKER_BASE"] = os.fspath(shared / "worker_base.py")

    # A REMOVAL IS A None VALUE. `supervisor.child_env` builds the child's
    # environment from `os.environ` and applies this mapping over it, so a name
    # merely left out of a pruned copy comes straight back -- af3_jax shipped
    # that bug and a stray variable reached the worker.
    #
    # `PROTEINMPNN_OPT` from an operator's shell is the kit's environment route
    # of the mode, against the `--mode` on the command line. The declared name
    # itself is kept when this provider sets it (it does not), everything else
    # under the prefix goes.
    removals: Dict[str, Optional[str]] = {
        name: None
        for name in os.environ
        if name.startswith("PROTEINMPNN_") and name not in env
    }
    return argv, {**removals, **env}
