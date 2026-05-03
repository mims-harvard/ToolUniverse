"""
Tests for health disparities tools.

These tools provide information about data sources rather than direct data access.
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
class TestHealthDisparitiesTools:
    """Tests for health disparities tools."""

    def test_get_svi_info(self, tu):
        """Test getting SVI information."""
        result = tu.run({
            "name": "health_disparities_get_svi_info",
            "arguments": {
                "year": 2020
            }
        })
        
        assert "error" not in result, f"Error: {result.get('error')}"
        assert "data" in result
        data = result["data"]
        assert "data_sources" in data
        sources = data["data_sources"]
        assert len(sources) > 0
        assert "download_url" in sources[0]

    def test_get_county_rankings_info(self, tu):
        """Test getting County Health Rankings information."""
        result = tu.run({
            "name": "health_disparities_get_county_rankings_info",
            "arguments": {}
        })
        
        assert "error" not in result, f"Error: {result.get('error')}"
        assert "data" in result
        data = result["data"]
        assert "data_sources" in data
        sources = data["data_sources"]
        assert len(sources) > 0
        assert "access_url" in sources[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

