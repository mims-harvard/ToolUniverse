"""Build the command line that starts Carbon-X's resident worker.

Like ``remote/rfd4_proteina/launch.py`` and ``remote/bioemu2/launch.py``, this
exists because there is **no optimization kit**:
``tooluniverse.remote_resident.kit_launch`` would refuse this provider while
describing a checkout and a mode variable that do not exist. What it does
instead is the one thing this provider needs and no sibling does -- check the
*engine*, not only the weights.

WHY THE ENGINE IS CHECKED HERE AND NOT BY ``[weights] files``. Carbon-X is
served by llama.cpp binaries, and ``[[weights.files]]`` is a single list that
cannot vary by architecture: the aarch64 tarball ships 16 loadable files and
the x86_64 one 22, with different digests and different names. Listing either
set would make the manifest refuse the other machine. So the GGUF -- which is
identical everywhere -- is pinned in the manifest, and the engine is pinned in
``environment/llamacpp-b11742.pins``, one line per file per architecture,
checked below against the host's own ``uname -m``.

AND IT IS CHECKED AT ALL BECAUSE THESE FILES ARE EXECUTED. A weights file that
has drifted produces a wrong answer; a drifted ``libggml-cuda.so`` runs
whatever it now contains. The sibling that pins a hydra ``config.yaml``
because ``instantiate()`` can import and call a ``_target_`` is making the
same argument about a much smaller attack surface.

**What IS set here.** ``LD_LIBRARY_PATH``, so the backends ggml dlopens come
from beside the pinned ``llama-server`` rather than from a system path where a
different build might win. Nothing else: the sampling defaults, the context
size and the slot count are command-line arguments of the engine, and the
worker passes them explicitly rather than through the environment.

**What is NOT set here, and why.**

* No ``CUDA_VISIBLE_DEVICES``: the supervisor owns device placement.
* No ``LLAMA_*`` tuning variables. llama.cpp reads very few, and every lever
  that matters here -- ``-ngl``, ``-c``, ``-np``, the sampler -- is an
  argument the worker sets where a reader can see it.
* No ``HF_HOME`` or ``HF_TOKEN``: nothing is resolved from the Hub at run
  time. The GGUF is a path, and ``tu remote setup`` is what put it there.
"""

from __future__ import annotations

import hashlib
import os
import platform
from pathlib import Path
from typing import Dict, List, Tuple

from tooluniverse.remote_resident.kit_launch import KitUnavailable

ENGINE_BUILD = "b11742"
ENGINE_DIRNAME = f"llama.cpp-{ENGINE_BUILD}"
PINS = Path(__file__).resolve().parent / "environment" / f"llamacpp-{ENGINE_BUILD}.pins"


def _engine_problems(engine_dir: Path) -> List[str]:
    """Every pinned engine file that is absent, resized or off its digest.

    The pin file is ``arch name size sha256`` per line. A host architecture
    with no lines at all is itself a refusal: it means this provider has never
    been fetched for that machine, and guessing which tarball to trust is
    exactly the decision a pin exists to remove.
    """
    arch = platform.machine()
    wanted = []
    for line in PINS.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        row_arch, name, size, digest = line.split()
        if row_arch == arch:
            wanted.append((name, int(size), digest))
    if not wanted:
        return [
            f"{PINS.name} pins no files for {arch}; this provider has been "
            f"measured and pinned on aarch64 and x86_64 Linux only"
        ]

    problems = []
    for name, size, digest in wanted:
        path = engine_dir / name
        if not path.is_file():
            problems.append(f"{name}: absent")
            continue
        actual = path.stat().st_size
        if actual != size:
            problems.append(f"{name}: {actual} bytes, the pin is {size}")
            continue
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 22), b""):
                h.update(chunk)
        if h.hexdigest() != digest:
            problems.append(
                f"{name}: sha256 {h.hexdigest()[:16]}… , the pin is {digest[:16]}…"
            )
    return problems


def build_command(worker) -> Tuple[List[str], Dict[str, str]]:
    """``(argv, environment)`` for ``worker``. The supervisor calls this."""
    manifest = worker.manifest

    python = manifest.python_executable()
    if not Path(python).is_file():
        raise KitUnavailable(
            f"[env] python points at {python}, which is not a file -- it must be "
            f"the interpreter of {manifest.slug}'s own environment "
            f"(set TOOLUNIVERSE_CARBONX_PYTHON)"
        )

    root = manifest.weights_root()
    if manifest.weights and root is None:
        raise KitUnavailable(f"no weights directory: set {manifest.weights_root_env}")

    problems = manifest.verify_weights()
    if problems:
        raise KitUnavailable(
            f"{manifest.slug}: the weights under {root} are not at their pins:\n  "
            + "\n  ".join(problems)
            + f"\n  run `tu remote setup {manifest.slug}` after removing the named file"
        )

    engine_dir = Path(root) / ENGINE_DIRNAME
    engine_problems = _engine_problems(engine_dir)
    if engine_problems:
        raise KitUnavailable(
            f"{manifest.slug}: the llama.cpp {ENGINE_BUILD} engine under "
            f"{engine_dir} is not at its pins:\n  "
            + "\n  ".join(engine_problems)
            + f"\n  run `tu remote setup {manifest.slug}` after removing that "
            f"directory. {ENGINE_BUILD} is not a preference: it is the first "
            f"release that knows Carbon-X's HybridDNATokenizer, and an older "
            f"one loads the same file and tokenizes DNA wrongly without saying so"
        )

    fields = {
        "socket": worker.socket_path,
        "slug": manifest.slug,
        "weights_root": os.fspath(root) if root else "",
        "python": python,
        "gguf": os.fspath(Path(root) / "carbon-x-q8_0.gguf"),
        "engine": os.fspath(engine_dir),
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
    # the engine's environment, and must not be.
    env["TOOLUNIVERSE_REMOTE_PROTOCOL"] = os.fspath(shared / "protocol.py")
    env["TOOLUNIVERSE_REMOTE_WORKER_BASE"] = os.fspath(shared / "worker_base.py")

    existing = os.environ.get("LD_LIBRARY_PATH")
    env["LD_LIBRARY_PATH"] = os.pathsep.join(
        [os.fspath(engine_dir)] + ([existing] if existing else [])
    )

    return argv, {**os.environ, **env}
