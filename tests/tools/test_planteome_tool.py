"""Tests for the Planteome tool.

Planteome's GOlr-style search index (browser.planteome.org/api) has no
official client library, so these tests hit it live to confirm both
term search/lookup and the gene-to-ontology-term annotation search
resolve to real, matching data -- not just a 200 with an empty body.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

POLLEN_DEVELOPMENT = "GO:0009555"
VAMP711_GENE = "AT4G32150"


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
        assert "Planteome_search_terms" in names
        assert "Planteome_get_term" in names
        assert "Planteome_search_annotations" in names


class TestSearchTerms:
    def test_keyword_search_returns_matching_terms(self, tu):
        rows = data_of(tu.tools.Planteome_search_terms(query="pollen development", limit=10))
        assert rows
        assert any(r["id"] == POLLEN_DEVELOPMENT for r in rows)

    def test_nonsense_query_returns_empty(self, tu):
        rows = data_of(tu.tools.Planteome_search_terms(query="zzznonexistentxyz123"))
        assert rows == []

    def test_limit_is_respected(self, tu):
        rows = data_of(tu.tools.Planteome_search_terms(query="stress", limit=3))
        assert len(rows) <= 3

    def test_missing_query(self, tu):
        result = tu.tools.Planteome_search_terms(query="")
        assert result["status"] == "error"


class TestGetTerm:
    def test_known_term_resolves(self, tu):
        data = data_of(tu.tools.Planteome_get_term(term_id=POLLEN_DEVELOPMENT))
        assert data["id"] == POLLEN_DEVELOPMENT
        assert data["annotation_class_label"] == "pollen development"

    def test_unknown_term(self, tu):
        result = tu.tools.Planteome_get_term(term_id="GO:0009999999")
        assert result["status"] == "error"

    def test_missing_term_id(self, tu):
        result = tu.tools.Planteome_get_term(term_id="")
        assert result["status"] == "error"


class TestSearchAnnotations:
    def test_gene_resolves_to_its_go_annotations(self, tu):
        rows = data_of(tu.tools.Planteome_search_annotations(query=VAMP711_GENE, limit=10))
        assert rows
        assert all(r["bioentity"] and VAMP711_GENE in r["bioentity"] for r in rows)
        assert any(r["annotation_class_label"] == "vesicle-mediated transport" for r in rows)

    def test_missing_query(self, tu):
        result = tu.tools.Planteome_search_annotations(query="")
        assert result["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("Planteome_search_terms", {"query": ""}),
            ("Planteome_get_term", {"term_id": ""}),
            ("Planteome_search_annotations", {"query": ""}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
