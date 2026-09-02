import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


pytestmark = pytest.mark.unit

FINGERPRINT = "a" * 64

SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "test_all_tools.py"
SPEC = importlib.util.spec_from_file_location("tool_sweep_result_states", SCRIPT_PATH)
tool_sweep = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = tool_sweep
SPEC.loader.exec_module(tool_sweep)


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        ({"tests_run": 2, "passed": 2, "exit_code": 0}, "passed"),
        ({"tests_run": 2, "passed": 1, "failed": 1}, "failed"),
        ({"tests_run": 1, "passed": 1, "schema_invalid": 1}, "schema_error"),
        ({"tests_run": 0, "passed": 0, "exit_code": 0}, "no_tests"),
        ({"timed_out": True, "error": "late", "exit_code": -1}, "timeout"),
        ({"error": "boom", "exit_code": -1}, "error"),
        ({"tests_run": 0, "passed": 0, "exit_code": 2}, "error"),
        ({"tests_run": 2, "passed": 1, "exit_code": 0}, "error"),
    ],
)
def test_classify_result_has_unambiguous_terminal_states(result, expected):
    assert tool_sweep.classify_result(result) == expected


def test_zero_tests_is_never_rendered_as_a_pass():
    status = tool_sweep._format_result_status(
        {"tests_run": 0, "passed": 0, "exit_code": 0}
    )

    assert status.startswith("NO TESTS")
    assert "passed" not in status.lower()


def test_run_pattern_classifies_process_failure_without_summary_as_error(tmp_path):
    completed = subprocess.CompletedProcess([], returncode=2, stdout="", stderr="bad")

    with patch.object(tool_sweep.subprocess, "run", return_value=completed):
        result = tool_sweep.run_test_for_pattern("example", tmp_path)

    assert result["state"] == "error"
    assert result["exit_code"] == 2


def test_run_pattern_preserves_timeout_as_its_own_state(tmp_path):
    with patch.object(
        tool_sweep.subprocess,
        "run",
        side_effect=subprocess.TimeoutExpired("test", 300),
    ):
        result = tool_sweep.run_test_for_pattern("example", tmp_path)

    assert result["state"] == "timeout"
    assert result["timed_out"] is True


def test_checkpoint_round_trip_is_atomic_and_self_describing(tmp_path):
    checkpoint = tmp_path / "results.json"
    results = {
        "alpha": {"tests_run": 1, "passed": 1, "failed": 0, "exit_code": 0},
        "beta": {"tests_run": 0, "passed": 0, "failed": 0, "exit_code": 0},
    }

    tool_sweep.write_checkpoint(
        checkpoint,
        results,
        ["alpha", "beta"],
        FINGERPRINT,
        "2026-01-01T00:00:00+00:00",
        complete=True,
    )

    payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert payload["schema_version"] == tool_sweep.CHECKPOINT_SCHEMA_VERSION
    assert payload["complete"] is True
    assert payload["completed_patterns"] == 2
    assert payload["status_counts"]["passed"] == 1
    assert payload["status_counts"]["no_tests"] == 1
    assert not checkpoint.with_name("results.json.tmp").exists()
    assert (
        tool_sweep.load_checkpoint(checkpoint, ["alpha", "beta"], FINGERPRINT)
        == payload["results"]
    )


def test_checkpoint_rejects_a_tampered_state(tmp_path):
    checkpoint = tmp_path / "results.json"
    checkpoint.write_text(
        json.dumps(
            {
                "schema_version": tool_sweep.CHECKPOINT_SCHEMA_VERSION,
                "expected_patterns": ["alpha"],
                "sweep_fingerprint": FINGERPRINT,
                "results": {
                    "alpha": {
                        "state": "passed",
                        "tests_run": 0,
                        "passed": 0,
                        "exit_code": 0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="state mismatch"):
        tool_sweep.load_checkpoint(checkpoint, ["alpha"], FINGERPRINT)


@pytest.mark.parametrize(
    ("expected_patterns", "fingerprint", "message"),
    [
        (["beta"], FINGERPRINT, "test scope"),
        (["alpha"], "b" * 64, "fingerprint"),
    ],
)
def test_checkpoint_rejects_stale_scope_or_sources(
    tmp_path, expected_patterns, fingerprint, message
):
    checkpoint = tmp_path / "results.json"
    tool_sweep.write_checkpoint(
        checkpoint,
        {"alpha": {"tests_run": 1, "passed": 1, "exit_code": 0}},
        ["alpha"],
        FINGERPRINT,
        "2026-01-01T00:00:00+00:00",
        complete=True,
    )

    with pytest.raises(ValueError, match=message):
        tool_sweep.load_checkpoint(checkpoint, expected_patterns, fingerprint)


def test_sweep_fingerprint_changes_with_relevant_inputs(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "src" / "tooluniverse" / "data").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "scripts" / "test_all_tools.py").write_text("runner", encoding="utf-8")
    (tmp_path / "scripts" / "test_new_tools.py").write_text("harness", encoding="utf-8")
    (tmp_path / "src" / "tooluniverse" / "base.py").write_text(
        "BASE = 1\n", encoding="utf-8"
    )
    config = tmp_path / "src" / "tooluniverse" / "data" / "alpha_tools.json"
    config.write_text("[]\n", encoding="utf-8")
    patterns = {"alpha": [config]}

    before = tool_sweep.compute_sweep_fingerprint(tmp_path, ["alpha"], patterns)
    config.write_text('[{"name": "changed"}]\n', encoding="utf-8")
    after = tool_sweep.compute_sweep_fingerprint(tmp_path, ["alpha"], patterns)

    assert before != after


def test_resume_skips_completed_patterns_and_checkpoints_new_results():
    calls = []
    snapshots = []

    def fake_run(pattern, repo_root, verbose=False, fail_fast=False):
        calls.append(pattern)
        return {"tests_run": 1, "passed": 1, "failed": 0, "exit_code": 0}

    def record_snapshot(pattern, results):
        snapshots.append((pattern, set(results)))

    initial = {
        "alpha": {
            "state": "passed",
            "tests_run": 1,
            "passed": 1,
            "failed": 0,
            "exit_code": 0,
        }
    }
    with patch.object(tool_sweep, "run_test_for_pattern", side_effect=fake_run):
        results = tool_sweep.run_all_patterns(
            ["alpha", "beta"],
            Path("."),
            initial_results=initial,
            on_result=record_snapshot,
        )

    assert calls == ["beta"]
    assert set(results) == {"alpha", "beta"}
    assert snapshots == [("beta", {"alpha", "beta"})]


def test_fail_fast_stops_on_runtime_error():
    def fake_run(pattern, repo_root, verbose=False, fail_fast=False):
        if pattern == "alpha":
            return {"error": "boom", "exit_code": -1}
        raise AssertionError("second pattern should not run")

    with patch.object(tool_sweep, "run_test_for_pattern", side_effect=fake_run):
        results = tool_sweep.run_all_patterns(
            ["alpha", "beta"], Path("."), fail_fast=True
        )

    assert list(results) == ["alpha"]
    assert results["alpha"]["state"] == "error"


def test_markdown_report_identifies_categories_without_tests(tmp_path):
    report_path = tmp_path / "report.md"
    tool_sweep.generate_report(
        {"empty": {"tests_run": 0, "passed": 0, "exit_code": 0}},
        {"empty": [Path("empty_tools.json")]},
        0.1,
        str(report_path),
    )

    report = report_path.read_text(encoding="utf-8")
    assert "### NO_TESTS - empty" in report
    assert "Categories Without Executable Tests" in report
    assert "### PASSED - empty" not in report
