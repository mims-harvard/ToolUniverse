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
                try:
                    if float(driver.split(".")[0]) < 580:
                        problems.append(
                            f"driver_old: {driver}; the pinned stack is CUDA 13.0 "
                            f"and needs the 580 series or newer"
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
def step_environment(manifest: ProviderManifest) -> StepResult:
    """Install the lock into the interpreter the manifest names. Never create one."""
    t = time.time()
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
            return StepResult(
                "environment",
                PRESENT,
                f"{python} already satisfies [env] verify",
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
    pins = [ln for ln in text if ln.strip() and not ln.lstrip().startswith("#")]
    boot = [ln for ln in pins if ln.split("==")[0] in ("pip", "wheel")]
    rest = [ln for ln in pins if ln not in boot]

    lines: List[str] = []
    for label, batch, extra in (("pip/wheel", boot, []), ("stack", rest, [])):
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

    return StepResult(
        "environment",
        OK,
        f"{len(pins)} pinned distributions in {python}",
        lines=lines,
        seconds=time.time() - t,
    )


# Running the kit and installing it editable leave byproducts in its tree:
# bytecode caches and the egg-info of the editable install. They are untracked,
# they are not the kit's code, and treating them as tampering would refuse
# every tree that has ever been used. Anything else untracked is still
# reported: a new file beside a module can be imported by name.
_BYPRODUCTS = ("__pycache__/", ".egg-info/", ".pyc", ".pyo", ".jit/", "/.seeded")


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
    command = install.format(
        weights_root=os.fspath(root) if root else "",
        python=python,
        kit=os.fspath(workdir),
    )
    out = _run(["bash", "-lc", command], cwd=workdir, env=env, timeout=7200)
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
                "yaml": smoke_input.read_text(),
                "out_dir": os.fspath(
                    measured_path(manifest.slug).parent / f"{manifest.slug}-smoke"
                ),
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

    path = measured_path(manifest.slug)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=1, sort_keys=True))
        written = f"; recorded in {path}"
    except OSError as exc:
        written = f"; the record could not be written ({exc})"

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
    for step in STEPS:
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
