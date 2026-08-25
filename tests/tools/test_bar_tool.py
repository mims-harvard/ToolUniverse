"""Tests for the BAR (Bio-Analytic Resource for Plant Biology) tool.

The BAR publishes a documented, unauthenticated OpenAPI spec
(bar.utoronto.ca/api/swagger.json). These tests hit the live gene
annotation and RNA-seq expression endpoints with a well-known
Arabidopsis gene (AT1G01010) to confirm real data comes back, not
just a 200 with an empty/placeholder body.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

NAC001 = "AT1G01010"
TIR1 = "AT3G62980"


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
        assert "BAR_get_gene_info" in names
        assert "BAR_get_rnaseq_expression" in names


class TestGetGeneInfo:
    def test_known_gene_returns_correct_annotation(self, tu):
        data = data_of(tu.tools.BAR_get_gene_info(gene_id=NAC001))
        assert data["chromosome"] == "Chr1"
        assert "NAC001" in data["aliases"]
        assert "NAC domain" in data["annotation"]

    def test_second_known_gene(self, tu):
        data = data_of(tu.tools.BAR_get_gene_info(gene_id=TIR1))
        assert "TIR1" in data["aliases"]

    def test_unknown_gene(self, tu):
        result = tu.tools.BAR_get_gene_info(gene_id="NOTAREALGENE999")
        assert result["status"] == "error"

    def test_unknown_species(self, tu):
        result = tu.tools.BAR_get_gene_info(gene_id=NAC001, species="notarealspecies")
        assert result["status"] == "error"

    def test_missing_gene_id(self, tu):
        result = tu.tools.BAR_get_gene_info(gene_id="")
        assert result["status"] == "error"


class TestGetRnaseqExpression:
    def test_known_gene_returns_cluster_expression(self, tu):
        data = data_of(tu.tools.BAR_get_rnaseq_expression(gene_id="At1g01010"))
        assert data
        assert all(isinstance(v, (int, float)) for v in data.values())

    def test_two_different_genes_return_different_profiles(self, tu):
        nac001 = data_of(tu.tools.BAR_get_rnaseq_expression(gene_id="At1g01010"))
        tir1 = data_of(tu.tools.BAR_get_rnaseq_expression(gene_id="At3g62980"))
        assert nac001 != tir1

    def test_unknown_gene(self, tu):
        result = tu.tools.BAR_get_rnaseq_expression(gene_id="NOTAREALGENE999")
        assert result["status"] == "error"

    def test_missing_gene_id(self, tu):
        result = tu.tools.BAR_get_rnaseq_expression(gene_id="")
        assert result["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("BAR_get_gene_info", {"gene_id": ""}),
            ("BAR_get_rnaseq_expression", {"gene_id": ""}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
