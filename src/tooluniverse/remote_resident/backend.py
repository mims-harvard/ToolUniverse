"""One resident worker per provider, built from its ``provider.toml``.

The registry is process-wide and lazy: a provider's worker object is created the
first time something asks for it, and the model process behind it starts on the
first request (and, with ``idle_timeout_s`` set, stops again when the requests
do). Importing this module starts nothing.

``[runtime] launch`` in the manifest names the callable that builds the worker's
command line, as ``package.module:function``. That indirection is deliberate:
the declarative facts -- weights, budget, isolation, timeouts -- belong in the
manifest where anything can read them, while the one part that is genuinely
provider-specific (how to invoke that model's environment) is a named function
rather than a growing set of TOML keys that only one provider ever sets.
"""

from __future__ import annotations

import atexit
import importlib
import os
import sys
import threading
from pathlib import Path
from typing import Dict, Optional

from .manifest import ManifestError, ProviderManifest, load
from .supervisor import ResidentWorker

_WORKERS: Dict[str, ResidentWorker] = {}
_LOCK = threading.Lock()

# Set in a provider server's environment by whoever started it to ask for the model to
# be loaded as the server comes up. `tu remote pool`'s prewarm is what sets it; nothing
# else does, and nothing reads it but `warm_if_requested`.
WARM_ON_START_ENV = "TOOLUNIVERSE_REMOTE_WARM_MODEL"


def _resolve_callable(spec: str):
    if ":" not in spec:
        raise ManifestError(
            f"[runtime] launch = {spec!r} must read 'package.module:function'"
        )
    module_name, _, attr = spec.partition(":")
    module = importlib.import_module(module_name)
    try:
        return getattr(module, attr)
    except AttributeError as exc:
        raise ManifestError(f"{module_name} has no {attr!r}") from exc


def _main_directory() -> Optional[Path]:
    """The directory of the script this process was started as, if it has one."""
    main = sys.modules.get("__main__")
    path = getattr(main, "__file__", None)
    return Path(path).resolve().parent if path else None


def warm_if_requested(provider_dir: os.PathLike | str | None = None) -> Optional[str]:
    """Load this provider's model now, if whoever started this server asked for it.

    WHAT THIS IS FOR. A provider's MCP server is a CPU-only process that binds a port
    in seconds; the model behind it loads in a worker, on the first request, and that
    takes minutes. So starting the server is not warming the provider, and a scheduler
    that prewarms by starting servers hides nothing from the call that follows -- it
    reports a provider ready and the caller still waits out the whole load. This is the
    other half: the server comes up AND the weights go in.

    In a thread, because the port is what the thing that started this process is waiting
    for. `ResidentWorker.ensure_started` holds the worker's lock for the whole load, so a
    request arriving mid-load queues on it and is served when the load finishes rather
    than starting a second one.

    Returns the slug whose load was started, or None -- no request in the environment,
    no manifest next to the entry script, or a manifest that keeps no worker. A warm
    must never be the reason a server fails to start, so every failure here is one of
    those Nones, and a load that fails says so in the log the worker was given.
    """

    if os.environ.get(WARM_ON_START_ENV) != "1":
        return None
    try:
        directory = (
            Path(provider_dir) if provider_dir is not None else _main_directory()
        )
        if directory is None:
            return None
        path = directory / "provider.toml"
        if not path.is_file():
            return None
        manifest: ProviderManifest = load(path)
        if manifest.mode != "resident":
            return None
        worker = worker_for(path)
    except Exception:  # noqa: BLE001 - a warm never stops a server from starting
        return None

    def run() -> None:
        try:
            worker.ensure_started()
        except BaseException as exc:  # noqa: BLE001 - including a kit's SystemExit
            print(f"[{worker.slug}] warm start failed: {exc}", flush=True)

    threading.Thread(target=run, name=f"tu-warm-{manifest.slug}", daemon=True).start()
    return manifest.slug


def log_path_for(slug: str) -> str:
    root = os.environ.get("TOOLUNIVERSE_REMOTE_LOG_DIR") or os.path.expanduser(
        "~/.cache/tooluniverse/remote-logs"
    )
    return os.path.join(root, f"{slug}-resident.log")


def worker_for(manifest_path: os.PathLike | str) -> ResidentWorker:
    """The :class:`ResidentWorker` of the provider ``manifest_path`` declares."""
    manifest: ProviderManifest = load(manifest_path)
    if manifest.mode != "resident":
        raise ManifestError(
            f"{manifest.path}: [runtime] mode = {manifest.mode!r}; this provider "
            f"declares it is not held resident ({manifest.mode_reason})"
        )
    with _LOCK:
        existing = _WORKERS.get(manifest.slug)
        if existing is not None:
            return existing
        if not manifest.launch:
            raise ManifestError(
                f"{manifest.path}: [runtime] launch is required for a resident "
                f"provider — it names what builds the worker's command line"
            )
        worker = ResidentWorker(
            slug=manifest.slug,
            build_command=_resolve_callable(manifest.launch),
            start_timeout_s=manifest.start_timeout_s,
            request_timeout_s=manifest.request_timeout_s,
            idle_timeout_s=manifest.idle_timeout_s,
            vram_budget_gb=manifest.vram_budget_gb,
            log_path=log_path_for(manifest.slug),
            manifest=manifest,
        )
        _WORKERS[manifest.slug] = worker
        # A clean exit of the MCP server gives the card back immediately. A
        # crash does not reach here, which is why each worker also watches for
        # being orphaned and retires itself.
        if len(_WORKERS) == 1:
            atexit.register(stop_all, grace_s=10.0)
        return worker


def worker_for_provider_dir(directory: os.PathLike | str) -> ResidentWorker:
    """The worker of the provider whose directory is ``directory``."""
    return worker_for(Path(directory) / "provider.toml")


def running() -> Dict[str, Optional[float]]:
    """``{slug: vram_budget_gb}`` for every worker currently holding the card.

    What a scheduler above this reads to know what is resident right now; the
    budgets are the manifests' measured peaks, not live device queries.
    """
    with _LOCK:
        return {
            slug: w.vram_budget_gb for slug, w in _WORKERS.items() if w.is_running()
        }


def stop_all(*, grace_s: float = 30.0) -> None:
    """Retire every worker this process started. Safe to call twice."""
    with _LOCK:
        workers = list(_WORKERS.values())
    for w in workers:
        try:
            w.stop(grace_s=grace_s)
        except Exception:  # noqa: BLE001 - shutdown must not raise
            pass
