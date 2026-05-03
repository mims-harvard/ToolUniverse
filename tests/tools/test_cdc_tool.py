"""
Tests for CDC Data tools.

These tests verify that the CDC Data tools can retrieve real data from Data.CDC.gov.
"""

import pytest
from tooluniverse import ToolUniverse


@pytest.fixture
def tu():
    """Create ToolUniverse instance for testing."""
    tu = ToolUniverse()
    tu.load_tools()
    yield tu
    tu.close()


@pytest.mark.network
@pytest.mark.integration
class TestCDCTools:
    """Integration tests for CDC Data tools with real API calls."""

    def test_search_datasets_basic(self, tu):
        """Test basic dataset search."""
        result = tu.run({
            "name": "cdc_data_search_datasets",
            "arguments": {
                "limit": 10
            }
        })
        
        assert "error" not in result, f"Error: {result.get('error')}"
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) > 0
        assert "id" in data[0]
        assert "name" in data[0]

    def test_search_datasets_with_query(self, tu):
        """Test dataset search with query term."""
        result = tu.run({
            "name": "cdc_data_search_datasets",
            "arguments": {
                "search_query": "mortality",
                "limit": 10
            }
        })
        
        assert "error" not in result, f"Error: {result.get('error')}"
        data = result["data"]
        assert len(data) > 0
        # Verify search results are relevant (name or description contains search term)
        assert any("mortality" in str(d.get("name", "")).lower() or 
                  "mortality" in str(d.get("description", "")).lower() 
                  for d in data[:5])

    def test_get_dataset(self, tu):
        """Test getting data from a specific dataset."""
        # First, find a dataset
        search_result = tu.run({
            "name": "cdc_data_search_datasets",
            "arguments": {
                "limit": 1
            }
        })
        
        if "error" not in search_result:
            datasets = search_result.get("data", [])
            if datasets:
                dataset_id = datasets[0].get("id")
                
                # Get data from that dataset
                result = tu.run({
                    "name": "cdc_data_get_dataset",
                    "arguments": {
                        "dataset_id": dataset_id,
                        "limit": 5
                    }
                })

                # Some datasets return HTTP 400 from the CDC API (e.g. non-tabular
                # datasets).  Treat that as a graceful "not available" rather than
                # a test failure.  The error may be nested inside "data".
                data_payload = result.get("data", result)
                if result.get("status") == "error" or "error" in data_payload:
                    pytest.skip(
                        f"Dataset {dataset_id} returned API error: "
                        f"{data_payload.get('error', result.get('error', 'unknown'))}"
                    )

                data = result["data"]
                assert "data" in data or isinstance(data, list)
                # Data should be a list of rows or have a data field
                if isinstance(data, list):
                    assert len(data) > 0
                elif "data" in data:
                    assert len(data["data"]) > 0

    def test_get_dataset_requires_id(self, tu):
        """Test that dataset_id is required."""
        result = tu.run({
            "name": "cdc_data_get_dataset",
            "arguments": {
                "limit": 10
            }
        })
        
        # Should return an error
        assert "error" in result
        assert "dataset_id" in result["error"].lower()

    def test_pagination(self, tu):
        """Test pagination with offset."""
        # Get first page
        result1 = tu.run({
            "name": "cdc_data_search_datasets",
            "arguments": {
                "limit": 5,
                "offset": 0
            }
        })
        
        # Get second page
        result2 = tu.run({
            "name": "cdc_data_search_datasets",
            "arguments": {
                "limit": 5,
                "offset": 5
            }
        })
        
        assert "error" not in result1
        assert "error" not in result2
        
        data1 = result1["data"]
        data2 = result2["data"]
        
        # Results should be different (unless there are fewer than 5 total)
        if len(data1) == 5 and len(data2) > 0:
            assert data1[0]["id"] != data2[0]["id"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

