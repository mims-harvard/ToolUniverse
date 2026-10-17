"""Build the command line that starts esm_if1's resident worker.

``tooluniverse.remote_resident.kit_launch:build_command`` is not used, and the
reason is the same shape as ef2inv's and af3_torch's: a property of the kit, not
a preference of this provider.

**This kit has no mode variable to set, and setting one would break it.** The
shared probe reads ``modes.ENV`` and then ``_autoload.ENV``. ``esm_if1_opt``
has neither: there is no ``_autoload`` module at all, because the kit ships no
autoload ``.pth`` -- its own ``opt/pyproject.toml`` says so in as many words,
"this kit ships no autoload .pth (the mode is chosen on the command line; no
import is hooked), so the template builds plain setuptools wheels" -- and its
mode name is ``modes.ENV_MODE = "ESM_IF1_OPT"``, which is documented as "the
environment route of the mode (this command line and run.sh only)".

So the mode reaches the worker as ``--mode``, and ``ESM_IF1_OPT`` must be
**removed** from the child's environment rather than merely not set. That is
not caution, it is the kit's own rule: ``modes.resolve(cli_value, environ)``
raises ``ModeConflict`` -- a usage error -- when ``--mode`` and
``ESM_IF1_OPT`` name different modes, so an ``ESM_IF1_OPT=off`` inherited from
an operator's shell would make a worker launched with ``--mode fast`` exit on
its first statement. af3_jax taught this in its harsher form (a ``.pth`` whose
only job is to refuse an inherited variable); here the consequence is milder
and the fix is identical, because not setting a variable and removing one are
different operations and only the second is safe against an environment you
did not build.

**The list of names to strip is read from the kit, not copied.** ``esm_if1_opt
.stack`` carries ``MUST_BE_ABSENT_PREFIXES`` -- the mode variable, the reserved
``ESM_IF1_KIT`` prefix, and the TF32 / cuBLAS / loader switches
(``NVIDIA_TF32_OVERRIDE``, ``TORCH_ALLOW_TF32_CUBLAS_OVERRIDE``,
``CUBLAS_WORKSPACE_CONFIG``, ``TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD``) -- plus
``INTERPRETER_ENV`` (``PYTHONSAFEPATH``). The kit requires those absent from a
*stock* child; this is a *kit* child, so the kit would not require it of us.
We strip them anyway for the four numeric ones, because STOCK.md states
"Precision is PyTorch's defaults on every mode: fp32, matmul TF32 off" and an
inherited ``NVIDIA_TF32_OVERRIDE=1`` would move this provider's numbers
without moving anything it reports. The list is read by running four lines in
the model's interpreter (``stack`` imports neither torch nor esm, so this costs
~0.3 s and no CUDA context); ``_FALLBACK_PREFIXES`` is what a checkout the
probe cannot read would get, and it is the same list.

**Nothing else of the kit is asked for here, because there is nothing to ask.**
``modes.resolve(name)`` returns a mode *string*; there is no ``env`` mapping,
no ``exports``, and no ``Resolution`` object anywhere in this kit -- its
deployment variables live in ``configs/<card>.env``, shipped for h100, h200 and
a100 and not for this machine, and all three set the same four things. Those
four are set below, from the manifest, with ``configs/h100.env``'s own
derivations:

* ``MODEL_OPT``            -- the kit tree (``home.tree_home`` reads it)
* ``MODEL_OPT_STATE``      -- the state directory that holds ``torch_home/``
* ``PYTHONDONTWRITEBYTECODE`` -- the kit tree is read-only to us
* ``ESM_IF1_WEIGHTS``      -- the checkpoint file, from ``[weights]``

``MODEL_OPT_TARGET_GPU`` is deliberately NOT set. It is the GPU class the kit's
``check`` verb reports ``target=`` / ``match=`` against, "a report, never a
refusal", and every shipped config names a card this machine is not. A value
there would put a false card in a record nobody gates on, which is the worst
kind of harmless.

``OMP_NUM_THREADS`` is deliberately NOT set to 1, and that is the one place
this provider departs from the hazard list on purpose. The rule boltzgen
established is "a resident worker that has run any host-tensor work must not
let a library fork", and the cheap guarantee was to make the OpenMP pool not
exist. This provider runs on the CPU: the pool *is* the model. Nothing here
forks -- upstream's ESM-IF1 path constructs no DataLoader, no multiprocessing
pool and no subprocess (checked: ``esm/inverse_folding/`` and
``esm_if1_opt/batched.py`` between them import ``torch``, ``biotite``,
``numpy``, ``scipy`` and nothing that forks), and the worker's own
``num_workers`` is not a parameter because there is no loader to give it to.
The worker states the same thing in its docstring and sets
``torch.set_num_threads`` itself.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

from tooluniverse.remote_resident.kit_launch import KitUnavailable
from tooluniverse.remote_resident.setup import kit_checkout

# stack.MUST_BE_ABSENT_PREFIXES + stack.INTERPRETER_ENV of esm_if1_opt 0.4.2,
# used only when the probe below cannot run. Matched as prefixes, which is how
# the kit's own `opt_core.stock_proof.strip_env` matches them.
_FALLBACK_PREFIXES = (
    "ESM_IF1_OPT",
    "ESM_IF1_KIT",
    "NVIDIA_TF32_OVERRIDE",
    "TORCH_ALLOW_TF32_CUBLAS_OVERRIDE",
    "CUBLAS_WORKSPACE_CONFIG",
    "TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD",
    "PYTHONSAFEPATH",
)

# Four lines in the model's interpreter. `esm_if1_opt.stack` imports `os`,
# `sys`, `opt_core.gates` and `opt_core.home` -- no torch, no esm, no CUDA.
_PROBE = (
    "import json,sys\n"
    "from esm_if1_opt import stack\n"
    "sys.stdout.write('PREFIXES ' + json.dumps("
    "list(stack.MUST_BE_ABSENT_PREFIXES) + list(stack.INTERPRETER_ENV)) + chr(10))\n"
)

# Names an operator may supply that this provider passes straight through: the
# kit's own, from STOCK.md's Variables table. TORCH_HOME is here rather than
# derived because the kit documents it as the operator's to set, and the worker
# refuses by name if the checkpoint does not end up linked into whichever
# torch.hub cache it names -- so an operator pointing it somewhere odd gets a
# refusal, not a silent download of 1.7 GB.
PASS_THROUGH = ("TORCH_HOME", "MODEL_OPT_STATE")


def _strip_prefixes(python: str) -> List[str]:
    """The kit's own list of variables a child of it must not carry."""
    try:
        out = subprocess.run(  # noqa: S603 - the interpreter the manifest names
            [python, "-c", _PROBE],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return list(_FALLBACK_PREFIXES)
    for line in (out.stdout or "").splitlines():
        if line.startswith("PREFIXES "):
            try:
                names = json.loads(line[len("PREFIXES ") :])
            except ValueError:
                break
            if names:
                return [str(n) for n in names]
    return list(_FALLBACK_PREFIXES)


def build_command(worker) -> Tuple[List[str], Dict[str, str]]:
    """``(argv, environment)`` for ``worker``. The supervisor calls this."""
    manifest = worker.manifest

    python = manifest.python_executable()
    if not Path(python).is_file():
        raise KitUnavailable(
            f"[env] python points at {python}, which is not a file -- it must be "
            f"the interpreter of {manifest.slug}'s own environment "
            f"(set TOOLUNIVERSE_ESM_IF1_PYTHON)"
        )

    root = manifest.weights_root()
    if manifest.weights and root is None:
        raise KitUnavailable(f"no weights directory: set {manifest.weights_root_env}")
    problems = manifest.verify_weights()
    if problems:
        # Nothing is fetched here. A short or altered checkpoint is named and
        # the launch stops, rather than a model loading whatever is on disk --
        # which is the failure this project paid a month for.
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
    # The kit tree the package resolves its stock/ and opt/ from
    # (`home.tree_home(__file__, require=("stock/src/.../sample_sequences.py",
    # "opt"))`, else MODEL_OPT). The package is installed editable from the
    # checkout so it would find this itself; stating it keeps a non-editable
    # install working, and run.sh exports it on every command.
    env["MODEL_OPT"] = os.fspath(kit_home)
    # configs/<card>.env's own value, under our cache root rather than the
    # kit's default so a provider's state is where this project keeps state.
    # stack.torch_home() derives <state>/torch_home from it when TORCH_HOME is
    # unset, which is what the kit's own configs do.
    env["MODEL_OPT_STATE"] = os.path.expanduser(
        f"~/.cache/tooluniverse/{manifest.slug}-state"
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # The kit's own variable for "a local copy of the checkpoint": it names the
    # FILE, not a directory (STOCK.md, Variables). `stack.stage_torch_home()`
    # in the worker links torch.hub's cache entry to it, so upstream's loader
    # reads the file this provider just verified and downloads nothing.
    if root is not None:
        env["ESM_IF1_WEIGHTS"] = os.fspath(root / "esm_if1_gvp4_t16_142M_UR50.pt")
    for name in PASS_THROUGH:
        if os.environ.get(name):
            env[name] = os.environ[name]

    off = manifest.kit.get("levers_off") or ()
    if off:
        # Declared impossible in provider.toml: nothing in esm_if1_opt reads
        # MODEL_OPT_LEVERS_OFF. This branch exists so that a kit that grows the
        # door is served without a code change, and so that a reviewer can see
        # that the manifest's empty list is a statement rather than an omission.
        env["MODEL_OPT_LEVERS_OFF"] = ",".join(str(x) for x in off)
    for key, value in (manifest.kit.get("env") or {}).items():
        env[str(key)] = str(value)

    # Both shared files are found by path: this package is not importable from
    # the model's environment, and must not be.
    env["TOOLUNIVERSE_REMOTE_PROTOCOL"] = os.fspath(shared / "protocol.py")
    env["TOOLUNIVERSE_REMOTE_WORKER_BASE"] = os.fspath(shared / "worker_base.py")

    # A REMOVAL IS A None VALUE, not a pruned copy. `supervisor.child_env`
    # builds the child's environment from `os.environ` and then applies this
    # mapping over it, so a name merely left out of a copy comes straight back.
    # This launcher used to prune `dict(os.environ)` and its strip did nothing:
    # measured, with the stray variable exported and the worker exiting 3 at the
    # very refusal the strip existed to prevent. STANDARD section 12 has the
    # general form -- a launcher's intent has to be expressed in something the
    # executor acts on.
    # An ESM_IF1_OPT inherited from an operator's shell is a ModeConflict
    # against --mode on the worker's first statement.
    removals = {
        name: None
        for prefix in _strip_prefixes(python)
        for name in os.environ
        if name.startswith(prefix) and name not in env
    }
    return argv, {**removals, **env}
