"""--skip-remote has to drop every remote provider, not a list of ten names.

`src/tooluniverse/remote/<slug>/` is a provider that needs its own server, so
the weekly sweep passes --skip-remote. That flag carried a hardcoded list of
ten patterns and the repository grew to 30 provider directories, so 24 of them
were still being tested. Without its server the tool is never loaded, so each
one failed with "Tool 'X' not found even after loading tools" and the report
counted 22 categories of phantom failures -- a third of everything it called
broken, none of it a defect in any tool.

Derived from the filesystem now. These tests exist so a provider added later
cannot slip back out of the skip list, which is exactly how the drift happened.
"""

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
REMOTE_ROOT = ROOT / "src" / "tooluniverse" / "remote"


def _sweep():
    spec = importlib.util.spec_from_file_location(
        "test_all_tools_under_test", ROOT / "scripts" / "test_all_tools.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _provider_dirs():
    return {
        entry.name
        for entry in REMOTE_ROOT.iterdir()
        if entry.is_dir() and not entry.name.startswith(("_", "."))
    }


def test_every_remote_provider_directory_is_skipped():
    """The drift this replaces: 30 directories, 10 of them on the list."""
    skipped = _sweep().remote_tool_patterns()
    providers = _provider_dirs()

    missing = sorted(providers - skipped)
    assert not missing, (
        "these remote providers would be tested without their server, and each "
        f"reports as a failed category: {missing}"
    )
    assert len(providers) >= 20, (
        f"only {len(providers)} provider directories found; if remote/ moved, "
        "this test is no longer checking anything"
    )


def test_the_known_phantom_failures_are_gone():
    """The 22 categories the 2026-10-03 sweep reported as failures."""
    phantom = """borzoi cell2location cellrank celltypist chrombpnet enformer
    harmony ldsc liana macs3 milo mofa monocle3 paga scanvi scrublet scvelo
    scvi singler slingshot squidpy tangram""".split()
    skipped = _sweep().remote_tool_patterns()

    still_tested = [name for name in phantom if name not in skipped]
    assert not still_tested, still_tested


def test_the_external_services_stay_skipped():
    """Not every skipped pattern is a provider directory."""
    skipped = _sweep().remote_tool_patterns()

    for name in ("blast", "simbad", "uspto", "depmap"):
        assert name in skipped, (
            f"{name} needs a remote service but has no remote/ directory, so "
            "it has to stay on the explicit list"
        )


def test_the_skip_list_is_not_hardcoded():
    """A list in the source is what drifted; the test should notice a revert."""
    source = (ROOT / "scripts" / "test_all_tools.py").read_text(encoding="utf-8")

    assert "remote_tool_patterns" in source
    assert "REMOTE_ROOT" in source or "remote" in source
    # The old list named these inline. Any of them reappearing as a literal in
    # the skip construction means the filesystem derivation was replaced.
    assert "'transcriptformer'" not in source, (
        "the hardcoded remote list is back; it drifted by 24 providers last time"
    )
