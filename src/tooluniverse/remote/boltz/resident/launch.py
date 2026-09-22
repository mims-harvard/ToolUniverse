"""Build the command that starts Boltz-2's resident worker.

The worker runs under the optimization kit's own launcher::

    <model python> -m boltz2_opt.worker_launch --route … --attach … -- \
        boltz_resident_worker.py --socket … --cache … --checkpoint …

so the kit's import hooks attach its levers to the model the worker builds.
Nothing of the kit is copied or patched: our script simply occupies the position
the kit's batch worker occupies.

The options and the environment row are not written down here. They belong to
the kit and change with it, and this process -- ToolUniverse's -- cannot import
``boltz2_opt`` at all, because it lives in the model's own environment with a
pinned stack that does not coexist with ours. So the kit is asked, once per
worker start, in its own interpreter: :func:`_ask_kit` runs a few lines there
and reads back the row. A hard-coded copy would drift silently the first time
the kit is updated; this cannot.

One subtlety worth stating, since it looks like an oversight. ``BOLTZ_PREFETCH``
stays in the row even though the persistent featurizer it switches on hangs on
this box. The adapter is in ``--attach``, and an attached adapter whose switch is
missing from the row refuses the whole launch (exit 3) rather than skip. With the
switch present and no ``--pipeline`` argument it declines by its own name --
``skipped_by_name:pipeline0`` -- which is a legal disposition and keeps the
hanging code out of the process. Removing the variable would break the launch;
leaving it is what keeps the featurizer away.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

# Asked of the kit's interpreter. MODEL_OPT is the kit directory, derived from
# where boltz2_opt was installed from (<kit>/opt/boltz2_opt) rather than from a
# variable a deployment would have to keep in step.
_PROBE = r"""
import json, os, pathlib, sys
import boltz2_opt
os.environ.setdefault("MODEL_OPT", str(pathlib.Path(boltz2_opt.__file__).resolve().parents[2]))
from boltz2_opt import modes, stack
mode = sys.argv[1]
row = dict(modes.resolve(mode)["env"])
out = {
    "opts": stack.launch_opts(mode, 1, "defaults"),
    "env": {k: str(v) for k, v in row.items()},
    "model_opt": os.environ["MODEL_OPT"],
    "stack_key": modes.jit_cache_key(),
}
sys.stdout.write("KITROW " + json.dumps(out))
"""

KIT_PROBE_TIMEOUT_S = 180.0


class KitUnavailable(RuntimeError):
    """The optimization kit is not installed on the model environment's python."""


def _ask_kit(python: str, mode: str) -> Dict:
    proc = subprocess.run(
        [python, "-c", _PROBE, mode],
        capture_output=True,
        text=True,
        timeout=KIT_PROBE_TIMEOUT_S,
    )
    marker = "KITROW "
    for line in proc.stdout.splitlines():
        if line.startswith(marker):
            return json.loads(line[len(marker) :])
    raise KitUnavailable(
        f"{python}: could not read the Boltz-2 kit's mode row for mode={mode!r} "
        f"(rc {proc.returncode}). Its own words:\n{(proc.stderr or proc.stdout).strip()[-1500:]}"
    )


def build_command(worker) -> Tuple[List[str], Dict[str, str]]:
    """``(argv, extra environment)`` for ``worker``. Called by the supervisor."""
    manifest = worker.manifest  # attached by the provider's backend
    python = manifest.python_executable()
    if not Path(python).is_file():
        raise KitUnavailable(
            f"[env] python points at {python}, which is not a file — it must be the "
            f"interpreter of the environment holding boltz 2.2.1 and the kit"
        )

    cache = manifest.weights_root()
    if cache is None:
        raise KitUnavailable(f"no weights directory: set {manifest.weights_root_env}")
    problems = manifest.verify_weights()
    if problems:
        # Nothing is fetched here. A short cache is named and the launch stops,
        # rather than a model loading whatever bytes happen to be on disk.
        raise KitUnavailable(
            f"{manifest.slug}: the weights under {cache} are not at their pins:\n  "
            + "\n  ".join(problems)
        )

    kit_mode = manifest.kit.get("mode", "fast")
    row = _ask_kit(python, kit_mode)

    worker_py = manifest.resolve(manifest.worker)
    protocol_py = (
        Path(__file__).resolve().parents[3] / "remote_resident" / "protocol.py"
    )

    argv = [
        python,
        "-m",
        "boltz2_opt.worker_launch",
        *row["opts"],
        "--",
        os.fspath(worker_py),
        "--socket",
        worker.socket_path,
        "--cache",
        os.fspath(cache),
        "--checkpoint",
        os.fspath(cache / "boltz2_conf.ckpt"),
        "--slug",
        manifest.slug,
    ]

    env: Dict[str, str] = dict(row["env"])
    env["MODEL_OPT"] = row["model_opt"]
    env["MODEL_OPT_STACK_KEY"] = row["stack_key"]
    env["BOLTZ_CACHE"] = os.fspath(cache)
    # The worker loads the wire protocol by path: it must not import
    # tooluniverse, whose dependencies are not in the model's environment.
    env["TOOLUNIVERSE_REMOTE_PROTOCOL"] = os.fspath(protocol_py)
    # Compiled Triton kernels keyed by torch+CUDA+arch. Persisting them across
    # worker lifetimes is what keeps a restart from recompiling: on this box the
    # first request after a cold cache costs ~28 s against ~6 s warm.
    jit_root = os.environ.get("MODEL_OPT_JIT_ROOT") or os.path.expanduser(
        "~/.cache/tooluniverse/boltz-jit"
    )
    os.makedirs(jit_root, exist_ok=True)
    env["MODEL_OPT_JIT_ROOT"] = jit_root
    return argv, env
