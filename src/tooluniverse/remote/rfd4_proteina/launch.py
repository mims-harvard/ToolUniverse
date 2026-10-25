"""Build the command line that starts RFD4-Proteina's resident worker.

This is the sixteenth provider in ``remote/`` that does not use
``tooluniverse.remote_resident.kit_launch:build_command``, and the first whose
reason is not a property of a kit: **there is no kit**. The other fifteen all
pin a commit of ``anthropics/uplifting-biomolecular-modeling`` and differ only
in how that kit engages -- a ``.pth`` autoload, a ``worker_launch`` hook, a
replacement entry script, a differently-spelled mode variable, an explicit
in-process API. RFD4-Proteina has none of those because nothing wraps it.
Upstream publishes the inference runtime itself as ``rfd4-proteina`` on PyPI.

``kit_launch.build_command`` would refuse this provider on its first line of
real work: it resolves ``kit_checkout(manifest)`` and then reads the kit's mode
variable out of ``<package>.modes.ENV`` or ``<package>._autoload.ENV``. With no
``[kit]`` table there is no checkout to resolve and no package to read, and the
refusal it would raise ("exposes no modes.ENV, so there is no way to engage it
in our own process") would be describing a kit that does not exist. So the
launch is here, and it is the shortest one in the tree, because without a kit
there is nothing to arm: the interpreter, the weights pin and the socket.

**What this provider engages instead.** The levers a kit would supply are
already configuration upstream owns, in ``configs/inference.yaml``:

* ``inference_backend: native | bioir`` -- BioIR is NVIDIA's inference runtime,
  and under it ``bioir.cuda_graph`` captures the trunk and replays it. That is
  the same mechanism the standard's section 3 cites for Boltz-2, and it is
  per-PROCESS, which is the whole argument for holding this model.
* ``compile_lengths`` -- a list of token buckets, each compiled the first time
  it is touched.

Both are chosen per request by the worker from the caller's arguments, not
exported here, because they are config keys rather than environment variables
and a worker engages them by composing a config. Setting a variable for them
would be a claim that something reads it.

**What is NOT set here, and why.**

* No ``MODEL_OPT`` / ``*_OPT`` mode variable: there is no kit to put in a mode.
* No ``MODEL_OPT_LEVERS_OFF``: same.
* No ``TRITON_PTXAS_PATH``: the siblings that set it do so because triton
  3.4.0's bundled ptxas is CUDA 12.8 and has no ``sm_121a``. This stack is
  torch 2.14.1+cu132, whose triton ships a CUDA 13 ptxas that knows the card.
* No ``DATA_PATH``: upstream's config defaults ``ckpt_path`` and
  ``autoencoder_ckpt_path`` under ``${oc.env:DATA_PATH}``, but this provider
  loads through ``hf_ckpt_path``/``hf_ckpt_revision``, which override both. The
  Hub cache is pointed at by ``HF_HOME``, set below from the weights root, so
  the matched pair lands where ``tu remote setup`` verified it rather than in
  whatever ``~/.cache`` the serving user happens to have.
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
            f"(set TOOLUNIVERSE_RFD4_PROTEINA_PYTHON)"
        )

    root = manifest.weights_root()
    if manifest.weights and root is None:
        raise KitUnavailable(f"no weights directory: set {manifest.weights_root_env}")

    problems = manifest.verify_weights()
    if problems:
        # Nothing is fetched here. The flow model and the autoencoder are a
        # matched pair -- upstream: mixing one release's flow model with
        # another's autoencoder "produces nonsense rather than an error" --
        # so a file that is not at its pin is named and the launch stops,
        # rather than a model loading whatever is on disk and designing from a
        # latent space it was not trained in.
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
        # The Hub cache, so `from_pretrained` reads the bundle `tu remote setup`
        # verified instead of re-resolving one into the serving user's
        # ~/.cache. HF_HUB_OFFLINE is deliberately NOT set: the revision is
        # pinned, so a cache miss should fetch that exact commit rather than
        # fail, and `setup` is what guarantees there is no miss.
        env["HF_HOME"] = os.fspath(root)

    # Inductor's cache, so a length bucket compiled by one worker is not
    # recompiled by the next. The siblings export MODEL_OPT_JIT_ROOT because a
    # kit reads it; nothing here does, so this is torch's own variable.
    jit_root = os.environ.get("TORCHINDUCTOR_CACHE_DIR") or os.path.expanduser(
        f"~/.cache/tooluniverse/{manifest.slug}-inductor"
    )
    os.makedirs(jit_root, exist_ok=True)
    env["TORCHINDUCTOR_CACHE_DIR"] = jit_root

    popen_env = dict(os.environ)
    popen_env.update(env)
    return argv, popen_env
