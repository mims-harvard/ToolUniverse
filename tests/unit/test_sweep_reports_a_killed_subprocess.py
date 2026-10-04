"""A category killed by a signal should say so, not "invalid test output".

The xml category was OOM-killed on every weekly sweep -- 120 GB of RSS, exit
137 -- and the report said only "ERROR: incomplete or invalid test output",
which reads like a formatting problem in the runner. The subprocess's return
code carried the answer the whole time: Python reports a signal death as a
negative return code.
"""

import importlib.util
import signal
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def _sweep():
    spec = importlib.util.spec_from_file_location(
        "test_all_tools_signals", ROOT / "scripts" / "test_all_tools.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_sigkill_is_named_and_points_at_memory():
    sweep = _sweep()
    source = (ROOT / "scripts" / "test_all_tools.py").read_text("utf-8")

    assert "result.returncode < 0" in source, (
        "a signal death is only visible in the return code's sign"
    )
    assert "OOM killer" in source
    assert hasattr(signal, "SIGKILL")
    assert sweep.PATTERN_TIMEOUT_SECONDS == 600


def test_the_timeout_is_reported_from_the_constant():
    """Three places printed the number and two still said five minutes."""
    source = (ROOT / "scripts" / "test_all_tools.py").read_text("utf-8")

    assert "Timeout after 5 minutes" not in source
    assert "exceeded 5 minutes" not in source
    assert source.count("PATTERN_TIMEOUT_SECONDS") >= 4


def test_a_timeout_and_a_kill_are_different_states():
    sweep = _sweep()

    timed_out = sweep.normalize_result(
        {"error": "Timeout after 10 minutes", "timed_out": True, "exit_code": -1}
    )
    killed = sweep.normalize_result(
        {"error": "Killed by SIGKILL.", "exit_code": -9}
    )

    assert timed_out["state"] == "timeout"
    assert killed["state"] == "error"
    assert "SIGKILL" in killed["error"]
