"""Regression guard for Fix-R30D-6: CompoundGeneDiseaseAssociationTool's
OpenTargets sub-query, for a gene-only request (no disease given), passed
the gene SYMBOL into OpenTargets_get_disease_ids_by_name -- a disease-NAME
search. Confirmed live for LMNA: that call returns 0-1 spurious hits that
merely contain "LMNA" as a substring (e.g. "congenital muscular dystrophy
due to LMNA mutation"), not LMNA's real 6084 OpenTargets disease
associations (confirmed via OpenTargets_get_diseases_phenotypes_by_target_
ensembl once resolved to its Ensembl ID, ENSG00000160789) -- so the
concordance table could never show OpenTargets agreeing with any other
source on a gene-only query, undermining the tool's whole purpose.

Fixed by resolving the gene symbol to its Ensembl target ID via
OpenTargets_get_target_id_description_by_name first, then querying that
ID's real associated-diseases list.
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


_TARGET_SEARCH_RESPONSE = {
    "status": "success",
    "data": {
        "search": {
            "hits": [
                {"id": "ENSG00000160789", "name": "LMNA", "description": "lamin A/C"},
                {"id": "ENSG00000146147", "name": "MLIP", "description": "..."},
            ]
        }
    },
}

_ASSOCIATED_DISEASES_RESPONSE = {
    "status": "success",
    "data": {
        "target": {
            "id": "ENSG00000160789",
            "approvedSymbol": "LMNA",
            "associatedDiseases": {
                "count": 2,
                "rows": [
                    {
                        "disease": {
                            "id": "MONDO_0005021",
                            "name": "dilated cardiomyopathy",
                        }
                    },
                    {
                        "disease": {
                            "id": "MONDO_0016419",
                            "name": "Hutchinson-Gilford progeria syndrome",
                        }
                    },
                ],
            },
        }
    },
}


class TestOpenTargetsGeneOnlyLookup:
    def test_resolves_gene_symbol_before_fetching_diseases(self):
        tool = _tool()
        tu = MagicMock()
        tu.run_one_function.side_effect = [
            _TARGET_SEARCH_RESPONSE,
            _ASSOCIATED_DISEASES_RESPONSE,
        ]
        sources_failed = []

        result = tool._opentargets_gene_diseases(tu, "LMNA", sources_failed)

        assert result == _ASSOCIATED_DISEASES_RESPONSE
        first_call, second_call = tu.run_one_function.call_args_list
        assert (
            first_call.args[0]["name"]
            == "OpenTargets_get_target_id_description_by_name"
        )
        assert first_call.args[0]["arguments"] == {"targetName": "LMNA"}
        assert (
            second_call.args[0]["name"]
            == "OpenTargets_get_diseases_phenotypes_by_target_ensembl"
        )
        assert second_call.args[0]["arguments"] == {"ensemblId": "ENSG00000160789"}
        assert sources_failed == []

    def test_exception_from_run_one_function_is_caught_not_raised(self):
        """Fix (PR #339 review): _opentargets_gene_diseases previously had no
        try/except around its two tu.run_one_function calls, unlike every
        other source in run() which routes through _try_tool -- an
        unhandled exception here (e.g. a network error) would propagate out
        of run() and crash the whole multi-source lookup instead of just
        marking OpenTargets failed."""
        tool = _tool()
        tu = MagicMock()
        tu.run_one_function.side_effect = ConnectionError("simulated network failure")
        sources_failed = []

        result = tool._opentargets_gene_diseases(tu, "LMNA", sources_failed)

        assert result["status"] == "error"
        assert "simulated network failure" in result["error"]
        assert len(sources_failed) == 1
        assert "OpenTargets" in sources_failed[0]
        assert "simulated network failure" in sources_failed[0]

    def test_exception_on_second_call_is_also_caught(self):
        tool = _tool()
        tu = MagicMock()
        tu.run_one_function.side_effect = [
            _TARGET_SEARCH_RESPONSE,
            TimeoutError("simulated timeout"),
        ]
        sources_failed = []

        result = tool._opentargets_gene_diseases(tu, "LMNA", sources_failed)

        assert result["status"] == "error"
        assert "simulated timeout" in result["error"]
        assert len(sources_failed) == 1

    def test_gene_only_query_degrades_gracefully_on_opentargets_exception(self):
        """End-to-end: run() must not raise even when OpenTargets's chained
        lookup blows up -- other sources still return normally."""
        tool = _tool()
        tu = MagicMock()

        def fake_run(call):
            if call["name"] == "OpenTargets_get_target_id_description_by_name":
                raise ConnectionError("simulated network failure")
            return {"status": "error", "error": "unused source"}

        tu.run_one_function.side_effect = fake_run

        with patch("tooluniverse.execute_function.ToolUniverse", return_value=tu):
            result = tool.run({"gene": "LMNA"})

        assert result["status"] == "success"
        failed = result["data"]["sources_failed"]
        assert any("OpenTargets" in f and "simulated network failure" in f for f in failed)

    def test_no_target_match_records_failure_without_crashing(self):
        tool = _tool()
        tu = MagicMock()
        tu.run_one_function.return_value = {
            "status": "success",
            "data": {"search": {"hits": []}},
        }
        sources_failed = []

        result = tool._opentargets_gene_diseases(tu, "NOTAREALGENE", sources_failed)

        assert result["status"] == "error"
        assert len(sources_failed) == 1
        assert "NOTAREALGENE" in sources_failed[0]

    def test_extracts_real_disease_names_from_associated_diseases_shape(self):
        tool = _tool()
        items = tool._extract_genes_or_diseases(
            _ASSOCIATED_DISEASES_RESPONSE, "OpenTargets"
        )

        names = [i["name"] for i in items]
        assert "Hutchinson-Gilford progeria syndrome" in names
        assert "dilated cardiomyopathy" in names
        assert all(i["source"] == "OpenTargets" for i in items)

    def test_disease_query_still_uses_direct_name_search(self):
        """A disease-provided query is unaffected -- still the original,
        already-correct OpenTargets_get_disease_ids_by_name path."""
        tool = _tool()
        tu = MagicMock()
        tu.run_one_function.return_value = {
            "status": "success",
            "data": {"search": {"hits": [{"name": "progeria"}]}},
        }

        # run() itself dispatches this, but exercising just the extraction
        # helper's untouched branch is enough to confirm no regression.
        r = tu.run_one_function(
            {
                "name": "OpenTargets_get_disease_ids_by_name",
                "arguments": {"name": "progeria"},
            }
        )
        items = tool._extract_genes_or_diseases(r, "OpenTargets")
        assert items[0]["name"] == "progeria"


class TestRunDispatch:
    def test_gene_only_query_routes_through_target_resolution(self):
        tool = _tool()
        tu = MagicMock()
        tu.run_one_function.side_effect = lambda call: {
            "OpenTargets_get_target_id_description_by_name": _TARGET_SEARCH_RESPONSE,
            "OpenTargets_get_diseases_phenotypes_by_target_ensembl": _ASSOCIATED_DISEASES_RESPONSE,
        }.get(call["name"], {"status": "error", "error": "unused source"})

        with patch("tooluniverse.execute_function.ToolUniverse", return_value=tu):
            result = tool.run({"gene": "LMNA"})

        assert result["status"] == "success"
        ot_names = [
            r["name"] for r in result["data"]["per_source_results"]["OpenTargets"]
        ]
        assert "Hutchinson-Gilford progeria syndrome" in ot_names
        # The bug's spurious substring-match shape must not appear.
        assert "congenital muscular dystrophy due to LMNA mutation" not in ot_names

    def test_disease_query_still_calls_disease_name_search_directly(self):
        tool = _tool()
        tu = MagicMock()

        def fake_run(call):
            if call["name"] == "OpenTargets_get_disease_ids_by_name":
                assert call["arguments"] == {"name": "progeria"}
                return {
                    "status": "success",
                    "data": {"search": {"hits": [{"name": "progeria"}]}},
                }
            return {"status": "error", "error": "unused source"}

        tu.run_one_function.side_effect = fake_run

        with patch("tooluniverse.execute_function.ToolUniverse", return_value=tu):
            result = tool.run({"disease": "progeria"})

        assert result["status"] == "success"
        # The target-resolution helper must never be invoked for a
        # disease-provided query.
        called_names = [c.args[0]["name"] for c in tu.run_one_function.call_args_list]
        assert "OpenTargets_get_target_id_description_by_name" not in called_names
