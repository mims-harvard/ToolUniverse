
import unittest
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tooluniverse.hpa_tool import HPASearchTool

@pytest.mark.network
class TestHPATools(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.tool_config = {
            "name": "HPA_generic_search", 
            "type": "HPASearchTool",
            "parameter": {}
        }
        self.tool = HPASearchTool(self.tool_config)

    def test_hpa_search_basic(self):
        """Test basic HPA search functionality with real network call."""
        result = self.tool.run({
            "search_query": "p53",
            "columns": "g,gs",
            "format": "json"
        })
        
        # Verify basic structure
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        
        # Verify content of first result
        first_hit = result[0]
        self.assertIn("Gene", first_hit)
        self.assertIn("Gene synonym", first_hit)

    def test_hpa_search_custom_columns(self):
        """Test HPA search with custom columns."""
        # 'gd' = Gene description
        result = self.tool.run({
            "search_query": "INS", 
            "columns": "g,gd",
            "format": "json"
        })
        
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        
        first_hit = result[0]
        self.assertIn("Gene", first_hit)
        self.assertIn("Gene description", first_hit)
        
    def test_missing_query(self):
        """Test error handling for missing query."""
        result = self.tool.run({})
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Parameter 'search_query' is required")

if __name__ == "__main__":
    unittest.main()
