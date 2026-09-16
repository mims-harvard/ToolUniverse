"""Regression tests for the MCPB bundle (issue #201).

Two defects motivated these tests:

  Bug #1 — older MCPB loaders rejected ``server.type: "uv"``. MCPB 0.4 now
  supports it, and Desktop needs that type to prepare dependencies before
  starting the MCP handshake. Using ``python`` with ``uv run`` instead made
  cold installs spend the handshake timeout downloading dependencies.

  Bug #2 — ``tooluniverse/__init__.py`` called ``version("tooluniverse")``
  unconditionally. Inside the bundle the dist installs as
  ``tooluniverse-mcpb-native``, so the lookup raised ``PackageNotFoundError``
  and the package crashed on import. The fix added a fallback chain.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
MCPB_DIR = REPO_ROOT / "mcpb"
MANIFEST = MCPB_DIR / "manifest.json"
BUNDLE_PYPROJECT = MCPB_DIR / "pyproject.toml"
ROOT_PYPROJECT = REPO_ROOT / "pyproject.toml"

# MCPB 0.4 adds host-managed UV setup to the earlier schema's server types.
VALID_SERVER_TYPES = {"python", "node", "binary"}


def _version_from_pyproject(path: Path) -> str:
    import re

    m = re.search(r'^version\s*=\s*"([^"]+)"', path.read_text(), re.MULTILINE)
    assert m, f"no version field in {path}"
    return m.group(1)


def _bundle_version_from_pyproject() -> str:
    return _version_from_pyproject(BUNDLE_PYPROJECT)


# ── Bug #1: manifest schema ──────────────────────────────────────────────────


def test_mcpb_manifest_exists():
    """Bundle source manifest must live in the repo so changes are reviewable."""
    assert MANIFEST.is_file(), f"missing bundle manifest at {MANIFEST}"


def test_mcpb_server_type_is_valid_enum():
    """Regression for #201: server.type must be in the MCPB schema enum."""
    manifest = json.loads(MANIFEST.read_text())
    server_type = manifest["server"]["type"]
    valid_types = VALID_SERVER_TYPES | (
        {"uv"} if manifest["manifest_version"] == "0.4" else set()
    )
    assert server_type in valid_types, (
        f"server.type {server_type!r} violates the MCPB schema enum "
        f"{sorted(valid_types)} for manifest {manifest['manifest_version']}"
    )


def test_mcpb_launcher_command_preserved():
    """UV dependencies must be installed before the MCP handshake begins."""
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["server"]["type"] == "uv"
    config = manifest["server"]["mcp_config"]
    assert config["command"] == "uv"
    assert "--no-sync" in config["args"]
    assert "--with" not in config["args"]
    assert "--python" not in config["args"]  # Shared via .python-version instead.
    assert (MCPB_DIR / ".python-version").read_text().strip() == "3.12"


def test_mcpb_python_range_has_semver_syntax_and_matching_bounds():
    """Desktop rejects PEP 440 commas even when the installed Python fits."""
    import re

    from packaging.specifiers import SpecifierSet

    manifest = json.loads(MANIFEST.read_text())
    runtime_range = manifest["compatibility"]["runtimes"]["python"]
    assert "," not in runtime_range, "Desktop requires space-separated semver bounds"
    declared = re.search(
        r'^requires-python\s*=\s*"([^"]+)"',
        BUNDLE_PYPROJECT.read_text(),
        re.MULTILINE,
    )
    assert declared
    # For the bundle's simple comparison bounds, translate the separator only.
    assert SpecifierSet(",".join(runtime_range.split())) == SpecifierSet(
        declared.group(1)
    )


def test_mcpb_manifest_version_matches_pyproject():
    """Manifest and bundle pyproject versions must stay in sync per release."""
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["version"] == _bundle_version_from_pyproject(), (
        "mcpb/manifest.json and mcpb/pyproject.toml versions drifted; "
        "bump both together when shipping a new bundle"
    )


def test_mcpb_version_tracks_root_pyproject():
    """The bundle version must track the package release version.

    The release bump touches the root pyproject.toml; without this guard the
    mcpb/ files silently lag behind (as happened after the 1.2.3 bump), and the
    published bundle ships an older version string than the package it carries.
    """
    bundle_version = _bundle_version_from_pyproject()
    root_version = _version_from_pyproject(ROOT_PYPROJECT)
    assert bundle_version == root_version, (
        f"mcpb bundle version {bundle_version!r} != root package version "
        f"{root_version!r}; bump mcpb/manifest.json and mcpb/pyproject.toml "
        f"whenever the root release version changes"
    )


# ── Bug #2: version resolution must not crash on import ──────────────────────


def test_version_is_importable_and_nonempty():
    """Regression: importing tooluniverse must not crash on version lookup."""
    import tooluniverse

    assert isinstance(tooluniverse.__version__, str)
    assert tooluniverse.__version__, "__version__ resolved to an empty string"


def test_version_falls_back_when_dist_metadata_absent():
    """Bundle scenario: when neither dist name is registered, fall back to source.

    Faithfully reproduces the failure mode by patching importlib.metadata in a
    subprocess so neither ``tooluniverse`` nor ``tooluniverse-mcpb-native``
    resolves, then asserts the resolver lands on the final source fallback.
    """
    # Faithfully reproduce the bundle scenario in a clean subprocess: force the
    # "tooluniverse" dist lookup to raise. "tooluniverse-mcpb-native" is not
    # installed in the test env either, so resolution must land on the final
    # source fallback rather than raising PackageNotFoundError.
    #
    # PYTHONPATH must point at *this* checkout's src/ — otherwise the subprocess
    # imports whatever editable install the active venv resolves (which may be a
    # different worktree that doesn't carry the fix).
    import os

    snippet = (
        "import importlib.metadata as m\n"
        "_orig = m.version\n"
        "def fake(name):\n"
        "    if name in ('tooluniverse', 'tooluniverse-mcpb-native'):\n"
        "        raise m.PackageNotFoundError(name)\n"
        "    return _orig(name)\n"
        "m.version = fake\n"
        "import tooluniverse\n"
        "print(tooluniverse.__version__)\n"
    )
    env = os.environ.copy()
    env["TOOLUNIVERSE_LIGHT_IMPORT"] = "true"
    env["PYTHONPATH"] = str(REPO_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    assert proc.returncode == 0, f"import crashed:\n{proc.stderr}"
    assert proc.stdout.strip() == "0.0.0+source", (
        f"expected source fallback, got {proc.stdout.strip()!r}\n{proc.stderr}"
    )
