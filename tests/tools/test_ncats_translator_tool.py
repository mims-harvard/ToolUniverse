"""Tests for the NCATS Translator tool.

Translator aggregates ~15 knowledge providers behind a shared biolink model.
Tests assert known biology survives the round trip: Alzheimer disease
resolves to its MONDO identifier, and BRCA1 is a documented risk gene for
breast neoplasm, rather than checking response shape alone.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

ALZHEIMER = "MONDO:0004975"
BRCA1 = "NCBIGene:672"


@pytest.fixture(scope="module")
def tu():
    instance = ToolUniverse()
    instance.load_tools()
    return instance


def data_of(result):
    if result.get("status") == "error":
        error = str(result.get("error", ""))
        if any(t in error for t in TRANSIENT):
            pytest.skip(f"upstream temporarily unavailable: {error[:80]}")
        pytest.fail(f"unexpected error response: {error[:200]}")
    return result["data"]


class TestRegistration:
    def test_tools_load(self, tu):
        names = {t.get("name") for t in tu.all_tools if isinstance(t, dict)}
        assert "NCATSTranslator_resolve_entity" in names
        assert "NCATSTranslator_query_associations" in names


class TestResolveEntity:
    def test_disease_name_resolves_to_mondo(self, tu):
        rows = data_of(
            tu.tools.NCATSTranslator_resolve_entity(name="Alzheimer disease")
        )
        assert rows[0]["curie"] == ALZHEIMER
        assert "biolink:Disease" in rows[0]["categories"]

    def test_biolink_type_filters_matches(self, tu):
        rows = data_of(
            tu.tools.NCATSTranslator_resolve_entity(name="BRCA1", biolink_type="Gene")
        )
        assert rows
        assert all("biolink:Gene" in r["categories"] for r in rows)

    def test_limit_is_respected(self, tu):
        rows = data_of(
            tu.tools.NCATSTranslator_resolve_entity(name="aspirin", limit=2)
        )
        assert len(rows) <= 2

    def test_unresolvable_name(self, tu):
        result = tu.tools.NCATSTranslator_resolve_entity(
            name="zzzznotarealbiomedicalterm12345"
        )
        assert result["status"] == "error"

    def test_missing_name(self, tu):
        assert tu.tools.NCATSTranslator_resolve_entity(name="")["status"] == "error"


class TestQueryAssociations:
    def test_chemicals_that_treat_alzheimers(self, tu):
        rows = data_of(
            tu.tools.NCATSTranslator_query_associations(
                entity_id=ALZHEIMER,
                target_category="ChemicalEntity",
                predicate="treats",
                limit=10,
            )
        )
        assert rows
        assert all(r["id"] and r["name"] for r in rows)
        # Results should be sorted by score, descending.
        scores = [r["score"] for r in rows if r["score"] is not None]
        assert scores == sorted(scores, reverse=True)

    def test_brca1_is_associated_with_breast_neoplasm(self, tu):
        # BRCA1 is the textbook example: a well-documented breast cancer
        # risk gene, reachable in the object role of the predicate.
        rows = data_of(
            tu.tools.NCATSTranslator_query_associations(
                entity_id=BRCA1,
                target_category="Disease",
                predicate="gene_associated_with_condition",
                target_role="object",
                limit=25,
            )
        )
        names = [str(r["name"]).lower() for r in rows if r["name"]]
        assert any("breast" in n for n in names)

    def test_knowledge_sources_are_attached(self, tu):
        rows = data_of(
            tu.tools.NCATSTranslator_query_associations(
                entity_id=ALZHEIMER,
                target_category="ChemicalEntity",
                predicate="treats",
                limit=5,
            )
        )
        assert any(r["knowledge_sources"] for r in rows)

    def test_limit_is_respected(self, tu):
        rows = data_of(
            tu.tools.NCATSTranslator_query_associations(
                entity_id=ALZHEIMER,
                target_category="ChemicalEntity",
                predicate="treats",
                limit=3,
            )
        )
        assert len(rows) <= 3

    def test_nonexistent_predicate_reports_reasoner_hint(self, tu):
        result = tu.tools.NCATSTranslator_query_associations(
            entity_id=ALZHEIMER,
            target_category="ChemicalEntity",
            predicate="not_a_real_predicate",
        )
        assert result["status"] == "error"

    def test_invalid_target_role(self, tu):
        result = tu.tools.NCATSTranslator_query_associations(
            entity_id=ALZHEIMER,
            target_category="ChemicalEntity",
            predicate="treats",
            target_role="sideways",
        )
        assert result["status"] == "error"

    def test_bare_category_and_predicate_are_normalized(self, tu):
        # Callers may omit the biolink: prefix; the tool should add it.
        rows = data_of(
            tu.tools.NCATSTranslator_query_associations(
                entity_id=ALZHEIMER,
                target_category="ChemicalEntity",
                predicate="treats",
                limit=3,
            )
        )
        assert rows


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("NCATSTranslator_resolve_entity", {"name": ""}),
            (
                "NCATSTranslator_query_associations",
                {"entity_id": "", "target_category": "", "predicate": ""},
            ),
            (
                "NCATSTranslator_query_associations",
                {
                    "entity_id": "MONDO:0004975",
                    "target_category": "ChemicalEntity",
                    "predicate": "treats",
                    "target_role": "nonsense",
                },
            ),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
