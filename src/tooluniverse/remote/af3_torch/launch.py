"""Build the command line that starts AF3-torch's resident worker.

This is the one provider in ``remote/`` that does not use
``tooluniverse.remote_resident.kit_launch:build_command``, and the reason is
worth stating precisely, because it is a property of the kit rather than a
preference of this provider.

``kit_launch``'s autoload path ends with ``env[mode_env] = mode``. For the
thirty kits that activate through a ``.pth`` that is the whole mechanism: the
hook waits for the model package's import and patches it in place. ``af3_torch``
installs the same shaped ``.pth`` and then does the opposite with it. From
``af3_torch_opt/_autoload.py``:

    On this model the hook applies nothing: the levers are arguments of the
    kit's own ``build_model`` in a model process the wrapper launches (cli.py /
    forward.py), not an in-process patch of an import. ... the hook cannot
    apply that mode in this process, so it refuses: the ``NOT ACTIVE`` line and
    exit 3 ... at the first import (a ``find_spec`` probe of a trigger counts).

The triggers are ``xfold`` and ``af3_torch_api``, and the resident worker must
import both to hold the model at all. So setting ``AF3_TORCH_OPT`` in the
worker's environment does not merely fail to engage the kit -- it terminates
the worker with ``os._exit(3)`` before it can bind its socket. The kit's own
model process avoids this the same way this function does: ``forward.py`` says
"Runs with no AF3_TORCH_OPT* variable in its environment
(stack.model_process_env)", and that function strips every name under the
``AF3_TORCH_OPT`` prefix.

Two smaller incompatibilities point the same way and are recorded in
``provider.toml``: the kit spells its mode variable ``ENV_MODE`` rather than
``ENV``, so the probe finds no name to set; and ``modes.resolve(mode)`` returns
the kit's lever composition, which carries no ``env`` or ``exports`` key,
because this kit keeps the child's environment in ``stack.model_process_env()``
instead.

**Still required, re-checked rather than assumed.** After the shared layer's
two reporting fixes (a fetch exiting 3 reports REFUSED; ``[kit] install`` and
``[weights] fetch`` run under ``bash -c``), ``kit_launch.build_command`` still
ends its autoload path with ``env[mode_env] = manifest.kit.get("mode", "fast")``
unconditionally, and ``_row_of`` still reads only ``env`` / ``exports``. So this
module cannot be dropped. ``provider.toml``'s header spells out the three
changes the shared launcher would need -- and that fixing only the probe's
``ENV_MODE`` blindness, without making that assignment conditional, would be
strictly worse here: it would find the name and use it to kill the worker at
``import xfold``, turning a clean ``KitUnavailable`` before launch into a death
after the supervisor has committed to the process.

This function was exercised on the host without starting a model: it built the
argv below, verified the weights against their pins, and -- with
``AF3_TORCH_OPT=fast`` deliberately exported in the parent -- produced a child
environment containing no ``AF3_TORCH_OPT*`` name at all, which is the one thing
it exists to guarantee.

**Where the kit is asked for its own parameters.** Not here. A hard-coded copy
of a kit's lever table drifts the first time the kit moves, so it must be read
from the kit -- but unlike every other provider, this one does not need a
subprocess probe to do it: ``af3_torch_opt`` imports neither torch nor jax, and
the worker already runs in the interpreter where it is installed. The worker
therefore calls ``modes.resolve()`` and ``stack.model_process_env()`` itself,
in process, at start. This function passes the mode NAME and nothing else about
it.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Tuple

from tooluniverse.remote_resident.kit_launch import KitUnavailable
from tooluniverse.remote_resident.setup import kit_checkout

# Names the operator supplies that this provider passes straight through to the
# worker. They are the kit's own (STOCK.md, section Variables) and they are
# per-machine paths, so nothing here invents a default for them; the worker
# refuses by name when one it needs is missing.
PASS_THROUGH = (
    "AF3_TORCH_JAX_PY",  # the featurisation / writer interpreter (CPU only)
    "AF3_TORCH_JAX_REPO",  # the sokrypton/alphafold3 fork checkout
    "AF3_TORCH_GPU",  # the target card word; the kit only reads it as a fallback
)


def build_command(worker) -> Tuple[List[str], Dict[str, str]]:
    """``(argv, environment)`` for ``worker``. The supervisor calls this."""
    manifest = worker.manifest

    python = manifest.python_executable()
    if not Path(python).is_file():
        raise KitUnavailable(
            f"[env] python points at {python}, which is not a file -- it must be "
            f"the interpreter of {manifest.slug}'s own environment "
            f"(set TOOLUNIVERSE_AF3_TORCH_PYTHON)"
        )

    root = manifest.weights_root()
    if manifest.weights and root is None:
        raise KitUnavailable(f"no weights directory: set {manifest.weights_root_env}")
    problems = manifest.verify_weights()
    if problems:
        # Nothing is fetched here. A short or altered parameter file is named
        # and the launch stops, rather than a model loading whatever is there.
        # For this provider that matters more than usual: the file is produced
        # by a converter rather than downloaded, so "plausible but wrong" is a
        # shape it can actually take.
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
    # The kit's tree, for stack.home(). The package is installed editable from
    # the checkout so it would derive this itself; stating it keeps a
    # non-editable install working too, which is what AF3_TORCH_OPT_HOME is for.
    env["MODEL_OPT"] = os.fspath(kit_home)
    # The kit's own name for the interpreter this worker runs on. It reads it
    # through stack.torch_python() and its pin check asks it for torch and
    # triton; `[env] python` already says which interpreter that is.
    env["AF3_TORCH_PY"] = python
    if root is not None and manifest.weights_root_env:
        env[manifest.weights_root_env] = os.fspath(root)
    for name in PASS_THROUGH:
        if os.environ.get(name):
            env[name] = os.environ[name]

    off = manifest.kit.get("levers_off") or ()
    if off:
        env["MODEL_OPT_LEVERS_OFF"] = ",".join(str(x) for x in off)

    # DELIBERATELY NOT SET: AF3_TORCH_OPT. See this module's docstring. The
    # mode reaches the worker as `--mode` and is resolved to levers in process.

    # Both shared files are found by path: this package is not importable from
    # the model's environment, and must not be.
    env["TOOLUNIVERSE_REMOTE_PROTOCOL"] = os.fspath(shared / "protocol.py")
    env["TOOLUNIVERSE_REMOTE_WORKER_BASE"] = os.fspath(shared / "worker_base.py")

    # Compiled kernels keyed by torch + CUDA + arch. Keeping them across worker
    # lifetimes is what stops a restart recompiling; under `fast` this kit
    # torch.compile's the sampler as well as building Triton kernels, and its
    # own README puts a cold first run at a minute to ninety seconds.
    jit_root = os.environ.get("MODEL_OPT_JIT_ROOT") or os.path.expanduser(
        f"~/.cache/tooluniverse/{manifest.slug}-jit"
    )
    os.makedirs(jit_root, exist_ok=True)
    env["MODEL_OPT_JIT_ROOT"] = jit_root

    # A REMOVAL IS A None VALUE, not a pruned copy. `supervisor.child_env`
    # builds the child's environment from `os.environ` and then applies this
    # mapping over it, so a name merely left out of a copy comes straight back.
    # This launcher used to prune `dict(os.environ)` and its strip did nothing:
    # measured, with the stray variable exported and the worker exiting 3 at the
    # very refusal the strip existed to prevent. STANDARD section 12 has the
    # general form -- a launcher's intent has to be expressed in something the
    # executor acts on.
    # An AF3_TORCH_OPT inherited from the operator's shell would reach the
    # worker and kill it at `import xfold`, and it is exactly the variable an
    # operator who has been running `run.sh` by hand is likely to have set.
    popen_env = {name: None for name in os.environ if name.startswith("AF3_TORCH_OPT")}
    popen_env.update(env)
    return argv, popen_env
