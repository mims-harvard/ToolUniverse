"""The weekly report has to say why a category failed, not only that it did.

Run 37193646910 flagged 42 new failures, and about ten of them passed on every
machine except the CI runner. Its artifacts held a markdown report and a
progress log, both counts only -- the per-test messages live in the sweep's
JSON results, which the workflow never uploaded. So "rdkit_cheminfo: 6
failures" could not be told apart from an outage without rebuilding CI's
environment locally, which is how it was eventually found: RDKit is
deliberately left out of the dev extra, and seven tools that need it declared
nothing, so CI ran them and counted the import error.
"""

import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src" / "tooluniverse" / "data"


def _mod():
    spec = importlib.util.spec_from_file_location(
        "summarize_health_sweep_why", ROOT / "scripts" / "summarize_health_sweep.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _results(tmp_path, results, name="TOOL_TEST_RESULTS_0.json"):
    path = tmp_path / name
    path.write_text(json.dumps({"results": results}), encoding="utf-8")
    return str(path)


def test_first_errors_reads_each_categorys_own_message(tmp_path):
    mod = _mod()
    path = _results(tmp_path, {
        "rdkit_cheminfo": {"raw_output": "  ❌ RDKit_x Ex 1: Failed - RDKit is required.\n"},
        "elixir_tess": {"raw_output": "  ❌ E Ex 1: Failed - returned HTTP 522\n"},
        "ok": {"raw_output": "  ✅ fine\n"},
    })

    errors = mod.first_errors([path])

    assert errors["rdkit_cheminfo"] == "RDKit is required."
    assert errors["elixir_tess"] == "returned HTTP 522"
    assert "ok" not in errors


def test_a_schema_mismatch_is_reported_too(tmp_path):
    mod = _mod()
    path = _results(tmp_path, {
        "x": {"raw_output": "  ⚠️  T Ex 1: Schema Mismatch: At root: bad\n"},
    })

    assert mod.first_errors([path])["x"] == "At root: bad"


def test_unreadable_or_missing_results_are_skipped(tmp_path):
    mod = _mod()
    bad = tmp_path / "TOOL_TEST_RESULTS_9.json"
    bad.write_text("{not json", encoding="utf-8")

    assert mod.first_errors([str(bad), str(tmp_path / "nope_*.json")]) == {}
    assert mod.first_errors(None) == {}


def test_the_summary_lists_the_reason_for_each_new_failure(tmp_path):
    mod = _mod()
    results = {"rdkit_cheminfo": False, "fine": True}
    errors = {"rdkit_cheminfo": "RDKit is required."}

    text, _ = mod.build_summary(
        results, {"rdkit_cheminfo": 6}, set(), set(), 2, errors=errors
    )

    assert "First error per new failure" in text
    assert "- `rdkit_cheminfo`: RDKit is required." in text


def test_a_summary_without_results_is_unchanged(tmp_path):
    """--results is optional; an older invocation still works."""
    mod = _mod()

    text, _ = mod.build_summary({"a": False}, {"a": 1}, set(), set(), 1)

    assert "First error per new failure" not in text


def test_the_workflow_writes_uploads_and_summarizes_the_json():
    workflow = (
        ROOT / ".github" / "workflows" / "weekly-tool-healthcheck.yml"
    ).read_text("utf-8")

    assert "--json-output TOOL_TEST_RESULTS_${{ matrix.shard }}.json" in workflow
    assert "TOOL_TEST_RESULTS_${{ matrix.shard }}.json" in workflow.split(
        "upload-artifact", 1
    )[1]
    assert "--results 'shards/*/TOOL_TEST_RESULTS_*.json'" in workflow


@pytest.mark.parametrize(
    ("file_name", "tool_name"),
    [
        ("chem_compute_tools.json", "Chem_sa_score"),
        ("drug_properties_tools.json", "DrugProps_lipinski_filter"),
        ("drug_properties_tools.json", "DrugProps_calculate_qed"),
        ("drug_properties_tools.json", "DrugProps_pains_filter"),
        ("rdkit_cheminfo_tools.json", "RDKit_pharmacophore_features"),
        ("rdkit_cheminfo_tools.json", "RDKit_matched_molecular_pair"),
    ],
)
def test_every_rdkit_tool_declares_it(file_name, tool_name):
    """RDKit is kept out of the dev extra on purpose, so CI lacks it."""
    tools = json.loads((DATA / file_name).read_text("utf-8"))
    tool = next(t for t in tools if t["name"] == tool_name)

    assert "rdkit" in (tool.get("required_packages") or [])
