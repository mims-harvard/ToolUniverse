"""Regression guard: scripts/test_all_tools.py's --parallel flag was
declared in argparse and documented in the docstring/CI workflow (which
passes it), but never actually read anywhere in main() -- the main loop
ran strictly sequentially regardless of the flag. With several hundred
unique tool patterns and up to a 300s subprocess timeout each, this made
the weekly GitHub Actions health-check run ~4 hours, triggering
"hosted runner lost communication with the server" (confirmed live: the
workflow failed 6 of its last 7 scheduled runs).

Fixed by extracting the per-pattern loop into run_all_patterns(), which
dispatches through a concurrent.futures.ThreadPoolExecutor when
parallel=True (each pattern is already an independent subprocess call --
I/O-bound work, well suited to threads) instead of a plain for loop.
"""

import importlib.util
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

_SCRIPT_PATH = Path(__file__).parent.parent.parent / "scripts" / "test_all_tools.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("test_all_tools", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["test_all_tools"] = module
    spec.loader.exec_module(module)
    return module


_mod = _load_module()


def _slow_result(pattern, repo_root, verbose=False, fail_fast=False, delay=0.2):
    time.sleep(delay)
    return {"tests_run": 3, "passed": 3, "failed": 0}


def test_parallel_runs_faster_than_sequential_for_many_patterns():
    patterns = [f"pattern_{i}" for i in range(8)]
    repo_root = Path(".")

    with patch.object(_mod, "run_test_for_pattern", side_effect=_slow_result):
        start = time.time()
        sequential_results = _mod.run_all_patterns(
            patterns, repo_root, parallel=False
        )
        sequential_duration = time.time() - start

        start = time.time()
        parallel_results = _mod.run_all_patterns(
            patterns, repo_root, parallel=True, max_workers=8
        )
        parallel_duration = time.time() - start

    assert set(sequential_results.keys()) == set(patterns)
    assert set(parallel_results.keys()) == set(patterns)
    # 8 patterns * 0.2s each: sequential ~1.6s, parallel (8 workers) ~0.2s.
    # A generous 2x margin keeps this robust on a loaded CI runner while
    # still proving parallel is meaningfully faster, not just not-slower.
    assert parallel_duration < sequential_duration / 2


def test_parallel_and_sequential_produce_the_same_results():
    patterns = ["alpha", "beta", "gamma"]
    repo_root = Path(".")

    def fake_result(pattern, repo_root, verbose=False, fail_fast=False):
        return {"tests_run": 1, "passed": 1, "failed": 0, "pattern": pattern}

    with patch.object(_mod, "run_test_for_pattern", side_effect=fake_result):
        sequential_results = _mod.run_all_patterns(patterns, repo_root, parallel=False)
        parallel_results = _mod.run_all_patterns(patterns, repo_root, parallel=True)

    assert sequential_results == parallel_results


def test_parallel_stops_submitting_new_work_after_fail_fast():
    patterns = [f"pattern_{i}" for i in range(20)]
    repo_root = Path(".")
    call_count = {"n": 0}

    def fake_result(pattern, repo_root, verbose=False, fail_fast=False):
        call_count["n"] += 1
        if pattern == "pattern_0":
            return {"tests_run": 1, "passed": 0, "failed": 1}
        time.sleep(0.05)
        return {"tests_run": 1, "passed": 1, "failed": 0}

    with patch.object(_mod, "run_test_for_pattern", side_effect=fake_result):
        _mod.run_all_patterns(
            patterns, repo_root, fail_fast=True, parallel=True, max_workers=4
        )

    # Not all 20 should have run -- cancellation should have prevented at
    # least some not-yet-started patterns from being dispatched.
    assert call_count["n"] < len(patterns)
