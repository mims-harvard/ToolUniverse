"""How to run a command in the model's environment: a venv, a container, or an image.

The optimization kits offer the same stack three ways — a Docker image, an
Apptainer `.sif` converted from it, or a Python venv at the pinned versions —
and note that steps 2 to 4 are identical whichever you pick. The same holds
here: a resident worker is the same script, holding the same model, answering
on the same socket. Only the argv that starts it differs, so only that is
abstracted.

**Paths are mapped identity.** Every bind mounts a host path at the same path
inside, `-v /p:/p`. The alternative — a private layout inside the container —
would need translation for the socket, the weights, the worker script, the
shared protocol file, and every per-request output directory the caller names,
in both directions, forever. Identity mapping costs one convention and removes
all of it: a path means the same thing on both sides of the boundary.

**Containers run as the calling user.** The kits' own recipes say "Containers
run as root. The Docker and Apptainer recipes do not create an unprivileged
user", which for a model writing predictions into a bind-mounted directory
means root-owned output on the host. Docker is given `--user`; Apptainer runs
as the caller already.

Apptainer is implemented here and has not been exercised on this project's
machine, which has no Apptainer installed. It is written from the kits' own
documented invocation. Treat it as untested until a host with Apptainer says
otherwise.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

KINDS = ("venv", "docker", "apptainer")


class ExecEnvironmentError(RuntimeError):
    """The declared execution environment cannot be used as declared."""


def _container_home(cache: Path) -> Path:
    """A writable home for the container, inside the bound cache.

    Not the host's. Binding $HOME would hand the model every dotfile on the
    machine, and not binding it while claiming it exists is worse: the path is
    a mount point the daemon created and owns, so `~/.triton` cannot be made
    and Triton's probe fails with a permission error that reads as a kernel
    refusal. Giving the container a home of its own is smaller and truer —
    the container does not have the host's home.
    """
    home = cache / "home"
    home.mkdir(parents=True, exist_ok=True)
    return home


def _identity_files(home: str) -> Tuple[Path, Path]:
    """A one-user ``passwd`` and ``group``, and the home directory they name.

    Running a container as the calling uid leaves that uid absent from the
    image's own ``/etc/passwd``, and a surprising amount of scientific Python
    asks for it: ``pwd.getpwuid`` raises ``KeyError: 'getpwuid(): uid not
    found'``, which surfaced here as a Boltz-2 zygote preload failing and then
    a nanobind abort from the double import that followed.

    Binding the host's own ``/etc/passwd`` would fix it and expose every account
    on the machine to the model. These files carry root and the caller and
    nothing else, and are the only identity the container sees.
    """
    root = Path(
        os.environ.get("TOOLUNIVERSE_CONTAINER_ID_DIR")
        or os.path.expanduser("~/.cache/tooluniverse/container-identity")
    )
    root.mkdir(parents=True, exist_ok=True)
    uid, gid = os.getuid(), os.getgid()
    passwd = root / "passwd"
    group = root / "group"
    passwd.write_text(
        f"root:x:0:0:root:/root:/bin/sh\ntu:x:{uid}:{gid}:tooluniverse:{home}:/bin/sh\n"
    )
    group.write_text(f"root:x:0:\ntu:x:{gid}:\n")
    return passwd, group


@dataclass
class ExecEnvironment:
    """Turns a Python command into an argv that runs it where the model lives."""

    kind: str
    python: Optional[str] = None  # venv: the interpreter
    image: Optional[str] = None  # docker: the tag
    sif: Optional[str] = None  # apptainer: the .sif
    container_python: str = "python"
    binds: List[Path] = field(default_factory=list)
    gpu: bool = True
    network: Optional[str] = None  # docker --network / apptainer --net

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ExecEnvironmentError(
                f"[env] kind = {self.kind!r} is not one of {KINDS}"
            )

    # ------------------------------------------------------------------ binds
    def _bind_paths(self) -> List[str]:
        """Existing host paths, de-duplicated, parents before children."""
        seen: List[str] = []
        for raw in self.binds:
            p = Path(raw).expanduser()
            if not p.exists():
                continue
            s = os.fspath(p.resolve())
            if not any(s == t or s.startswith(t + os.sep) for t in seen):
                seen.append(s)
        return seen

    # ------------------------------------------------------------------ cache
    def cache_dir(self) -> Path:
        root = Path(
            os.environ.get("TOOLUNIVERSE_CONTAINER_CACHE_DIR")
            or os.path.expanduser("~/.cache/tooluniverse/container-cache")
        )
        root.mkdir(parents=True, exist_ok=True)
        return root

    def cache_env(self) -> Dict[str, str]:
        c = self.cache_dir()
        for sub in ("numba", "matplotlib", "xdg", "fontconfig", "triton", "home"):
            (c / sub).mkdir(exist_ok=True)
        return {
            "XDG_CACHE_HOME": os.fspath(c / "xdg"),
            "NUMBA_CACHE_DIR": os.fspath(c / "numba"),
            "MPLCONFIGDIR": os.fspath(c / "matplotlib"),
            "FONTCONFIG_PATH": os.fspath(c / "fontconfig"),
            # Triton's own default is ~/.triton, which a container home would
            # otherwise have to be writable for; naming it removes the question.
            "TRITON_CACHE_DIR": os.fspath(c / "triton"),
            # The kits' Apptainer recipe sets this for the same reason: a host
            # user site-packages must not shadow the image's pinned stack.
            "PYTHONNOUSERSITE": "1",
        }

    # ------------------------------------------------------------------- argv
    def argv(
        self, args: Sequence[str], env: Optional[Dict[str, str]] = None
    ) -> Tuple[List[str], Dict[str, str]]:
        """``(argv, environment for Popen)`` running ``python <args>`` inside.

        A venv inherits the environment; a container is given it explicitly,
        because the variables would otherwise reach only the client.
        """
        env = dict(env or {})
        if self.kind == "venv":
            if not self.python:
                raise ExecEnvironmentError('[env] kind = "venv" needs [env] python')
            return [self.python, *args], {**os.environ, **env}

        if self.kind == "docker":
            if not self.image:
                raise ExecEnvironmentError('[env] kind = "docker" needs [env] image')
            if not shutil.which("docker"):
                raise ExecEnvironmentError("docker is not on PATH")
            argv = ["docker", "run", "--rm", "-i", "--init"]
            if self.gpu:
                argv += ["--gpus", "all"]
            # The kits' own run line uses it: a model's DataLoader and any
            # shared-memory transport need more than the 64 MB default.
            argv += ["--ipc=host"]
            argv += ["--user", f"{os.getuid()}:{os.getgid()}"]
            home = os.fspath(_container_home(self.cache_dir()))
            passwd, group = _identity_files(home)
            argv += ["-v", f"{passwd}:/etc/passwd:ro", "-v", f"{group}:/etc/group:ro"]
            env.setdefault("HOME", home)
            # Running as the caller means site-packages is root-owned and not
            # writable, and several libraries want to write beside the module
            # they are compiling: numba refuses with "cannot cache function ...
            # no locator available", matplotlib and Triton pick their own
            # directories. Point them all at one bound, writable place.
            for key, value in self.cache_env().items():
                env.setdefault(key, value)
            argv += ["-v", f"{self.cache_dir()}:{self.cache_dir()}"]
            if self.network:
                argv += ["--network", self.network]
            for p in self._bind_paths():
                argv += ["-v", f"{p}:{p}"]
            for k, v in env.items():
                argv += ["-e", f"{k}={v}"]
            argv += ["-w", os.fspath(Path.cwd())] if Path.cwd().exists() else []
            argv += [self.image, self.container_python, *args]
            return argv, dict(os.environ)

        if not self.sif:
            raise ExecEnvironmentError('[env] kind = "apptainer" needs [env] sif')
        runner = shutil.which("apptainer") or shutil.which("singularity")
        if not runner:
            raise ExecEnvironmentError("neither apptainer nor singularity is on PATH")
        # Apptainer runs as the caller with the host's own identity already;
        # there is no uid to introduce.
        argv = [runner, "exec", "--cleanenv"]
        for key, value in self.cache_env().items():
            env.setdefault(key, value)
        env.setdefault("HOME", os.fspath(_container_home(self.cache_dir())))
        self.binds.append(self.cache_dir())
        if self.gpu:
            argv += ["--nv"]
        if self.network:
            argv += ["--net", "--network", self.network]
        for p in self._bind_paths():
            argv += ["--bind", f"{p}:{p}"]
        for k, v in env.items():
            argv += ["--env", f"{k}={v}"]
        argv += [os.fspath(Path(self.sif).expanduser()), self.container_python, *args]
        return argv, dict(os.environ)

    # ------------------------------------------------------------------ probe
    def describe(self) -> str:
        if self.kind == "venv":
            return f"venv {self.python}"
        if self.kind == "docker":
            return f"docker image {self.image}"
        return f"apptainer {self.sif}"


def from_manifest(
    manifest, *, extra_binds: Sequence[os.PathLike | str] = ()
) -> ExecEnvironment:
    """The execution environment a provider declares, with what it must see.

    The binds are the paths a resident worker touches across the boundary: the
    socket it serves on, the weights it reads, the ToolUniverse files it loads
    by path, its own directory, and the work root under which per-request
    output directories are created.
    """
    kind = manifest.env_kind
    binds: List[Path] = []
    if kind != "venv":
        from .protocol import socket_path

        binds.append(Path(socket_path(manifest.slug)).parent)
        root = manifest.weights_root()
        if root is not None:
            binds.append(root)
        binds.append(Path(__file__).resolve().parent)  # protocol.py, worker_base.py
        binds.append(manifest.directory)
        # The worker script and the smoke input are resolved from the manifest
        # but need not live beside it, and a path the container cannot read is
        # a FileNotFoundError minutes into a start rather than a refusal.
        for relative in (manifest.worker, manifest.smoke):
            resolved = manifest.resolve(relative)
            if resolved is not None:
                binds.append(resolved.parent)
        if manifest.work_root:
            binds.append(Path(manifest.work_root).expanduser())
        binds += [Path(p) for p in extra_binds]
    return ExecEnvironment(
        kind=kind,
        # Only a venv has a host interpreter to resolve; a container carries
        # its own, and asking for the host one would refuse a perfectly good
        # container provider whose variable is simply not set.
        python=manifest.python_executable() if kind == "venv" else None,
        image=manifest.env_image,
        sif=manifest.env_sif,
        container_python=manifest.env_container_python,
        binds=binds,
        gpu=manifest.gpu_policy != "none",
        network=manifest.env_network,
    )
