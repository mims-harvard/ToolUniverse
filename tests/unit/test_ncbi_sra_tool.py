"""Unit tests for NCBISRATool."""

import sys
from pathlib import Path

import pytest

repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root / "src"))

from tooluniverse.ncbi_sra_tool import NCBISRATool


@pytest.fixture
def sra_tool():
    """Create an NCBISRATool instance for testing."""
    tool_config = {
        "name": "test_sra_tool",
        "type": "NCBISRATool",
        "description": "Test SRA tool",
    }
    return NCBISRATool(tool_config)


class TestNCBISRATool:
    """Test cases for NCBISRATool."""

    def test_tool_initialization(self, sra_tool):
        """Test that the tool initializes correctly."""
        assert sra_tool is not None
        assert sra_tool.db == "sra"
        assert sra_tool.base_url == "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def test_missing_operation(self, sra_tool):
        """Test that missing operation returns error."""
        result = sra_tool.run({})
        assert result["status"] == "error"
        assert "operation" in result["error"].lower()

    def test_unknown_operation(self, sra_tool):
        """Test that unknown operation returns error."""
        result = sra_tool.run({"operation": "invalid_operation"})
        assert result["status"] == "error"
        assert "unknown operation" in result["error"].lower()

    def test_build_search_term_organism(self, sra_tool):
        """Test search term building with organism."""
        arguments = {"organism": "Homo sapiens"}
        term = sra_tool._build_search_term(arguments)
        assert "Homo sapiens[Organism]" in term

    def test_build_search_term_strategy(self, sra_tool):
        """Test search term building with strategy."""
        arguments = {"strategy": "RNA-Seq"}
        term = sra_tool._build_search_term(arguments)
        assert "RNA-Seq[Strategy]" in term

    def test_build_search_term_multiple(self, sra_tool):
        """Test search term building with multiple filters."""
        arguments = {
            "organism": "Homo sapiens",
            "strategy": "RNA-Seq",
            "platform": "ILLUMINA"
        }
        term = sra_tool._build_search_term(arguments)
        assert "Homo sapiens[Organism]" in term
        assert "RNA-Seq[Strategy]" in term
        assert "ILLUMINA[Platform]" in term
        assert " AND " in term

    def test_search_missing_criteria(self, sra_tool):
        """Test search with no criteria returns error."""
        result = sra_tool.run({"operation": "search"})
        assert result["status"] == "error"
        assert "no search criteria" in result["error"].lower()

    def test_get_run_info_missing_accessions(self, sra_tool):
        """Test get_run_info with missing accessions."""
        result = sra_tool.run({"operation": "get_run_info"})
        assert result["status"] == "error"
        assert "accessions" in result["error"].lower()

    def test_get_download_urls_missing_accessions(self, sra_tool):
        """Test get_download_urls with missing accessions."""
        result = sra_tool.run({"operation": "get_download_urls"})
        assert result["status"] == "error"
        assert "accessions" in result["error"].lower()

    def test_get_download_urls_construction(self, sra_tool):
        """Test download URL construction."""
        result = sra_tool._get_download_urls({"accessions": "SRR000001"})
        assert result["status"] == "success"
        assert len(result["data"]) == 1

        url_info = result["data"][0]
        assert url_info["accession"] == "SRR000001"
        assert "ftp_url" in url_info
        assert "s3_url" in url_info
        assert "ncbi_url" in url_info
        assert "SRR000001" in url_info["ftp_url"]
        assert "SRR000001" in url_info["s3_url"]
        assert "SRR000001" in url_info["ncbi_url"]

    def test_get_download_urls_invalid_accession(self, sra_tool):
        """Test download URL with invalid accession format."""
        result = sra_tool._get_download_urls({"accessions": "INVALID123"})
        assert result["status"] == "success"
        assert len(result["data"]) == 1
        assert "error" in result["data"][0]
        assert "invalid accession" in result["data"][0]["error"].lower()

    def test_get_download_urls_multiple(self, sra_tool):
        """Test download URLs for multiple accessions."""
        result = sra_tool._get_download_urls(
            {"accessions": ["SRR000001", "ERR000001", "DRR000001"]}
        )
        assert result["status"] == "success"
        assert len(result["data"]) == 3
        assert result["count"] == 3

    def test_link_to_biosample_missing_accessions(self, sra_tool):
        """Test link_to_biosample with missing accessions."""
        result = sra_tool.run({"operation": "link_to_biosample"})
        assert result["status"] == "error"
        assert "accessions" in result["error"].lower()

    def test_parse_sra_xml_empty(self, sra_tool):
        """Test XML parsing with empty data."""
        xml_data = '<?xml version="1.0"?><root></root>'
        result = sra_tool._parse_sra_xml(xml_data)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_parse_sra_xml_invalid(self, sra_tool):
        """Test XML parsing with invalid data."""
        xml_data = "not valid xml"
        with pytest.raises(Exception):
            sra_tool._parse_sra_xml(xml_data)


class TestNCBISRAToolIntegration:
    """Integration tests that make actual API calls."""

    @pytest.mark.integration
    def test_search_sra_runs_real(self, sra_tool):
        """Test real SRA search (requires network)."""
        result = sra_tool.run({
            "operation": "search",
            "organism": "Escherichia coli",
            "limit": 5
        })

        # Should succeed or fail gracefully
        assert result["status"] in ["success", "error"]

        if result["status"] == "success":
            assert "data" in result
            assert "uids" in result["data"]
            assert "count" in result["data"]
            assert isinstance(result["data"]["uids"], list)

    @pytest.mark.integration
    def test_get_run_info_real(self, sra_tool):
        """Test real run info retrieval (requires network)."""
        result = sra_tool.run({
            "operation": "get_run_info",
            "accessions": "SRR000001"
        })

        # Should succeed or fail gracefully
        assert result["status"] in ["success", "error"]

        if result["status"] == "success":
            assert "data" in result
            assert isinstance(result["data"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
