"""
Tests for UMLS tools.

These tests verify that the UMLS tools work correctly.
Note: These tests require UMLS_API_KEY environment variable to be set.
"""

import os
import pytest
from tooluniverse import ToolUniverse


@pytest.fixture
def tu():
    """Create ToolUniverse instance for testing."""
    tu = ToolUniverse()
    tu.load_tools()
    yield tu
    tu.close()


@pytest.fixture
def has_api_key():
    """Check if UMLS API key is available."""
    return os.environ.get("UMLS_API_KEY") is not None


@pytest.mark.network
@pytest.mark.integration
class TestUMLSTools:
    """Integration tests for UMLS tools with real API calls."""

    def test_search_concepts_requires_api_key(self, tu):
        """Test that search requires API key."""
        # Temporarily remove API key if present
        original_key = os.environ.get("UMLS_API_KEY")
        if "UMLS_API_KEY" in os.environ:
            del os.environ["UMLS_API_KEY"]
        
        try:
            result = tu.run({
                "name": "umls_search_concepts",
                "arguments": {
                    "query": "diabetes"
                }
            })
            
            # Should return an error about API key
            assert "error" in result
            assert "UMLS_API_KEY" in result["error"] or "api key" in result["error"].lower()
        finally:
            # Restore API key if it was present
            if original_key:
                os.environ["UMLS_API_KEY"] = original_key

    @pytest.mark.skipif(
        not os.environ.get("UMLS_API_KEY"),
        reason="UMLS_API_KEY not set - requires free registration at https://uts.nlm.nih.gov/uts/"
    )
    def test_search_concepts_with_api_key(self, tu):
        """Test concept search with valid API key."""
        result = tu.run({
            "name": "umls_search_concepts",
            "arguments": {
                "query": "diabetes",
                "pageSize": 5
            }
        })
        
        assert "error" not in result, f"Error: {result.get('error')}"
        assert "data" in result
        data = result["data"]
        assert "result" in data
        result_obj = data["result"]
        assert "results" in result_obj
        results = result_obj["results"]
        assert len(results) > 0
        assert "ui" in results[0]  # CUI
        assert "name" in results[0]

    @pytest.mark.skipif(
        not os.environ.get("UMLS_API_KEY"),
        reason="UMLS_API_KEY not set"
    )
    def test_icd_search_codes(self, tu):
        """Test ICD code search."""
        result = tu.run({
            "name": "icd_search_codes",
            "arguments": {
                "query": "hypertension",
                "version": "ICD10CM",
                "pageSize": 5
            }
        })
        
        assert "error" not in result, f"Error: {result.get('error')}"
        data = result["data"]
        results = data.get("result", {}).get("results", [])
        if len(results) > 0:
            # Verify results have standard UMLS fields; rootSource value varies by API version
            # (may be "ICD10CM", "ICD9CM", etc.)
            assert all("rootSource" in r for r in results)

    @pytest.mark.skipif(
        not os.environ.get("UMLS_API_KEY"),
        reason="UMLS_API_KEY not set"
    )
    def test_snomed_search_concepts(self, tu):
        """Test SNOMED CT concept search."""
        result = tu.run({
            "name": "snomed_search_concepts",
            "arguments": {
                "query": "diabetes",
                "pageSize": 5
            }
        })
        
        assert "error" not in result, f"Error: {result.get('error')}"
        data = result["data"]
        results = data.get("result", {}).get("results", [])
        if len(results) > 0:
            # Verify results have standard UMLS fields; rootSource value varies by API version
            # (may be "SNOMEDCT_US", "SNOMEDCT", etc.)
            assert all("rootSource" in r for r in results)

    @pytest.mark.skipif(
        not os.environ.get("UMLS_API_KEY"),
        reason="UMLS_API_KEY not set"
    )
    def test_loinc_search_codes(self, tu):
        """Test LOINC code search."""
        result = tu.run({
            "name": "loinc_search_codes",
            "arguments": {
                "query": "glucose",
                "pageSize": 5
            }
        })
        
        assert "error" not in result, f"Error: {result.get('error')}"
        data = result["data"]
        results = data.get("result", {}).get("results", [])
        if len(results) > 0:
            # Verify results are from LOINC
            assert any("LNC" in r.get("rootSource", "") for r in results)

    @pytest.mark.skipif(
        not os.environ.get("UMLS_API_KEY"),
        reason="UMLS_API_KEY not set"
    )
    def test_get_concept_details(self, tu):
        """Test getting concept details by CUI."""
        # Use a known CUI: C0011849 (Diabetes mellitus)
        result = tu.run({
            "name": "umls_get_concept_details",
            "arguments": {
                "cui": "C0011849"
            }
        })
        
        assert "error" not in result, f"Error: {result.get('error')}"
        data = result["data"]
        concept = data.get("result", {})
        assert concept.get("ui") == "C0011849"
        assert "name" in concept

    def test_search_requires_query(self, tu):
        """Test that search requires query parameter."""
        result = tu.run({
            "name": "umls_search_concepts",
            "arguments": {}
        })
        
        # Should return an error
        assert "error" in result
        assert "query" in result["error"].lower()

    def test_get_concept_requires_cui(self, tu):
        """Test that get_concept_details requires cui parameter."""
        result = tu.run({
            "name": "umls_get_concept_details",
            "arguments": {}
        })
        
        # Should return an error
        assert "error" in result
        assert "cui" in result["error"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

