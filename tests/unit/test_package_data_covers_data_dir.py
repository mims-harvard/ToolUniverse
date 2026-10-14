"""Every data file in the source tree must reach the installed package.

``package-data`` is a list of globs, and a glob that names subdirectories one
at a time drops the ones nobody remembered to add. That is not visible in a
source checkout or an editable install -- only in a wheel -- so it went
unnoticed from the introduction of ``data/remote_tools/`` through 1.5.6: the 42
remote tool definitions ``list_built_in_tools`` reads were in no release.

This test reads the globs out of ``pyproject.toml`` and matches them against
the files actually on disk, so adding a data subdirectory cannot quietly ship
empty.
"""

import fnmatch
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

try:  # 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - 3.10 and earlier
    import tomli as tomllib

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "src" / "tooluniverse"
DATA_ROOT = PACKAGE_ROOT / "data"

# Not data: generated output and editor leftovers that no release needs.
IGNORED_NAMES = {".DS_Store"}
IGNORED_SUFFIXES = (".pyc", ".backup")


def _declared_globs():
    pyproject = REPO_ROOT / "pyproject.toml"
    if not pyproject.is_file():
        pytest.skip("not running from a source checkout")
    config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    package_data = (
        config.get("tool", {})
        .get("setuptools", {})
        .get("package-data", {})
        .get("tooluniverse")
    )
    assert package_data, "pyproject.toml declares no package-data for tooluniverse"
    return package_data


def _is_covered(relative_path: str, globs) -> bool:
    """Match the way setuptools does: ``**`` spans directories, ``*`` does not.

    ``fnmatch`` lets ``*`` cross a ``/``, which would call every file covered
    and make this test pass on the very configuration that shipped broken. So
    a glob without ``**`` is compared segment by segment instead.
    """
    parts = relative_path.split("/")
    for pattern in globs:
        if "**" in pattern:
            prefix = pattern.split("**")[0].rstrip("/")
            if not prefix or relative_path.startswith(prefix + "/"):
                return True
            continue
        pattern_parts = pattern.split("/")
        if len(pattern_parts) != len(parts):
            continue
        if all(fnmatch.fnmatch(p, pat) for p, pat in zip(parts, pattern_parts)):
            return True
    return False


def _data_files():
    for path in sorted(DATA_ROOT.rglob("*")):
        if not path.is_file():
            continue
        if path.name in IGNORED_NAMES or path.name.endswith(IGNORED_SUFFIXES):
            continue
        if "__pycache__" in path.parts:
            continue
        yield path.relative_to(PACKAGE_ROOT).as_posix()


def test_every_data_file_is_covered_by_package_data():
    if not DATA_ROOT.is_dir():
        pytest.skip("data directory not present in this layout")
    globs = _declared_globs()
    uncovered = [rel for rel in _data_files() if not _is_covered(rel, globs)]
    assert not uncovered, (
        f"{len(uncovered)} file(s) under src/tooluniverse/data/ are not matched by "
        f"package-data {globs} and would be missing from the wheel, e.g. "
        f"{uncovered[:5]}"
    )


def test_the_remote_tool_definitions_are_covered():
    """The directory whose omission this test exists to prevent."""
    remote_dir = DATA_ROOT / "remote_tools"
    if not remote_dir.is_dir():
        pytest.skip("data/remote_tools not present in this layout")
    globs = _declared_globs()
    definitions = sorted(remote_dir.glob("*.json"))
    assert definitions, "expected remote tool definitions in data/remote_tools"
    for path in definitions:
        rel = path.relative_to(PACKAGE_ROOT).as_posix()
        assert _is_covered(rel, globs), f"{rel} would be missing from the wheel"


def test_a_per_directory_glob_list_is_recognized_as_insufficient():
    """Guard the matcher itself: it must reject what actually shipped.

    With ``fnmatch`` alone, ``data/*`` matches ``data/remote_tools/boltz.json``
    and the check above would have passed on 1.5.6.
    """
    shipped_1_5_6 = ["data/*", "data/packages/*", "data/geant4/*"]
    assert not _is_covered("data/remote_tools/boltz_tools.json", shipped_1_5_6)
    assert _is_covered("data/packages/anything.json", shipped_1_5_6)
    assert _is_covered("data/opentargets_tools.json", shipped_1_5_6)
    assert _is_covered("data/remote_tools/boltz_tools.json", ["data/*", "data/**/*"])
