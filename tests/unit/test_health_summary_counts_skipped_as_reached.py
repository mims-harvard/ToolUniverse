"""A skipped category was reached; it just has no verdict.

Run 37193646910 -- the first CI sweep after the 2026-10-03/04 fixes, and the
first whose every shard succeeded -- reported:

    Categories reported: 598 of 664 -- 66 never reached
    > 66 category/categories were never reached -- a shard was lost.

All 8 shards had logged 83 of 83 categories. The 66 were 61 SKIPPED and 5
NO TESTS: reached, with no pass/fail verdict. Keeping them out of passing and
failing was right. Counting them as unreached was not, and it produced a false
"a shard was lost" on the one run where nothing was.

SKIPPED was introduced to the sweep in #699 and never added to this parser's
pattern, which is how the two disagreed.
"""

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]

SHARD = """\
[1/5] alpha: PASSED: 3 test(s)
[2/5] beta: FAILED: 2 test failure(s)
[3/5] gamma: SKIPPED: 1 tool(s) need a credential this run does not have
[4/5] delta: NO TESTS: category has no executable examples
[5/5] epsilon: SKIPPED: 2 tool(s) need a package that is not installed
"""


def _mod():
    spec = importlib.util.spec_from_file_location(
        "summarize_health_sweep_reached", ROOT / "scripts" / "summarize_health_sweep.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _log(tmp_path, text=SHARD, name="sweep_output_0.log"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_skipped_and_no_tests_are_reached(tmp_path):
    mod = _mod()
    logs = [_log(tmp_path)]

    results, counts, timed_out, expected, _ = mod.parse_logs(logs)
    text, row = mod.build_summary(
        results, counts, timed_out, set(), expected,
        no_verdict=mod.parse_no_verdict(logs),
    )

    assert expected == 5
    assert row["reported"] == 5
    assert row["never_reached"] == 0
    assert "never reached" not in text
    assert "a shard was lost" not in text


def test_they_still_have_no_verdict(tmp_path):
    """Neither passing nor failing -- that part was always right."""
    mod = _mod()
    logs = [_log(tmp_path)]

    results, counts, timed_out, expected, _ = mod.parse_logs(logs)
    _, row = mod.build_summary(
        results, counts, timed_out, set(), expected,
        no_verdict=mod.parse_no_verdict(logs),
    )

    assert row["passing"] == 1
    assert row["failing"] == 1
    assert row["skipped"] == 2
    assert row["no_tests"] == 1
    assert "gamma" not in results and "delta" not in results


def test_the_no_verdict_line_names_both_kinds(tmp_path):
    mod = _mod()
    logs = [_log(tmp_path)]

    results, counts, timed_out, expected, _ = mod.parse_logs(logs)
    text, _ = mod.build_summary(
        results, counts, timed_out, set(), expected,
        no_verdict=mod.parse_no_verdict(logs),
    )

    assert "No verdict: **2** skipped" in text
    assert "**1** with no examples" in text


def test_a_genuinely_missing_category_is_still_reported(tmp_path):
    """The fix must not hide a real gap: here one category never ran."""
    mod = _mod()
    truncated = "\n".join(SHARD.splitlines()[:4]) + "\n"  # epsilon absent
    logs = [_log(tmp_path, truncated)]

    results, counts, timed_out, expected, _ = mod.parse_logs(logs)
    text, row = mod.build_summary(
        results, counts, timed_out, set(), expected,
        no_verdict=mod.parse_no_verdict(logs),
    )

    assert expected == 5
    assert row["reported"] == 4
    assert row["never_reached"] == 1
    assert "1 never reached" in text


def test_a_lost_shard_still_raises_the_alarm(tmp_path):
    mod = _mod()
    logs = [_log(tmp_path)]

    results, counts, timed_out, expected, seen = mod.parse_logs(logs)
    text, _ = mod.build_summary(
        results, counts, timed_out, set(), expected,
        shards_seen=seen, shards_expected=2,
        no_verdict=mod.parse_no_verdict(logs),
    )

    assert "1 uploaded nothing" in text


def test_callers_that_omit_no_verdict_keep_the_old_behaviour(tmp_path):
    """build_summary's new argument is optional and defaults to nothing."""
    mod = _mod()
    logs = [_log(tmp_path)]

    results, counts, timed_out, expected, _ = mod.parse_logs(logs)
    _, row = mod.build_summary(results, counts, timed_out, set(), expected)

    assert row["reported"] == 2
    assert row["never_reached"] == 3
