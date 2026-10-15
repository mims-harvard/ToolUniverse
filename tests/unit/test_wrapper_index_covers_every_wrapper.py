"""A wrapper file with no import line is worse than a missing name.

build_tools.py keeps a wrapper whose API key is absent -- cleanup_orphaned_files
is given every name from the built-in configs for exactly that reason, and its
comment comes right out and says BRENDA, NvidiaNIM, OMIM and DisGeNET must not
be deleted because a machine lacks their keys. The index was generated from the
key-filtered set instead, so the file stayed and the import line went.

157 wrappers were in that state, all of them tools this environment declares
but cannot load. The effect is not a clean failure. Python finds the submodule
and hands it back, so

    from tooluniverse.tools import Addgene_get_plasmid

returned a module that looks importable and is not callable. Measured in a
fresh process before the fix: `type(...)` was `module`; after it is `function`.

It also made the committed index depend on which credentials the generating
machine held, which is the drift #703 noted when gating seven tools dropped
seven import lines.
"""

import ast
import glob
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "src" / "tooluniverse" / "tools"


def _imported_modules():
    tree = ast.parse((TOOLS / "__init__.py").read_text("utf-8"))
    return {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module
    }


def _wrapper_files():
    return {
        os.path.basename(path)[:-3]
        for path in glob.glob(str(TOOLS / "*.py"))
        if not os.path.basename(path).startswith("_")
    }


def test_every_wrapper_file_has_an_import_line():
    """The 157 that did not were all key-gated tools."""
    orphans = sorted(_wrapper_files() - _imported_modules())

    assert not orphans, (
        f"{len(orphans)} wrapper files are not exported, so importing them "
        f"yields a module rather than the tool: {orphans[:8]}"
    )


def test_no_import_line_points_at_a_missing_file():
    """An import line for a file that is not there breaks the whole package."""
    missing = sorted(
        name
        for name in _imported_modules()
        if name != "_shared_client" and not (TOOLS / f"{name}.py").exists()
    )

    assert not missing, missing


def test_a_key_gated_tool_imports_as_a_function_not_a_module():
    """Run in a fresh process: the first import of a submodule shadows the name.

    Testing this in-process is unreliable -- importing
    tooluniverse.tools.X binds X as the submodule on the package, which is the
    very confusion being checked for.
    """
    for name in (
        "Addgene_get_plasmid",
        "ESM2_score_missense_variant",
        "IUCN_get_conservation_status",
    ):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                f"from tooluniverse.tools import {name}\nprint(type({name}).__name__)",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
            timeout=300,
        )
        assert result.returncode == 0, result.stderr[-400:]
        assert result.stdout.strip().endswith("function"), (
            f"{name} imported as {result.stdout.strip()!r}; a module here means "
            "the index lost its import line again"
        )


def test_the_generator_indexes_files_rather_than_loadable_tools():
    source = (ROOT / "src" / "tooluniverse" / "generate_tools.py").read_text("utf-8")

    assert "generate_init(exportable, output)" in source
    assert 'if (output / f"{name}.py").exists()' in source, (
        "restricted to files that exist, or a declared-but-never-generated "
        "tool breaks the package at import time"
    )
    assert "generate_init(list(builtin_tool_dict.keys())" not in source


def test_the_metadata_file_does_not_shrink_on_a_machine_without_keys():
    """It was rebuilt from the key-filtered set, so entries disappeared."""
    source = (
        ROOT / "src" / "tooluniverse" / "build_optimizer.py"
    ).read_text("utf-8")

    assert "known_tool_names" in source
    assert "if tool_name not in new_metadata and tool_name in known_tool_names" in source
    # Sorted, so two machines that do agree produce the same bytes.
    assert "save_metadata(dict(sorted(new_metadata.items())), metadata_file)" in source


def test_a_retired_tool_is_still_dropped_from_the_metadata():
    """Carrying forward must not resurrect something removed from the configs.

    GtoPdb's two disease tools were retired in #704; their entries should be
    gone, not preserved by the carry-forward.
    """
    import json

    metadata = json.loads((TOOLS / ".tool_metadata.json").read_text("utf-8"))

    for retired in ("GtoPdb_search_diseases", "GtoPdb_get_disease_associations"):
        assert retired not in metadata, retired
