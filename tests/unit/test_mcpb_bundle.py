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
import re
import os
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
    """UV dependencies must be installed before the MCP handshake begins.

    The bundle ships no .venv and no uv.lock, so uv has to sync from the
    bundled pyproject.toml on first launch. ``--no-sync`` suppresses exactly
    that: it leaves an empty virtualenv and the server dies on the first
    third-party import (``ModuleNotFoundError: No module named 'yaml'``)
    before the handshake. ``--with .`` is unnecessary because the dependency
    list already lives in that pyproject.toml, but the sync itself is not.
    """
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["server"]["type"] == "uv"
    config = manifest["server"]["mcp_config"]
    assert config["command"] == "uv"
    assert "--no-sync" not in config["args"], (
        "--no-sync stops uv installing the bundle's dependencies, so the "
        "server never starts"
    )
    assert "--with" not in config["args"]
    # The interpreter is pinned on the command line as well as in
    # .python-version. The file alone is not enough: uv lets the environment
    # win, so a user with UV_PYTHON=3.14 exported gets a 3.14 interpreter for
    # the bundle, and the dependency set has no solution there (onnxruntime
    # publishes no cp314 wheels), which fails the install and presents in
    # Desktop as "Server disconnected" -- the same symptom as the fitz
    # breakage. Verified: with UV_PYTHON=3.14 the bundle resolves to 3.14 and
    # fails; adding --python 3.12 overrides the variable and it starts.
    args = config["args"]
    assert "--python" in args, (
        "pin the interpreter; UV_PYTHON overrides .python-version"
    )
    assert args[args.index("--python") + 1] == "3.12"
    assert (MCPB_DIR / ".python-version").read_text().strip() == "3.12"


def test_mcpb_user_config_fields_match_the_env_block():
    """Every credential field Desktop collects must reach the server, and the
    reverse: an env entry referencing a field that does not exist would be
    passed through literally as "${user_config.x}"."""
    manifest = json.loads(MANIFEST.read_text())
    user_config = manifest.get("user_config", {})
    env = manifest["server"]["mcp_config"]["env"]

    referenced = {
        value[len("${user_config.") : -1]
        for value in env.values()
        if isinstance(value, str) and value.startswith("${user_config.")
    }
    assert referenced, "no credential fields are wired into the server env"
    assert referenced <= set(user_config), (
        f"env references fields that do not exist: {sorted(referenced - set(user_config))}"
    )
    assert set(user_config) <= referenced, (
        f"fields collected but never passed to the server: {sorted(set(user_config) - referenced)}"
    )
    for name, field in user_config.items():
        assert field.get("required") is False, f"{name} must not block installation"
        assert {"type", "title", "description"} <= set(field), name
        if field["type"] == "string":
            assert field.get("sensitive") is True, (
                f"{name} holds a key; mark it sensitive"
            )


def test_mcpb_launcher_drops_blank_user_config_values():
    """A field the user left empty must not shadow a key from their .env.

    Desktop substitutes every ${user_config.*} entry, blank ones included, and
    ToolUniverse loads .env files with override=False -- so an empty
    BOLTZ_API_KEY in the environment would silently disable those tools for a
    user who had set the key in ~/.tooluniverse/.env.
    """
    launcher = (MCPB_DIR / "src" / "run_stdio.py").read_text()
    guard = launcher.split("# Enable compact mode")[0]
    namespace = {"__name__": "launcher_guard"}
    env_backup = dict(os.environ)
    try:
        os.environ.update(
            {
                "TU_TEST_BLANK": "",
                "TU_TEST_PLACEHOLDER": "${user_config.something}",
                "TU_TEST_REAL": "keep-me",
            }
        )
        exec(compile(guard, "run_stdio.py", "exec"), namespace)
        assert "TU_TEST_BLANK" not in os.environ
        assert "TU_TEST_PLACEHOLDER" not in os.environ
        assert os.environ["TU_TEST_REAL"] == "keep-me"
    finally:
        os.environ.clear()
        os.environ.update(env_backup)


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


def test_the_bundle_declares_tooluniverse_instead_of_carrying_it():
    """The bundle ships a launcher, not the library.

    A desktop extension has no self-serve update: every change to the published
    artifact is a manual submission to the directory. Carrying the source meant
    a submission per fix. Declaring the dependency and refreshing it at launch
    means a resubmission is needed only when the bundle itself changes.
    """
    bundle_pyproject = (MCPB_DIR / "pyproject.toml").read_text()

    assert re.search(r'"tooluniverse(\[[^]]*\])?>=[0-9][^"]*<2"', bundle_pyproject), (
        "the bundle must depend on tooluniverse with a major-version ceiling"
    )
    assert not (MCPB_DIR / "src" / "tooluniverse").exists(), (
        "the package is installed from PyPI, not copied into the bundle"
    )
    assert "src/tooluniverse" not in (MCPB_DIR / "build.sh").read_text()


def test_the_launcher_refreshes_that_dependency_on_every_start():
    """Without the flag uv reuses whatever it resolved the first time, so a
    published release would never reach an installed bundle. Verified on the
    built artifact: 1.5.2 comes up as 1.5.3 at the next launch with the flag,
    and stays on 1.5.2 without it."""
    args = json.loads(MANIFEST.read_text())["server"]["mcp_config"]["args"]

    assert "--upgrade-package" in args
    assert args[args.index("--upgrade-package") + 1] == "tooluniverse"
