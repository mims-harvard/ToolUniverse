"""Provider-controlled file resolution for remote analysis tools."""

from __future__ import annotations

import os
from numbers import Integral
from pathlib import Path
from typing import Any, Callable, Collection
from urllib.parse import urlsplit


DEFAULT_REMOTE_DATA_ROOT_ENV = "TOOLUNIVERSE_REMOTE_DATA_ROOT"
DEFAULT_MAX_H5AD_BYTES = 2_000_000_000
DEFAULT_MAX_H5AD_OBS = 1_000_000
DEFAULT_MAX_H5AD_VARS = 200_000
MAX_REMOTE_PATH_CHARS = 4096


def _positive_environment_integer(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"the provider must configure {name} as a positive integer") from None
    if value < 1:
        raise ValueError(f"the provider must configure {name} as a positive integer")
    return value


def resolve_remote_data_path(
    value: str,
    *,
    allowed_suffixes: Collection[str],
    root_env: str = DEFAULT_REMOTE_DATA_ROOT_ENV,
) -> Path:
    """Resolve a caller-supplied file inside an administrator-approved root.

    URLs, missing files, directories, traversal, and symlinks that escape the
    configured root are rejected. Error messages intentionally omit the root's
    local path so a remote caller cannot discover provider filesystem layout.
    """

    if not isinstance(value, str) or not value.strip():
        raise ValueError("a non-empty local file name is required")

    raw_value = value.strip()
    if len(raw_value) > MAX_REMOTE_PATH_CHARS or "\x00" in raw_value:
        raise ValueError("the requested data file name is invalid")
    parsed = urlsplit(raw_value)
    if parsed.scheme or parsed.netloc or raw_value.startswith("//"):
        raise ValueError(
            "URLs are not allowed; select a file from the provider data directory"
        )

    root_value = os.environ.get(root_env, "").strip()
    if not root_value:
        raise ValueError(f"the provider must configure {root_env}")

    try:
        root = Path(root_value).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValueError(
            "the configured provider data directory is unavailable"
        ) from None
    if not root.is_dir():
        raise ValueError("the configured provider data directory is unavailable")

    candidate = Path(raw_value).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValueError("the requested data file does not exist") from None

    try:
        resolved.relative_to(root)
    except ValueError:
        raise ValueError(
            "the requested file is outside the provider data directory"
        ) from None

    suffixes = {
        suffix.lower() if suffix.startswith(".") else f".{suffix.lower()}"
        for suffix in allowed_suffixes
    }
    lower_name = resolved.name.lower()
    if not suffixes or not any(lower_name.endswith(suffix) for suffix in suffixes):
        allowed = ", ".join(sorted(suffixes))
        raise ValueError(f"the data file must use one of these suffixes: {allowed}")
    if not resolved.is_file():
        raise ValueError("the requested data path is not a regular file")

    return resolved


def load_remote_h5ad(value: str, read_h5ad: Callable[[Path], Any]) -> Any:
    """Load provider-approved AnnData without exposing provider path details."""

    resolved = resolve_remote_data_path(value, allowed_suffixes={".h5ad"})
    max_bytes = _positive_environment_integer(
        "TOOLUNIVERSE_REMOTE_MAX_H5AD_BYTES", DEFAULT_MAX_H5AD_BYTES
    )
    try:
        file_size = resolved.stat().st_size
    except OSError:
        raise ValueError("the requested .h5ad file is unavailable") from None
    if file_size > max_bytes:
        raise ValueError("the requested .h5ad file exceeds the provider size limit")

    limits = (
        (
            "n_obs",
            _positive_environment_integer(
                "TOOLUNIVERSE_REMOTE_MAX_H5AD_OBS", DEFAULT_MAX_H5AD_OBS
            ),
        ),
        (
            "n_vars",
            _positive_environment_integer(
                "TOOLUNIVERSE_REMOTE_MAX_H5AD_VARS", DEFAULT_MAX_H5AD_VARS
            ),
        ),
    )

    def validate_dimensions(adata: Any) -> None:
        for attribute, limit in limits:
            observed = getattr(adata, attribute, None)
            if isinstance(observed, Integral) and not isinstance(observed, bool):
                if int(observed) > limit:
                    raise ValueError(
                        f"the requested .h5ad exceeds the provider {attribute} limit"
                    )

    # AnnData/Scanpy support backed mode, which reads metadata without
    # materializing the expression matrix. Preflight dimensions there so a
    # small, highly compressed file cannot allocate an oversized matrix before
    # its observation/variable caps are enforced. Keep a compatibility fallback
    # for simple test or third-party readers that do not accept ``backed``.
    backed_adata = None
    try:
        backed_adata = read_h5ad(resolved, backed="r")
    except TypeError:
        backed_adata = None
    except Exception:
        raise ValueError("the requested .h5ad file could not be read") from None
    if backed_adata is not None:
        try:
            validate_dimensions(backed_adata)
        finally:
            file_manager = getattr(backed_adata, "file", None)
            close = getattr(file_manager, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass

    try:
        adata = read_h5ad(resolved)
    except Exception:
        raise ValueError("the requested .h5ad file could not be read") from None
    validate_dimensions(adata)
    return adata


def resolve_remote_data_directory(value: str, *, root_env: str) -> Path:
    """Resolve a caller-selected directory inside an administrator-owned root."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError("a non-empty provider directory name is required")
    raw_value = value.strip()
    if len(raw_value) > MAX_REMOTE_PATH_CHARS or "\x00" in raw_value:
        raise ValueError("the requested provider directory name is invalid")
    parsed = urlsplit(raw_value)
    if parsed.scheme or parsed.netloc or raw_value.startswith("//"):
        raise ValueError("URLs are not allowed; select a provider directory")

    root_value = os.environ.get(root_env, "").strip()
    if not root_value:
        raise ValueError(f"the provider must configure {root_env}")
    try:
        root = Path(root_value).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValueError("the configured provider directory is unavailable") from None
    if not root.is_dir():
        raise ValueError("the configured provider directory is unavailable")

    candidate = Path(raw_value).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValueError("the requested provider directory does not exist") from None
    try:
        resolved.relative_to(root)
    except ValueError:
        raise ValueError(
            "the requested directory is outside the provider directory"
        ) from None
    if not resolved.is_dir():
        raise ValueError("the requested provider path is not a directory")
    return resolved
