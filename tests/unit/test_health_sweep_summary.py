"""The weekly summary must reflect the sweep, not render green regardless.

PROGRESS expected an emoji format that `scripts/test_all_tools.py` does not
print. It matched nothing, so every run reported "No new failures ✅" while
96 categories were failing and an entire shard had been lost.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "summarize_health_sweep.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("summarize_health_sweep", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# Copied verbatim from a real shard artifact.
SHARD = """[1/86] cellrank: FAILED: 1 test failure(s)
[2/86] brenda: PASSED: 3 test(s)
[39/86] mcp_contracts.lock: NO TESTS: category has no executable examples
[58/86] pdbe_compound: SCHEMA ERROR: 1 invalid result(s)
[70/86] slow_one: TIMEOUT: exceeded per-category limit
"""


def _write(tmp_path, text, name="sweep_output_0.log"):
    path = tmp_path / name
    path.write_text(text)
    return str(tmp_path / "*.log")


def test_the_real_progress_format_is_parsed(tmp_path, mod):
    results, counts, timed_out, expected = mod.parse_logs([_write(tmp_path, SHARD)])

    assert results["cellrank"] is False
    assert results["brenda"] is True
    assert results["pdbe_compound"] is False
    assert results["slow_one"] is False
    assert counts["cellrank"] == 1
    assert "slow_one" in timed_out


def test_no_tests_is_neither_pass_nor_fail(tmp_path, mod):
    """Counting it as passing would make a category losing its examples look
    like a recovery."""
    results, _, _, _ = mod.parse_logs([_write(tmp_path, SHARD)])
    assert "mcp_contracts.lock" not in results


def test_expected_total_comes_from_the_shards(tmp_path, mod):
    """Without it, a lost shard is indistinguishable from a clean run."""
    _, _, _, expected = mod.parse_logs([_write(tmp_path, SHARD)])
    assert expected == 86


def test_a_lost_shard_is_reported_as_unknown(tmp_path, mod):
    results, counts, timed_out, expected = mod.parse_logs([_write(tmp_path, SHARD)])
    text, row = mod.build_summary(results, counts, timed_out, set(), expected)
    assert "never reached" in text
    assert "No new failures" not in text


def test_the_old_emoji_format_still_parses(tmp_path, mod):
    older = "[1/638] zinc: ❌ 1 failures\n[2/638] gbif: ✅ 7 tests passed\n"
    results, counts, _, _ = mod.parse_logs([_write(tmp_path, older, "old.log")])
    assert results == {"zinc": False, "gbif": True}
    assert counts["zinc"] == 1


def test_parsing_nothing_is_not_reported_as_clean(tmp_path, mod, capsys):
    (tmp_path / "junk.log").write_text("nothing resembling progress output\n")
    baseline = tmp_path / "baseline.txt"
    baseline.write_text("")
    summary = tmp_path / "summary.md"

    code = mod.main(
        [
            "--logs",
            str(tmp_path / "junk.log"),
            "--baseline",
            str(baseline),
            "--summary",
            str(summary),
        ]
    )

    assert code == 1
    assert "No new failures" not in summary.read_text()
