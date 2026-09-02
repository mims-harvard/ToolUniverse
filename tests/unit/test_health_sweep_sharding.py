"""Sharding and summarising for the weekly tool health check.

The sweep used to run as one job that wrote its report only after the last
category. An evicted runner never reaches the upload step, so nothing survived:
10 of 12 consecutive weekly runs ended that way (exit code 143, "the runner has
received a shutdown signal"), one of them after 636 of 638 categories.

Two properties matter and are asserted here: the shards must cover every pattern
exactly once, or a silent gap looks like health; and the summary must report
categories it never heard about as missing rather than passing.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load(name: str):
    path = REPO_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sweep = _load("test_all_tools")
summarize = _load("summarize_health_sweep")


PATTERNS = [f"cat{i:03d}" for i in range(638)]


# ---------- sharding ----------

def test_shards_cover_every_pattern_exactly_once():
    """A gap between shards would look exactly like a category that passed."""
    seen = []
    for index in range(8):
        selected, _, _ = sweep.select_shard(PATTERNS, f"{index}/8")
        seen.extend(selected)
    assert sorted(seen) == sorted(PATTERNS)
    assert len(seen) == len(set(seen))


def test_shards_are_striped_not_contiguous():
    """Consecutive patterns often share an upstream host, so a contiguous block
    would concentrate one API's outage in a single shard."""
    selected, _, _ = sweep.select_shard(PATTERNS, "0/8")
    assert selected[:3] == ["cat000", "cat008", "cat016"]


def test_a_single_shard_is_the_whole_list():
    selected, _, _ = sweep.select_shard(PATTERNS, "0/1")
    assert selected == sorted(PATTERNS)


def test_more_shards_than_patterns_is_allowed():
    selected, _, _ = sweep.select_shard(["a", "b"], "5/8")
    assert selected == []


@pytest.mark.parametrize("spec", ["8/8", "-1/8", "0/0", "3/2"])
def test_out_of_range_shard_is_rejected(spec):
    with pytest.raises(ValueError):
        sweep.select_shard(PATTERNS, spec)


@pytest.mark.parametrize("spec", ["nonsense", "", "1", "a/b", "1/"])
def test_malformed_shard_is_rejected(spec):
    with pytest.raises(ValueError):
        sweep.select_shard(PATTERNS, spec)


# ---------- summarising ----------

def _log(*rows) -> str:
    return "\n".join(
        f"Tool sweep\tSTEP\t2026-08-17T06:40:{i:02d}Z [{i + 1}/6] {row}"
        for i, row in enumerate(rows)
    )


def test_summary_merges_shard_logs(tmp_path):
    (tmp_path / "a.log").write_text(_log("alpha: ✅ 7 tests passed", "beta: ❌ 9 failures"))
    (tmp_path / "b.log").write_text(_log("gamma: 🔥 ERROR: Timeout after 5 minutes"))
    results, counts, timed_out, _ = summarize.parse_logs([str(tmp_path / "*.log")])
    assert results == {"alpha": True, "beta": False, "gamma": False}
    assert counts["beta"] == 9
    assert timed_out == {"gamma"}


def test_categories_never_reached_are_missing_not_passing(tmp_path):
    (tmp_path / "a.log").write_text(_log("alpha: ✅ 1 tests passed"))
    results, counts, timed_out, _ = summarize.parse_logs([str(tmp_path / "*.log")])
    text, row = summarize.build_summary(results, counts, timed_out, set(), 638)
    assert row["never_reached"] == 637
    assert "never reached" in text
    assert "**unknown**, not passing" in text


def test_new_failures_are_ranked_with_timeouts_first(tmp_path):
    (tmp_path / "a.log").write_text(_log(
        "alpha: ❌ 20 failures", "beta: 🔥 ERROR: Timeout after 5 minutes"
    ))
    results, counts, timed_out, _ = summarize.parse_logs([str(tmp_path / "*.log")])
    _, row = summarize.build_summary(results, counts, timed_out, set(), 0)
    assert row["new_failing"] == ["beta", "alpha"]


def test_baseline_splits_new_from_known_and_recovered(tmp_path):
    (tmp_path / "a.log").write_text(_log(
        "alpha: ✅ 1 tests passed", "beta: ❌ 1 failures", "gamma: ❌ 1 failures"
    ))
    results, counts, timed_out, _ = summarize.parse_logs([str(tmp_path / "*.log")])
    _, row = summarize.build_summary(results, counts, timed_out, {"alpha", "gamma"}, 0)
    assert row["new_failing"] == ["beta"]
    assert row["recovered"] == ["alpha"]


def test_history_row_is_one_json_line(tmp_path):
    log = tmp_path / "a.log"
    log.write_text(_log("alpha: ❌ 2 failures"))
    history = tmp_path / "history.jsonl"
    baseline = tmp_path / "baseline.txt"
    baseline.write_text("")
    summarize.main([
        "--logs", str(tmp_path / "*.log"), "--baseline", str(baseline),
        "--history", str(history), "--run-id", "42", "--sha", "abc",
        "--timestamp", "2026-08-17T06:00:00+00:00", "--expected-total", "3",
    ])
    rows = [json.loads(line) for line in history.read_text().splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["run_id"] == "42"
    assert rows[0]["never_reached"] == 2
    assert rows[0]["new_failing"] == ["alpha"]


def test_history_appends_rather_than_replaces(tmp_path):
    log = tmp_path / "a.log"
    log.write_text(_log("alpha: ✅ 1 tests passed"))
    history = tmp_path / "history.jsonl"
    baseline = tmp_path / "baseline.txt"
    baseline.write_text("")
    for run in ("1", "2"):
        summarize.main([
            "--logs", str(tmp_path / "*.log"), "--baseline", str(baseline),
            "--history", str(history), "--run-id", run,
            "--timestamp", "2026-08-17T06:00:00+00:00",
        ])
    assert len(history.read_text().strip().splitlines()) == 2


def test_baseline_comments_are_ignored(tmp_path):
    path = tmp_path / "baseline.txt"
    path.write_text("# why these fail\n\nalpha\nbeta  # upstream HTTP 500\n")
    assert summarize.load_baseline(path) == {"alpha", "beta"}


def test_a_sweep_that_produced_nothing_still_summarises(tmp_path):
    """Every shard lost is itself a fact worth recording."""
    baseline = tmp_path / "baseline.txt"
    baseline.write_text("")
    history = tmp_path / "history.jsonl"
    summarize.main([
        "--logs", str(tmp_path / "nothing-*.log"), "--baseline", str(baseline),
        "--history", str(history), "--expected-total", "638",
        "--timestamp", "2026-08-17T06:00:00+00:00",
    ])
    row = json.loads(history.read_text().strip())
    assert row["reported"] == 0
    assert row["never_reached"] == 638
