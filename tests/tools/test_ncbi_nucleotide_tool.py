"""
Tests for NCBI Nucleotide Search Tool
"""

import pytest
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.ncbi_nucleotide_tool import NCBINucleotideSearchTool
from tooluniverse import ToolUniverse


class TestNCBINucleotideToolDirect:
    """Level 1: Direct class testing"""

    @pytest.fixture
    def tool_config(self):
        """Load tool config from JSON"""
        config_path = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data" / "ncbi_nucleotide_tools.json"
        with open(config_path) as f:
            tools = json.load(f)
            return next(t for t in tools if t["name"] == "NCBI_search_nucleotide")

    @pytest.fixture
    def tool(self, tool_config):
        """Create tool instance"""
        return NCBINucleotideSearchTool(tool_config)

    def test_search_by_organism_strain(self, tool):
        """Test searching by organism and strain"""
        result = tool.run({
            "operation": "search",
            "organism": "Escherichia coli",
            "strain": "K-12",
            "keywords": "complete genome",
            "limit": 5
        })

        assert result["status"] == "success"
        assert "data" in result
        assert "uids" in result["data"]
        assert len(result["data"]["uids"]) > 0
        assert result["data"]["count"] > 0
        print(f"✓ Found {result['data']['count']} E. coli K-12 genomes")

    def test_search_by_organism_gene(self, tool):
        """Test searching by organism and gene"""
        result = tool.run({
            "operation": "search",
            "organism": "Homo sapiens",
            "gene": "BRCA1",
            "limit": 10
        })

        assert result["status"] == "success"
        assert "data" in result
        assert "uids" in result["data"]
        assert len(result["data"]["uids"]) > 0
        print(f"✓ Found {result['data']['count']} human BRCA1 sequences")

    def test_search_with_seq_type_filter(self, tool):
        """Test searching with sequence type filter"""
        result = tool.run({
            "operation": "search",
            "organism": "SARS-CoV-2",
            "seq_type": "complete_genome",
            "limit": 5
        })

        assert result["status"] == "success"
        assert "data" in result
        print(f"✓ Found {result['data']['count']} SARS-CoV-2 genomes")

    def test_missing_search_criteria(self, tool):
        """Test error when no search criteria provided"""
        result = tool.run({
            "operation": "search",
            "limit": 10
        })

        assert result["status"] == "error"
        assert "No search criteria" in result["error"]
        print("✓ Correctly handles missing search criteria")

    def test_fetch_accession_single_uid(self):
        """Test fetching accession for single UID"""
        config_path = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data" / "ncbi_nucleotide_tools.json"
        with open(config_path) as f:
            tools = json.load(f)
            config = next(t for t in tools if t["name"] == "NCBI_fetch_accessions")

        tool = NCBINucleotideSearchTool(config)
        result = tool.run({
            "operation": "fetch_accession",
            "uids": ["545778205"]
        })

        assert result["status"] == "success"
        assert "data" in result
        assert isinstance(result["data"], list)
        assert len(result["data"]) > 0
        print(f"✓ Fetched accession: {result['data'][0]}")

    def test_fetch_sequence(self):
        """Test fetching sequence by accession"""
        config_path = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data" / "ncbi_nucleotide_tools.json"
        with open(config_path) as f:
            tools = json.load(f)
            config = next(t for t in tools if t["name"] == "NCBI_get_sequence")

        tool = NCBINucleotideSearchTool(config)
        result = tool.run({
            "operation": "fetch_sequence",
            "accession": "U00096",
            "format": "fasta"
        })

        assert result["status"] == "success"
        assert "data" in result
        assert isinstance(result["data"], str)
        assert result["data"].startswith(">")
        assert result["accession"] == "U00096"
        assert result["format"] == "fasta"
        print(f"✓ Fetched sequence: {len(result['data'])} characters")


class TestNCBINucleotideToolInterface:
    """Level 2: ToolUniverse interface testing"""

    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance"""
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_registered(self, tu):
        """Verify all 3 tools are registered"""
        assert hasattr(tu.tools, "NCBI_search_nucleotide"), "NCBI_search_nucleotide not registered"
        assert hasattr(tu.tools, "NCBI_fetch_accessions"), "NCBI_fetch_accessions not registered"
        assert hasattr(tu.tools, "NCBI_get_sequence"), "NCBI_get_sequence not registered"
        print("✓ All 3 NCBI nucleotide tools registered")

    def test_search_execution_via_tu(self, tu):
        """Test search via ToolUniverse interface"""
        result = tu.tools.NCBI_search_nucleotide(
            operation="search",
            organism="Escherichia coli",
            strain="K-12",
            keywords="complete genome",
            limit=3
        )

        assert result["status"] == "success"
        assert "data" in result
        assert "uids" in result["data"]
        print(f"✓ Search via ToolUniverse: Found {len(result['data']['uids'])} UIDs")

    def test_fetch_accessions_via_tu(self, tu):
        """Test accession fetching via ToolUniverse interface"""
        result = tu.tools.NCBI_fetch_accessions(
            operation="fetch_accession",
            uids=["545778205"]
        )

        assert result["status"] == "success"
        assert "data" in result
        assert isinstance(result["data"], list)
        print(f"✓ Fetch accessions via ToolUniverse: {result['data']}")

    def test_get_sequence_via_tu(self, tu):
        """Test sequence retrieval via ToolUniverse interface"""
        result = tu.tools.NCBI_get_sequence(
            operation="fetch_sequence",
            accession="U00096",
            format="fasta"
        )

        assert result["status"] == "success"
        assert "data" in result
        assert result["data"].startswith(">")
        print(f"✓ Get sequence via ToolUniverse: {len(result['data'])} chars")


class TestNCBINucleotideRealAPI:
    """Level 3: Real API integration testing"""

    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance"""
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_complete_workflow(self, tu):
        """Test complete workflow: search → fetch UIDs → get accessions → get sequence"""
        print("\n▶ Step 1: Search for E. coli K-12 genome")
        search_result = tu.tools.NCBI_search_nucleotide(
            operation="search",
            organism="Escherichia coli",
            strain="K-12",
            keywords="complete genome",
            limit=2
        )

        if search_result["status"] != "success":
            pytest.skip(f"API unavailable: {search_result.get('error')}")

        uids = search_result["data"]["uids"]
        print(f"  ✓ Found {len(uids)} UIDs: {uids[:2]}")

        print("\n▶ Step 2: Fetch accession numbers")
        accession_result = tu.tools.NCBI_fetch_accessions(
            operation="fetch_accession",
            uids=uids[:2]
        )

        assert accession_result["status"] == "success"
        accessions = accession_result["data"]
        print(f"  ✓ Got accessions: {accessions}")

        # Check we have both GenBank and possibly RefSeq accessions
        genbank_accessions = [acc for acc in accessions if not acc.startswith("NC_")]
        refseq_accessions = [acc for acc in accessions if acc.startswith("NC_")]

        print(f"  ✓ GenBank/EMBL accessions: {genbank_accessions}")
        if refseq_accessions:
            print(f"  ✓ RefSeq accessions: {refseq_accessions}")

        print("\n▶ Step 3: Get sequence for first accession")
        seq_result = tu.tools.NCBI_get_sequence(
            operation="fetch_sequence",
            accession=accessions[0],
            format="fasta"
        )

        assert seq_result["status"] == "success"
        assert seq_result["data"].startswith(">")
        print(f"  ✓ Retrieved sequence: {len(seq_result['data']):,} characters")
        print(f"  ✓ FASTA header: {seq_result['data'].split(chr(10))[0][:80]}...")

        print("\n✓ Complete workflow successful!")

    def test_search_different_organisms(self, tu):
        """Test searching for different organisms"""
        organisms = [
            ("Escherichia coli", "K-12"),
            ("Homo sapiens", None),
            ("SARS-CoV-2", None),
        ]

        for organism, strain in organisms:
            print(f"\n▶ Testing: {organism}" + (f" {strain}" if strain else ""))

            args = {
                "operation": "search",
                "organism": organism,
                "limit": 3
            }
            if strain:
                args["strain"] = strain

            result = tu.tools.NCBI_search_nucleotide(**args)

            if result["status"] == "success":
                print(f"  ✓ Found {result['data']['count']} results")
            else:
                print(f"  ⚠️  Error: {result.get('error')}")


if __name__ == "__main__":
    # Run with pytest or directly
    pytest.main([__file__, "-v", "-s"])
