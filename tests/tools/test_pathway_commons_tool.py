import unittest
from unittest.mock import patch, MagicMock
try:
    from tooluniverse.pathway_commons_tool import PathwayCommonsTool
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.getcwd(), 'src'))
    from tooluniverse.pathway_commons_tool import PathwayCommonsTool

class TestPathwayCommonsTool(unittest.TestCase):
    def setUp(self):
        dummy_config = {
            "name": "pc_search_pathways",
            "type": "PathwayCommonsTool",
            "description": "Test",
            "parameter": {}
        }
        self.tool = PathwayCommonsTool(tool_config=dummy_config)

    @patch('tooluniverse.pathway_commons_tool.requests.get')
    def test_search_pathways(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "numHits": 1,
            "searchHit": [
                {
                    "name": "Test Pathway",
                    "uri": "http://uri",
                    "dataSource": ["reactome"],
                    "organism": ["human"]
                }
            ]
        }
        mock_get.return_value = mock_response

        result = self.tool.run({
            "action": "search_pathways",
            "keyword": "test",
            "limit": 5
        })

        self.assertEqual(result["total_hits"], 1)
        self.assertEqual(result["pathways"][0]["name"], "Test Pathway")
        
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["q"], "test")

    @patch('tooluniverse.pathway_commons_tool.requests.get')
    def test_get_interaction_graph(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        # SIF text response
        mock_response.text = "A\tcontrols-state-change-of\tB\nB\tin-complex-with\tC"
        mock_get.return_value = mock_response

        result = self.tool.run({
            "action": "get_interaction_graph",
            "gene_list": ["A", "B", "C"]
        })

        self.assertEqual(len(result["interactions"]), 2)
        self.assertEqual(result["interactions"][0]["source"], "A")
        self.assertEqual(result["interactions"][0]["target"], "B")
        self.assertEqual(result["interactions"][1]["relation"], "in-complex-with")

if __name__ == "__main__":
    unittest.main()
