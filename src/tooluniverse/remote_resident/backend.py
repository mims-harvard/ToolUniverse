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
import threading
from pathlib import Path
from typing import Dict, Optional

from .manifest import ManifestError, ProviderManifest, load
from .supervisor import ResidentWorker

_WORKERS: Dict[str, ResidentWorker] = {}
_LOCK = threading.Lock()


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
