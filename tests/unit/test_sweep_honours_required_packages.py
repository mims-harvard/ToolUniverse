"""required_packages was declared by 119 tools and read by nothing.

Only `tu info` displayed it. So a tool needing pybiolib, py3Dmol or biopython
was run in the sweep anyway, failed on the import, and was counted as a broken
tool that no change to the tool could fix. Five categories in the 2026-10-04
sweep were that and nothing else: dtu_protein, structure_annotation,
protein_structure_3d, molecule_3d and dataset.

The runner now skips a tool whose declared distributions are not installed,
with the reason, alongside the existing skips for a missing credential, a
caller-supplied input file and a long-running upstream job.

Checked against that sweep before changing anything: 24 tools across 9
categories gain a skip, and none of those categories was passing -- so this
only relabels failures, it hides no working tool. That is the check that kept
FDA_API_KEY undeclared in #699, where declaring it would have skipped 186
tools that work without it.
"""

import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src" / "tooluniverse" / "data"


def _module(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_an_installed_distribution_is_not_reported_missing():
    runner = _module("scripts/test_new_tools.py", "tnt_pkgs")

    assert runner._missing_distributions(["requests", "numpy"]) == []


def test_a_missing_distribution_is_reported_by_its_pip_name():
    """Checked by distribution, not module: biopython imports as Bio."""
    runner = _module("scripts/test_new_tools.py", "tnt_pkgs2")

    assert runner._missing_distributions(
        ["requests", "definitely-not-installed-tu-probe"]
    ) == ["definitely-not-installed-tu-probe"]


def test_an_empty_declaration_skips_nothing():
    runner = _module("scripts/test_new_tools.py", "tnt_pkgs3")

    assert runner._missing_distributions([]) == []


def test_the_runner_skips_before_trying_the_tool():
    source = (ROOT / "scripts" / "test_new_tools.py").read_text("utf-8")

    assert 'tool.get("required_packages")' in source
    assert "skipped_missing_package" in source
    assert "Skipped missing package:" in source


def test_the_sweep_labels_the_reason():
    sweep = _module("scripts/test_all_tools.py", "tat_pkgs")

    only = sweep.normalize_result(
        {"skipped": 1, "skipped_missing_package": 1, "tests_run": 0}
    )
    mixed = sweep.normalize_result(
        {
            "skipped": 3,
            "skipped_missing_package": 1,
            "skipped_local_input": 1,
            "tests_run": 0,
        }
    )

    assert "package that is not installed" in sweep._format_result_status(only)
    assert "credential" not in sweep._format_result_status(only)
    label = sweep._format_result_status(mixed)
    assert "1 need a package" in label
    assert "1 need an input file" in label
    assert "1 need a credential" in label


@pytest.mark.parametrize(
    ("file_name", "tool_name", "package"),
    [
        ("dataset_tools.json", "drugbank_full_search", "pyarrow"),
        ("molecule_3d_tools.json", "visualize_molecule_3d", "py3Dmol"),
    ],
)
def test_the_two_silent_dependencies_are_declared(file_name, tool_name, package):
    """drugbank_full_search reads parquet; visualize_molecule_3d imports py3Dmol."""
    tools = json.loads((DATA / file_name).read_text("utf-8"))
    tool = next(t for t in tools if t["name"] == tool_name)

    assert package in (tool.get("required_packages") or [])
