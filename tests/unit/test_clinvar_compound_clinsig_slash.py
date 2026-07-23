"""Unit test: ClinVar_search_variants handles slash-compound clinical significance.

Regression: a compound aggregate class like "Pathogenic/Likely pathogenic" (which
the tool's OWN get_clinical_significance emits) has no single NCBI clinsig token
-- the slash broke both the [Filter] phrase and the [prop] token, so the search
silently returned total_count 0 for a valid value. The slash is now treated as OR
and expanded to the individual classes (the clinically-actionable union).
"""
from unittest.mock import patch

import pytest

from tooluniverse.clinvar_tool import ClinVarSearchVariants

pytestmark = pytest.mark.unit


def _tool():
    return ClinVarSearchVariants({"name": "ClinVar_search_variants"})


def _term_for(arguments):
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={"status": "success", "data": {}},
    ) as mock_request:
        tool.run(arguments)
    return mock_request.call_args[0][1]["term"]


def test_slash_value_expands_to_or_of_components():
    term = _term_for(
        {"gene": "RYR1", "clinical_significance": "Pathogenic/Likely pathogenic"}
    )
    # Both component classes present, joined by OR, and NO broken slash token.
    assert '"clinsig pathogenic"[Filter]' in term
    assert '"clinsig likely pathogenic"[Filter]' in term
    assert "clinsig_likely_pathogenic[prop]" in term
    assert "/" not in term.split("RYR1[gene]")[1]  # no slash survives in clinsig
    assert " OR " in term


def test_single_value_unchanged():
    term = _term_for({"gene": "RYR1", "clinical_significance": "Pathogenic"})
    assert '("clinsig pathogenic"[Filter] OR clinsig_pathogenic[prop])' in term


def test_compound_note_only_on_compound_value():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={
            "status": "success",
            "data": {"esearchresult": {"count": "5", "idlist": []}},
        },
    ):
        compound = tool.run(
            {"gene": "RYR1", "clinical_significance": "Benign/Likely benign"}
        )
        single = tool.run({"gene": "RYR1", "clinical_significance": "Benign"})
    assert "clinical_significance_note" in compound["data"]
    assert "clinical_significance_note" not in single["data"]
