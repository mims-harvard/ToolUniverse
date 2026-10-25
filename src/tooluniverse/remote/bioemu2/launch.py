"""Build the command line that starts BioEmu-2's resident worker.

Like ``remote/rfd4_proteina/launch.py``, this exists because there is **no
optimization kit**: upstream publishes the inference runtime itself
(``bioemu2`` on PyPI), so ``tooluniverse.remote_resident.kit_launch`` has
nothing to resolve. Its first real step is ``kit_checkout(manifest)`` followed
by reading the kit's mode variable out of ``<package>.modes.ENV``, and with no
``[kit]`` table there is neither a checkout nor a package; the refusal it
would raise would be describing a kit that does not exist.

**What this provider's levers are instead.** The things a kit would add are
already arguments upstream owns, and they are chosen per request or at load:
``precision`` for the trunk, ``matmul_precision`` for the denoiser,
``batch_size``, ``num_steps``, ``compile_denoiser``, and the memory-saving
``trimul_variant``/``opm_variant`` kernels that live in the checkpoint's own
``config.yaml``. None of them is an environment variable, so none is exported
here. Setting one would be a claim that something reads it.

**What IS set here.**

* ``HF_HOME`` -- the checkpoint is loaded by name (``bioemu2-preview``) from
  the Hub, so what must be present is the pinned revision's snapshot. Pointing
  it at the weights root is what makes the worker read the bundle that
  ``tu remote setup`` verified rather than re-resolving one into whatever
  ``~/.cache`` the serving user happens to have.
* ``BIOEMU2_MSA_CACHE`` -- upstream's A3M cache. It defaults to
  ``~/.cache/bioemu2/colabfold_msa``; pinning it under the weights root keeps
  alignments fetched by one worker available to the next, which is the
  difference between one ColabFold query per system and one per process.

**What is NOT set here, and why.**

* No ``*_OPT`` mode variable and no ``MODEL_OPT_LEVERS_OFF``: there is no kit
  to put in a mode.
* No ``TRITON_PTXAS_PATH``: the siblings that set it do so because triton
  3.4.0's bundled ptxas is CUDA 12.8 and has no ``sm_121a``. This stack is
  torch 2.13.0+cu130, and cuEquivariance ships an ``sm_121a`` cubin in
  ``libcue_ops.so`` -- checked with ``cuobjdump`` rather than assumed.
* No ``HF_HUB_OFFLINE``: the revision is pinned, so a cache miss should fetch
  that exact commit rather than fail, and ``setup`` is what guarantees there
  is no miss.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Tuple

from tooluniverse.remote_resident.kit_launch import KitUnavailable


def build_command(worker) -> Tuple[List[str], Dict[str, str]]:
    """``(argv, environment)`` for ``worker``. The supervisor calls this."""
    manifest = worker.manifest

    python = manifest.python_executable()
    if not Path(python).is_file():
        raise KitUnavailable(
            f"[env] python points at {python}, which is not a file -- it must be "
            f"the interpreter of {manifest.slug}'s own environment "
            f"(set TOOLUNIVERSE_BIOEMU2_PYTHON)"
        )

    root = manifest.weights_root()
    if manifest.weights and root is None:
        raise KitUnavailable(f"no weights directory: set {manifest.weights_root_env}")

    problems = manifest.verify_weights()
    if problems:
        # Nothing is fetched here. The checkpoint carries its own
        # ``config.yaml``, and ``load_model()`` instantiates that config with
        # hydra -- upstream's own warning is that "config-controlled targets
        # can execute arbitrary code". A config that is not at its pin is
        # therefore a refusal, not something to load and hope about.
        raise KitUnavailable(
            f"{manifest.slug}: the weights under {root} are not at their pins:\n  "
            + "\n  ".join(problems)
            + f"\n  run `tu remote setup {manifest.slug}` after removing the named file"
        )

    fields = {
        "socket": worker.socket_path,
        "slug": manifest.slug,
        "weights_root": os.fspath(root) if root else "",
        "python": python,
    }
    worker_py = manifest.resolve(manifest.worker)
    argv = [python, os.fspath(worker_py)] + [
        str(a).format(**fields) for a in (manifest.worker_args or ())
    ]

    shared = (
        Path(
            __import__(
                "tooluniverse.remote_resident.worker_base", fromlist=["worker_base"]
            ).__file__
        )
        .resolve()
        .parent
    )

    env: Dict[str, str] = {}

    # Both shared files are found by path: this package is not importable from
    # the model's environment, and must not be.
    env["TOOLUNIVERSE_REMOTE_PROTOCOL"] = os.fspath(shared / "protocol.py")
    env["TOOLUNIVERSE_REMOTE_WORKER_BASE"] = os.fspath(shared / "worker_base.py")

    if root is not None:
        env["HF_HOME"] = os.fspath(root)
        msa_cache = Path(root) / "colabfold_msa"
        msa_cache.mkdir(parents=True, exist_ok=True)
        env["BIOEMU2_MSA_CACHE"] = os.fspath(msa_cache)

    return argv, {**os.environ, **env}
