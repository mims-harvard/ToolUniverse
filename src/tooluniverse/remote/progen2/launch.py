"""Build the command line that starts progen2's resident worker.

This is the third provider in ``remote/`` that does not use
``tooluniverse.remote_resident.kit_launch:build_command`` (af3_torch and ef2inv
are the first two), and as there the reason is a property of the kit rather than
a preference of this provider. Here it is the sharpest of the three:

**This kit has no mode variable, and no autoload ``.pth`` either.** The shared
probe reads ``<pkg>.modes.ENV`` and then ``<pkg>._autoload.ENV``; ``progen2_opt``
has no ``ENV`` in either place, and no ``_autoload`` module at all. So
``kit_launch.build_command`` reaches

    if not mode_env:
        raise KitUnavailable(
            f"{package} exposes no modes.ENV, so there is no way to engage it "
            f"in our own process; if its form is a replacement entry script "
            f'(ChromBPNet is), the provider belongs in mode = "subprocess"')

and refuses the launch. **That advice is wrong for this kit**, which is why this
file exists rather than a ``mode = "subprocess"`` manifest: progen2's form is not
a replacement entry script, it is an explicit in-process API. Its own README:
"Programmatic use, one size per process: ``from progen2_opt.api import load,
sample, score, close``". Its ``STOCK.md`` states the absence as a design rule --
"Kit-declared variables only; no variable selects a mode or a size (``--mode``,
``--model`` do) and nothing is configured per card" -- and ``CHANGES.md`` repeats
it: "no environment variable changes lever behaviour". A worker engages a mode by
CALLING something, so there is nothing for a launcher to export.

That makes this a sixth activation shape for the standard's taxonomy, after
``.pth`` autoload, ``worker_launch``, replacement entry script, autoload-plus-
patched-tree, and ef2inv/af3_torch's differently-spelled variable. It is reported
as a gap in the shared probe rather than patched around silently: the probe could
reasonably grow a third place to look and a way to say "this kit engages by call",
and until it does, a kit of this shape needs a provider-local launcher.

**What this provider actually engages: nothing.** ``[kit] mode = "off"`` (see
provider.toml for the two independent reasons), so no kit module is imported into
the worker at all and the worker builds stock ProGen2 itself. The kit checkout
still matters for three things, which is why it is located here and passed on:

* ``stock/src/progen2`` holds the pinned upstream checkout -- ``sample.py``,
  ``likelihood.py``, ``models/progen/modeling_progen.py`` and ``tokenizer.json``.
  Nothing of upstream is pip-installed anywhere (``STOCK.md``: "no package
  metadata ... the commit is the pin"), so that directory IS the model code.
* ``stock/PINS.json`` is where the weights' digests and the model's own config
  fields come from.
* the four ``PROGEN2_*`` deployment variables are the kit's own names for paths,
  and are set below from the manifest rather than left to an operator's shell.

**What is NOT set here, and why each absence is deliberate.**

* No mode variable, per the above.
* No ``MODEL_OPT_LEVERS_OFF``: the string does not appear anywhere in this kit
  (``dependencies = []``, nothing from ``common/opt_core`` is importable), and
  ``modes.py`` says "One composition per mode: no lever inside it". Setting it
  would do nothing, which is worse than saying so.
* No ``TRITON_PTXAS_PATH`` / ``TRITON_PTXAS-BLACKWELL_PATH``. e1, atlasfold and
  their siblings set those because triton 3.4.0's bundled ptxas is CUDA 12.8 and
  has no ``sm_121a``. **There is no Triton in this environment**: no cp39 aarch64
  build of triton 3.4.0 exists on any index, and neither stock ProGen2 nor the kit
  calls ``torch.compile`` or carries a ``@triton.jit`` (environment/requirements.lock
  DEVIATION 2). Pointing a variable at a compiler nothing will invoke would be a
  claim that something compiles here.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Tuple

from tooluniverse.remote_resident.kit_launch import KitUnavailable
from tooluniverse.remote_resident.setup import kit_checkout


def build_command(worker) -> Tuple[List[str], Dict[str, str]]:
    """``(argv, environment)`` for ``worker``. The supervisor calls this."""
    manifest = worker.manifest

    python = manifest.python_executable()
    if not Path(python).is_file():
        raise KitUnavailable(
            f"[env] python points at {python}, which is not a file -- it must be "
            f"the interpreter of {manifest.slug}'s own environment "
            f"(set TOOLUNIVERSE_PROGEN2_PYTHON)"
        )

    root = manifest.weights_root()
    if manifest.weights and root is None:
        raise KitUnavailable(f"no weights directory: set {manifest.weights_root_env}")
    problems = manifest.verify_weights()
    if problems:
        # Nothing is fetched here. A short or altered checkpoint is named and the
        # launch stops, rather than a model loading whatever is on disk. ProGen2
        # is the standard's own cautionary shape in miniature: upstream's README
        # downloads a tarball and unpacks it in place, so a truncated transfer
        # and a corrupt file look alike on the filesystem.
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
    # The pinned upstream checkout, which under mode = "off" is the whole model:
    # there is no installed `progen` package anywhere, so this directory on
    # sys.path is how `models.progen.modeling_progen` and `tokenizer.json` are
    # found. Named here rather than derived in the worker because the kit lets a
    # deployment move it (PROGEN2_STOCK_DIR) and the digest check in
    # stock/check_pins.py is written against whatever that names.
    stock_dir = kit_home / "stock" / "src" / "progen2"
    if not (stock_dir / "tokenizer.json").is_file():
        raise KitUnavailable(
            f"{manifest.slug}: the pinned stock checkout is not at {stock_dir} "
            f"(no tokenizer.json) -- run `tu remote setup {manifest.slug} --only kit`"
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
        "stock_dir": os.fspath(stock_dir),
        "weights_root": os.fspath(root) if root else "",
        "python": python,
    }
    worker_py = manifest.resolve(manifest.worker)
    argv = [python, os.fspath(worker_py)] + [
        str(a).format(**fields) for a in (manifest.worker_args or ())
    ]

    env: Dict[str, str] = {}
    # The kit tree, by the shared core's name for it. This kit resolves its own
    # directories from the installed package's location and would derive this
    # itself; stating it keeps a non-editable install working and matches what
    # every other provider's launcher exports.
    env["MODEL_OPT"] = os.fspath(kit_home)
    # The kit's four declared deployment variables (STOCK.md, Variables). All
    # four are PATHS -- none of them selects a mode or a size.
    if root is not None and manifest.weights_root_env:
        env[manifest.weights_root_env] = os.fspath(root)
    env["PROGEN2_STOCK_DIR"] = os.fspath(stock_dir)
    # The interpreter the kit would spawn stock processes with. This provider
    # spawns none -- the worker is in-process -- but a kit module that reads it
    # (stack.python()) must not fall back to `python` on PATH, which in a
    # ToolUniverse deployment is a different interpreter entirely.
    env["PROGEN2_PYTHON"] = python
    # The stock run directory. The kit builds a tree of symlinks here when
    # anything asks it to, and `_own_run_root` refuses a shared temp path it does
    # not own, printing a refusal and falling back to a private mkdtemp. Giving
    # it a per-slug directory under the user's cache makes that decision once,
    # predictably, instead of per process in $TMPDIR.
    run_dir = os.environ.get("PROGEN2_RUN_DIR") or os.path.expanduser(
        f"~/.cache/tooluniverse/{manifest.slug}-run"
    )
    os.makedirs(run_dir, mode=0o700, exist_ok=True)
    env["PROGEN2_RUN_DIR"] = run_dir
    # run.sh exports this itself: the kit tree and the stock checkout are
    # third-party code we execute and whose bytes `setup`'s kit_modified check
    # compares, so nothing of ours writes a __pycache__ into them.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # The stock scripts' own set_env() sets this before anything else
    # (sample.py / likelihood.py L35-36); the worker does not run those scripts,
    # so it is set here -- and it has to be in the environment before tokenizers
    # is imported, not after.
    env["TOKENIZERS_PARALLELISM"] = "false"
    # Nothing is fetched at run time: the two weight files were verified above
    # and the tokenizer is a file in the pinned checkout. ProGen2 touches no hub,
    # but transformers 4.16.2 is in this environment and will try one if asked.
    env.setdefault("HF_HUB_OFFLINE", "1")
    env.setdefault("TRANSFORMERS_OFFLINE", "1")

    for key, value in (manifest.kit.get("env") or {}).items():
        env[str(key)] = str(value)

    # Both shared files are found by path: this package is not importable from
    # the model's environment, and must not be.
    env["TOOLUNIVERSE_REMOTE_PROTOCOL"] = os.fspath(shared / "protocol.py")
    env["TOOLUNIVERSE_REMOTE_WORKER_BASE"] = os.fspath(shared / "worker_base.py")

    # Every other provider keeps compiled kernels across worker lifetimes here.
    # This one compiles nothing -- the kit's own CHANGES.md: "nothing is compiled
    # at install or run time", and there is no Triton or Inductor in the
    # environment to compile with. The directory is still made and exported, so
    # that a reader comparing providers sees the same name and finds it empty
    # rather than wondering whether it was forgotten.
    jit_root = os.environ.get("MODEL_OPT_JIT_ROOT") or os.path.expanduser(
        f"~/.cache/tooluniverse/{manifest.slug}-jit"
    )
    os.makedirs(jit_root, exist_ok=True)
    env["MODEL_OPT_JIT_ROOT"] = jit_root

    popen_env = dict(os.environ)
    popen_env.update(env)
    return argv, popen_env
