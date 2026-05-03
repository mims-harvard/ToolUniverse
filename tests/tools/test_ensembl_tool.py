"""
Unit tests for Ensembl REST API tools
Tests both direct class instantiation and ToolUniverse interface
"""

import json
import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.ensembl_tool import EnsemblRESTTool
from tooluniverse import ToolUniverse


class TestEnsemblDirectClass:
    """Level 1: Direct class testing - validates implementation logic"""

    @pytest.fixture
    def tool_configs(self):
        """Load all Ensembl tool configs"""
        config_path = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data" / "ensembl_tools.json"
        with open(config_path) as f:
            return json.load(f)

    def test_lookup_gene_by_id(self, tool_configs):
        """Test gene lookup by Ensembl ID"""
        config = next(t for t in tool_configs if t["name"] == "ensembl_lookup_gene")
        tool = EnsemblRESTTool(config)
        
        result = tool.run({
            "gene_id": "ENSG00000012048",
            "species": "homo_sapiens"
        })
        
        assert result["status"] == "success"
        assert "data" in result
        assert result["data"]["id"] == "ENSG00000012048"
        assert "display_name" in result["data"]
        assert "description" in result["data"]

    def test_lookup_gene_by_symbol(self, tool_configs):
        """Test gene lookup by gene symbol"""
        config = next(t for t in tool_configs if t["name"] == "ensembl_lookup_gene")
        tool = EnsemblRESTTool(config)
        
        result = tool.run({
            "gene_id": "BRCA1",
            "species": "homo_sapiens"
        })
        
        assert result["status"] == "success"
        assert "data" in result
        assert result["data"]["display_name"] == "BRCA1"

    def test_get_sequence(self, tool_configs):
        """Test sequence retrieval"""
        config = next(t for t in tool_configs if t["name"] == "ensembl_get_sequence")
        tool = EnsemblRESTTool(config)
        
        result = tool.run({
            "id": "ENSG00000012048",
            "type": "genomic"
        })
        
        assert result["status"] == "success"
        assert "data" in result
        # Response should be array or single object with sequence
        if isinstance(result["data"], list):
            assert len(result["data"]) > 0
            assert "seq" in result["data"][0]
        else:
            assert "seq" in result["data"]

    def test_get_variants_in_region(self, tool_configs):
        """Test variant retrieval in genomic region"""
        config = next(t for t in tool_configs if t["name"] == "ensembl_get_variants")
        tool = EnsemblRESTTool(config)
        
        result = tool.run({
            "region": "13:32315086-32400268",
            "species": "human"
        })
        
        assert result["status"] == "success"
        assert "data" in result
        assert isinstance(result["data"], list)

    def test_get_variation_by_id(self, tool_configs):
        """Test variation lookup by rsID"""
        config = next(t for t in tool_configs if t["name"] == "ensembl_get_variation")
        tool = EnsemblRESTTool(config)
        
        result = tool.run({
            "id": "rs699",
            "species": "human",
            "phenotypes": 1
        })
        
        assert result["status"] == "success"
        assert "data" in result
        assert result["data"]["name"] == "rs699"

    def test_get_xrefs(self, tool_configs):
        """Test cross-reference retrieval"""
        config = next(t for t in tool_configs if t["name"] == "ensembl_get_xrefs")
        tool = EnsemblRESTTool(config)
        
        result = tool.run({
            "id": "ENSG00000139618"
        })
        
        assert result["status"] == "success"
        assert "data" in result
        assert isinstance(result["data"], list)
        assert len(result["data"]) > 0
        # Should have various database cross-references
        db_names = [xref.get("dbname") for xref in result["data"]]
        assert len(db_names) > 0

    def test_get_regulatory_features(self, tool_configs):
        """Test regulatory feature retrieval"""
        config = next(t for t in tool_configs if t["name"] == "ensembl_get_regulatory_features")
        tool = EnsemblRESTTool(config)
        
        result = tool.run({
            "region": "1:1000000-2000000",
            "species": "human",
            "feature": "regulatory"
        })
        
        assert result["status"] == "success"
        assert "data" in result
        assert isinstance(result["data"], list)

    def test_get_homology(self, tool_configs):
        """Test homology retrieval (orthologues/paralogues)"""
        config = next(t for t in tool_configs if t["name"] == "ensembl_get_homology")
        tool = EnsemblRESTTool(config)
        
        result = tool.run({
            "species": "human",
            "symbol": "BRCA2",
            "target_species": "mouse",
            "type": "orthologues"
        })
        
        # Should now work with symbol-based endpoint
        assert result["status"] == "success"
        assert "data" in result
        # Response structure: result["data"]["data"][0]["homologies"]
        if "data" in result["data"] and len(result["data"]["data"]) > 0:
            if "homologies" in result["data"]["data"][0]:
                assert isinstance(result["data"]["data"][0]["homologies"], list)

    def test_get_alignment(self, tool_configs):
        """Test genomic alignment retrieval"""
        config = next(t for t in tool_configs if t["name"] == "ensembl_get_alignment")
        tool = EnsemblRESTTool(config)
        
        result = tool.run({
            "species": "human",
            "region": "2:106000000-106100000",
            "species_set_group": "mammals",
            "method": "EPO"
        })
        
        # Should now work with species_set_group parameter
        assert result["status"] == "success"
        assert "data" in result
        assert isinstance(result["data"], list)

    def test_get_taxonomy(self, tool_configs):
        """Test taxonomy classification retrieval"""
        config = next(t for t in tool_configs if t["name"] == "ensembl_get_taxonomy")
        tool = EnsemblRESTTool(config)
        
        result = tool.run({
            "id": "9606"  # Human taxonomy ID
        })
        
        assert result["status"] == "success"
        assert "data" in result
        assert isinstance(result["data"], list)
        assert len(result["data"]) > 0
        # Should have taxonomy structure (even without 'rank' field)
        first_item = result["data"][0]
        assert "scientific_name" in first_item or "name" in first_item

    def test_get_species(self, tool_configs):
        """Test species information retrieval"""
        config = next(t for t in tool_configs if t["name"] == "ensembl_get_species")
        tool = EnsemblRESTTool(config)
        
        result = tool.run({
            "division": "EnsemblVertebrates"
        })
        
        assert result["status"] == "success"
        assert "data" in result
        assert "species" in result["data"]
        assert isinstance(result["data"]["species"], list)
        assert len(result["data"]["species"]) > 0

    def test_get_archive(self, tool_configs):
        """Test archive/historical data retrieval"""
        config = next(t for t in tool_configs if t["name"] == "ensembl_get_archive")
        tool = EnsemblRESTTool(config)
        
        result = tool.run({
            "id": "ENSG00000139618"
        })
        
        assert result["status"] == "success"
        assert "data" in result
        # Archive returns array of versions
        if isinstance(result["data"], list):
            assert len(result["data"]) > 0
        elif isinstance(result["data"], dict):
            # Some endpoints return single object
            assert "id" in result["data"]

    def test_get_ontology_term(self, tool_configs):
        """Test ontology term retrieval"""
        config = next(t for t in tool_configs if t["name"] == "ensembl_get_ontology_term")
        tool = EnsemblRESTTool(config)
        
        result = tool.run({
            "id": "GO:0005737"  # Cytoplasm
        })
        
        assert result["status"] == "success"
        assert "data" in result
        assert result["data"]["accession"] == "GO:0005737"
        assert "name" in result["data"]
        assert "definition" in result["data"]

    def test_get_ontology_ancestors(self, tool_configs):
        """Test ontology ancestor retrieval"""
        config = next(t for t in tool_configs if t["name"] == "ensembl_get_ontology_ancestors")
        tool = EnsemblRESTTool(config)
        
        result = tool.run({
            "id": "GO:0005737"
        })
        
        assert result["status"] == "success"
        assert "data" in result
        assert isinstance(result["data"], list)

    def test_get_ontology_descendants(self, tool_configs):
        """Test ontology descendant retrieval"""
        config = next(t for t in tool_configs if t["name"] == "ensembl_get_ontology_descendants")
        tool = EnsemblRESTTool(config)
        
        result = tool.run({
            "id": "GO:0005737",
            "closest_term": False
        })
        
        assert result["status"] == "success"
        assert "data" in result
        assert isinstance(result["data"], list)

    def test_get_overlap_features(self, tool_configs):
        """Test overlapping feature retrieval"""
        config = next(t for t in tool_configs if t["name"] == "ensembl_get_overlap_features")
        tool = EnsemblRESTTool(config)
        
        result = tool.run({
            "species": "human",
            "region": "7:140424943-140624564",
            "feature": "gene"
        })
        
        assert result["status"] == "success"
        assert "data" in result
        assert isinstance(result["data"], list)

    def test_vep_region(self, tool_configs):
        """Test Variant Effect Predictor"""
        config = next(t for t in tool_configs if t["name"] == "ensembl_vep_region")
        tool = EnsemblRESTTool(config)
        
        result = tool.run({
            "species": "human",
            "region": "21:25891796-25891796",
            "allele": "T"
        })
        
        assert result["status"] == "success"
        assert "data" in result
        assert isinstance(result["data"], list)
        if len(result["data"]) > 0:
            # VEP returns transcript_consequences, not consequence_terms
            assert "transcript_consequences" in result["data"][0] or "most_severe_consequence" in result["data"][0]

    def test_error_handling_missing_param(self, tool_configs):
        """Test error handling for missing required parameters"""
        config = next(t for t in tool_configs if t["name"] == "ensembl_lookup_gene")
        tool = EnsemblRESTTool(config)
        
        result = tool.run({})
        
        assert result["status"] == "error"
        assert "gene_id" in result["error"]

    def test_error_handling_invalid_id(self, tool_configs):
        """Test error handling for invalid IDs"""
        config = next(t for t in tool_configs if t["name"] == "ensembl_lookup_gene")
        tool = EnsemblRESTTool(config)
        
        result = tool.run({
            "gene_id": "INVALID_GENE_ID_XXXXXX"
        })
        
        # Should return error from API
        assert result["status"] == "error"


class TestEnsemblToolUniverse:
    """Level 2: ToolUniverse interface testing - validates registration and access"""

    @pytest.fixture
    def tu(self):
        """Initialize ToolUniverse with all tools loaded"""
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_loaded(self, tu):
        """Verify all Ensembl tools are properly registered"""
        ensembl_tools = [
            "ensembl_lookup_gene",
            "ensembl_get_sequence",
            "ensembl_get_variants",
            "ensembl_get_variation",
            "ensembl_get_variation_phenotypes",
            "ensembl_get_xrefs",
            "ensembl_get_xrefs_by_name",
            "ensembl_get_regulatory_features",
            "ensembl_get_genetree",
            "ensembl_get_homology",
            "ensembl_get_alignment",
            "ensembl_get_taxonomy",
            "ensembl_get_species",
            "ensembl_get_archive",
            "ensembl_get_ontology_term",
            "ensembl_get_ontology_ancestors",
            "ensembl_get_ontology_descendants",
            "ensembl_get_overlap_features",
            "ensembl_vep_region"
        ]
        
        for tool_name in ensembl_tools:
            assert hasattr(tu.tools, tool_name), f"Tool {tool_name} not loaded"

    def test_lookup_via_tooluniverse(self, tu):
        """Test gene lookup via ToolUniverse interface"""
        result = tu.tools.ensembl_lookup_gene(**{
            "gene_id": "ENSG00000012048",
            "species": "homo_sapiens"
        })
        
        assert result["status"] == "success"
        assert "data" in result

    def test_homology_via_tooluniverse(self, tu):
        """Test homology retrieval via ToolUniverse interface"""
        result = tu.tools.ensembl_get_homology(**{
            "species": "human",
            "symbol": "BRCA2",
            "target_species": "mouse",
            "type": "orthologues"
        })
        
        # Should now work with symbol-based endpoint
        assert result["status"] == "success"
        assert "data" in result

    def test_taxonomy_via_tooluniverse(self, tu):
        """Test taxonomy via ToolUniverse interface"""
        result = tu.tools.ensembl_get_taxonomy(**{
            "id": "9606"
        })
        
        assert result["status"] == "success"
        assert "data" in result

    def test_ontology_term_via_tooluniverse(self, tu):
        """Test ontology term via ToolUniverse interface"""
        result = tu.tools.ensembl_get_ontology_term(**{
            "id": "GO:0005737"
        })
        
        assert result["status"] == "success"
        assert "data" in result

    def test_vep_via_tooluniverse(self, tu):
        """Test VEP via ToolUniverse interface"""
        result = tu.tools.ensembl_vep_region(**{
            "species": "human",
            "region": "21:25891796-25891796",
            "allele": "T"
        })
        
        assert result["status"] == "success"
        assert "data" in result


class TestEnsemblRealAPI:
    """Level 3: Real API integration tests"""

    @pytest.fixture
    def tu(self):
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_real_gene_lookup(self, tu):
        """Test real API call for gene lookup"""
        result = tu.tools.ensembl_lookup_gene(**{
            "gene_id": "BRCA2",
            "species": "homo_sapiens"
        })
        
        if result["status"] == "success":
            assert result["data"]["display_name"] == "BRCA2"
            print("✅ Real API: Gene lookup works")
        else:
            print(f"⚠️  API returned error (may be down): {result['error']}")

    def test_real_homology(self, tu):
        """Test real API call for homology"""
        result = tu.tools.ensembl_get_homology(**{
            "species": "human",
            "symbol": "BRCA2",
            "target_species": "mouse",
            "type": "orthologues"
        })
        
        if result["status"] == "success":
            print("✅ Real API: Homology retrieval works")
            # Verify we got actual homology data
            if "data" in result["data"] and len(result["data"]["data"]) > 0:
                if "homologies" in result["data"]["data"][0]:
                    print(f"   Found {len(result['data']['data'][0]['homologies'])} orthologues")
        else:
            print(f"⚠️  API returned error: {result['error']}")

    def test_real_taxonomy(self, tu):
        """Test real API call for taxonomy"""
        result = tu.tools.ensembl_get_taxonomy(**{
            "id": "9606"
        })
        
        if result["status"] == "success":
            # Should have complete lineage
            assert len(result["data"]) > 5
            print("✅ Real API: Taxonomy works")
        else:
            print(f"⚠️  API returned error: {result['error']}")

    def test_real_ontology(self, tu):
        """Test real API call for ontology"""
        result = tu.tools.ensembl_get_ontology_term(**{
            "id": "GO:0005737"
        })
        
        if result["status"] == "success":
            assert "cytoplasm" in result["data"]["name"].lower()
            print("✅ Real API: Ontology works")
        else:
            print(f"⚠️  API returned error: {result['error']}")

    def test_real_vep(self, tu):
        """Test real API call for VEP"""
        result = tu.tools.ensembl_vep_region(**{
            "species": "human",
            "region": "21:25891796-25891796",
            "allele": "T"
        })
        
        if result["status"] == "success":
            print("✅ Real API: VEP works")
        else:
            print(f"⚠️  API returned error: {result['error']}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
