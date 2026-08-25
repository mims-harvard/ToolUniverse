"""Guard for the shared `join_all` helper in tests/helpers/threads.py.

`Thread.join(timeout=...)` returns the same thing whether the thread finished
or the wait expired, so concurrency tests that joined with a timeout and then
asserted on their collected results reported "concurrency is broken" when the
truth was "we stopped waiting". That produced a real flaky CI failure in
tests/unit/test_tool_finder_edge_cases.py::test_concurrent_calls, which passed
on re-run with no code change.

These tests pin the two properties that make the helper worth having: a
timeout is reported as a timeout, and the budget is shared rather than granted
per thread.
"""

import sys
import threading
import time
from pathlib import Path

import pytest

# `helpers` also comes from pytest.ini's `pythonpath`; this keeps the module
# importable when the file is run directly rather than under pytest.
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.threads import join_all

pytestmark = pytest.mark.unit


def _thread(fn, name):
    return threading.Thread(target=fn, name=name, daemon=True)


class TestJoinAll:
    def test_returns_quietly_when_every_thread_finishes(self):
        done = []
        threads = [_thread(lambda: done.append(1), f"w{i}") for i in range(3)]
        for t in threads:
            t.start()

        join_all(threads, timeout=10)
        assert len(done) == 3

    def test_timeout_is_reported_as_a_timeout(self):
        stuck = _thread(lambda: time.sleep(2), "stuck-worker")
        quick = _thread(lambda: None, "quick-worker")
        for t in (quick, stuck):
            t.start()

        with pytest.raises(AssertionError) as exc:
            join_all([quick, stuck], timeout=0.2)

        message = str(exc.value)
        # The message must name the culprit and must not let a reader
        # conclude the code under test is broken.
        assert "stuck-worker" in message
        assert "quick-worker" not in message
        assert "1 of 2" in message
        assert "not a concurrency defect" in message
        assert "0.2s" in message

    def test_budget_is_shared_across_threads_not_granted_per_thread(self):
        # Three stuck threads and a 0.3s budget must cost ~0.3s in total, not
        # 0.3s each -- the per-thread loop it replaces would have taken 0.9s.
        threads = [_thread(lambda: time.sleep(2), f"stuck-{i}") for i in range(3)]
        for t in threads:
            t.start()

        start = time.monotonic()
        with pytest.raises(AssertionError):
            join_all(threads, timeout=0.3)
        elapsed = time.monotonic() - start

        assert elapsed < 0.9, f"budget was not shared: took {elapsed:.2f}s"

    def test_accepts_any_iterable_and_reports_the_full_count(self):
        threads = [_thread(lambda: time.sleep(2), f"s{i}") for i in range(2)]
        for t in threads:
            t.start()

        with pytest.raises(AssertionError, match="2 of 2"):
            join_all(iter(threads), timeout=0.1)
