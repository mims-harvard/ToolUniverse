"""Regression tests for DNA GC interpretation provenance and schema semantics."""

import pytest

from tooluniverse.dna_tools import DNATool


pytestmark = pytest.mark.unit


def _tool() -> DNATool:
    return DNATool(
        {
            "name": "DNA_calculate_gc_content",
            "fields": {"operation": "calculate_gc_content"},
        }
    )


@pytest.mark.parametrize(
    ("sequence", "gc", "interpretation"),
    [
        ("G" * 39 + "A" * 61, 39.0, "Low GC"),
        ("G" * 40 + "A" * 60, 40.0, "Normal GC"),
        ("G" * 60 + "A" * 40, 60.0, "Normal GC"),
        ("G" * 61 + "A" * 39, 61.0, "High GC"),
    ],
)
def test_gc_interpretation_exact_boundaries(sequence, gc, interpretation):
    """40% and 60% are inclusive normal-GC boundaries."""
    result = _tool().run({"sequence": sequence})

    data = result["data"]
    assert data["gc_content_percent"] == gc
    assert data["interpretation"] == interpretation
    assert data["interpretation_criteria"]["metric_value"] == gc


def test_ambiguous_bases_are_excluded_and_rule_is_published():
    """N does not dilute the GC denominator and that choice is explicit."""
    result = _tool().run({"sequence": "GGCCATNNNN"})

    data = result["data"]
    assert data["sequence_length"] == 10
    assert data["effective_length"] == 6
    assert data["gc_content_percent"] == pytest.approx(66.67)
    criteria = data["interpretation_criteria"]
    assert criteria["derived"] is True
    assert criteria["derived_by"] == "ToolUniverse"
    assert criteria["denominator"] == "A+T+G+C bases; N bases excluded"
    assert "not a retrieved experimental" in criteria["scope_note"]


def test_all_n_sequence_returns_null_percentages_and_defined_provenance():
    """Undefined composition is null rather than a false 0% GC value."""
    result = _tool().run({"sequence": "NNNN"})

    data = result["data"]
    assert data["gc_content_percent"] is None
    assert data["at_content_percent"] is None
    assert data["interpretation"] == "Undefined (no ATGC bases)"
    assert data["interpretation_criteria"]["metric_value"] is None
    assert data["interpretation_criteria"]["undefined_rule"] == "no A/T/G/C bases"
