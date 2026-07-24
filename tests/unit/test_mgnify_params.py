"""MGnify tools map friendly args onto the API's real query parameters.

Regression: the original tool sent `biome=`/`size=` against the
`api/latest` base. `api/latest` 301-redirects to `api/v2` (dropping the query
string) and, on the real endpoint, the biome filter is `lineage=` and pagination
is `page_size=`. The net effect was a silent empty result (`data: []`) even for
well-populated biomes such as the human gut. The tools must target `api/v1` and
translate `biome -> lineage` and `size -> page_size`.
"""

import unittest
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


def _studies_tool():
    from tooluniverse.mgnify_tool import MGnifyStudiesTool

    return MGnifyStudiesTool(
        {
            "settings": {
                "base_url": "https://www.ebi.ac.uk/metagenomics/api/v1",
                "timeout": 30,
            }
        }
    )


def _analyses_tool():
    from tooluniverse.mgnify_tool import MGnifyAnalysesTool

    return MGnifyAnalysesTool(
        {
            "settings": {
                "base_url": "https://www.ebi.ac.uk/metagenomics/api/v1",
                "timeout": 30,
            }
        }
    )


class TestMGnifyParams(unittest.TestCase):
    def test_studies_biome_maps_to_lineage_and_v1(self):
        tool = _studies_tool()
        with patch("tooluniverse.mgnify_tool._http_get") as http:
            http.return_value = {"data": [{"id": "MGYS00002012"}]}
            result = tool.run(
                {"biome": "root:Host-associated:Human:Digestive system", "size": 3}
            )
        called_url = http.call_args.args[0]
        # biome must be sent as the API's `lineage` filter, not `biome`
        self.assertIn("lineage=", called_url)
        self.assertNotIn("biome=", called_url)
        # size must be sent as `page_size`, not `size`
        self.assertIn("page_size=3", called_url)
        # must target the stable v1 endpoint (api/latest 301-redirects + drops query)
        self.assertIn("/api/v1/studies", called_url)
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 1)

    def test_studies_search_passthrough(self):
        tool = _studies_tool()
        with patch("tooluniverse.mgnify_tool._http_get") as http:
            http.return_value = {"data": []}
            tool.run({"search": "gut", "size": 2})
        called_url = http.call_args.args[0]
        self.assertIn("search=gut", called_url)
        self.assertIn("page_size=2", called_url)

    def test_analyses_uses_page_size_and_v1(self):
        tool = _analyses_tool()
        with patch("tooluniverse.mgnify_tool._http_get") as http:
            http.return_value = {"data": [{"id": "MGYA00598815"}]}
            result = tool.run({"study_accession": "MGYS00002012", "size": 2})
        called_url = http.call_args.args[0]
        self.assertIn("study_accession=MGYS00002012", called_url)
        self.assertIn("page_size=2", called_url)
        self.assertIn("/api/v1/analyses", called_url)
        self.assertEqual(result["status"], "success")


if __name__ == "__main__":
    unittest.main()
