import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


pytestmark = pytest.mark.unit
REPO_ROOT = Path(__file__).parents[2]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sweep = _load("tool_sweep_sharding", REPO_ROOT / "scripts" / "test_all_tools.py")
aggregate = _load(
    "aggregate_tool_sweep", REPO_ROOT / "scripts" / "aggregate_tool_sweep.py"
)


def _result(state="passed"):
    results = {
        "passed": {"tests_run": 1, "passed": 1, "failed": 0, "exit_code": 0},
        "failed": {"tests_run": 1, "passed": 0, "failed": 1, "exit_code": 1},
        "no_tests": {"tests_run": 0, "passed": 0, "failed": 0, "exit_code": 0},
    }
    return results[state]


def _checkpoint(tmp_path, index, count, patterns, states=None, complete=True):
    states = states or ["passed"] * len(patterns)
    path = tmp_path / f"shard-{index}.json"
    sweep.write_checkpoint(
        path,
        {
            pattern: _result(state)
            for pattern, state in zip(patterns, states, strict=True)
        },
        patterns,
        "2026-01-01T00:00:00+00:00",
        complete,
        run_metadata={"shard_index": index, "shard_count": count},
    )
    return path


def test_shards_are_stable_disjoint_and_exhaustive():
    patterns = ["zeta", "alpha", "gamma", "beta", "theta", "delta"]

    shards = [sweep.select_shard(patterns, index, 4) for index in range(4)]

    flattened = [pattern for shard in shards for pattern in shard]
    assert sorted(flattened) == sorted(patterns)
    assert len(flattened) == len(set(flattened))
    assert shards == [
        ["alpha", "theta"],
        ["beta", "zeta"],
        ["delta"],
        ["gamma"],
    ]


@pytest.mark.parametrize(
    ("index", "count"),
    [(-1, 4), (4, 4), (0, 0)],
)
def test_shard_selection_rejects_invalid_bounds(index, count):
    with pytest.raises(ValueError):
        sweep.select_shard(["alpha"], index, count)


def test_checkpoint_records_shard_metadata(tmp_path):
    path = _checkpoint(tmp_path, 2, 4, ["alpha"])

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["run"] == {"shard_count": 4, "shard_index": 2}


def test_aggregate_accepts_complete_shards_including_an_empty_shard(tmp_path):
    paths = [
        _checkpoint(tmp_path, 0, 4, ["alpha"]),
        _checkpoint(tmp_path, 1, 4, ["beta"], ["no_tests"]),
        _checkpoint(tmp_path, 2, 4, ["gamma"]),
        _checkpoint(tmp_path, 3, 4, []),
    ]

    payload = aggregate.aggregate_checkpoints(paths, expected_shards=4)

    assert payload["complete"] is True
    assert payload["errors"] == []
    assert payload["completed_patterns"] == 3
    assert payload["status_counts"]["passed"] == 2
    assert payload["status_counts"]["no_tests"] == 1


def test_aggregate_reports_a_missing_or_interrupted_shard(tmp_path):
    paths = [
        _checkpoint(tmp_path, 0, 2, ["alpha"]),
    ]

    payload = aggregate.aggregate_checkpoints(paths, expected_shards=2)

    assert payload["complete"] is False
    assert "Expected 2 shard checkpoint(s), found 1" in payload["errors"]


def test_aggregate_rejects_duplicate_pattern_assignment(tmp_path):
    paths = [
        _checkpoint(tmp_path, 0, 2, ["alpha"]),
        _checkpoint(tmp_path, 1, 2, ["alpha"]),
    ]

    payload = aggregate.aggregate_checkpoints(paths, expected_shards=2)

    assert payload["complete"] is False
    assert any(
        "duplicate expected pattern 'alpha'" in error for error in payload["errors"]
    )
    assert any(
        "duplicate completed pattern 'alpha'" in error for error in payload["errors"]
    )


def test_aggregate_requires_the_exact_shard_index_set(tmp_path):
    paths = [
        _checkpoint(tmp_path, 0, 2, ["alpha"]),
        _checkpoint(tmp_path, 2, 2, ["beta"]),
    ]

    payload = aggregate.aggregate_checkpoints(paths, expected_shards=2)

    assert payload["complete"] is False
    assert any("shard_index 2 is out of range" in error for error in payload["errors"])
    assert "Missing shard index(es): [1]" in payload["errors"]


def test_markdown_lists_failures_and_coverage_gaps(tmp_path):
    path = _checkpoint(
        tmp_path,
        0,
        1,
        ["broken", "empty"],
        ["failed", "no_tests"],
    )
    payload = aggregate.aggregate_checkpoints([path], expected_shards=1)

    markdown = aggregate.render_markdown(payload)

    assert "## Failed (1)" in markdown
    assert "`broken`" in markdown
    assert "## No Tests (1)" in markdown
    assert "`empty`" in markdown


def test_baseline_comparison_separates_new_known_and_recovered(tmp_path):
    checkpoint = _checkpoint(
        tmp_path,
        0,
        1,
        ["known", "new", "recovered"],
        ["failed", "failed", "passed"],
    )
    baseline = tmp_path / "baseline.txt"
    baseline.write_text("known\nrecovered # old failure\n", encoding="utf-8")
    payload = aggregate.aggregate_checkpoints([checkpoint], expected_shards=1)

    aggregate.add_baseline_comparison(payload, baseline)

    assert payload["baseline"] == {
        "new_failures": ["new"],
        "known_failures": ["known"],
        "recovered": ["recovered"],
    }
    markdown = aggregate.render_markdown(payload)
    assert "## New Failing Categories (1)" in markdown
    assert "## Known Failing Categories (1)" in markdown
    assert "## Baseline Categories That Passed (1)" in markdown


def test_aggregate_cli_writes_artifacts_and_fails_for_test_failures(tmp_path):
    checkpoint = _checkpoint(tmp_path, 0, 1, ["broken"], ["failed"])
    json_output = tmp_path / "aggregate.json"
    markdown_output = tmp_path / "aggregate.md"
    argv = [
        "aggregate_tool_sweep.py",
        str(checkpoint),
        "--expected-shards",
        "1",
        "--json-output",
        str(json_output),
        "--markdown-output",
        str(markdown_output),
    ]

    with patch.object(sys, "argv", argv):
        exit_code = aggregate.main()

    assert exit_code == 1
    assert json_output.is_file()
    assert markdown_output.is_file()
    assert not json_output.with_name("aggregate.json.tmp").exists()


def test_weekly_workflow_bounds_concurrency_and_preserves_partial_results():
    workflow_path = REPO_ROOT / ".github" / "workflows" / "weekly-tool-healthcheck.yml"
    workflow = yaml.load(
        workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    health_check = workflow["jobs"]["health-check"]
    run_step = next(step for step in health_check["steps"] if step.get("id") == "sweep")

    assert health_check["strategy"]["max-parallel"] == "2"
    assert health_check["strategy"]["matrix"]["shard"] == ["0", "1", "2", "3"]
    assert run_step["timeout-minutes"] == "165"
    assert "--max-workers 6" in run_step["run"]
    assert "--shard-count 4" in run_step["run"]
    assert any(
        step.get("uses") == "actions/upload-artifact@v4"
        and step.get("if") == "always()"
        for step in health_check["steps"]
    )
