"""Regression guard for Fix-R28D-2: CompoundGeneDiseaseAssociationTool's
OpenTargets sub-query silently answered about a DIFFERENT gene.

`OpenTargets_get_target_id_description_by_name` is a fuzzy free-text search,
so an unrecognised symbol still comes back with a full, relevance-ranked hit
list. `_opentargets_gene_diseases` picked the exact name match when there was
one and otherwise fell back to `hits[0]` -- the top fuzzy hit -- and then
fetched THAT target's associated diseases. Confirmed live that
{"gene": "THP"} (the historical clinical alias for uromodulin/UMOD, a kidney
gene) returned GLI2's "holoprosencephaly 9" at score 0.80 and the rest of
GLI2's disease list, shaped exactly like a correct answer with nothing
anywhere signalling the substitution.

The hits carry only id/name/description -- no synonym fields -- so the alias
is genuinely unresolvable from this response. The fix reports the symbol as
unresolved and names the candidate symbols the search did return, instead of
guessing one.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.compound_gene_disease_tool import CompoundGeneDiseaseAssociationTool

pytestmark = pytest.mark.unit


DISEASES_TOOL = "OpenTargets_get_diseases_phenotypes_by_target_ensembl"
SEARCH_TOOL = "OpenTargets_get_target_id_description_by_name"

# The live hit list for targetName="THP", in order. No hit is named "THP".
_FUZZY_SEARCH_RESPONSE = {
    "status": "success",
    "data": {
        "search": {
            "hits": [
                {"id": "ENSG00000074047", "name": "GLI2", "description": "..."},
                {"id": "ENSG00000169344", "name": "UMOD", "description": "..."},
                {"id": "ENSG00000090534", "name": "THPO", "description": "..."},
                {"id": "ENSG00000184500", "name": "PROS1", "description": "..."},
                {"id": "ENSG00000115718", "name": "PROC", "description": "..."},
            ]
        }
    },
}

# GLI2's diseases -- what the old fallback misattributed to "THP".
_WRONG_TARGET_DISEASES = {
    "status": "success",
    "data": {
        "target": {
            "id": "ENSG00000074047",
            "approvedSymbol": "GLI2",
            "associatedDiseases": {
                "count": 1,
                "rows": [
                    {
                        "disease": {
                            "id": "MONDO_0012322",
                            "name": "holoprosencephaly 9",
                        },
                        "score": 0.7985980288493254,
                    }
                ],
            },
        }
    },
}

_EXACT_SEARCH_RESPONSE = {
    "status": "success",
    "data": {
        "search": {
            "hits": [
                {"id": "ENSG00000074047", "name": "GLI2", "description": "..."},
                {"id": "ENSG00000169344", "name": "UMOD", "description": "..."},
            ]
        }
    },
}

_UMOD_DISEASES = {
    "status": "success",
    "data": {
        "target": {
            "id": "ENSG00000169344",
            "approvedSymbol": "UMOD",
            "associatedDiseases": {
                "count": 1,
                "rows": [
                    {
                        "disease": {
                            "id": "MONDO_0008170",
                            "name": "familial juvenile hyperuricemic nephropathy",
                        },
                        "score": 0.9,
                    }
                ],
            },
        }
    },
}


def _tool():
    return CompoundGeneDiseaseAssociationTool({"name": "gather_test"})


def _fake_tu(responses):
    """A ToolUniverse stub that answers by tool name and records every call."""
    tu = MagicMock()
    tu.run_one_function.side_effect = lambda call: responses[call["name"]]
    return tu


def _called_names(tu):
    return [c.args[0]["name"] for c in tu.run_one_function.call_args_list]


class TestNoWrongTargetSubstitution:
    def test_non_matching_symbol_never_fetches_another_targets_diseases(self):
        tu = _fake_tu(
            {SEARCH_TOOL: _FUZZY_SEARCH_RESPONSE, DISEASES_TOOL: _WRONG_TARGET_DISEASES}
        )
        sources_failed = []

        result = _tool()._opentargets_gene_diseases(tu, "THP", sources_failed)

        # The diseases-by-Ensembl lookup must not happen at all.
        assert DISEASES_TOOL not in _called_names(tu)
        assert result["status"] == "error"

    def test_non_matching_symbol_reports_an_actionable_failure(self):
        tu = _fake_tu(
            {SEARCH_TOOL: _FUZZY_SEARCH_RESPONSE, DISEASES_TOOL: _WRONG_TARGET_DISEASES}
        )
        sources_failed = []

        result = _tool()._opentargets_gene_diseases(tu, "THP", sources_failed)

        assert len(sources_failed) == 1
        msg = sources_failed[0]
        assert msg.startswith("OpenTargets: ")
        assert "THP" in msg
        # Names the candidates the search actually returned, so the caller can
        # re-query with a real symbol.
        for candidate in ("GLI2", "UMOD", "THPO"):
            assert candidate in msg
        assert msg.endswith(result["error"])

    def test_wrong_targets_diseases_never_reach_the_extracted_items(self):
        tu = _fake_tu(
            {SEARCH_TOOL: _FUZZY_SEARCH_RESPONSE, DISEASES_TOOL: _WRONG_TARGET_DISEASES}
        )
        tool = _tool()

        result = tool._opentargets_gene_diseases(tu, "THP", [])
        items = tool._extract_genes_or_diseases(result, "OpenTargets")

        assert items == []

    def test_case_insensitive_exact_match_still_resolves(self):
        tu = _fake_tu(
            {SEARCH_TOOL: _EXACT_SEARCH_RESPONSE, DISEASES_TOOL: _UMOD_DISEASES}
        )
        sources_failed = []

        result = _tool()._opentargets_gene_diseases(tu, "umod", sources_failed)

        assert result == _UMOD_DISEASES
        assert sources_failed == []
        # Resolved to UMOD's Ensembl ID, not the higher-ranked GLI2 hit.
        second_call = tu.run_one_function.call_args_list[1].args[0]
        assert second_call["name"] == DISEASES_TOOL
        assert second_call["arguments"] == {"ensemblId": "ENSG00000169344"}

    def test_exact_match_behind_a_higher_ranked_fuzzy_hit_is_unchanged(self):
        tu = _fake_tu(
            {SEARCH_TOOL: _EXACT_SEARCH_RESPONSE, DISEASES_TOOL: _UMOD_DISEASES}
        )
        tool = _tool()

        result = tool._opentargets_gene_diseases(tu, "UMOD", [])
        names = [
            i["name"] for i in tool._extract_genes_or_diseases(result, "OpenTargets")
        ]

        assert names == ["familial juvenile hyperuricemic nephropathy"]
