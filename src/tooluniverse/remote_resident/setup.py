"""``tu remote setup <slug>`` — bring one provider's environment, kit and weights
to what its manifest declares, then prove it by running the model once.

The design follows the optimization kits' own install step, whose choices are
worth stating because each answers a failure this project has actually had:

*Idempotence comes from checking, not from a flag.* There is no ``--force`` and
no state file. Every step asks the filesystem whether it is already done,
reports ``present``, and skips. Re-running after a failure is the normal way to
continue.

*Nothing upstream owns is restated here.* Weights are fetched by the provider's
own declared command, which calls upstream's downloader with upstream's URL
lists and fallbacks. No URL appears in this file or in any manifest, so a
mirror change upstream cannot break setup.

*Nothing is deleted and nothing is retried automatically.* A file whose digest
is not the pin's is named and left in place: upstream writes straight to the
final name, so a truncated transfer and a corrupt file are indistinguishable,
and deleting one to retry would destroy the evidence that says which it was. A
2,286 MB checkpoint that arrived as 28.5 MB of itself served predictions from
this repository for over a month because nothing compared it to anything.

*The environment is verified, not created.* Setup installs into an interpreter
the manifest names through a variable; it does not build venvs, because the
outcome is what matters and uv, ``python -m venv``, conda and pixi all reach it.
An unset variable is refused with the recipe from the lock file's own header.

*It ends by running the model, under a deadline.* Installing successfully is not
evidence that anything works: of the four problems hit bringing up the first
provider, three appeared only at run time, and one of those presented as a
stall rather than an error. Without a deadline a setup waits forever and reports
nothing.
"""

from __future__ import annotations

import contextlib
import fnmatch
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .manifest import ManifestError, ProviderManifest
from .manifest import load as load_manifest

EXIT_OK, EXIT_FAILED, EXIT_USAGE, EXIT_REFUSED, EXIT_NO_ACCELERATOR = 0, 1, 2, 3, 5

# Three verbs, as the kits use them: OK is done, REFUSED is "this does not match
# what was declared", FAILED is "something broke". A caller branches on the word.
OK, REFUSED, FAILED, PRESENT, SKIPPED = "OK", "REFUSED", "FAILED", "present", "skipped"


@dataclass
class StepResult:
    step: str
    verdict: str
    detail: str = ""
    # One blank-free token when this went wrong, so a skill's table can key on it.
    reason: str = ""
    lines: List[str] = field(default_factory=list)
    seconds: float = 0.0

    @property
    def ok(self) -> bool:
        return self.verdict in (OK, PRESENT, SKIPPED)


def kit_root() -> Path:
    return Path(
        os.environ.get("TOOLUNIVERSE_KIT_ROOT")
        or os.path.expanduser("~/.cache/tooluniverse/kits")
    )


def kit_checkout(manifest: ProviderManifest) -> Optional[Path]:
    """Where this provider's kit lives: content-addressed by its pinned commit.

    Two providers pinning the same commit share one checkout, and fetching a
    newer commit lands beside the working one instead of over it.
    """
    kit = manifest.kit
    if not kit.get("upstream") or not kit.get("commit"):
        return None
    name = kit["upstream"].rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
    return kit_root() / f"{name}@{kit['commit']}"


def _run(
    argv: List[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: float = 3600,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        cwd=None if cwd is None else os.fspath(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _tail(text: str, n: int = 12) -> List[str]:
    return [ln for ln in (text or "").strip().splitlines()[-n:] if ln.strip()]


# ------------------------------------------------------------------- preflight
def step_preflight(manifest: ProviderManifest) -> StepResult:
    """Refuse for a host reason before anything large is downloaded.

    Every check here is cheap and local. The expensive steps below assume it
    passed, so that a machine that cannot run this provider learns so in a
    second rather than after 16 GB.
    """
    t = time.time()
    problems: List[str] = []
    notes: List[str] = []

    free_gb = shutil.disk_usage(Path.home()).free / 2**30
    # The first provider needs ~16 GB: 9.0 weights, 6.4 environment, 0.5 kit.
    if free_gb < 20:
        problems.append(
            f"disk_low: {free_gb:.1f} GiB free under {Path.home()}, this needs ~20"
        )

    if manifest.gpu_policy != "none":
        smi = shutil.which("nvidia-smi")
        if not smi:
            problems.append("no_nvidia_smi: nvidia-smi is not on PATH")
        else:
            out = _run(
                [
                    smi,
                    "--query-gpu=name,driver_version,compute_cap",
                    "--format=csv,noheader",
                ],
                timeout=30,
            )
            row = (out.stdout or "").strip().splitlines()
            if out.returncode != 0 or not row:
                problems.append(f"no_gpu: nvidia-smi returned {out.returncode}")
            else:
                name, driver, cap = (c.strip() for c in row[0].split(",")[:3])
                notes.append(f"GPU {name}, driver {driver}, compute capability {cap}")
                # The floor comes from the manifest, not from a constant. It
                # is a property of the provider's pinned CUDA and only the
                # provider knows it: cu130 needs the 580 series, cu128 runs on
                # 570. A hard-coded 580 refused three providers that work, with
                # a message asserting a CUDA version they do not pin.
                floor = manifest.driver_min
                try:
                    if floor is not None and float(driver.split(".")[0]) < floor:
                        problems.append(
                            f"driver_old: {driver}; this provider declares a "
                            f"floor of {floor:.0f} because {manifest.driver_min_reason}"
                        )
                    elif floor is None:
                        notes.append(
                            "no [gpu] driver_min declared, so the driver is "
                            "reported and not judged"
                        )
                except ValueError:
                    pass
                try:
                    if float(cap) < 8.0:
                        problems.append(
                            f"cc_below_floor: compute capability {cap}; the kits' "
                            f"floor is 8.0 and no configuration lowers it"
                        )
                except ValueError:
                    pass

    if not shutil.which("cc") and not shutil.which("gcc"):
        # Triton builds kernels at first use. Not installable without root, so
        # this is refused rather than worked around.
        problems.append(
            "compiler_missing: no cc or gcc on PATH; Triton compiles the kit's "
            "kernels at run time (Debian/Ubuntu: apt-get install build-essential)"
        )

    try:
        shm = shutil.disk_usage("/dev/shm").total / 2**30
        if shm < 1:
            notes.append(
                f"/dev/shm is {shm:.2f} GiB — small (a container default); "
                f"this provider's worker sets num_workers=0 and does not rely on it"
            )
    except OSError:
        pass

    if problems:
        return StepResult(
            "preflight",
            REFUSED,
            "; ".join(problems),
            reason=problems[0].split(":")[0],
            lines=notes,
            seconds=time.time() - t,
        )
    return StepResult(
        "preflight",
        OK,
        "host meets the declared prerequisites",
        lines=notes,
        seconds=time.time() - t,
    )


# ----------------------------------------------------------------- environment
@contextlib.contextmanager
def _build_context(dest: Path, dockerfile: Path):
    """A build context that is the kit tree, without writing into the kit tree.

    Two things are in tension. The kit checkout must stay byte-identical to its
    pinned commit -- that is what the tamper check enforces, and it is
    third-party code we execute. But the kits' Dockerfiles take an optional
    pre-filled compile cache from a `_jitcache/` directory in the context, and
    their own STOCK.md notes that "a builder that refuses an unmatched COPY glob
    needs an empty archive there first". BuildKit is such a builder, and without
    one the build stops at `lstat /_jitcache: no such file or directory`.

    So the context is a hard-linked shadow of the checkout: no file is copied,
    nothing in the checkout is touched, and the empty archive the builder wants
    exists only in the shadow, which is removed afterwards.
    """
    import tarfile
    import tempfile

    root = Path(tempfile.mkdtemp(prefix="tu-build-ctx-"))
    try:
        shadow = root / "ctx"
        link = subprocess.run(
            ["cp", "-al", os.fspath(dest), os.fspath(shadow)],
            capture_output=True,
            text=True,
        )
        if link.returncode != 0:  # a different filesystem, or no hard links
            shutil.copytree(dest, shadow, ignore=shutil.ignore_patterns(".git"))
        if "_jitcache" in dockerfile.read_text():
            jit = shadow / "_jitcache"
            jit.mkdir(exist_ok=True)
            # The name has to satisfy the Dockerfile's own glob, which is
            # keyed on the kit: `COPY _jitcache/<kit>-*-jit.ta[r]`. An archive
            # the glob does not match leaves the pattern unmatched, which is
            # the failure this exists to prevent.
            kit_name = dockerfile.resolve().parents[1].name
            with tarfile.open(jit / f"{kit_name}-empty-jit.tar", "w"):
                pass
        yield shadow
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _build_image(manifest, dest: Path, t: float) -> Optional[StepResult]:
    """Build the provider's image from the kit's own recipe, if it is absent.

    The kits ship `environment/Dockerfile` and `environment/apptainer.def` for
    every one of the thirty-six, and the Dockerfile expects the bundle root as
    its build context (it copies `common/` as well as the kit). Neither recipe
    is copied or rewritten here; the checkout is the context.
    """
    kit = manifest.kit
    subdir = kit.get("subdir")
    if not subdir:
        return StepResult(
            "environment",
            REFUSED,
            "a container environment needs [kit] subdir: the image is built from "
            "that kit's own environment/ recipe",
            reason="no_kit_subdir",
            seconds=time.time() - t,
        )

    if manifest.env_kind == "docker":
        if not shutil.which("docker"):
            return StepResult(
                "environment",
                REFUSED,
                "docker is not on PATH",
                reason="docker_missing",
                seconds=time.time() - t,
            )
        have = _run(["docker", "image", "inspect", manifest.env_image], timeout=120)
        if "permission denied" in (have.stderr or "").lower():
            return StepResult(
                "environment",
                REFUSED,
                f"this process cannot reach the docker daemon. Being added to the "
                f"docker group does not change a session already running: start a "
                f"new login shell, or run this under `sg docker -c ...`",
                reason="docker_permission",
                seconds=time.time() - t,
            )
        if have.returncode == 0:
            return StepResult(
                "environment",
                PRESENT,
                f"docker image {manifest.env_image} is present",
                seconds=time.time() - t,
            )
        dockerfile = dest / subdir / "environment" / "Dockerfile"
        if not dockerfile.is_file():
            return StepResult(
                "environment",
                REFUSED,
                f"{dockerfile} does not exist",
                reason="no_dockerfile",
                seconds=time.time() - t,
            )
        # The kit's apptainer.def bootstraps from a Docker tag of its own
        # choosing. Applying that tag here as well lets the Apptainer route use
        # the kit's recipe unchanged -- its %post creates the libcuda symlinks
        # Triton's launcher stub wants -- instead of editing a file in a
        # checkout that has to stay byte-identical to its pinned commit.
        tags = ["-t", manifest.env_image]
        definition = dest / subdir / "environment" / "apptainer.def"
        if definition.is_file():
            for line in definition.read_text().splitlines():
                if line.strip().lower().startswith("from:"):
                    wanted = line.split(":", 1)[1].strip()
                    if wanted and wanted != manifest.env_image:
                        tags += ["-t", wanted]
                    break
        with _build_context(dest, dockerfile) as context:
            out = _run(
                [
                    "docker",
                    "build",
                    "-f",
                    os.fspath(context / dockerfile.relative_to(dest)),
                    *tags,
                    os.fspath(context),
                ],
                timeout=14400,
            )
        if out.returncode != 0:
            return StepResult(
                "environment",
                FAILED,
                f"building {manifest.env_image} from {dockerfile} failed",
                reason="docker_build_failed",
                lines=_tail(out.stderr or out.stdout, 12),
                seconds=time.time() - t,
            )
        return StepResult(
            "environment",
            OK,
            f"built docker image {manifest.env_image}",
            lines=_tail(out.stdout, 3),
            seconds=time.time() - t,
        )

    runner = shutil.which("apptainer") or shutil.which("singularity")
    if not runner:
        return StepResult(
            "environment",
            REFUSED,
            "neither apptainer nor singularity is on PATH",
            reason="apptainer_missing",
            seconds=time.time() - t,
        )
    sif = Path(manifest.env_sif).expanduser()
    if sif.is_file():
        return StepResult(
            "environment", PRESENT, f"{sif} is present", seconds=time.time() - t
        )
    definition = dest / subdir / "environment" / "apptainer.def"
    if not definition.is_file():
        return StepResult(
            "environment",
            REFUSED,
            f"{definition} does not exist",
            reason="no_apptainer_def",
            seconds=time.time() - t,
        )
    # The kits' .def bootstraps from the Docker image built first; a published
    # tag would change its two header lines, which is the kit's business.
    sif.parent.mkdir(parents=True, exist_ok=True)
    out = _run(
        [runner, "build", os.fspath(sif), os.fspath(definition)],
        cwd=dest,
        timeout=14400,
    )
    if out.returncode != 0:
        return StepResult(
            "environment",
            FAILED,
            f"building {sif} from {definition} failed",
            reason="apptainer_build_failed",
            lines=_tail(out.stderr or out.stdout, 12),
            seconds=time.time() - t,
        )
    return StepResult("environment", OK, f"built {sif}", seconds=time.time() - t)


_ARCH_PROBE = r"""
import json, sys
out = {}
try:
    import torch
    out["torch"] = torch.__version__
    out["arch_list"] = list(torch.cuda.get_arch_list())
    if torch.cuda.is_available():
        out["device_sm"] = "sm_%d%d" % torch.cuda.get_device_capability(0)
        out["device"] = torch.cuda.get_device_name(0)
except Exception as exc:
    out["error"] = "%s: %s" % (type(exc).__name__, exc)
try:
    import glob as _glob, os as _os, re as _re, subprocess as _sp
    import triton as _triton
    _d = _os.path.dirname(_triton.__file__)
    out["triton"] = _triton.__version__
    _llvm = set()
    for _lib in (_glob.glob(_os.path.join(_d, "_C", "libtriton*.so"))
                 + _glob.glob(_os.path.join(_d, "**", "libtriton*.so"), recursive=True))[:2]:
        with open(_lib, "rb") as _f:
            _llvm |= {m.decode() for m in _re.findall(rb"sm_\d+a?", _f.read())}
    out["triton_llvm"] = sorted(_llvm)
    _ptx = {}
    for _p in sorted(_glob.glob(_os.path.join(_d, "backends", "nvidia", "bin", "ptxas*"))):
        try:
            _r = _sp.run([_p, "--help"], capture_output=True, text=True, timeout=60)
            _ptx[_os.path.basename(_p)] = sorted(
                set(_re.findall(r"sm_\d+a?", (_r.stdout or "") + (_r.stderr or ""))))
        except Exception:
            _ptx[_os.path.basename(_p)] = []
    out["triton_ptxas"] = _ptx
except Exception:
    pass
try:
    # A provider's accelerator is not always torch's. af3_jax pins a CPU-only
    # torch because its weights converter is a torch script, and judging that
    # provider's card by `torch.cuda.is_available()` refused it while JAX drove
    # the GPU. So the probe reports what every framework present can see and
    # the caller decides, rather than assuming one of them is authoritative.
    import jax as _jax
    out["jax"] = _jax.__version__
    out["jax_backend"] = _jax.default_backend()
    _devs = _jax.local_devices(backend="gpu") if out["jax_backend"] == "gpu" else []
    if _devs:
        out["jax_device"] = str(_devs[0])
        out["jax_device_cc"] = str(getattr(_devs[0], "compute_capability", "") or "")
except Exception:
    pass
sys.stdout.write("ARCH " + json.dumps(out))
"""


def _probe_arch(exec_env) -> Optional[Dict[str, Any]]:
    """What the model interpreter says about torch and Triton, probed once.

    Both toolchain checks read this, so the interpreter is started once rather
    than once per check.
    """
    argv, env = exec_env.argv(["-c", _ARCH_PROBE])
    try:
        out = _run(argv, env=env, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"probe_error": type(exc).__name__}
    for line in (out.stdout or "").splitlines():
        if line.startswith("ARCH "):
            return json.loads(line[5:])
    return None


def _toolchain_problems(exec_env, gpu_required: bool) -> tuple:
    """``(refusal, reason, notes)``: torch's cubins refuse; Triton's two stages note."""
    info = _probe_arch(exec_env)
    if info is None:
        return None, "", []
    if "probe_error" in info:
        return (
            f"the installed torch could not be probed ({info['probe_error']})",
            "torch_arch_unsupported",
            [],
        )
    problem = _arch_problem(info, gpu_required)
    if problem:
        return problem, "torch_arch_unsupported", []
    notes = _check_triton_targets_this_gpu(info)
    if info.get("triton") and info.get("device_sm"):
        probed = _probe_triton_compile(exec_env)
        if probed and not probed.get("skipped") and not probed.get("ok"):
            notes.insert(
                0,
                f"MEASURED: this interpreter cannot compile and run a "
                f"warp-shuffle kernel on {info['device_sm']} "
                f"(rc={probed.get('rc')}: {probed.get('why', 'no reason')}). "
                f"Any kernel reaching tl.sum, tl.max or tl.dot aborts the "
                f"process, which no worker can catch. This is the question the "
                f"string reads below only approximate: atlasfold passed them "
                f"and still died, because cuEquivariance ships Triton kernels "
                f"of its own. Three real routes out -- ablate the Triton levers "
                f"through the kit's door where it has one, switch upstream's "
                f"own kernel flag where it has one (atlasfold needed BOTH), or "
                f"a host whose Triton knows this card",
            )
    return None, "", notes


# The kernel the probe compiles. `tl.sum` is the construct that emits the warp
# shuffle, which is the instruction a Triton too old for this card cannot lower.
_REDUCE_SRC = "\n".join(
    [
        "import torch, triton, triton.language as tl",
        "",
        "@triton.jit",
        "def _k(x_ptr, o_ptr, N: tl.constexpr):",
        "    tl.store(o_ptr, tl.sum(tl.load(x_ptr + tl.arange(0, N)), axis=0))",
        "",
        "x = torch.ones(256, device='cuda', dtype=torch.float32)",
        "o = torch.zeros(1, device='cuda', dtype=torch.float32)",
        "_k[(1,)](x, o, N=256)",
        "torch.cuda.synchronize()",
        "assert abs(float(o[0]) - 256.0) < 1e-3, float(o[0])",
        "print('REDUCE_OK')",
    ]
)

# Written to a FILE and run as a CHILD, for two reasons that each cost an agent
# an hour. ``@triton.jit`` reads its own body with ``inspect.getsource``, so a
# kernel defined inside ``python -c`` fails with "could not get source code" --
# the right verdict for the wrong reason. And the failure being tested for is an
# abort(), which no try/except in the calling process could survive.
_TRITON_COMPILE_PROBE = "\n".join(
    [
        "import json, os, subprocess, sys, tempfile",
        "SRC = " + repr(_REDUCE_SRC),
        "out = {}",
        "try:",
        "    import triton",
        "except Exception:",
        "    sys.stdout.write('TRITONC ' + json.dumps({'skipped': 'no triton'}))",
        "    raise SystemExit",
        "d = tempfile.mkdtemp(prefix='tu-triton-probe-')",
        "f = os.path.join(d, 'probe_reduce.py')",
        "open(f, 'w').write(SRC)",
        "try:",
        "    r = subprocess.run([sys.executable, f], capture_output=True,",
        "                       text=True, timeout=600)",
        "    out['rc'] = r.returncode",
        "    out['ok'] = 'REDUCE_OK' in (r.stdout or '')",
        "    if not out['ok']:",
        "        tail = ((r.stderr or '') + (r.stdout or '')).strip().splitlines()",
        "        out['why'] = tail[-1][:200] if tail else 'no output'",
        "except Exception as exc:",
        "    out['rc'], out['ok'] = None, False",
        "    out['why'] = '%s: %s' % (type(exc).__name__, exc)",
        "sys.stdout.write('TRITONC ' + json.dumps(out))",
    ]
)


def _probe_triton_compile(exec_env) -> Optional[Dict[str, Any]]:
    """Can this interpreter compile AND RUN a warp-shuffle kernel on this card?

    Strictly stronger than reading ``libtriton.so``'s target strings, and the
    atlasfold bring-up is why it exists: that provider's static reads were
    correct and still did not predict its failure, because **cuEquivariance
    ships Triton kernels of its own** and nothing in Triton's target list says
    whether a second consumer's kernels will build. The question a host
    actually has is "can this interpreter emit a shuffle kernel for this GPU",
    and one kernel answers it in about two seconds.
    """
    argv, env = exec_env.argv(["-c", _TRITON_COMPILE_PROBE])
    try:
        out = _run(argv, env=env, timeout=900)
    except (OSError, subprocess.TimeoutExpired):
        return None
    for line in (out.stdout or "").splitlines():
        if line.startswith("TRITONC "):
            return json.loads(line[8:])
    return None


def _check_triton_targets_this_gpu(info: Dict[str, Any]) -> List[str]:
    """Notes on Triton's two separate abilities to emit code for this card.

    Triton is a SECOND toolchain beside torch's cubins, and the existing arch
    check cannot see it: a stack whose ``torch.cuda.get_arch_list()`` covers
    this card can still fail its kernels. There are two places it fails:

    * **LLVM.** Triton's target machine must list ``sm_<cc>a``. triton 3.3.1
      does not, and a kernel reducing ACROSS LANES then aborts the process:
      ``LLVM ERROR: Cannot select: intrinsic %llvm.nvvm.shfl.sync.bfly.i32``.
    * **ptxas.** Triton shells out to the ``ptxas`` bundled in its own wheel.
      triton 3.4.0's is CUDA 12.8, which has no sm_121 of any spelling, while
      Triton asks for ``sm_121a`` above cc 90.

    **Both are notes and neither is a refusal, and the first version of this
    check got that wrong.** It refused the LLVM case on the grounds that "every
    kernel this stack compiles would abort", which is false. evo2 runs on triton
    3.3.1 on this card: its kit spells its reductions out by hand for bitwise
    reproducibility, and nothing on its path calls ``tl.sum``, ``tl.reduce`` or
    ``tl.dot``. atlasfold, on the identical triton, dies. A bare ``tl.sum``
    kernel probed in both environments core-dumps in both -- so the stack's
    inability is real, and whether it matters is a property of the provider's
    kernels, which this layer cannot see. It reports what it measured and names
    the audit. A refusal was a false refusal on a provider that works, which is
    worse than having no check.

    Measured across twelve provider environments on one card: ten clean, e1
    (3.4.0) ptxas only, atlasfold and evo2 (3.3.1) both -- and of those two, one
    runs. triton 3.6.0 onward bundles a ``ptxas-blackwell`` and needs nothing.
    """
    sm = info.get("device_sm")
    if not sm or "triton" not in info:
        return []
    notes: List[str] = []
    wanted = {sm, sm + "a"}
    llvm = set(info.get("triton_llvm") or ())
    if llvm and not (wanted & llvm):
        notes.append(
            f"triton {info['triton']}'s LLVM target machine does not list {sm} "
            f"and ignores it. A kernel that reduces ACROSS LANES -- tl.sum, "
            f'tl.max, tl.dot -- then aborts the process with "LLVM ERROR: '
            f'Cannot select: intrinsic %llvm.nvvm.shfl.sync.bfly.i32", which '
            f"no worker can catch. A kernel that does not reduce compiles and "
            f"runs correctly: on this card atlasfold dies and evo2 does not, on "
            f"the same triton 3.3.1, because evo2's kit spells its reductions "
            f"out by hand. So AUDIT the kernels on this provider's path for "
            f"tl.sum, tl.reduce and tl.dot, and record the audit in the "
            f"manifest. The first Triton to list {sm} is 3.4.0; raising it "
            f"deviates from the kit's lock, which is a decision, not a fix"
        )
    ptxas = info.get("triton_ptxas") or {}
    if ptxas and not any(wanted & set(v) for v in ptxas.values()):
        notes.append(
            f"triton {info['triton']} bundles no ptxas that targets {sm} "
            f"({', '.join(sorted(ptxas)) or 'none found'}), so kernels fail "
            f"with \"ptxas fatal: Value '{sm}a' is not defined\" unless the "
            f"provider supplies one. The fix is nvidia-cuda-nvcc-cu12==12.9.86 "
            f"in the lock, pointed at by the worker only when triton's own does "
            f"not list this card (see remote/e1 and remote/evo2). The variable "
            f"name is derived rather than literal: triton builds it as "
            f"TRITON_<BINARY>_PATH and selects ptxas-blackwell above cc 100, so "
            f"on this card it reads TRITON_PTXAS-BLACKWELL_PATH, hyphen "
            f"included, and a worker should set both spellings. triton 3.6.0 "
            f"onward bundles its own 12.9 and needs none of this"
        )
    return notes


def _check_torch_targets_this_gpu(exec_env, gpu_required: bool) -> Optional[str]:
    """Why the installed torch cannot drive this card, or None.

    A pinned stack can be perfectly installable and still unable to emit code
    for the GPU in front of it. Five of the thirty-six kits pin torch below 2.7
    -- flashzoi 2.5.1, proteinmpnn 2.5.1, rfdiffusion1 2.4.0, caliby 2.6.0 --
    whose CUDA builds stop at sm_90, and this project's card is sm_121. Without
    this the first sign is a kernel error after several gigabytes have been
    downloaded and an environment built.

    Read from torch rather than inferred from a version: ``get_arch_list`` is
    what the build actually carries, and a build can carry PTX for an older
    architecture that the driver then compiles forward, which a version
    comparison would call a failure.
    """
    info = _probe_arch(exec_env)
    if info is None:
        return None  # no torch in this environment: not every provider has one
    if "probe_error" in info:
        return f"the installed torch could not be probed ({info['probe_error']})"
    return _arch_problem(info, gpu_required)


def _arch_problem(info: Dict[str, Any], gpu_required: bool) -> Optional[str]:
    """Why torch's own cubins cannot drive this card, or None."""
    if info.get("error") or not info.get("device_sm"):
        if info.get("jax_backend") == "gpu" and info.get("jax_device"):
            # Another framework has the card. This was a false refusal on
            # af3_jax, whose kit must pin a CPU-only torch because its weights
            # converter is a torch script: `torch_arch_unsupported` fired while
            # jax reported a CudaDevice and drove the GPU. The lesson is the one
            # the Triton note already carries -- a check written from one
            # framework's assumptions refuses providers that work.
            return None
        return (
            None
            if not gpu_required
            else f"torch reports no usable GPU: {info.get('error', 'no device')}"
        )
    sm, arches = info["device_sm"], info.get("arch_list") or []

    def parse(name):
        digits = "".join(c for c in name.split("_")[-1] if c.isdigit())
        return (int(digits[:-1]), int(digits[-1])) if len(digits) >= 2 else None

    want = parse(sm)
    if want is None:
        return None
    for arch in arches:
        got = parse(arch)
        if got is None:
            continue
        # CUDA binaries are compatible within one major compute capability,
        # later minor versions included: an sm_120 cubin runs on sm_121, which
        # is how both of this project's stacks drive a card neither lists.
        if got[0] == want[0] and got[1] <= want[1]:
            return None
        # PTX for an earlier architecture is compiled forward by the driver.
        if (arch.endswith("+PTX") or "compute_" in arch) and got <= want:
            return None
    return (
        f"torch {info.get('torch')} was built for {', '.join(arches) or 'nothing'} "
        f"and this card is {sm} ({info.get('device')}); nothing there is binary "
        f"compatible with it and there is no PTX to compile forward from"
    )


def step_environment(manifest: ProviderManifest) -> StepResult:
    """Install the lock into the interpreter the manifest names. Never create one."""
    t = time.time()
    if manifest.env_kind != "venv":
        # A container carries the stack; there is no lock to install into it.
        # What has to exist is the image, and the kit's own recipe builds it.
        dest = kit_checkout(manifest)
        if dest is None or not dest.is_dir():
            return StepResult(
                "environment",
                REFUSED,
                f'[env] kind = "{manifest.env_kind}" builds from the kit\'s recipe, '
                f"which is not checked out yet — run the kit step first",
                reason="kit_not_checked_out",
                seconds=time.time() - t,
            )
        return _build_image(manifest, dest, t)

    try:
        python = manifest.python_executable()
    except ManifestError as exc:
        lock = manifest.resolve(manifest.env_lock)
        recipe = ""
        if lock and lock.is_file():
            recipe = (
                f"\n  the recipe is in the header of {lock}; in short:\n"
                f"    uv venv --seed --managed-python --python 3.11.12 ~/{manifest.slug}-venv\n"
                f"    export {str(manifest.env_python or '').lstrip('$')}=~/{manifest.slug}-venv/bin/python"
            )
        return StepResult(
            "environment",
            REFUSED,
            f"{exc}{recipe}",
            reason="env_python_unset",
            seconds=time.time() - t,
        )

    if not Path(python).is_file():
        return StepResult(
            "environment",
            REFUSED,
            f"{python} is not a file — it must be the interpreter of "
            f"{manifest.slug}'s own environment",
            reason="env_python_missing",
            seconds=time.time() - t,
        )

    if manifest.env_verify:
        probe = _run([python, "-c", manifest.env_verify], timeout=300)
        if probe.returncode == 0:
            from .exec_env import from_manifest

            problem, why, notes = _toolchain_problems(
                from_manifest(manifest), manifest.gpu_policy == "required"
            )
            if problem:
                return StepResult(
                    "environment",
                    REFUSED,
                    problem,
                    reason=why,
                    seconds=time.time() - t,
                )
            return StepResult(
                "environment",
                PRESENT,
                f"{python} already satisfies [env] verify",
                lines=[f"NOTE: {n}" for n in notes],
                seconds=time.time() - t,
            )

    lock = manifest.resolve(manifest.env_lock)
    if lock is None:
        return StepResult(
            "environment",
            REFUSED,
            "[env] lock is not declared, so the environment cannot be rebuilt",
            reason="no_lock",
            seconds=time.time() - t,
        )

    # --no-deps because the lock is complete; letting a resolver re-derive the
    # set is how a stack stops being the one that was measured.
    text = lock.read_text().splitlines()

    # A lock may declare ORDERED passes with `# --- pass break ---`, and one
    # kit needs it. pip does not honour requirement order within a single
    # install, so a lock carrying two CUDA generations installs whichever of a
    # colliding pair pip reaches last: protenix_v1's keeps both the CUDA 12.9
    # and 13.0 runtimes, and 27 paths under nvidia/{cudnn,nccl,cusparselt}
    # collide. Measured, one pass leaves nvidia/cudnn/lib/libcudnn.so.9 at
    # 124,920 bytes -- the cu12 wheel's file -- where two passes with CUDA 13
    # last leave the cu13 wheel's 6,328,728-byte one, which is the single path
    # torch 2.13.0+cu130 preloads. The result imports fine and is simply not
    # the stack that was measured, which is the kind of wrong that survives a
    # smoke. The kit's own Dockerfile uses two passes and says why.
    groups: List[List[str]] = [[]]
    for ln in text:
        if ln.strip().startswith("#"):
            if "pass break" in ln:
                groups.append([])
            continue
        if ln.strip():
            groups[-1].append(ln)
    pins = [ln for g in groups for ln in g]
    boot = [ln for ln in pins if ln.split("==")[0] in ("pip", "wheel")]
    passes = [[ln for ln in g if ln not in boot] for g in groups]
    passes = [g for g in passes if g]

    lines: List[str] = []
    batches = [("pip/wheel", boot, [])]
    if len(passes) <= 1:
        batches.append(("stack", passes[0] if passes else [], []))
    else:
        batches += [
            (f"stack pass {i + 1}/{len(passes)}", g, []) for i, g in enumerate(passes)
        ]
    for label, batch, extra in batches:
        if not batch:
            continue
        listing = lock.parent / f".{manifest.slug}-{label.replace('/', '-')}.txt"
        listing.write_text("\n".join(batch) + "\n")
        try:
            out = _run(
                [
                    python,
                    "-m",
                    "pip",
                    "install",
                    "--no-deps",
                    "--disable-pip-version-check",
                    *extra,
                    "-r",
                    os.fspath(listing),
                ],
                timeout=7200,
            )
        finally:
            listing.unlink(missing_ok=True)
        if out.returncode != 0:
            return StepResult(
                "environment",
                FAILED,
                f"installing the {label} of {lock.name} into {python} failed",
                reason="lock_install_failed",
                lines=_tail(out.stderr or out.stdout),
                seconds=time.time() - t,
            )
        lines.append(f"{label}: {len(batch)} distributions")

    from .exec_env import from_manifest

    problem, why, notes = _toolchain_problems(
        from_manifest(manifest), manifest.gpu_policy == "required"
    )
    if problem:
        return StepResult(
            "environment",
            REFUSED,
            problem,
            reason=why,
            lines=lines
            + [
                "the stack installed correctly; it simply cannot emit code for "
                "this card. A kit pinning an older torch needs newer hardware, "
                "or a host of the architecture it was pinned for",
            ],
            seconds=time.time() - t,
        )

    return StepResult(
        "environment",
        OK,
        f"{len(pins)} pinned distributions in {python}",
        lines=lines + [f"NOTE: {n}" for n in notes],
        seconds=time.time() - t,
    )


# Running the kit and installing it editable leave byproducts in its tree:
# bytecode caches and the egg-info of the editable install. They are untracked,
# they are not the kit's code, and treating them as tampering would refuse
# every tree that has ever been used. Anything else untracked is still
# reported: a new file beside a module can be imported by name.
_BYPRODUCTS = ("__pycache__/", ".egg-info/", ".pyc", ".pyo", ".jit/", "/.seeded")


def _foreign_objects(root: Path, limit: int = 40) -> List[str]:
    """Prebuilt shared objects in ``root`` that this machine cannot load.

    Eight of the thirty-six upstream kits carry prebuilt host objects and all
    of them are x86-64; none ships an aarch64 build. A kit's own `check` does
    not catch this — it reports the GPU architecture its CUDA objects target,
    which says nothing about the ELF machine type of the file holding them — so
    the first sign is an ImportError reading "cannot open shared object file"
    minutes into a smoke run, which is `dlopen`'s wording for a file that is
    right there.

    **This scans one directory, and the message says so.** The caller passes
    ``dest / subdir``, not the whole sparse set, so objects under ``common/``
    are not examined — and that is where the shared core keeps 48 x86-64 ``.so``
    files and 113 cubins that ten providers' levers reach. Widening the scan
    would refuse all ten, because those files sit under
    ``...x86_64-linux-gnu-sm90/`` paths that are never selected on aarch64 and
    the core falls back to NVRTC. A false refusal on ten working providers is
    worse than a narrow check, so the check stays narrow and stops claiming
    more than it did. The question it cannot answer — "will this interpreter's
    kernels actually build for this card" — is answered by the Triton compile
    probe instead.
    """
    import platform
    import struct

    want = {"x86_64": 0x3E, "aarch64": 0xB7, "ppc64le": 0x15, "s390x": 0x16}.get(
        platform.machine()
    )
    if want is None:
        return []
    foreign = []
    for path in list(root.rglob("*.so"))[:limit]:
        try:
            with open(path, "rb") as f:
                head = f.read(20)
        except OSError:
            continue
        if len(head) < 20 or head[:4] != b"\x7fELF":
            continue
        machine = struct.unpack_from("<H", head, 18)[0]
        if machine != want:
            foreign.append(
                f"{path.name}: ELF machine 0x{machine:02x}, this host is {platform.machine()}"
            )
    return foreign


def _is_tampering(porcelain_line: str) -> bool:
    line = porcelain_line.rstrip()
    if not line:
        return False
    path = line[3:]
    if not line.startswith("?? "):
        return True  # a tracked file that differs from the pinned commit
    return not any(mark in path for mark in _BYPRODUCTS)


# ------------------------------------------------------------------------ kit
def step_kit(manifest: ProviderManifest) -> StepResult:
    """Fetch the pinned third-party kit, if this provider uses one, and install it."""
    t = time.time()
    dest = kit_checkout(manifest)
    if dest is None:
        return StepResult(
            "kit", SKIPPED, "this provider declares no kit", seconds=time.time() - t
        )

    kit = manifest.kit
    lines: List[str] = []
    if dest.is_dir() and (dest / ".git").is_dir():
        lines.append(f"present at {dest}")
        # The checkout is shared by every provider pinning this commit, and each
        # declares only the paths it needs. A second provider arriving at an
        # existing checkout must widen the sparse set rather than find its kit
        # missing from a directory that looks complete.
        want = list(kit.get("sparse") or [])
        subdir = kit.get("subdir")
        if want and subdir and not (dest / subdir).is_dir():
            have = _run(["git", "sparse-checkout", "list"], cwd=dest, timeout=300)
            merged = sorted(set((have.stdout or "").split()) | set(want))
            widen = _run(
                ["git", "sparse-checkout", "set", *merged], cwd=dest, timeout=600
            )
            if widen.returncode != 0 or not (dest / subdir).is_dir():
                return StepResult(
                    "kit",
                    FAILED,
                    f"{subdir}/ is absent from the shared checkout at {dest} and the "
                    f"sparse set could not be widened to {merged}",
                    reason="kit_sparse_widen_failed",
                    lines=_tail(widen.stderr),
                    seconds=time.time() - t,
                )
            lines.append(f"sparse set widened to {' '.join(merged)}")
    else:
        if not shutil.which("git"):
            return StepResult(
                "kit",
                REFUSED,
                "git is not on PATH",
                reason="git_missing",
                seconds=time.time() - t,
            )
        dest.parent.mkdir(parents=True, exist_ok=True)
        sparse = list(kit.get("sparse") or [])
        argv = ["git", "clone", "--filter=blob:none", "--depth", "1", "--no-checkout"]
        if sparse:
            argv.append("--sparse")
        argv += [kit["upstream"], os.fspath(dest)]
        out = _run(argv, timeout=3600)
        if out.returncode != 0:
            return StepResult(
                "kit",
                FAILED,
                f"cloning {kit['upstream']} failed",
                reason="kit_clone_failed",
                lines=_tail(out.stderr),
                seconds=time.time() - t,
            )
        if sparse:
            _run(["git", "sparse-checkout", "init", "--cone"], cwd=dest, timeout=300)
            _run(["git", "sparse-checkout", "set", *sparse], cwd=dest, timeout=300)
        # --depth 1 fetched only the tip; ask for the pinned commit by name so a
        # pin that is not the tip still resolves.
        fetch = _run(
            ["git", "fetch", "--depth", "1", "origin", kit["commit"]],
            cwd=dest,
            timeout=3600,
        )
        checkout = _run(
            ["git", "checkout", "--detach", kit["commit"]], cwd=dest, timeout=600
        )
        if checkout.returncode != 0:
            return StepResult(
                "kit",
                FAILED,
                f"the pinned commit {kit['commit'][:12]} could not be "
                f"checked out (the clone is left at {dest} for inspection)",
                reason="kit_commit_missing",
                lines=_tail(checkout.stderr) + _tail(fetch.stderr, 4),
                seconds=time.time() - t,
            )
        lines.append(f"cloned at {kit['commit'][:12]} into {dest}")

    head = _run(["git", "rev-parse", "HEAD"], cwd=dest, timeout=60)
    got = (head.stdout or "").strip()
    if got != kit["commit"]:
        return StepResult(
            "kit",
            REFUSED,
            f"{dest} is at {got[:12]}, the pin is {kit['commit'][:12]} — "
            f"left in place; remove it by hand and re-run",
            reason="kit_wrong_commit",
            seconds=time.time() - t,
        )
    dirty = _run(["git", "status", "--porcelain"], cwd=dest, timeout=300)
    changed = [ln for ln in (dirty.stdout or "").splitlines() if _is_tampering(ln)]
    if changed:
        return StepResult(
            "kit",
            REFUSED,
            f"{dest} has local modifications; this is third-party code "
            f"we execute, so a changed tree is refused rather than run",
            reason="kit_modified",
            lines=changed[:6],
            seconds=time.time() - t,
        )

    subdir = kit.get("subdir")
    # Under mode = "off" the kit installs no finder and loads none of its
    # objects, so their architecture does not matter.
    checking_objects = subdir and kit.get("mode", "fast") != "off"
    foreign = _foreign_objects(dest / subdir) if checking_objects else []
    if foreign:
        return StepResult(
            "kit",
            REFUSED,
            f"{subdir}/ carries prebuilt shared objects this machine cannot "
            f"load; a lever that dlopens one fails at import, not at check",
            reason="kit_foreign_objects",
            lines=foreign[:6]
            + [
                'set [kit] mode = "off" to run the provider without the kit\'s '
                "levers, or use a host of the architecture the kit was built for",
                "note this scanned only "
                f"{subdir}/: objects under common/ are not examined, because the "
                "shared core's x86-64 files sit under paths never selected on "
                "this architecture and refusing on them would refuse every "
                "provider that works. Whether the kernels actually build is a "
                "different question, answered by the Triton compile probe in the "
                "environment step",
            ],
            seconds=time.time() - t,
        )

    if manifest.env_kind != "venv":
        # The image carries the kit: its own Dockerfile ran the install step at
        # build time, into the interpreter the image holds. Running it again on
        # the host would install into whatever python is on the host's PATH,
        # which is not where the model lives.
        lines.append(f"install is the image's ({manifest.env_kind}); not re-run here")
        return StepResult(
            "kit",
            OK,
            f"checkout present for the image build at {dest}",
            lines=lines,
            seconds=time.time() - t,
        )

    install = kit.get("install")
    if not install:
        return StepResult(
            "kit",
            OK,
            "; ".join(lines) + " (no install step declared)",
            seconds=time.time() - t,
        )

    python = manifest.python_executable()
    workdir = dest / kit.get("subdir", "")
    env = dict(os.environ)
    # NOT resolve(): a venv's bin/python is a symlink to the interpreter it was
    # built from, and following it lands in that interpreter's bin directory.
    env["PATH"] = (
        str(Path(python).expanduser().absolute().parent)
        + os.pathsep
        + env.get("PATH", "")
    )
    root = manifest.weights_root()
    # The weights root is exported here as well as in the weights step. A kit's
    # own `run.sh install --weights DIR` often reads the root from the
    # environment rather than from its argument, and without this every such
    # manifest has to restate it on the command line -- atlasfold had to write
    # `ATLASFOLD_WEIGHTS_DIR={weights_root} bash run.sh install ...`. The
    # placeholder is computed two lines below either way, so this costs nothing.
    if root is not None and manifest.weights_root_env:
        env[manifest.weights_root_env] = os.fspath(root)
    command = install.format(
        weights_root=os.fspath(root) if root else "",
        python=python,
        kit=os.fspath(workdir),
    )
    out = _run(["bash", "-c", command], cwd=workdir, env=env, timeout=7200)
    lines += _tail(out.stdout, 6)
    if out.returncode != 0:
        return StepResult(
            "kit",
            FAILED,
            f"the kit's own install step exited {out.returncode} "
            f"(`{command}` in {workdir})",
            reason="kit_install_failed",
            lines=lines + _tail(out.stderr, 8),
            seconds=time.time() - t,
        )
    return StepResult(
        "kit", OK, f"installed from {dest}", lines=lines, seconds=time.time() - t
    )


# -------------------------------------------------------------------- weights
def step_weights(manifest: ProviderManifest) -> StepResult:
    """Every declared file present and at its pin. Deep: what is certified is read."""
    t = time.time()
    if not manifest.weights:
        return StepResult(
            "weights",
            SKIPPED,
            "this provider declares no weights",
            seconds=time.time() - t,
        )
    root = manifest.weights_root()
    lines: List[str] = []
    problems = manifest.verify_weights(deep=True)
    if problems and manifest.weights_fetch:
        # Not every kit fetches weights in its install step: some models pull
        # their own from a hub at first load. The provider declares the command
        # that does it, which calls upstream's own downloader -- no URL is
        # restated in ToolUniverse, so a mirror change upstream cannot break us.
        lines.append(f"{len(problems)} entr(ies) absent or off pin: fetching")
        python = manifest.python_executable()
        env = dict(os.environ)
        # The same PATH the kit step gives its install command. A kit's own
        # fetcher runs through its run.sh, and those look for `python` on PATH
        # rather than reading a PYTHON= variable -- chai1's and openfold3's
        # both do. Without this the fetch fails with "no python on PATH" at
        # exactly the moment a weight file is missing.
        if manifest.env_kind == "venv":
            bin_dir = str(Path(python).expanduser().absolute().parent)
            env["PATH"] = bin_dir + (
                os.pathsep + env["PATH"] if env.get("PATH") else ""
            )
        if root is not None and manifest.weights_root_env:
            env[manifest.weights_root_env] = os.fspath(root)
        out = _run(
            [
                "bash",
                "-c",
                # The same fields [kit] install and [runtime] worker_args get.
                # A placeholder the caller can write but this cannot fill is a
                # KeyError at the moment the weights are actually missing,
                # which is the worst moment to discover it.
                manifest.weights_fetch.format(
                    python=python,
                    weights_root=os.fspath(root) if root else "",
                    kit=os.fspath(kit_checkout(manifest) or ""),
                    slug=manifest.slug,
                ),
            ],
            env=env,
            timeout=7200,
        )
        if out.returncode == 3:
            # The kits' own vocabulary, which STANDARD.md section 8 adopts: 3 is
            # "refused, and here is the fix", 1 is "it broke". Reporting a
            # refusal as a failure loses that distinction at the exit code a
            # caller branches on -- af3_torch's fetch refuses by name because
            # its weights are produced by a second interpreter, which is a
            # correct answer, not a fault.
            return StepResult(
                "weights",
                REFUSED,
                "the declared fetch command refused (exit 3); its own words follow",
                reason="weights_fetch_refused",
                lines=lines + _tail(out.stderr or out.stdout, 8),
                seconds=time.time() - t,
            )
        if out.returncode != 0:
            return StepResult(
                "weights",
                FAILED,
                f"the declared fetch command exited {out.returncode}",
                reason="weights_fetch_failed",
                lines=lines + _tail(out.stderr or out.stdout, 8),
                seconds=time.time() - t,
            )
        problems = manifest.verify_weights(deep=True)
    if problems:
        return StepResult(
            "weights",
            REFUSED,
            f"{len(problems)} of {len(manifest.weights)} declared files are not at "
            f"their pins under {root}",
            reason="weights_off_pin",
            # Nothing is deleted: upstream writes straight to the final name, so a
            # truncated transfer and a corrupt file look alike, and removing one to
            # retry destroys the evidence that says which it was.
            lines=problems
            + [
                "files are left in place for inspection; remove the named one by "
                "hand and re-run this step to fetch it again",
            ],
            seconds=time.time() - t,
        )
    total = sum(w.size or 0 for w in manifest.weights) / 2**30
    return StepResult(
        "weights",
        OK,
        f"{len(manifest.weights)}/{len(manifest.weights)} entries at "
        f"their pins under {root} ({total:.1f} GiB)",
        seconds=time.time() - t,
    )


# ---------------------------------------------------------------------- smoke
def measured_path(slug: str) -> Path:
    root = os.environ.get("TOOLUNIVERSE_MEASURED_DIR") or os.path.expanduser(
        "~/.cache/tooluniverse/measured"
    )
    return Path(root) / f"{slug}.json"


def _write_measured(slug: str, record: Dict[str, Any]) -> str:
    """Persist one smoke record; return the phrase describing where it went."""
    path = measured_path(slug)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=1, sort_keys=True))
        return f"; recorded in {path}"
    except OSError as exc:
        return f"; the record could not be written ({exc})"


def _what_it_produced(
    manifest: ProviderManifest, result: Dict[str, Any], out_dir: Path
) -> tuple:
    """``(matched, refusal)`` for the manifest's declared success condition.

    An exit code is not evidence that a model ran. OpenFold3's runner catches
    a per-query exception, writes a summary saying "Failed Queries: 1" and
    returns normally; the smoke step saw a reply, a timing and a GPU peak, and
    called that verified. What it had never asked was whether a structure came
    out. This asks.

    Files are matched against ``[runtime] outputs`` -- both the paths the
    worker reported and a walk of the output directory, because a provider is
    not obliged to list what it wrote. ``[runtime] output_keys`` covers the
    providers that answer with arrays and write nothing at all.
    """
    matched: Dict[str, Any] = {}

    if manifest.outputs:
        seen = [Path(f) for f in (result.get("files") or [])]
        if out_dir.is_dir():
            seen.extend(q for q in out_dir.rglob("*") if q.is_file())
        hits = sorted(
            {
                os.fspath(q)
                for q in seen
                for pattern in manifest.outputs
                if fnmatch.fnmatch(q.name, pattern)
            }
        )
        matched["outputs"] = hits
        if not hits:
            listing = sorted({q.name for q in seen})[:8] or ["nothing at all"]
            return matched, (
                f"the model answered but produced none of {list(manifest.outputs)} "
                f"\u2014 what it wrote was {listing}. An exit code is not evidence "
                f"that a model ran: upstream may have caught its own per-request "
                f"exception and returned normally. Read the worker transcript and "
                f"any summary file in {out_dir}"
            )

    missing = [
        k
        for k in manifest.output_keys
        if result.get(k) is None or result.get(k) == [] or result.get(k) == {}
    ]
    if manifest.output_keys:
        matched["output_keys"] = [k for k in manifest.output_keys if k not in missing]
    if missing:
        return matched, (
            f"the model answered but its reply has nothing under {missing} "
            f"\u2014 the keys [runtime] output_keys says a successful run fills. "
            f"Read the worker transcript"
        )

    return matched, ""


def step_smoke(manifest: ProviderManifest) -> StepResult:
    """Run the model once, under a deadline, and record what this machine did.

    Installing is not evidence. Of the four problems hit bringing up the first
    provider, three appeared only here — a kit lever whose featurizer hangs, a
    Triton kernel that reports OutOfResources on this compute capability, and
    an ``nvidia-smi`` field that returns ``[N/A]`` on unified memory. The first
    of those presents as a stall, which is why the deadline is not optional.

    What it writes is the point of the step. ``provider.toml``'s numbers are the
    reference they were measured against; the file this writes is what this
    machine actually did, and a scheduler reads that one.
    """
    t = time.time()
    if manifest.mode != "resident":
        return StepResult(
            "smoke",
            SKIPPED,
            f"[runtime] mode = {manifest.mode!r}: nothing is held to test",
            seconds=time.time() - t,
        )
    smoke_input = manifest.resolve(manifest.smoke)
    if smoke_input is None:
        return StepResult(
            "smoke",
            SKIPPED,
            "[runtime] smoke is not declared, so nothing was run — "
            "this provider stays untested on this machine",
            reason="no_smoke_declared",
            seconds=time.time() - t,
        )

    from . import backend  # imported late: starting nothing is the default

    worker = backend.worker_for(manifest.path)
    smoke_out = (
        Path(manifest.work_root).expanduser() / f"{manifest.slug}-smoke"
        if manifest.work_root
        else measured_path(manifest.slug).parent / f"{manifest.slug}-smoke"
    )
    # Emptied, not reused. The outputs assertion walks this directory, so a
    # structure left by an earlier run would keep a provider green after it
    # stopped producing one -- the same false pass the assertion exists to
    # catch, arriving through the back door. Guarded on the "-smoke" suffix
    # because this removes a tree.
    if smoke_out.name.endswith("-smoke") and smoke_out.is_dir():
        shutil.rmtree(smoke_out, ignore_errors=True)
    smoke_out.mkdir(parents=True, exist_ok=True)
    record: Dict[str, Any] = {
        "slug": manifest.slug,
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "host": socket.gethostname(),
        "manifest_vram_budget_gb": manifest.vram_budget_gb,
    }
    try:
        deadline = manifest.smoke_timeout_s
        worker.request_timeout_s = deadline
        worker.start_timeout_s = max(worker.start_timeout_s, deadline)
        pong = worker.request({"op": "ping"})
        record["build_s"] = pong.get("build_s")
        reply = worker.request(
            {
                "op": "predict",
                # Neutral: the provider decides what its input text means.
                "input": smoke_input.read_text(),
                # Under work_root when the provider declares one: a container
                # sees only what was bound, and that is the path bound for
                # exactly this.
                "out_dir": os.fspath(smoke_out),
                "name": "smoke",
                "seed": 0,
                "options": {},
            }
        )
    except Exception as exc:  # noqa: BLE001 — every failure here is the answer
        reason = getattr(exc, "reason", "") or type(exc).__name__
        where = f" (its transcript is in {worker.log_path})" if worker.log_path else ""
        return StepResult(
            "smoke",
            FAILED,
            f"the model did not answer within {manifest.smoke_timeout_s:.0f}s "
            f"or failed: {exc}{where}",
            reason=f"smoke_{reason}".lower()[:40],
            seconds=time.time() - t,
        )
    finally:
        worker.stop(grace_s=60)

    result = reply.get("result", {})
    record.update(
        {
            "wall_s": round(time.time() - t, 1),
            "timing": result.get("timing"),
            "peak_reserved_gib": result.get("peak_reserved_gib"),
            "files": len(result.get("files") or []),
        }
    )
    produced, refusal = _what_it_produced(manifest, result, smoke_out)
    record["produced"] = produced
    if refusal:
        where = f" (its transcript is in {worker.log_path})" if worker.log_path else ""
        _write_measured(manifest.slug, record)
        return StepResult(
            "smoke",
            FAILED,
            refusal + where,
            reason="smoke_produced_nothing",
            seconds=time.time() - t,
        )
    gpu = _run(
        [
            "nvidia-smi",
            "--query-gpu=name,driver_version,compute_cap",
            "--format=csv,noheader",
        ],
        timeout=30,
    )
    if gpu.returncode == 0 and gpu.stdout.strip():
        record["gpu"] = gpu.stdout.strip().splitlines()[0]

    written = _write_measured(manifest.slug, record)

    budget = record.get("peak_reserved_gib")
    over = (
        budget is not None
        and manifest.vram_budget_gb is not None
        and budget > manifest.vram_budget_gb
    )
    detail = f"one prediction in {record['wall_s']:.0f}s, peak reserved {budget} GiB{written}"
    lines = [f"timing: {result.get('timing')}"]
    if over:
        lines.append(
            f"NOTE: peak {budget} GiB exceeds the manifest's {manifest.vram_budget_gb} GiB — "
            f"that figure was measured on other hardware; schedule on the recorded value"
        )
    return StepResult("smoke", OK, detail, lines=lines, seconds=time.time() - t)


# --------------------------------------------------------------------- driver
STEPS = (step_preflight, step_environment, step_kit, step_weights, step_smoke)
# A container image is built FROM the kit's recipe, so for those providers the
# checkout has to come first. Everything else keeps the declared order.
CONTAINER_STEPS = (step_preflight, step_kit, step_environment, step_weights, step_smoke)


def run_setup(slug_or_path: str, *, only: Optional[str] = None) -> List[StepResult]:
    """Every step in order, stopping at the first that is not ok.

    Stopping is deliberate: each step assumes the previous one holds, and a
    cascade of failures caused by one missing thing buries the one that
    mattered. Re-running after fixing it continues from where it stopped,
    because every step reports ``present`` for work already done.
    """
    manifest = (
        load_manifest(slug_or_path)
        if os.path.exists(slug_or_path)
        else load_manifest(_provider_dir(slug_or_path))
    )
    results: List[StepResult] = []
    steps = STEPS if manifest.env_kind == "venv" else CONTAINER_STEPS
    for step in steps:
        name = step.__name__.removeprefix("step_")
        if only and name != only:
            continue
        result = step(manifest)
        results.append(result)
        if not result.ok:
            break
    return results


def _provider_dir(slug: str) -> Path:
    import importlib.util

    spec = importlib.util.find_spec(f"tooluniverse.remote.{slug}")
    if spec is None or not spec.submodule_search_locations:
        raise ManifestError(f"no provider package for slug {slug!r}")
    return Path(list(spec.submodule_search_locations)[0])


def exit_code(results: List[StepResult]) -> int:
    for r in results:
        if r.verdict == REFUSED:
            return EXIT_REFUSED
        if r.verdict == FAILED:
            return EXIT_FAILED
    return EXIT_OK
