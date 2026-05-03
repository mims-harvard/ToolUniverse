"""
Tests for NHANES tools.

These tools provide information about NHANES datasets.
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


@pytest.mark.unit
class TestNHANESTools:
    """Tests for NHANES tools."""

    def test_get_dataset_info(self, tu):
        """Test getting NHANES dataset information."""
        result = tu.run({
            "name": "nhanes_get_dataset_info",
            "arguments": {
                "year": "2017-2018"
            }
        })
        
        assert "error" not in result, f"Error: {result.get('error')}"
        assert "data" in result
        data = result["data"]
        assert "datasets" in data
        datasets = data["datasets"]
        assert len(datasets) > 0
        assert "download_url" in datasets[0]

    def test_search_datasets(self, tu):
        """Test searching for NHANES datasets."""
        result = tu.run({
            "name": "nhanes_search_datasets",
            "arguments": {
                "search_term": "glucose"
            }
        })
        
        assert "error" not in result, f"Error: {result.get('error')}"
        assert "data" in result
        data = result["data"]
        assert "datasets" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

