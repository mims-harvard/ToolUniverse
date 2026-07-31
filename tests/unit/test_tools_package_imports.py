"""Guard the generated `tooluniverse.tools` package against filename/symbol drift.

`tooluniverse/tools/__init__.py` imports every generated wrapper eagerly, so a
single wrapper whose filename does not match its tool name breaks
`import tooluniverse.tools` outright -- not just that one tool. Three wrappers
had drifted this way (ClinVar_get_variant_details,
ClinVar_get_clinical_significance, dbsnp_get_variant_by_rsid): the file on disk
differed from the import only by letter case, which resolves fine on a
case-insensitive filesystem but fails everywhere Python actually checks, so the
whole typed SDK was unimportable in the published package.

Nothing caught it because the wrappers are generated, and CI stops at the
`ruff check` step before any test runs.

These tests are deliberately name-agnostic: they assert the whole package
imports and that every exported name resolves, so the next occurrence is caught
regardless of which tool drifts.
"""

import importlib
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

TOOLS_DIR = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "tools"


def test_tools_package_imports_in_a_clean_interpreter():
    """A fresh interpreter must be able to import the package.

    Run in a subprocess so an already-imported module in this session cannot
    mask a broken import.
    """
    proc = subprocess.run(
        [sys.executable, "-c", "import tooluniverse.tools"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (
        f"import tooluniverse.tools failed:\n{proc.stderr.strip()}"
    )


def test_every_import_in_init_resolves_to_a_real_module():
    """Every `from .X import X` in __init__ must have a matching X.py.

    Compared case-sensitively against a directory listing, because
    importlib.util.find_spec can be fooled by a case-insensitive filesystem.
    """
    init_src = (TOOLS_DIR / "__init__.py").read_text()
    referenced = set(
        re.findall(r"^from \.([A-Za-z0-9_]+) import", init_src, re.MULTILINE)
    )
    on_disk = {p.stem for p in TOOLS_DIR.glob("*.py") if p.name != "__init__.py"}

    missing = sorted(referenced - on_disk)
    assert not missing, (
        "__init__.py imports modules with no matching file (check letter case): "
        f"{missing}"
    )


def test_every_exported_name_is_importable():
    """Every name in __all__ must actually be gettable off the package."""
    tools = importlib.import_module("tooluniverse.tools")
    unresolved = [name for name in tools.__all__ if not hasattr(tools, name)]
    assert not unresolved, f"names in __all__ that do not resolve: {unresolved[:20]}"


@pytest.mark.parametrize(
    "tool_name",
    [
        "ClinVar_get_variant_details",
        "ClinVar_get_clinical_significance",
        "dbsnp_get_variant_by_rsid",
    ],
)
def test_previously_unresolvable_wrappers_resolve(tool_name):
    """The three wrappers whose filenames had drifted from their tool names."""
    assert importlib.util.find_spec(f"tooluniverse.tools.{tool_name}") is not None
    assert (TOOLS_DIR / f"{tool_name}.py").name in {
        p.name for p in TOOLS_DIR.glob("*.py")
    }, f"{tool_name}.py not present with exactly that capitalisation"


def test_wrapper_filenames_match_the_symbol_they_define():
    """The generator writes f"{tool_name}.py"; filename and symbol must agree."""
    mismatched = []
    on_disk = {p.name for p in TOOLS_DIR.glob("*.py")}
    for path in sorted(TOOLS_DIR.glob("*.py")):
        if path.name in ("__init__.py", "_shared_client.py"):
            continue
        defined = re.findall(r"^def ([A-Za-z0-9_]+)\(", path.read_text(), re.MULTILINE)
        if defined and f"{defined[0]}.py" not in on_disk:
            mismatched.append((path.name, defined[0]))
    assert not mismatched, (
        "wrapper files whose defining symbol has no equally-named file: "
        f"{mismatched[:20]}"
    )
