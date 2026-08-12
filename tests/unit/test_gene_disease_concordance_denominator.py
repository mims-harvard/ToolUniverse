"""gather_gene_disease_associations must not count sources that never answered.

The tool queries five databases and reports, on every association row,
``concordance`` (how many named the entity) beside ``total_sources_queried:
5``. That denominator counts every source ATTEMPTED, including ones that
failed on a missing API key and ones that structurally cannot contribute
(ClinVar's variant rows carry no disease name, so it adds nothing in the
gene->disease direction). Agreement therefore reads as disagreement.

Measured live 2026-08 with no API keys configured, ``{"gene": "CFH"}``:

    sources_failed = ["DisGeNET: ... DISGENET_API_KEY", "OMIM: ... OMIM_API_KEY"]
    per_source_result_counts = {DisGeNET 0, OMIM 0, OpenTargets 25,
                                GenCC 10, ClinVar 0}
    associations[0] = {"name": "complement factor H deficiency",
                       "sources": ["GenCC", "OpenTargets"],
                       "concordance": 2, "total_sources_queried": 5}

Two sources could answer at all, yet the row invited "2 of 5". BRCA1's
"breast cancer" reported 1 of 5 the same way.

Two caps compounded it. ``per_source_results`` was sliced to ten rows per
source with no flag while ``num_associations`` counted the full table, so that
same CFH response showed "OpenTargets: 10" against "num_associations: 29" with
nothing saying OpenTargets had actually returned 25. ``associations`` was
sliced to fifty the same way.

Pinned here: the honest denominator rides on every row, both caps are restated
rather than silent, the disclosure notes fire only when they apply, and the
two fields dropped during review stay dropped. Pure functions only -- no
network, no ToolUniverse construction.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.compound_gene_disease_tool import (  # noqa: E402
    CompoundGeneDiseaseAssociationTool,
)

pytestmark = pytest.mark.unit


def _tool():
    return CompoundGeneDiseaseAssociationTool({"name": "gather_test"})


def _entry(name, score=None, source="OpenTargets"):
    return {"name": name, "score": score, "source": source}


# The live CFH shape: DisGeNET and OMIM failed on missing keys, ClinVar cannot
# contribute disease names in this direction, so only two sources answered.
CFH_BY_SOURCE = {
    "DisGeNET": [],
    "OMIM": [],
    "OpenTargets": [
        _entry("complement factor H deficiency", 0.747),
        _entry("age-related macular degeneration", 0.732),
        _entry("atypical hemolytic-uremic syndrome", 0.729),
    ],
    "GenCC": [
        _entry("complement factor H deficiency", None, "GenCC"),
        _entry("dense deposit disease", None, "GenCC"),
    ],
    "ClinVar": [],
}


def test_sources_with_data_names_only_the_sources_that_answered():
    assert CompoundGeneDiseaseAssociationTool._sources_with_data(CFH_BY_SOURCE) == [
        "OpenTargets",
        "GenCC",
    ]


def test_every_row_carries_the_denominator_that_can_actually_be_divided_by():
    rows = _tool()._build_concordance(CFH_BY_SOURCE)

    assert rows, "expected a concordance table"
    for row in rows:
        # The pre-fix response had only the first of these, and readers divided
        # by it. Five sources were queried; two could answer.
        assert row["total_sources_queried"] == 5
        assert row["total_sources_with_data"] == 2
        assert row["concordance"] <= row["total_sources_with_data"]

    top = rows[0]
    assert top["name"] == "complement factor H deficiency"
    assert top["sources"] == ["GenCC", "OpenTargets"]
    assert top["concordance"] == 2


def test_a_source_that_answers_nothing_is_not_counted_as_disagreeing():
    """Same data, but every source contributes -- the denominator moves."""
    all_answering = {k: (v or [_entry("filler")]) for k, v in CFH_BY_SOURCE.items()}

    rows = _tool()._build_concordance(all_answering)

    assert all(r["total_sources_with_data"] == 5 for r in rows)


# ---- the two caps are restated, not silent ----


def _disclosure(tool, num_associations, per_source_counts, results_by_source=None):
    result = {
        "num_associations": num_associations,
        "truncated": num_associations > tool.ASSOCIATION_CAP,
        "per_source_result_counts": per_source_counts,
    }
    return result, tool._disclosure_notes(
        result, results_by_source if results_by_source is not None else CFH_BY_SOURCE
    )


def test_the_per_source_cap_names_what_it_cut():
    tool = _tool()
    # The live CFH figure: OpenTargets returned 25, ten were shown.
    _, notes = _disclosure(tool, 29, {"OpenTargets": 25, "GenCC": 10, "ClinVar": 0})

    cap_note = next(n for n in notes if "per_source_results" in n)
    assert "10 of 25" in cap_note
    assert "per_source_result_counts" in cap_note
    # GenCC sat exactly at the cap without being cut, so it must not be listed.
    assert "GenCC" not in cap_note


def test_the_association_cap_names_what_it_cut():
    tool = _tool()
    result, notes = _disclosure(tool, 63, {"OpenTargets": 3})

    assert result["truncated"] is True
    cap_note = next(n for n in notes if "'associations' is truncated" in n)
    assert "63" in cap_note and str(tool.ASSOCIATION_CAP) in cap_note
    assert "not evidence that no source reported it" in cap_note


def test_the_denominator_caveat_fires_only_when_the_denominator_misleads():
    tool = _tool()

    _, misleading = _disclosure(tool, 29, {"OpenTargets": 3})
    caveat = next(n for n in misleading if "total_sources_queried" in n)
    assert "Only 2 of them contributed" in caveat
    assert "OpenTargets, GenCC" in caveat

    all_answering = {k: (v or [_entry("filler")]) for k, v in CFH_BY_SOURCE.items()}
    _, honest = _disclosure(tool, 29, {"OpenTargets": 3}, all_answering)
    assert not any("total_sources_queried" in n for n in honest)


def test_nothing_cut_and_nothing_skewed_says_nothing():
    tool = _tool()
    all_answering = {k: (v or [_entry("filler")]) for k, v in CFH_BY_SOURCE.items()}

    _, notes = _disclosure(tool, 29, {"OpenTargets": 3}, all_answering)

    assert notes == []


def test_the_two_fields_dropped_during_review_stay_dropped():
    """`sources_with_data` and `associations_returned` were both derivable from
    what the response already carries; neither may creep back in as a second
    way to say the same thing."""
    source = Path(
        CompoundGeneDiseaseAssociationTool.__module__.replace(".", "/") + ".py"
    )
    text = (Path(__file__).parent.parent.parent / "src" / source).read_text()

    assert '"sources_with_data"' not in text
    assert "associations_returned" not in text
    # The private helper keeps its name; only the response key is gone.
    assert "def _sources_with_data" in text
