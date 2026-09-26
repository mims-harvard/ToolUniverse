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
import time
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


def test_mcpb_launch_path_does_not_depend_on_host_substitution(tmp_path):
    """The entry point must not be spelled with ${/}.

    ``--directory ${__dirname}`` already puts uv in the bundle, so the script
    can be named relative to it, exactly as the official hello-world-uv example
    does. Spelling it "${__dirname}${/}src${/}run_stdio.py" instead makes the
    launch depend on the host expanding ${/} -- and a host that does not leaves
    uv trying to spawn a literal "...${/}src${/}run_stdio.py", which fails with
    "No such file or directory" and no server at all. Verified both ways: the
    relative form starts (including from a path with spaces and CJK
    characters), the unexpanded form dies on spawn.
    """
    manifest = json.loads(MANIFEST.read_text())
    config = manifest["server"]["mcp_config"]
    args = config["args"]

    assert "--directory" in args
    assert args[args.index("--directory") + 1] == "${__dirname}"

    script = args[-1]
    assert script == "src/run_stdio.py", (
        "name the entry point relative to --directory so the launch does not "
        f"rely on the host expanding path variables (got {script!r})"
    )
    assert "${/}" not in " ".join(args), (
        "no launch argument may depend on ${/} expansion"
    )
    assert (MCPB_DIR / script).is_file()
    assert manifest["server"]["entry_point"] == script


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
    guard = launcher.split("# Pick up a published ToolUniverse release")[0]
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


def _load_launcher_refresh(bundle_dir):
    """Exec the launcher up to its call site and hand back the refresh.

    The module runs the server at import, so the test compiles the part above
    the call and pulls the function out of the resulting namespace. ``__file__``
    decides which directory the function treats as the bundle.
    """
    launcher = (MCPB_DIR / "src" / "run_stdio.py").read_text()
    head = launcher.split("\n_refresh_tooluniverse()")[0]
    namespace = {
        "__name__": "launcher_refresh",
        "__file__": str(bundle_dir / "src" / "run_stdio.py"),
    }
    exec(compile(head, "run_stdio.py", "exec"), namespace)
    return namespace["_refresh_tooluniverse"]


def _load_launcher_namespace(bundle_dir):
    launcher = (MCPB_DIR / "src" / "run_stdio.py").read_text()
    head = launcher.split("\n_refresh_tooluniverse()")[0]
    namespace = {
        "__name__": "launcher_refresh",
        "__file__": str(bundle_dir / "src" / "run_stdio.py"),
    }
    exec(compile(head, "run_stdio.py", "exec"), namespace)
    return namespace


def _fake_bundle(tmp_path, lock_text="tooluniverse==1.4.1\n"):
    (tmp_path / "src").mkdir()
    (tmp_path / "uv.lock").write_text(lock_text)
    return tmp_path


def test_mcpb_refresh_restores_the_lock_when_the_sync_fails(tmp_path, monkeypatch):
    """A failed update must not leave uv.lock ahead of the environment.

    ``uv sync`` writes the lock before it installs, so an install that fails
    leaves the lock naming a release the environment does not have. The launch
    command is --frozen, so the next start has to reach that release -- and
    offline, with nothing cached, uv refuses and the server never comes up. The
    bundle worked a minute earlier, which makes this the one failure the update
    path must not be able to cause.
    """
    import subprocess as real_subprocess

    bundle = _fake_bundle(tmp_path)
    refresh = _load_launcher_refresh(bundle)
    lock = bundle / "uv.lock"
    original = lock.read_text()

    def fake_run(cmd, **kwargs):
        # what uv does: resolve and write the lock, then fail to install
        lock.write_text("tooluniverse==1.5.3\n")
        return real_subprocess.CompletedProcess(cmd, 1, "", "error: permission denied")

    monkeypatch.setattr("subprocess.run", fake_run)
    refresh()

    assert lock.read_text() == original, (
        "uv.lock was left pointing at a release the environment does not have"
    )
    assert not (bundle / "uv.lock.pre-update").exists()


def test_mcpb_refresh_restores_the_lock_when_the_sync_times_out(tmp_path, monkeypatch):
    """The process bound is 8 s, which a slow connection reaches easily."""
    import subprocess as real_subprocess

    bundle = _fake_bundle(tmp_path)
    refresh = _load_launcher_refresh(bundle)
    lock = bundle / "uv.lock"
    original = lock.read_text()

    def fake_run(cmd, **kwargs):
        lock.write_text("tooluniverse==1.5.3\n")
        raise real_subprocess.TimeoutExpired(cmd, 8)

    monkeypatch.setattr("subprocess.run", fake_run)
    refresh()

    assert lock.read_text() == original
    assert not (bundle / "uv.lock.pre-update").exists()


def test_mcpb_refresh_keeps_the_new_lock_when_the_sync_succeeds(tmp_path, monkeypatch):
    """The guard must not undo the upgrade it exists to protect."""
    import subprocess as real_subprocess

    bundle = _fake_bundle(tmp_path)
    refresh = _load_launcher_refresh(bundle)
    lock = bundle / "uv.lock"

    def fake_run(cmd, **kwargs):
        lock.write_text("tooluniverse==1.5.3\n")
        return real_subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("subprocess.run", fake_run)
    refresh()

    assert lock.read_text() == "tooluniverse==1.5.3\n"
    assert not (bundle / "uv.lock.pre-update").exists()


def test_mcpb_refresh_discards_a_leftover_snapshot(tmp_path, monkeypatch):
    """A snapshot left by a killed run describes nothing worth going back to.

    uv brings the environment up to the lock before this file executes, so if
    the launcher is running at all, the current lock is installed. Restoring an
    older copy would downgrade a working environment and re-upgrade it at the
    next check.
    """
    import subprocess as real_subprocess

    bundle = _fake_bundle(tmp_path, lock_text="tooluniverse==1.5.3\n")
    (bundle / "uv.lock.pre-update").write_text("tooluniverse==1.4.1\n")
    refresh = _load_launcher_refresh(bundle)

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return real_subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("subprocess.run", fake_run)
    refresh()

    assert calls, "the refresh should still run"
    assert (bundle / "uv.lock").read_text() == "tooluniverse==1.5.3\n", (
        "a stale snapshot must not roll the installed lock back"
    )
    assert not (bundle / "uv.lock.pre-update").exists()


def test_mcpb_refresh_waits_for_a_concurrent_update_instead_of_importing(
    tmp_path, monkeypatch
):
    """Two clients can share one install, and they start independently.

    The stamp is written before the sync, so without a lock the second process
    reads a fresh stamp, decides no update is due and returns straight into a
    site-packages tree the first one is still replacing. Measured on the real
    bundle: one of two simultaneous launches died with dozens of "Error reading
    .../tooluniverse/<module>.py: No such file or directory" while the other
    upgraded. So the wait has to come before the stamp is consulted.
    """
    import subprocess as real_subprocess

    bundle = _fake_bundle(tmp_path)
    namespace = _load_launcher_namespace(bundle)
    # a fresh stamp, as the process holding the lock would have just written
    (bundle / ".last-update-check").write_text("0")
    os.utime(bundle / ".last-update-check", None)
    (bundle / ".update.lock").write_text("99999")

    calls = []
    monkeypatch.setattr(
        "subprocess.run",
        lambda cmd, **kw: calls.append(cmd)
        or real_subprocess.CompletedProcess(cmd, 0, "", ""),
    )

    started = time.monotonic()
    namespace["_refresh_tooluniverse"](timeout_seconds=0)
    waited = time.monotonic() - started

    assert not calls, "two syncs must not run against one environment"
    assert waited >= 1.5, (
        "the launcher returned immediately and would import a tree that the "
        f"other process is still replacing (waited {waited:.2f}s)"
    )
    assert (bundle / ".update.lock").exists(), "someone else's lock must survive"


def test_mcpb_refresh_breaks_a_stale_update_lock(tmp_path, monkeypatch):
    """A process killed mid-update must not disable updates for good."""
    import subprocess as real_subprocess

    bundle = _fake_bundle(tmp_path)
    namespace = _load_launcher_namespace(bundle)
    stale = bundle / ".update.lock"
    stale.write_text("1")
    os.utime(stale, (time.time() - 3600, time.time() - 3600))

    calls = []
    monkeypatch.setattr(
        "subprocess.run",
        lambda cmd, **kw: calls.append(cmd)
        or real_subprocess.CompletedProcess(cmd, 0, "", ""),
    )
    namespace["_refresh_tooluniverse"](timeout_seconds=0)

    assert calls, "a stale lock must not block the update forever"
    assert not stale.exists(), "the lock must be released"


def test_mcpb_python_range_is_semver_and_no_stricter_than_the_bundle_needs():
    """The two Python ranges answer different questions, so they may differ.

    ``manifest.json`` gates installation against the Python the *user* has;
    the bundle never runs it, because uv provisions its own interpreter. The
    bundle's ``requires-python`` is that provisioning range, and it has to
    exclude interpreters the locked graph cannot install on -- 3.14 today,
    via markitdown -> magika 0.6.3 -> onnxruntime with no cp314 wheels.

    So the invariant is containment, not equality: the manifest must not be
    stricter than the bundle (that would block users whose own Python is
    irrelevant), and the pinned interpreter must satisfy both.
    """
    import re

    from packaging.specifiers import SpecifierSet
    from packaging.version import Version

    manifest = json.loads(MANIFEST.read_text())
    runtime_range = manifest["compatibility"]["runtimes"]["python"]
    assert "," not in runtime_range, "Desktop requires space-separated semver bounds"
    declared = re.search(
        r'^requires-python\s*=\s*"([^"]+)"',
        BUNDLE_PYPROJECT.read_text(),
        re.MULTILINE,
    )
    assert declared
    manifest_spec = SpecifierSet(",".join(runtime_range.split()))
    bundle_spec = SpecifierSet(declared.group(1))

    # Anything the bundle can provision, Desktop must allow to install.
    probes = [Version(f"3.{minor}") for minor in range(8, 20)]
    allowed_by_bundle = {v for v in probes if v in bundle_spec}
    allowed_by_manifest = {v for v in probes if v in manifest_spec}
    assert allowed_by_bundle <= allowed_by_manifest, (
        "manifest.json is stricter than mcpb/pyproject.toml for "
        f"{sorted(str(v) for v in allowed_by_bundle - allowed_by_manifest)}; "
        "the manifest gates on the user's own Python, which the bundle does "
        "not use, so it must not be the tighter of the two"
    )

    pinned = MCPB_DIR / ".python-version"
    pinned_version = Version(pinned.read_text().strip())
    assert pinned_version in bundle_spec, (
        f"mcpb/.python-version pins {pinned_version}, outside the bundle's "
        f"own requires-python ({bundle_spec})"
    )
    assert pinned_version in manifest_spec, (
        f"mcpb/.python-version pins {pinned_version}, which Desktop's "
        f"declared range ({runtime_range}) would reject"
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


def test_startup_never_depends_on_reaching_an_index():
    """The launch must install from the shipped lock, not resolve over the network.

    Putting --upgrade-package on the launch command made uv reach the index
    before running anything, so an index that hangs stopped a bundle that was
    already installed: measured at 44 s to failure against a blackholed index,
    which Desktop shows as "Server disconnected". With --frozen and a shipped
    lock the same scenario starts in 1.2 s.
    """
    args = json.loads(MANIFEST.read_text())["server"]["mcp_config"]["args"]

    assert "--frozen" in args, "startup must install from the lock, not re-resolve"
    assert "--upgrade-package" not in args, (
        "the refresh belongs in the launcher, where it is bounded and optional"
    )
    assert "uv lock" in (MCPB_DIR / "build.sh").read_text(), (
        "build.sh must resolve the lock that --frozen then installs from"
    )


def test_the_refresh_is_bounded_and_optional():
    """Every failure mode of the update check has to end in a started server."""
    launcher = (MCPB_DIR / "src" / "run_stdio.py").read_text()

    assert "--upgrade-package" in launcher and "tooluniverse" in launcher
    assert "UV_HTTP_TIMEOUT" in launcher, "bound the hanging-connection case"
    assert "timeout=timeout_seconds" in launcher, "bound the whole subprocess"
    assert "TOOLUNIVERSE_SKIP_SELF_UPDATE" in launcher, "give operators a switch"
    assert "TOOLUNIVERSE_UPDATE_INTERVAL_HOURS" in launcher, (
        "a machine that cannot reach the index should pay the timeout once a "
        "day, not on every launch"
    )
    assert "except Exception" in launcher, "a failed check must not be fatal"


def test_the_update_uses_the_uv_that_launched_the_server():
    """PATH is not a reliable way to find uv here.

    Desktop may invoke uv by absolute path with a PATH that does not contain
    it, and `subprocess.run(["uv", ...])` then raises FileNotFoundError -- the
    bundle keeps working but never updates again, quietly, for the life of the
    install. `uv run` exports its own path as UV, so use that first. Verified
    with uv removed from PATH: the check used to be skipped and now runs.
    """
    launcher = (MCPB_DIR / "src" / "run_stdio.py").read_text()

    assert 'os.environ.get("UV")' in launcher, "prefer the uv that launched us"
    assert "shutil.which" in launcher, "then PATH"
    assert '"uv",\n                "sync"' not in launcher, (
        "the hardcoded name is what fails when PATH lacks uv"
    )


def test_a_backwards_clock_does_not_disable_updates():
    """A stamp dated in the future would otherwise read as a recent check."""
    launcher = (MCPB_DIR / "src" / "run_stdio.py").read_text()

    assert "abs(time.time() - os.path.getmtime(stamp))" in launcher


def test_a_refused_update_is_reported_not_swallowed():
    """A release can be uninstallable for reasons the user cannot guess -- it may
    need a newer Python than the 3.12 this bundle pins, or a dependency with no
    wheel for their platform. Discarding uv's output would make that look like
    the update mechanism working, and leave a support question unanswerable.
    Verified against an unsatisfiable requirement: the server starts on the
    installed version and the log carries both the reason and that version.
    """
    launcher = (MCPB_DIR / "src" / "run_stdio.py").read_text()

    assert "stderr=subprocess.DEVNULL" not in launcher, (
        "uv's diagnosis is the only clue a stuck user leaves behind"
    )
    assert "capture_output=True" in launcher
    assert "returncode != 0" in launcher, "report a refused update"
    assert "file=sys.stderr" in launcher, "stdout carries the protocol; log to stderr"
    assert "_report_running_version" in launcher, (
        "Desktop shows the manifest version, which stops matching the library "
        "as soon as the first update lands"
    )
