"""Start a resident worker under an optimization kit's own launcher.

Every kit in ``anthropics/uplifting-biomolecular-modeling`` is built on one
shared core, and the uniformity is usable: all 36 carry ``run.sh``,
``environment/``, ``opt/`` and ``stock/PINS.json``, and 35 name their package
``<kit>_opt`` (``protenix_v2`` is the one that does not, which is why
``[kit] package`` can be stated). Their launcher runs an arbitrary script::

    <model python> -m <kit>_opt.worker_launch --route … --attach … -- <script> …

so a resident worker is simply a different script in the position the kit's own
batch worker occupies, and the kit's import hooks attach the levers of the
active mode to the model that script builds. Nothing in the kit is patched,
copied or shadowed, and its own pin and version checks keep working.

The options and the environment row are deliberately not written down here.
They belong to the kit, change with it, and cannot be read from this process at
all — ``<kit>_opt`` lives in the model's environment, whose pinned stack does
not coexist with ToolUniverse's. So the kit is asked, once per worker start, in
its own interpreter. A hard-coded copy would drift silently the first time the
kit was updated; this cannot.

One subtlety that looks like an oversight in a manifest and is not: a kit's row
may set a switch for an adapter that misbehaves on a given host. Leave it. An
adapter named in ``--attach`` whose switch is *missing* from the row refuses the
whole launch, whereas one whose switch is present and whose preconditions are
not met declines by its own name and the launch proceeds. Removing the variable
breaks the start; leaving it is what keeps the code out of the process.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

KIT_PROBE_TIMEOUT_S = 180.0

# Runs in the model's interpreter. MODEL_OPT is the kit directory, derived from
# where the package was installed from rather than from a variable a deployment
# would have to keep in step with the checkout.
_PROBE = r"""
import json, os, pathlib, sys
pkg = __import__(sys.argv[1])
os.environ.setdefault("MODEL_OPT", str(pathlib.Path(pkg.__file__).resolve().parents[2]))
modes = __import__(sys.argv[1] + ".modes", fromlist=["modes"])
stack = __import__(sys.argv[1] + ".stack", fromlist=["stack"])
mode = sys.argv[2]
row = dict(modes.resolve(mode)["env"])
out = {
    "opts": stack.launch_opts(mode, 1, "defaults"),
    "env": {k: str(v) for k, v in row.items()},
    "model_opt": os.environ["MODEL_OPT"],
}
try:
    out["stack_key"] = modes.jit_cache_key()
except Exception as exc:
    out["stack_key_error"] = "%s: %s" % (type(exc).__name__, exc)
sys.stdout.write("KITROW " + json.dumps(out))
"""


class KitUnavailable(RuntimeError):
    """The kit is not installed on the model environment's interpreter."""


def kit_package(manifest) -> str:
    """``[kit] package``, else ``<subdir>_opt`` — the convention 35 of 36 follow."""
    declared = manifest.kit.get("package")
    if declared:
        return str(declared)
    subdir = manifest.kit.get("subdir") or manifest.slug
    return f"{subdir}_opt"


def ask_kit(python: str, package: str, mode: str) -> Dict:
    """The kit's own launch options and environment row, read in its interpreter."""
    proc = subprocess.run(
        [python, "-c", _PROBE, package, mode],
        capture_output=True, text=True, timeout=KIT_PROBE_TIMEOUT_S,
    )
    marker = "KITROW "
    for line in proc.stdout.splitlines():
        if line.startswith(marker):
            return json.loads(line[len(marker):])
    raise KitUnavailable(
        f"{python}: could not read {package}'s mode row for mode={mode!r} "
        f"(rc {proc.returncode}). Its own words:\n"
        f"{(proc.stderr or proc.stdout).strip()[-1500:]}"
    )


def build_command(worker) -> Tuple[List[str], Dict[str, str]]:
    """``(argv, extra environment)`` for ``worker``. The supervisor calls this."""
    manifest = worker.manifest
    python = manifest.python_executable()
    if not Path(python).is_file():
        raise KitUnavailable(
            f"[env] python points at {python}, which is not a file — it must be "
            f"the interpreter of {manifest.slug}'s own environment"
        )

    root = manifest.weights_root()
    if manifest.weights and root is None:
        raise KitUnavailable(f"no weights directory: set {manifest.weights_root_env}")
    problems = manifest.verify_weights()
    if problems:
        # Nothing is fetched here. A short or altered cache is named and the
        # launch stops, rather than a model loading whatever is on disk.
        raise KitUnavailable(
            f"{manifest.slug}: the weights under {root} are not at their pins:\n  "
            + "\n  ".join(problems)
            + f"\n  run `tu remote setup {manifest.slug}` after removing the named file"
        )

    package = kit_package(manifest)
    row = ask_kit(python, package, manifest.kit.get("mode", "fast"))

    worker_py = manifest.resolve(manifest.worker)
    shared = Path(__file__).resolve().parent
    fields = {
        "socket": worker.socket_path,
        "slug": manifest.slug,
        "weights_root": os.fspath(root) if root else "",
        "python": python,
        "kit": row["model_opt"],
    }
    argv = [
        python, "-m", f"{package}.worker_launch", *row["opts"], "--",
        os.fspath(worker_py),
        *[str(a).format(**fields) for a in (manifest.worker_args or ())],
    ]

    env: Dict[str, str] = dict(row["env"])
    env["MODEL_OPT"] = row["model_opt"]
    if row.get("stack_key"):
        env["MODEL_OPT_STACK_KEY"] = row["stack_key"]
    if root is not None and manifest.weights_root_env:
        env[manifest.weights_root_env] = os.fspath(root)
    # Both shared files are found by path: this process's package is not
    # importable from the model's environment, and must not be.
    env["TOOLUNIVERSE_REMOTE_PROTOCOL"] = os.fspath(shared / "protocol.py")
    env["TOOLUNIVERSE_REMOTE_WORKER_BASE"] = os.fspath(shared / "worker_base.py")
    # Compiled kernels keyed by torch+CUDA+arch. Keeping them across worker
    # lifetimes is what stops a restart recompiling: on the first provider the
    # smoke prediction fell from 42 s to 12 s once the cache was warm.
    jit_root = os.environ.get("MODEL_OPT_JIT_ROOT") or os.path.expanduser(
        f"~/.cache/tooluniverse/{manifest.slug}-jit"
    )
    os.makedirs(jit_root, exist_ok=True)
    env["MODEL_OPT_JIT_ROOT"] = jit_root
    return argv, env
