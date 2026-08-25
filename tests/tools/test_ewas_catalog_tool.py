"""Tests for the EWAS Catalog tool.

ToolUniverse has GWAS-style variant association (GWAS Catalog, PheWAS) but
nothing for methylation. Tests assert the textbook EWAS finding survives
the round trip: cg05575921 in AHRR is the strongest known
smoking-methylation association, so it should surface as a top hit.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

SMOKING_CPG = "cg05575921"


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
        assert "EWASCatalog_search_by_cpg" in names
        assert "EWASCatalog_search_by_gene" in names


class TestSearchByCpg:
    def test_ahrr_smoking_cpg_surfaces_smoking(self, tu):
        rows = data_of(
            tu.tools.EWASCatalog_search_by_cpg(cpg_id=SMOKING_CPG, limit=20)
        )
        assert rows
        traits = {r["trait"].lower() for r in rows if r["trait"]}
        assert any("smoking" in t for t in traits)

    def test_sorted_by_significance_ascending(self, tu):
        rows = data_of(
            tu.tools.EWASCatalog_search_by_cpg(cpg_id=SMOKING_CPG, limit=20)
        )
        p_values = [r["p"] for r in rows if isinstance(r["p"], (int, float))]
        assert p_values == sorted(p_values)

    def test_numeric_fields_are_coerced(self, tu):
        rows = data_of(
            tu.tools.EWASCatalog_search_by_cpg(cpg_id=SMOKING_CPG, limit=5)
        )
        assert isinstance(rows[0]["p"], (int, float))

    def test_limit_is_respected(self, tu):
        rows = data_of(
            tu.tools.EWASCatalog_search_by_cpg(cpg_id=SMOKING_CPG, limit=3)
        )
        assert len(rows) <= 3

    def test_unknown_cpg(self, tu):
        result = tu.tools.EWASCatalog_search_by_cpg(cpg_id="cgNOTREAL999999")
        assert result["status"] == "error"

    def test_missing_cpg(self, tu):
        assert tu.tools.EWASCatalog_search_by_cpg(cpg_id="")["status"] == "error"


class TestSearchByGene:
    def test_finds_associations_for_a_gene(self, tu):
        rows = data_of(
            tu.tools.EWASCatalog_search_by_gene(gene_symbol="AHRR", limit=20)
        )
        assert rows
        assert all(r["gene"] == "AHRR" for r in rows)

    def test_limit_is_respected(self, tu):
        rows = data_of(
            tu.tools.EWASCatalog_search_by_gene(gene_symbol="TP53", limit=5)
        )
        assert len(rows) <= 5

    def test_missing_gene(self, tu):
        assert tu.tools.EWASCatalog_search_by_gene(gene_symbol="")["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("EWASCatalog_search_by_cpg", {"cpg_id": ""}),
            ("EWASCatalog_search_by_cpg", {"cpg_id": "cgNOTREAL999999"}),
            ("EWASCatalog_search_by_gene", {"gene_symbol": ""}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
