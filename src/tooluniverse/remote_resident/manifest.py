"""``provider.toml`` -- what a GPU remote tool declares about itself.

One file per provider directory, beside its MCP server. It answers the
questions a host has to answer before it runs somebody else's model, and every
field is a fact somebody measured or pinned rather than a preference:

``[weights]``
    Every file, its size and its SHA-256. This exists because a Boltz-2
    checkpoint in this project downloaded as 1.2 % of itself and served broken
    predictions for over a month before anyone noticed -- a size check alone
    would have caught that one, a digest catches the rest. Nothing is fetched
    implicitly: a cache that is short a file is named and the provider refuses.

``[runtime]``
    ``mode = "resident"`` or ``"subprocess"``. Resident is the default because a
    held model answers in a fraction of the time a fresh one does (Boltz-2 on
    this project's GB10 box: 110 s per call as a subprocess, 47 s held), and a
    provider that cannot be held says so here with its reason.

``[gpu]``
    ``vram_budget_gb`` is the measured peak reserved, and it is what lets a host
    decide how many providers fit on one card at once. ``isolation`` states what
    the deployment actually provides, never what one would like: on hardware
    without MIG the honest answer is ``process``, and a manifest that claimed
    otherwise would be the dangerous kind of wrong.

``[env]``
    The interpreter the model's own environment lives in, and the lock file that
    rebuilds it. Providers do not share one environment -- their pinned stacks
    conflict -- so this is how the supervisor finds the right ``python``.

Reading is strict on purpose: an unknown key is a typo that would otherwise
apply silently as a default, so it is named and refused.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # 3.11+
    import tomllib as _toml
except ModuleNotFoundError:  # pragma: no cover - 3.10
    try:
        import tomli as _toml  # type: ignore[no-redef]
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ModuleNotFoundError(
            "reading provider.toml needs a TOML parser: Python 3.11 has tomllib, "
            "on 3.10 install tomli (pip install tomli)"
        ) from exc

MANIFEST_NAME = "provider.toml"

RUNTIME_MODES = ("resident", "subprocess")
GPU_POLICIES = ("required", "recommended", "none")
# What a deployment can actually promise. "mig" is absent on purpose: no box in
# this project has it, and a word nobody can honour does not belong in a
# vocabulary that a host reads to decide whether to accept other people's work.
ISOLATION = ("process", "mps", "container")
# How the model's environment is materialised. All three reach the same stack
# -- the kits offer the same three and note that everything after getting the
# stack is identical -- so this changes the argv that starts a worker and
# nothing else.
ENV_KINDS = ("venv", "docker", "apptainer")
# Whether anyone has actually run this provider end to end. "verified" is a
# claim about hardware, so it carries the hardware it was made on; "untested"
# installs the same way and says so. Nothing here promises a provider works on a
# machine nobody has tried it on -- see STANDARD.md section 9.
STATUSES = ("verified", "untested")

# Whether the kit's own environment row is something the probe reads, or
# something this provider states is not there to read. Four of the eight kits
# brought up so far return an empty row, and "empty" means two different
# things: esmfold2, esmc and rosettafold3 keep no row at all (their deployment
# variables live in per-card `configs/*.env` files that ship for h100/h200/a100
# and not for this hardware), while boltzgen has an eight-switch row that
# `stack.activate()` applies to itself in-process. Both are fine. What is not
# fine is a provider that MEANT to get a row and got nothing, which is what
# happened to openfold3: 0 variables instead of 37, no error, and its
# allocator lever reading `skipped reason=pending` for a week.
KIT_ENV_ROWS = ("probe", "none")

_SECTIONS = {
    "provider": {"slug", "description", "operations", "status", "verified_on"},
    "runtime": {
        "mode",
        "mode_reason",
        "worker",
        "launch",
        "idle_timeout_s",
        "start_timeout_s",
        "request_timeout_s",
        "smoke",
        "smoke_timeout_s",
        "worker_args",
        "outputs",
        "output_keys",
    },
    "gpu": {
        "policy",
        "vram_budget_gb",
        "shareable",
        "isolation",
        "driver_min",
        "driver_min_reason",
    },
    "env": {
        "python",
        "lock",
        "kind",
        "verify",
        "image",
        "sif",
        "container_python",
        "network",
        "work_root",
    },
    "weights": {"root_env", "root_default", "files", "fetch"},
    "kit": {
        "upstream",
        "commit",
        "subdir",
        "sparse",
        "mode",
        "levers_declined",
        # The complement of `levers_declined`, for a provider that keeps a
        # strict SUBSET of a mode's levers. Documentation, like
        # `levers_declined`: nothing reads it at launch. proteinmpnn is the
        # first to need it -- it declines every lever of the kit's `exact` line
        # on a measured timing and keeps the one lever with no device in it
        # (`fast_parse`, the read-once PDB parser), which its launcher refuses
        # to start without. A declined list alone would read as "the kit is
        # inert here", which is the conclusion that was wrong about this kit
        # twice.
        "levers_kept",
        "levers_off",
        "install",
        "package",
        "env_row",
        "env_row_reason",
        "env",
    },
}


class ManifestError(ValueError):
    """The manifest is missing, malformed, or says something impossible."""


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


class DigestMemo:
    """Digests of files already hashed, keyed by what would change if they were edited.

    The key is (size, modification time in nanoseconds). A file matching both is
    served from the memo; anything else is hashed again and recorded. It lives
    outside the weights directory so that a read-only or shared cache still
    benefits, and a memo that cannot be written is simply not written -- the
    digests are then computed afresh, which is correct, only slower.
    """

    def __init__(self, path: Path):
        self.path = path
        self._entries: Dict[str, List[Any]] = {}
        self._dirty = False
        try:
            self._entries = json.loads(path.read_text())
        except (OSError, ValueError):
            pass

    def get(self, name: str, st: os.stat_result) -> Optional[str]:
        row = self._entries.get(name)
        if not row or len(row) != 3:
            return None
        size, mtime_ns, digest = row
        if size == st.st_size and mtime_ns == st.st_mtime_ns:
            return str(digest)
        return None

    def put(self, name: str, st: os.stat_result, digest: str) -> None:
        self._entries[name] = [st.st_size, st.st_mtime_ns, digest]
        self._dirty = True

    def save(self) -> None:
        if not self._dirty:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._entries, indent=1, sort_keys=True))
        except OSError:
            pass  # a memo that cannot be written costs time, never correctness


@dataclass(frozen=True)
class WeightFile:
    name: str
    size: Optional[int] = None
    sha256: Optional[str] = None
    unpacked_dir: Optional[str] = None  # an archive that must also be extracted

    def verify(self, root: Path, memo: "DigestMemo | None" = None) -> Optional[str]:
        """None when the file is at its pin, else why it is not.

        With a ``memo``, a file whose size and modification time are unchanged
        since it was last hashed is taken at its recorded digest instead of
        being read again. Hashing this provider's 6.1 GiB costs ~4 s warm and
        far more from cold disk, and `tu remote check` would otherwise pay it
        on every invocation. Any change to either attribute forces a re-hash,
        so the shortcut cannot hide an edit.
        """
        path = root / self.name
        if not path.exists():
            return f"{self.name}: absent under {root}"
        st = path.stat()
        if self.size is not None and st.st_size != self.size:
            return (
                f"{self.name}: {st.st_size} bytes, the pin is {self.size} "
                f"({100 * st.st_size / self.size:.1f}% of it)"
            )
        if self.sha256:
            digest = None if memo is None else memo.get(self.name, st)
            if digest is None:
                digest = _sha256_of(path)
                if memo is not None:
                    memo.put(self.name, st, digest)
            if digest != self.sha256:
                return f"{self.name}: sha256 {digest[:16]}… , the pin is {self.sha256[:16]}…"
        if self.unpacked_dir and not (root / self.unpacked_dir).is_dir():
            return f"{self.name}: unpacked directory {self.unpacked_dir}/ is absent"
        return None


@dataclass(frozen=True)
class ProviderManifest:
    path: Path
    slug: str
    description: str = ""
    operations: tuple = ()
    status: str = "untested"
    verified_on: str = ""
    # What a run that actually worked leaves behind. Without this the smoke
    # step can only check that nothing raised, and that is not the question:
    # openfold3 exited 0 in 29 s, reported a GPU peak, and folded nothing,
    # because upstream caught the per-query exception and wrote a summary
    # saying "Failed Queries: 1". `outputs` are glob patterns matched against
    # the files a run produced; `output_keys` are reply fields that must be
    # present and non-empty, for a provider like enformer that returns arrays
    # and writes no files at all.
    outputs: tuple = ()
    output_keys: tuple = ()
    mode: str = "resident"
    mode_reason: str = ""
    worker: Optional[str] = None
    launch: Optional[str] = None
    idle_timeout_s: float = 0.0
    start_timeout_s: float = 900.0
    request_timeout_s: float = 3600.0
    gpu_policy: str = "none"
    vram_budget_gb: Optional[float] = None
    # The NVIDIA driver series this provider's pinned CUDA needs. There is no
    # default, because the right floor is a property of the pin and only the
    # provider knows it: boltz2 pins cu130 and needs 580, while evo2, openfold3
    # and atlasfold pin cu128 and run on 570. A hard-coded 580 refused those
    # three with a message asserting "the pinned stack is CUDA 13.0", which was
    # false for seven of eleven providers.
    driver_min: Optional[float] = None
    driver_min_reason: str = ""
    shareable: bool = True
    isolation: str = "process"
    env_python: Optional[str] = None
    env_lock: Optional[str] = None
    env_kind: str = "venv"
    env_verify: Optional[str] = None
    env_image: Optional[str] = None
    env_sif: Optional[str] = None
    env_container_python: str = "python"
    env_network: Optional[str] = None
    # Per-request output directories are created under this. A venv provider
    # needs none; a container one does, because a path the caller invents is
    # not visible inside unless something bound it.
    work_root: Optional[str] = None
    smoke: Optional[str] = None
    smoke_timeout_s: float = 1800.0
    worker_args: tuple = ()
    weights_root_env: Optional[str] = None
    weights_root_default: Optional[str] = None
    weights_fetch: Optional[str] = None
    weights: tuple = ()
    kit: Dict[str, Any] = field(default_factory=dict)

    @property
    def directory(self) -> Path:
        return self.path.parent

    def weights_root(self) -> Optional[Path]:
        if self.weights_root_env and os.environ.get(self.weights_root_env):
            return Path(os.environ[self.weights_root_env]).expanduser()
        if self.weights_root_default:
            return Path(self.weights_root_default).expanduser()
        return None

    def digest_memo_path(self) -> Path:
        root = os.environ.get("TOOLUNIVERSE_DIGEST_MEMO_DIR") or os.path.expanduser(
            "~/.cache/tooluniverse/weight-digests"
        )
        return Path(root) / f"{self.slug}.json"

    def verify_weights(self, *, deep: bool = False) -> List[str]:
        """Every problem, named. Empty means every declared file is at its pin.

        ``deep`` re-reads every file whatever the memo says. Setup uses it, so
        that what it certifies it actually hashed; `check` does not.
        """
        if not self.weights:
            return []
        root = self.weights_root()
        if root is None:
            return [
                f"no weights directory: set {self.weights_root_env} "
                f"(the manifest declares no default)"
            ]
        if not root.is_dir():
            return [f"{root}: the weights directory does not exist"]
        memo = None if deep else DigestMemo(self.digest_memo_path())
        problems = [p for p in (w.verify(root, memo) for w in self.weights) if p]
        if memo is not None:
            memo.save()
        return problems

    def resolve(self, relative: Optional[str]) -> Optional[Path]:
        """A manifest-relative path as an absolute one."""
        if not relative:
            return None
        p = Path(relative).expanduser()
        return p if p.is_absolute() else (self.directory / p).resolve()

    def python_executable(self) -> str:
        """The model environment's interpreter.

        ``[env] python`` may name an environment variable (``$NAME``) so a
        deployment can point at its own venv without editing the manifest.
        """
        raw = self.env_python
        if not raw and self.env_kind != "venv":
            # A container carries its own interpreter; [env] container_python
            # names it, and it is not a host path.
            return self.env_container_python
        if not raw:
            raise ManifestError(
                f'{self.path}: [env] python is required for mode = "resident": '
                f"the worker runs in the model's own environment, not ToolUniverse's"
            )
        if raw.startswith("$"):
            name = raw[1:]
            value = os.environ.get(name)
            if not value:
                raise ManifestError(
                    f"{self.path}: [env] python names ${name}, which is unset — "
                    f"point it at the interpreter of {self.slug}'s environment"
                )
            raw = value
        return os.fspath(Path(raw).expanduser())


def _check_keys(section: str, table: Dict[str, Any], path: Path) -> None:
    allowed = _SECTIONS[section]
    unknown = sorted(set(table) - allowed)
    if unknown:
        raise ManifestError(
            f"{path}: [{section}] has unknown key(s) {unknown}; "
            f"this section takes {sorted(allowed)}"
        )


def load(path: os.PathLike | str) -> ProviderManifest:
    """Read and validate one ``provider.toml``."""
    path = Path(path)
    if path.is_dir():
        path = path / MANIFEST_NAME
    if not path.is_file():
        raise ManifestError(f"{path}: no such manifest")
    with open(path, "rb") as f:
        try:
            doc = _toml.load(f)
        except Exception as exc:  # the parser's own words are the useful ones
            raise ManifestError(f"{path}: {exc}") from exc

    unknown_sections = sorted(set(doc) - set(_SECTIONS))
    if unknown_sections:
        raise ManifestError(
            f"{path}: unknown section(s) {unknown_sections}; "
            f"this file takes {sorted(_SECTIONS)}"
        )
    for name in _SECTIONS:
        if name in doc:
            _check_keys(
                name, {k: v for k, v in doc[name].items() if k != "files"}, path
            )

    prov = doc.get("provider", {})
    slug = prov.get("slug")
    if not slug:
        raise ManifestError(f"{path}: [provider] slug is required")

    status = prov.get("status", "untested")
    if status not in STATUSES:
        raise ManifestError(
            f"{path}: [provider] status = {status!r} is not one of {STATUSES}"
        )
    if status == "verified" and not prov.get("verified_on"):
        raise ManifestError(
            f'{path}: [provider] status = "verified" needs verified_on naming the '
            f'hardware it was verified on \u2014 a bare "verified" claims every machine'
        )

    kit = doc.get("kit", {})
    commit = kit.get("commit")
    if commit is not None and not re.fullmatch(r"[0-9a-f]{40}", str(commit)):
        raise ManifestError(
            f"{path}: [kit] commit = {commit!r} must be a full 40-character sha \u2014 "
            f"a tag or an abbreviation can move or collide, and this is what setup "
            f"fetches and names the shared checkout by"
        )

    rt = doc.get("runtime", {})
    mode = rt.get("mode", "resident")
    if mode not in RUNTIME_MODES:
        raise ManifestError(
            f"{path}: [runtime] mode = {mode!r} is not one of {RUNTIME_MODES}"
        )
    if mode == "subprocess" and not rt.get("mode_reason"):
        raise ManifestError(
            f'{path}: [runtime] mode = "subprocess" needs mode_reason — a provider '
            f"that pays the start-up cost on every request states why it must"
        )
    if doc.get("gpu", {}).get("driver_min") is not None and not doc["gpu"].get(
        "driver_min_reason"
    ):
        raise ManifestError(
            f"{path}: [gpu] driver_min needs driver_min_reason naming the CUDA "
            f"version that sets the floor \u2014 a bare number in a refusal is "
            f"what made the hard-coded one wrong for seven of eleven providers"
        )

    kit_env = doc.get("kit", {}).get("env", {})
    if not isinstance(kit_env, dict) or not all(
        isinstance(k, str) and isinstance(v, (str, int, float, bool))
        for k, v in kit_env.items()
    ):
        raise ManifestError(
            f"{path}: [kit.env] must be a table of scalar values \u2014 it is "
            f"passed to the model process verbatim"
        )

    kit_row = doc.get("kit", {}).get("env_row", "probe")
    if kit_row not in KIT_ENV_ROWS:
        raise ManifestError(
            f"{path}: [kit] env_row = {kit_row!r} is not one of {KIT_ENV_ROWS}"
        )
    if kit_row == "none" and not doc.get("kit", {}).get("env_row_reason"):
        raise ManifestError(
            f'{path}: [kit] env_row = "none" needs env_row_reason \u2014 a kit whose '
            f"mode row the probe cannot read looks exactly like a kit whose row we "
            f"failed to read, and openfold3 silently ran with 0 of its 37 variables "
            f"until someone noticed"
        )
    outputs = tuple(rt.get("outputs", ()))
    output_keys = tuple(rt.get("output_keys", ()))
    if status == "verified" and not (outputs or output_keys):
        raise ManifestError(
            f'{path}: [runtime] status = "verified" needs outputs or output_keys \u2014 '
            f"what a successful run leaves behind. Without one the smoke step can "
            f"only check that nothing raised, and a provider whose upstream catches "
            f"its own per-query exception passes that check having produced nothing"
        )

    gpu = doc.get("gpu", {})
    policy = gpu.get("policy", "none")
    if policy not in GPU_POLICIES:
        raise ManifestError(
            f"{path}: [gpu] policy = {policy!r} is not one of {GPU_POLICIES}"
        )
    isolation = gpu.get("isolation", "process")
    if isolation not in ISOLATION:
        raise ManifestError(
            f"{path}: [gpu] isolation = {isolation!r} is not one of {ISOLATION}"
        )
    if policy != "none" and mode == "resident" and gpu.get("vram_budget_gb") is None:
        raise ManifestError(
            f"{path}: [gpu] vram_budget_gb is required for a resident GPU provider — "
            f"it is what a host adds up to decide how many models fit on one card"
        )

    env_kind = doc.get("env", {}).get("kind", "venv")
    if env_kind not in ENV_KINDS:
        raise ManifestError(
            f"{path}: [env] kind = {env_kind!r} is not one of {ENV_KINDS}"
        )
    needs = {"venv": "python", "docker": "image", "apptainer": "sif"}[env_kind]
    if mode == "resident" and not doc.get("env", {}).get(needs):
        raise ManifestError(f'{path}: [env] kind = "{env_kind}" needs [env] {needs}')
    if env_kind != "venv" and not doc.get("env", {}).get("work_root"):
        raise ManifestError(
            f'{path}: [env] kind = "{env_kind}" needs [env] work_root — per-request '
            f"output directories are created under it, and a path the caller "
            f"invents is not visible inside a container unless something binds it"
        )

    wt = doc.get("weights", {})
    files = []
    for entry in wt.get("files", []):
        if "name" not in entry:
            raise ManifestError(f"{path}: every [[weights.files]] needs a name")
        if not entry.get("sha256") and not entry.get("size"):
            raise ManifestError(
                f"{path}: [[weights.files]] {entry['name']} declares neither size nor "
                f"sha256 — an unverified weight file is how a truncated download "
                f"serves wrong answers unnoticed"
            )
        files.append(
            WeightFile(
                name=entry["name"],
                size=entry.get("size"),
                sha256=entry.get("sha256"),
                unpacked_dir=entry.get("unpacked_dir"),
            )
        )

    env = doc.get("env", {})
    result = ProviderManifest(
        path=path,
        slug=slug,
        description=prov.get("description", ""),
        operations=tuple(prov.get("operations", ())),
        status=status,
        verified_on=prov.get("verified_on", ""),
        outputs=outputs,
        output_keys=output_keys,
        mode=mode,
        mode_reason=rt.get("mode_reason", ""),
        worker=rt.get("worker"),
        launch=rt.get("launch"),
        idle_timeout_s=float(rt.get("idle_timeout_s", 0.0)),
        start_timeout_s=float(rt.get("start_timeout_s", 900.0)),
        request_timeout_s=float(rt.get("request_timeout_s", 3600.0)),
        gpu_policy=policy,
        vram_budget_gb=gpu.get("vram_budget_gb"),
        driver_min=(
            float(gpu["driver_min"]) if gpu.get("driver_min") is not None else None
        ),
        driver_min_reason=gpu.get("driver_min_reason", ""),
        shareable=bool(gpu.get("shareable", True)),
        isolation=isolation,
        env_python=env.get("python"),
        env_lock=env.get("lock"),
        env_kind=env.get("kind", "venv"),
        env_verify=env.get("verify"),
        env_image=env.get("image"),
        env_sif=env.get("sif"),
        env_container_python=env.get("container_python", "python"),
        env_network=env.get("network"),
        work_root=env.get("work_root"),
        worker_args=tuple(rt.get("worker_args", ())),
        smoke=rt.get("smoke"),
        smoke_timeout_s=float(rt.get("smoke_timeout_s", 1800.0)),
        weights_root_env=wt.get("root_env"),
        weights_root_default=wt.get("root_default"),
        weights_fetch=wt.get("fetch"),
        weights=tuple(files),
        kit=dict(kit),
    )

    # A manifest that names a file it does not ship is worse than one that names
    # none: it reads as a promise the deployment can rebuild this environment.
    for key, value in (
        ("[runtime] worker", result.worker),
        ("[env] lock", result.env_lock),
    ):
        resolved = result.resolve(value)
        if resolved is not None and not resolved.exists():
            raise ManifestError(
                f"{path}: {key} = {value!r} does not exist ({resolved})"
            )
    return result
