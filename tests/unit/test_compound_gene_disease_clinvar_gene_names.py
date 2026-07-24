"""Regression guard for Fix-R80A-1: CompoundGeneDiseaseAssociationTool's
ClinVar sub-query used {"query": gene_or_disease} -- "query" is documented as
an alias for "condition" (a disease/phenotype free-text search), not a gene
lookup, the exact same mistake already caught and fixed in the sibling
compound_variant_tool.py (Fix-R31D-4/R31A-3) but never ported here.

Compounding this, the extraction logic then pulled each returned variant
row's "genes" field and added every gene symbol as if it were a disease
name -- confirmed live for LDLR: "LDLR" (the gene itself) and "LDLR-AS1" (a
co-located antisense RNA gene sharing overlapping ClinVar variant records)
both appeared as "diseases associated with LDLR" in the concordance table.
ClinVar_search_variants' row shape (title/genes/clinical_significance/
review_status) has no usable disease/condition name field at all, confirmed
live -- so the fix is to branch the query correctly (gene vs condition, like
DisGeNET/OpenTargets already do in this same file) AND stop fabricating
disease names from gene symbols, contributing nothing from ClinVar instead
with an explanatory note rather than silently misleading data.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.compound_gene_disease_tool import CompoundGeneDiseaseAssociationTool

pytestmark = pytest.mark.unit


def _tool():
    return CompoundGeneDiseaseAssociationTool({"name": "gather_test"})


_LDLR_CLINVAR_RESPONSE = {
    "status": "success",
    "data": {
        "total_count": 4909,
        "variant_ids": ["1", "2"],
        "variants": [
            {
                "variant_id": "1",
                "title": "NM_000527.5(LDLR):c.2566del (p.Glu856fs)",
                "genes": ["LDLR"],
                "clinical_significance": "Uncertain significance",
            },
            {
                "variant_id": "2",
                "title": "NM_000527.5(LDLR):c.1A>G",
                "genes": ["LDLR", "LDLR-AS1"],
                "clinical_significance": "Pathogenic",
            },
        ],
    },
}


class TestClinVarExtractionNoLongerFabricatesDiseaseNames:
    def test_extract_returns_empty_for_clinvar_variants_shape(self):
        tool = _tool()
        items = tool._extract_genes_or_diseases(_LDLR_CLINVAR_RESPONSE, "ClinVar")
        assert items == []

    def test_gene_symbols_never_appear_as_disease_names_end_to_end(self):
        tool = _tool()
        tu = MagicMock()
        tu.run_one_function.side_effect = lambda call: (
            _LDLR_CLINVAR_RESPONSE
            if call["name"] == "ClinVar_search_variants"
            else {"status": "error", "error": "unused source"}
        )

        with patch("tooluniverse.execute_function.ToolUniverse", return_value=tu):
            result = tool.run({"gene": "LDLR"})

        names = [a["name"] for a in result["data"]["associations"]]
        assert "LDLR" not in names
        assert "LDLR-AS1" not in names
        assert result["data"]["per_source_results"]["ClinVar"] == []


class TestClinVarQueryParameterBranching:
    def test_gene_only_query_uses_gene_param_not_query(self):
        tool = _tool()
        tu = MagicMock()
        tu.run_one_function.side_effect = lambda call: (
            _LDLR_CLINVAR_RESPONSE
            if call["name"] == "ClinVar_search_variants"
            else {"status": "error", "error": "unused source"}
        )

        with patch("tooluniverse.execute_function.ToolUniverse", return_value=tu):
            tool.run({"gene": "LDLR"})

        clinvar_call = next(
            c.args[0]
            for c in tu.run_one_function.call_args_list
            if c.args[0]["name"] == "ClinVar_search_variants"
        )
        assert clinvar_call["arguments"] == {"gene": "LDLR", "limit": 10}
        assert "query" not in clinvar_call["arguments"]

    def test_disease_only_query_uses_condition_param(self):
        tool = _tool()
        tu = MagicMock()
        tu.run_one_function.side_effect = lambda call: (
            {"status": "success", "data": {"variants": []}}
            if call["name"] == "ClinVar_search_variants"
            else {"status": "error", "error": "unused source"}
        )

        with patch("tooluniverse.execute_function.ToolUniverse", return_value=tu):
            tool.run({"disease": "familial hypercholesterolemia"})

        clinvar_call = next(
            c.args[0]
            for c in tu.run_one_function.call_args_list
            if c.args[0]["name"] == "ClinVar_search_variants"
        )
        assert clinvar_call["arguments"] == {
            "condition": "familial hypercholesterolemia",
            "limit": 10,
        }
        assert "query" not in clinvar_call["arguments"]


class TestNoteDistinguishesLimitationFromFailure:
    def test_note_added_when_clinvar_succeeds_but_has_no_usable_data(self):
        tool = _tool()
        tu = MagicMock()
        tu.run_one_function.side_effect = lambda call: (
            _LDLR_CLINVAR_RESPONSE
            if call["name"] == "ClinVar_search_variants"
            else {"status": "error", "error": "unused source"}
        )

        with patch("tooluniverse.execute_function.ToolUniverse", return_value=tu):
            result = tool.run({"gene": "LDLR"})

        notes = result["data"].get("notes", [])
        assert any("ClinVar" in n and "data-shape limitation" in n for n in notes)

    def test_note_not_added_when_clinvar_genuinely_fails(self):
        """A real ClinVar failure must be surfaced via sources_failed only,
        not conflated with the "queried fine, nothing to extract" note --
        those are different situations a caller should be able to tell
        apart."""
        tool = _tool()
        tu = MagicMock()
        tu.run_one_function.side_effect = lambda call: (
            {"status": "error", "error": "simulated ClinVar outage"}
            if call["name"] == "ClinVar_search_variants"
            else {"status": "error", "error": "unused source"}
        )

        with patch("tooluniverse.execute_function.ToolUniverse", return_value=tu):
            result = tool.run({"gene": "LDLR"})

        assert any("ClinVar" in f for f in result["data"]["sources_failed"])
        notes = result["data"].get("notes", [])
        assert not any("data-shape limitation" in n for n in notes)
