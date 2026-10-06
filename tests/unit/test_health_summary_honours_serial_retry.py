"""A failure the sweep's serial re-run cleared is not a failure.

The sweep re-runs load-shaped failures one at a time after the parallel pass
and keeps a pass. Its JSON records the pass; its log keeps both lines. Run
37273817054's summary read only the first, so 12 categories the sweep had
recorded as passing were listed among the new failures.
"""

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def _mod():
    spec = importlib.util.spec_from_file_location(
        "summarize_health_sweep_retry", ROOT / "scripts" / "summarize_health_sweep.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _log(tmp_path, text):
    path = tmp_path / "sweep_output_0.log"
    path.write_text(text, encoding="utf-8")
    return [str(path)]


# The shape of shard logs from run 37273817054.
LOG = """\
[1/4] gxa: FAILED: 4 test failure(s)
[2/4] dblp: FAILED: 6 test failure(s)
[3/4] neurovault: TIMEOUT: exceeded 600s
[4/4] brenda: PASSED: 3 test(s)

🔁 Re-running 3 category/categories serially: their failures all look like upstream load
   [1/3] dblp: still failed
   [2/3] gxa: passed (was failed under load)
   [3/3] neurovault: still timeout
"""


def test_a_serial_pass_replaces_the_parallel_failure(tmp_path):
    results, counts, timed_out, expected, _ = _mod().parse_logs(_log(tmp_path, LOG))

    assert results["gxa"] is True
    assert "gxa" not in counts


def test_still_failed_keeps_the_first_verdict(tmp_path):
    results, counts, timed_out, _, _ = _mod().parse_logs(_log(tmp_path, LOG))

    assert results["dblp"] is False and counts["dblp"] == 6
    assert results["neurovault"] is False and "neurovault" in timed_out


def test_retry_lines_do_not_change_the_shard_total(tmp_path):
    """The retry counter is [i/3], not the shard's [i/4]."""
    _, _, _, expected, _ = _mod().parse_logs(_log(tmp_path, LOG))

    assert expected == 4


def test_a_serial_skip_is_reached_without_a_verdict(tmp_path):
    mod = _mod()
    log = _log(tmp_path, "[1/1] x: FAILED: 1 test failure(s)\n"
                         "   [1/1] x: skipped (was failed under load)\n")

    results, _, _, _, _ = mod.parse_logs(log)
    assert "x" not in results
    assert mod.parse_no_verdict(log) == {"x": "SKIPPED"}


def test_the_summary_no_longer_lists_a_retried_pass_as_new(tmp_path):
    mod = _mod()
    results, counts, timed_out, expected, _ = mod.parse_logs(_log(tmp_path, LOG))

    text, row = mod.build_summary(results, counts, timed_out, set(), expected)

    assert "gxa" not in row["new_failing"]
    assert set(row["new_failing"]) == {"dblp", "neurovault"}


def test_the_indigo_tool_declares_it():
    """epam.indigo is optional; CI lacks it and ran the tool anyway (same run)."""
    import json

    tools = json.loads(
        (ROOT / "src" / "tooluniverse" / "data" / "chembl_tools.json").read_text("utf-8")
    )
    tool = next(t for t in tools if t["name"] == "ChEMBL_search_similar_molecules")

    assert tool.get("required_packages") == ["epam.indigo"]
