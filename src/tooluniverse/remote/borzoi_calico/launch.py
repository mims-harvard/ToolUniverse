"""``build_command`` for borzoi_calico.

Three things the generic ``kit_launch`` probe cannot do for this provider, which
is why it has its own launcher.

**The upstream code is two checkouts, not a package.** calico's own image puts
``borzoi/src/scripts`` and ``baskerville/src/baskerville/scripts`` on
``PYTHONPATH`` and sets ``BORZOI_DIR`` / ``BASKERVILLE_DIR``
(stock/PINS.json ``image.environment``). ``borzoi_sad`` is a *script* on that
path, not an importable module of an installed distribution -- and this worker
imports it on purpose, for its ``initialize_output_h5``, ``write_snp_len`` and
``write_pct``. Without the path there is no stock writer and the worker refuses.

**The weights directory holds two unrelated things.** ``f0/model0_best.h5`` is
read-only, and ``hg38.ml.fa`` must sit in a directory pysam can **write** to,
because ``pysam.Fastafile`` builds the ``.fai`` index beside the FASTA on first
use (borzoi_sad.py:246). A read-only weights mount works for every other
provider on this standard and does not work for this one.

**This kit keeps no environment row.** ``borzoi_opt`` resolves its modes against
its own files under ``opt/datapath/pipeline_tf/v17`` and exports no
``modes.resolve``, so the probe has nothing to read; ``[kit] env_row = "none"``
declares it.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ...remote_resident.kit_launch import KitUnavailable
from ...remote_resident.setup import kit_checkout

# Forwarded from the operator's environment when set: the kit's compile cache
# root, the thread caps worth holding down on a shared box (this provider runs
# at 600-850 % CPU), and the variant ceiling.
PASS_THROUGH = (
    "MODEL_OPT_JIT_ROOT",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "TF_NUM_INTRAOP_THREADS",
    "TF_NUM_INTEROP_THREADS",
    "BORZOI_CALICO_MAX_VARIANTS",
)


def build_command(worker) -> Tuple[List[str], Dict[str, Optional[str]]]:
    """``(argv, environment)`` for ``worker``. The supervisor calls this."""
    manifest = worker.manifest

    python = manifest.python_executable()
    if not Path(python).is_file():
        raise KitUnavailable(
            f"[env] python points at {python}, which is not a file -- it must be "
            f"the interpreter of {manifest.slug}'s own environment "
            f"(set TOOLUNIVERSE_BORZOI_CALICO_PYTHON)"
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
    # pysam writes hg38.ml.fa.fai beside the FASTA the first time it opens it.
    # Saying so here beats a worker that dies inside pysam with errno 30.
    if root is not None and not os.access(root, os.W_OK):
        raise KitUnavailable(
            f"{manifest.slug}: the weights directory {root} is not writable. "
            f"pysam builds hg38.ml.fa.fai beside the genome on first use "
            f"(borzoi_sad.py:246), so a read-only weights mount cannot serve "
            f"this provider -- unlike every other one on this standard."
        )

    checkout = kit_checkout(manifest)
    kit_home = checkout / manifest.kit.get("subdir", "") if checkout else None
    if kit_home is None or not kit_home.is_dir():
        raise KitUnavailable(
            f"{manifest.slug}: the kit checkout is not at {kit_home} -- "
            f"run `tu remote setup {manifest.slug} --only kit`"
        )

    borzoi_dir = Path(os.environ.get("BORZOI_DIR", "")).expanduser()
    baskerville_dir = Path(os.environ.get("BASKERVILLE_DIR", "")).expanduser()
    for d, name, what in (
        (borzoi_dir, "BORZOI_DIR", "calico/borzoi at 5c93582"),
        (baskerville_dir, "BASKERVILLE_DIR", "calico/baskerville at 544073b"),
    ):
        if not d.is_dir():
            raise KitUnavailable(
                f"{manifest.slug}: {name} does not name a directory ({d!r}). It "
                f"must be the checkout of {what}; the kit ships both as archives "
                f"under stock/ -- run `tu remote setup {manifest.slug} --only kit`"
            )
    stock_scripts = borzoi_dir / "src" / "scripts"
    if not (stock_scripts / "borzoi_sad.py").is_file():
        raise KitUnavailable(
            f"{manifest.slug}: stock borzoi_sad.py is not at {stock_scripts}. The "
            f"worker imports it for its own writer and refuses rather than "
            f"reimplementing it."
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
        "borzoi_dir": os.fspath(borzoi_dir),
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
    env["BORZOI_DIR"] = os.fspath(borzoi_dir)
    env["BASKERVILLE_DIR"] = os.fspath(baskerville_dir)
    if root is not None:
        env["BORZOI_CALICO_WEIGHTS"] = os.fspath(root)
    # Upstream's own PYTHONPATH head, in upstream's own order, PREPENDED to
    # whatever the operator has rather than replacing it.
    path_head = [
        os.fspath(stock_scripts),
        os.fspath(baskerville_dir / "src" / "baskerville" / "scripts"),
    ]
    existing = os.environ.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(
        path_head + ([existing] if existing else [])
    )
    # TensorFlow's own noise floor, as the kit's configs set it.
    env.setdefault("TF_CPP_MIN_LOG_LEVEL", "1")

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

    # A REMOVAL IS A None VALUE: `supervisor.child_env` applies this mapping over
    # a copy of os.environ, so a name merely left out comes straight back.
    # `BORZOI_OPT` is the kit's environment route of the mode and is set from the
    # manifest below; anything else an operator left under the prefix goes.
    env["BORZOI_OPT"] = str(manifest.kit.get("mode", "off"))
    removals: Dict[str, Optional[str]] = {
        name: None
        for name in os.environ
        if name.startswith("BORZOI_") and name not in env
    }
    return argv, {**removals, **env}
