"""
ToolUniverse Profile Configuration Loader

Simplified loader supporting HuggingFace, local files, and HTTP/HTTPS.
"""

import hashlib
import json
import zipfile
import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import yaml
import requests
from huggingface_hub import hf_hub_download

from ..utils import get_user_cache_dir
from .validator import validate_with_schema


def _is_github_repo_url(uri: str) -> bool:
    """Return True if ``uri`` looks like a GitHub repository URL (not a raw file)."""
    if not (uri.startswith("https://github.com/") or uri.startswith("http://github.com/")):
        return False
    # A repo URL has 2-3 path segments after the host: /user/repo[/tree/branch]
    # A raw file URL has more: /user/repo/raw/branch/file or /user/repo/blob/...
    parts = uri.rstrip("/").split("/")
    # ['https:', '', 'github.com', 'user', 'repo', ...]
    if len(parts) < 5:
        return False
    # If there's a 6th segment and it's 'raw', 'blob', 'releases', 'archive', it's a file URL
    if len(parts) >= 7 and parts[5] in ("raw", "blob", "releases", "archive"):
        return False
    return True


class ProfileLoader:
    """Simplified loader for ToolUniverse Profile configurations."""

    def __init__(self, cache_dir: Optional[Union[str, Path]] = None):
        """
        Initialize the Profile loader.

        Args:
            cache_dir: Directory for caching downloaded configurations
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(get_user_cache_dir()) / "profiles"

        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def load(self, uri: str) -> Dict[str, Any]:
        """
        Load Profile configuration from URI.

        Args:
            uri: Profile URI (e.g., "hf:user/repo", "./config.yaml", "https://example.com/config.yaml")

        Returns
            Loaded configuration dictionary

        Raises:
            ValueError: If URI is unsupported or configuration is invalid
        """
        config = self._load_raw(uri)

        # Resolve extends on the raw config before filling schema defaults.
        # Filling defaults first would cause absent child fields (e.g. tags=[])
        # to shadow values inherited from the base.
        config = self._resolve_extends(config)

        # Validate and fill defaults on the fully merged config
        yaml_content = yaml.dump(config, default_flow_style=False, allow_unicode=True)
        is_valid, errors, processed = validate_with_schema(yaml_content, fill_defaults_flag=True)
        if not is_valid:
            error_msg = "Configuration validation failed:\n" + "\n".join(
                f"  - {e}" for e in errors
            )
            raise ValueError(error_msg)

        return processed

    def _load_from_hf(self, uri: str) -> Dict[str, Any]:
        """Load configuration from HuggingFace Hub."""
        repo_id = uri[3:]  # Remove 'hf:' prefix

        try:
            # Try to download the config file
            config_path = hf_hub_download(
                repo_id=repo_id,
                filename="profile.yaml",
                cache_dir=self.cache_dir,
                local_files_only=False,
            )
            return self._load_from_file(config_path)
        except Exception as e:
            # Fallback: try profile.json
            try:
                config_path = hf_hub_download(
                    repo_id=repo_id,
                    filename="profile.json",
                    cache_dir=self.cache_dir,
                    local_files_only=False,
                )
                return self._load_from_file(config_path)
            except Exception:
                raise ValueError(
                    f"Failed to load Profile from HuggingFace {repo_id}: {e}"
                )

    def _load_from_url(self, uri: str) -> Dict[str, Any]:
        """Load configuration from HTTP/HTTPS URL."""
        try:
            response = requests.get(uri, timeout=30)
            response.raise_for_status()

            # Try YAML first, then JSON
            try:
                return yaml.safe_load(response.text)
            except yaml.YAMLError:
                return response.json()
        except Exception as e:
            raise ValueError(f"Failed to load Profile from URL {uri}: {e}")

    def _load_from_file(self, file_path: str) -> Dict[str, Any]:
        """Load configuration from local file."""
        path = Path(file_path)

        if not path.exists():
            raise ValueError(f"Profile file not found: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                if path.suffix.lower() in [".yaml", ".yml"]:
                    return yaml.safe_load(f)
                elif path.suffix.lower() == ".json":
                    return json.load(f)
                else:
                    # Try YAML first, then JSON
                    try:
                        f.seek(0)
                        return yaml.safe_load(f)
                    except yaml.YAMLError:
                        f.seek(0)
                        return json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to load Profile from file {file_path}: {e}")

    def _resolve_extends(
        self, config: Dict[str, Any], _chain: Optional[frozenset] = None
    ) -> Dict[str, Any]:
        """
        Resolve the ``extends`` field by loading the base Profile and merging.

        The base Profile is loaded first; the current config is then deep-merged
        on top so that every field in the current config overrides the base.
        The ``extends`` key itself is removed from the final result.

        ``_chain`` tracks the URIs already being resolved in the current call
        stack and is used to detect circular references before they cause
        infinite recursion.
        """
        base_uri = config.get("extends")
        if not base_uri:
            return config

        # Guard against non-string extends (e.g. ``extends: [a, b]``).
        # validate_with_schema would catch this later, but _resolve_extends runs
        # before validation, so emit a clear error instead of a TypeError.
        if not isinstance(base_uri, str):
            raise ValueError(
                f"Profile 'extends' must be a string URI, "
                f"got {type(base_uri).__name__}: {base_uri!r}"
            )

        if _chain is None:
            _chain = frozenset()

        if base_uri in _chain:
            raise ValueError(
                f"Circular Profile extends detected: '{base_uri}' appears more than "
                f"once in the inheritance chain {sorted(_chain)}"
            )

        try:
            raw = self._load_raw(base_uri)
            raw = self._resolve_extends(raw, _chain | {base_uri})
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Failed to load base Profile '{base_uri}': {e}") from e

        merged = self._deep_merge(raw, config)
        merged.pop("extends", None)
        return merged

    # ------------------------------------------------------------------
    # Phase 2 – URI → local directory resolution
    # ------------------------------------------------------------------

    def resolve_to_local_dir(self, uri: str) -> Path:
        """
        Resolve any URI to a local directory that contains Profile tool files.

        Supported URI forms:
        - Local path (file or directory): returned as a ``Path`` (file → parent)
        - ``hf:user/repo``: full repo downloaded via ``snapshot_download``
        - ``https://github.com/user/repo[/tree/branch]``: zip downloaded & extracted
        - Other ``http(s)://`` URL: single file downloaded; its parent dir returned

        The result is always a ``Path`` to an existing directory.
        """
        if uri.startswith("hf:"):
            return self._resolve_hf_to_dir(uri)
        if _is_github_repo_url(uri):
            return self._resolve_github_to_dir(uri)
        if uri.startswith(("http://", "https://")):
            return self._resolve_http_file_to_dir(uri)
        return self._resolve_local_to_dir(uri)

    def _resolve_local_to_dir(self, uri: str) -> Path:
        """Return a local path as a directory (file → parent)."""
        p = Path(uri)
        if not p.exists():
            raise ValueError(f"Profile path not found: {uri}")
        return p if p.is_dir() else p.parent

    def _resolve_hf_to_dir(self, uri: str) -> Path:
        """Download an entire HuggingFace repo and return its local path."""
        from huggingface_hub import snapshot_download

        repo_id = uri[3:]  # strip "hf:"
        cache_subdir = self.cache_dir / "hf"
        cache_subdir.mkdir(parents=True, exist_ok=True)
        try:
            local_dir = snapshot_download(
                repo_id=repo_id,
                cache_dir=str(cache_subdir),
            )
            return Path(local_dir)
        except Exception as e:
            raise ValueError(f"Failed to download HuggingFace repo '{repo_id}': {e}")

    def _resolve_github_to_dir(self, uri: str) -> Path:
        """Download a GitHub repo as a ZIP and extract it; return extracted dir."""
        # Parse: https://github.com/user/repo[/tree/branch]
        parts = uri.rstrip("/").split("/")
        # parts: ['https:', '', 'github.com', 'user', 'repo', ...]
        try:
            user, repo = parts[3], parts[4]
        except IndexError:
            raise ValueError(f"Cannot parse GitHub URL: {uri}")

        # Determine branch
        branch = "main"
        if len(parts) >= 7 and parts[5] == "tree":
            branch = parts[6]

        zip_url = f"https://github.com/{user}/{repo}/archive/refs/heads/{branch}.zip"

        # Use a stable cache key
        cache_key = hashlib.md5(f"{user}/{repo}@{branch}".encode()).hexdigest()[:10]
        extract_dir = self.cache_dir / "github" / cache_key
        marker = extract_dir / ".downloaded"

        if not marker.exists():
            extract_dir.mkdir(parents=True, exist_ok=True)
            try:
                resp = requests.get(zip_url, timeout=60)
                resp.raise_for_status()
                with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                    zf.extractall(extract_dir)
                marker.touch()
            except Exception as e:
                raise ValueError(
                    f"Failed to download GitHub repo {user}/{repo}@{branch}: {e}"
                )

        # The extracted root is typically "{repo}-{branch}/"
        candidates = list(extract_dir.iterdir())
        if len(candidates) == 1 and candidates[0].is_dir():
            return candidates[0]
        return extract_dir

    def _resolve_http_file_to_dir(self, uri: str) -> Path:
        """Download a single config file from an HTTP(S) URL into cache."""
        cache_key = hashlib.md5(uri.encode()).hexdigest()[:12]
        # Preserve the filename extension
        filename = uri.rstrip("/").split("/")[-1] or "profile.yaml"
        cached_file = self.cache_dir / "http" / cache_key / filename
        cached_file.parent.mkdir(parents=True, exist_ok=True)

        if not cached_file.exists():
            try:
                resp = requests.get(uri, timeout=30)
                resp.raise_for_status()
                cached_file.write_bytes(resp.content)
            except Exception as e:
                raise ValueError(f"Failed to download Profile from URL {uri}: {e}")

        return cached_file.parent

    # ------------------------------------------------------------------
    # Phase 3 – scan a local directory for tool files
    # ------------------------------------------------------------------

    @staticmethod
    def get_tool_files_from_dir(
        dir_path: Path,
    ) -> Tuple[List[Path], List[Path]]:
        """
        Scan ``dir_path`` for Python tool files and JSON config files.

        Follows the same layout convention as ``_get_user_tool_files()``:
        - Flat: ``*.py`` / ``*.json`` directly in the directory
        - Organised: ``tools/*.py`` and ``data/*.json`` / ``configs/*.json``

        ``profile.yaml`` / ``profile.json`` are excluded (handled separately).
        ``__init__.py`` is excluded (not a tool file).

        Returns:
            (python_files, json_files) — both are lists of ``Path`` objects.
        """
        python_files: List[Path] = []
        json_files: List[Path] = []

        base = Path(dir_path)
        if not base.is_dir():
            return python_files, json_files

        _SKIP_PY = {"__init__.py", "setup.py", "conftest.py"}

        # Flat layout
        for p in sorted(base.glob("*.py")):
            if p.name not in _SKIP_PY:
                python_files.append(p)
        for p in sorted(base.glob("*.json")):
            if p.stem not in ("profile",):
                json_files.append(p)

        # Organised layout
        tools_dir = base / "tools"
        if tools_dir.is_dir():
            for p in sorted(tools_dir.glob("*.py")):
                if p.name not in _SKIP_PY:
                    python_files.append(p)

        for sub in ("data", "configs"):
            sub_dir = base / sub
            if sub_dir.is_dir():
                for p in sorted(sub_dir.glob("*.json")):
                    if p.stem not in ("profile",):
                        json_files.append(p)

        return python_files, json_files

    def _load_raw(self, uri: str) -> Dict[str, Any]:
        """Load and parse a Profile URI without validation or extends resolution."""
        if uri.startswith("hf:"):
            result = self._load_from_hf(uri)
        elif uri.startswith(("http://", "https://")):
            result = self._load_from_url(uri)
        else:
            result = self._load_from_file(uri)

        if not isinstance(result, dict):
            raise ValueError(
                f"Profile configuration at '{uri}' must be a YAML/JSON mapping, "
                f"got {type(result).__name__}. Check the file is not empty."
            )
        return result

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively merge two dicts.

        For keys present in both: dicts are merged recursively; all other
        types are replaced by the override value.  Lists are replaced, not
        concatenated, so ``include_tools`` in the child fully replaces the
        parent list rather than extending it.
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ProfileLoader._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
