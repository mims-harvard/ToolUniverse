"""The report could not tell a broken tool from an upstream we overloaded.

The weekly sweep runs 10 workers against live APIs. On 2026-10-03 it reported
90 non-passing categories, and about 120 of the individual test failures were
self-inflicted. Two that made the point:

    ensembl_sequence   2 failures in the parallel sweep, 4/4 passing alone
    enrichr            "'str' object has no attribute ..." in parallel, passing alone

That second message reads exactly like a code defect, which is the problem --
every load-shaped failure had to be re-checked by hand before any of the report
could be trusted.

Measured with the retry pass, running the 13 ensembl categories with 10
workers: all 13 failed in parallel, and the serial re-run turned 9 of them into
passes, leaving 3 real failures and 1 timeout. The report now says which is
which instead of presenting 13 broken categories.
"""

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def _sweep():
    spec = importlib.util.spec_from_file_location(
        "test_all_tools_retry", ROOT / "scripts" / "test_all_tools.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _failed(*messages):
    return {
        "failed": len(messages),
        "passed": 0,
        "raw_output": "\n".join(f"  ❌ Tool Ex 1: Failed - {m}" for m in messages),
    }


@pytest.mark.parametrize(
    "message",
    [
        "Ensembl API HTTP 500: <!doctype html>",
        "Ensembl REST API HTTP error: unknown",
        "HTTP Error 503: Service Unavailable",
        "Semantic Scholar API error 429",
        "CATH API HTTP error: 429",
        "Ensembl API request timed out after 30 seconds",
        "Request failed: 502 Bad Gateway",
        "ENCORI API request failed: Response ended prematurely",
    ],
)
def test_a_load_shaped_failure_is_retried(message):
    sweep = _sweep()

    assert sweep.looks_contended(sweep.normalize_result(_failed(message)))


@pytest.mark.parametrize(
    "message",
    [
        "Tool 'X' not found even after loading tools",
        "API key is missing. In order to use the GtoPdb Web Services",
        "counts_file not found: /tmp/expr_anova_counts.csv",
        "GtoPdb has no ligand 999999",
    ],
)
def test_a_real_defect_is_not_retried(message):
    """Re-running these costs minutes and changes nothing."""
    sweep = _sweep()

    assert not sweep.looks_contended(sweep.normalize_result(_failed(message)))


def test_a_passing_category_is_never_retried():
    sweep = _sweep()

    passing = sweep.normalize_result(
        {"passed": 4, "failed": 0, "tests_run": 4, "raw_output": ""}
    )

    assert not sweep.looks_contended(passing)


def test_one_load_failure_among_many_is_enough():
    """Requiring all of them left 28 lines of noise beside one real defect."""
    sweep = _sweep()

    mixed = sweep.normalize_result(
        _failed("GtoPdb has no ligand 999999", "Ensembl API HTTP 500: <!doctype html>")
    )

    assert sweep.looks_contended(mixed)


def test_http_500_counts_as_load():
    """The first version of the marker list omitted 500.

    18 of ensembl's 29 failures were HTTP 500 -- Ensembl answers an overloaded
    request with a 500 HTML page -- so the category was not retried at all.
    """
    sweep = _sweep()

    assert "500" in sweep._CONTENTION_MARKERS


def test_a_timeout_state_is_retried():
    sweep = _sweep()

    timed_out = sweep.normalize_result(
        {"error": "Timeout after 10 minutes", "timed_out": True, "exit_code": -1}
    )

    assert sweep.looks_contended(timed_out)


def test_a_retry_that_passes_replaces_the_result(monkeypatch):
    sweep = _sweep()
    results = {"ensembl_sequence": sweep.normalize_result(_failed("HTTP 500"))}

    monkeypatch.setattr(
        sweep,
        "run_test_for_pattern",
        lambda *a, **k: {"passed": 4, "failed": 0, "tests_run": 4, "raw_output": ""},
    )

    changed = sweep.retry_contended_patterns(results, ROOT)

    assert changed == {"ensembl_sequence": "failed -> passed"}
    assert sweep.normalize_result(results["ensembl_sequence"])["state"] == "passed"
    assert results["ensembl_sequence"]["retried_serially"] is True


def test_a_retry_that_fails_keeps_the_original_evidence(monkeypatch):
    """A category that fails serially too should report what it first said."""
    sweep = _sweep()
    original = sweep.normalize_result(_failed("HTTP 500: <!doctype html>"))
    results = {"ensembl_vep": original}

    monkeypatch.setattr(
        sweep,
        "run_test_for_pattern",
        lambda *a, **k: _failed("something else entirely"),
    )

    changed = sweep.retry_contended_patterns(results, ROOT)

    assert changed == {}
    assert "<!doctype html>" in results["ensembl_vep"]["raw_output"]
    assert results["ensembl_vep"]["retried_serially"] is True


def test_nothing_to_retry_runs_nothing(monkeypatch):
    sweep = _sweep()
    calls = []
    monkeypatch.setattr(
        sweep, "run_test_for_pattern", lambda *a, **k: calls.append(a) or {}
    )

    changed = sweep.retry_contended_patterns(
        {"ok": sweep.normalize_result({"passed": 1, "failed": 0, "tests_run": 1})},
        ROOT,
    )

    assert changed == {}
    assert calls == []


def test_the_retry_can_be_turned_off():
    source = (ROOT / "scripts" / "test_all_tools.py").read_text("utf-8")

    assert "--no-retry" in source
    assert "args.parallel and not args.no_retry" in source, (
        "a serial run has no contention to undo, so the retry should only "
        "follow a parallel pass"
    )


def test_a_retry_reporting_no_tests_does_not_overwrite_a_failure(monkeypatch):
    """An absence is worse signal than the failure it would replace."""
    sweep = _sweep()
    results = {"something": sweep.normalize_result(_failed("HTTP 503"))}

    monkeypatch.setattr(
        sweep, "run_test_for_pattern", lambda *a, **k: {"tests_run": 0, "failed": 0}
    )

    changed = sweep.retry_contended_patterns(results, ROOT)

    assert changed == {}
    assert sweep.normalize_result(results["something"])["state"] == "failed"
