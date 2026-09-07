"""Bounded waits that fail honestly.

``threading.Thread.join(timeout=...)`` returns ``None`` whether the thread
finished or the wait expired.  A test that joins with a timeout and then
asserts on what the threads collected therefore reports "concurrent execution
is broken" when the truth is "we stopped waiting" — under CI load that is a
flaky failure whose message points at the wrong thing.

"""

from __future__ import annotations

import threading
import time
from typing import Iterable

# Chosen once, here, rather than invented per call site: it must stay well
# under pytest.ini's per-test `timeout = 60`, or pytest-timeout kills the test
# with its own generic message before join_all can explain itself.
DEFAULT_TIMEOUT = 30.0


def join_all(
    threads: Iterable[threading.Thread], timeout: float = DEFAULT_TIMEOUT
) -> None:
    """Wait up to ``timeout`` seconds *in total* for every thread to finish.

    Sharing one budget across the set keeps the wait bounded by ``timeout``
    however many threads there are, and independent of the order they are
    joined in.

    Raises:
        AssertionError: if any thread is still running at the deadline.
    """
    threads = list(threads)
    deadline = time.monotonic() + timeout
    for t in threads:
        t.join(timeout=max(0.0, deadline - time.monotonic()))
    still_running = [t.name for t in threads if t.is_alive()]
    if still_running:
        raise AssertionError(
            f"Timed out: {len(still_running)} of {len(threads)} threads still "
            f"running after {timeout}s ({', '.join(still_running)}) — a wait "
            f"budget problem, not a concurrency defect."
        )
