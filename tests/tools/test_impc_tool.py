"""Unit tests for IMPC (International Mouse Phenotyping Consortium) tools."""

import pytest
from tooluniverse import ToolUniverse


class TestIMPCTools:
    """Test suite for IMPC mouse phenotyping tools."""

    @pytest.fixture
    def tu(self):
        """Initialize ToolUniverse with all tools loaded."""
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_load(self, tu):
        """Verify all IMPC tools are registered and loadable."""
        assert hasattr(tu.tools, "IMPC_get_gene_summary")
        assert hasattr(tu.tools, "IMPC_get_phenotypes_by_gene")
        assert hasattr(tu.tools, "IMPC_search_genes")
        assert hasattr(tu.tools, "IMPC_get_gene_phenotype_hits")

    def test_search_genes(self, tu):
        """Test IMPC gene search functionality."""
        result = tu.tools.IMPC_search_genes(**{"query": "Trp53", "limit": 5})

        assert isinstance(result, dict)
        assert result.get("status") in ["success", "error"]

        if result["status"] == "success":
            data = result.get("data", {})
            assert "genes" in data
            assert "count" in data
            assert isinstance(data["genes"], list)
            # Should find Trp53 (tumor suppressor, widely studied)
            if data["genes"]:
                gene = data["genes"][0]
                assert "mgi_id" in gene
                assert "symbol" in gene
                print(f"✓ Found: {gene['symbol']} ({gene['mgi_id']})")

    def test_get_gene_summary(self, tu):
        """Test IMPC gene summary retrieval."""
        result = tu.tools.IMPC_get_gene_summary(**{"gene_symbol": "Trp53"})

        assert isinstance(result, dict)
        assert result.get("status") in ["success", "error"]

        if result["status"] == "success":
            data = result.get("data")
            if data:  # Gene found
                assert "mgi_id" in data
                assert "symbol" in data
                assert "human_ortholog" in data
                # Trp53 should map to human TP53
                assert "TP53" in data.get("human_ortholog", [])
                print(f"✓ Gene: {data['symbol']}, Human: {data['human_ortholog']}")
            else:
                # Gene not in IMPC
                assert result.get("message")
                print(f"✓ Gene not phenotyped: {result['message']}")

    def test_get_phenotypes_by_gene(self, tu):
        """Test IMPC phenotype retrieval by gene."""
        result = tu.tools.IMPC_get_phenotypes_by_gene(
            **{"gene_symbol": "Braf", "limit": 20}
        )

        assert isinstance(result, dict)
        assert result.get("status") in ["success", "error"]

        if result["status"] == "success":
            data = result.get("data", {})
            assert "gene_symbol" in data
            assert "phenotypes" in data
            assert isinstance(data["phenotypes"], list)
            # Phenotype summary should be grouped
            assert "phenotype_summary_by_system" in data
            print(
                f"✓ Found {data.get('unique_phenotypes', 0)} unique phenotypes "
                f"from {data.get('total_phenotype_calls', 0)} total calls"
            )

    def test_get_gene_phenotype_hits(self, tu):
        """Test IMPC statistical results retrieval."""
        result = tu.tools.IMPC_get_gene_phenotype_hits(
            **{"gene_symbol": "Trp53", "significant_only": True, "limit": 20}
        )

        assert isinstance(result, dict)
        assert result.get("status") in ["success", "error"]

        if result["status"] == "success":
            data = result.get("data", {})
            assert "gene_symbol" in data
            assert "hits" in data
            assert isinstance(data["hits"], list)
            # Each hit should have statistical info
            if data["hits"]:
                hit = data["hits"][0]
                assert "mp_term_name" in hit
                assert "p_value" in hit
                print(
                    f"✓ Found {len(data['hits'])} hits "
                    f"(total: {data.get('total_results', 0)})"
                )

    def test_missing_parameter_error(self, tu):
        """Test error handling for missing required parameters."""
        result = tu.tools.IMPC_get_gene_summary(**{})

        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert "error" in result
        assert "required" in result["error"].lower()

    def test_gene_not_found(self, tu):
        """Test handling of genes not in IMPC."""
        result = tu.tools.IMPC_get_gene_summary(
            **{"gene_symbol": "NONEXISTENT_GENE_12345"}
        )

        assert isinstance(result, dict)
        assert result["status"] == "success"
        # Should return data=None with explanatory message
        assert result.get("data") is None
        assert result.get("message")
        assert "not found" in result["message"].lower()
