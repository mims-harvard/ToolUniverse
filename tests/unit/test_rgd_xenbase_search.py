"""RGD/Xenbase gene search no longer sends the stale Alliance `category=gene`.

Regression: both tools queried Alliance with `category=gene` (which the API no
longer honours -> 0 results) and read the gene id from `primaryKey` (now
`curie`). A search for 'Tp53' returned an empty list even though Alliance
returns the rat (RGD:3889) and frog (Xenbase:...) genes. The tools must fetch
unfiltered, keep `gene_search_result` hits, and read `curie`.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

_ALLIANCE = {
    "total": 7046,
    "results": [
        {
            "category": "gene_search_result",
            "symbol": "Tp53",
            "name": "tumor protein p53",
            "curie": "RGD:3889",
            "species": "Rattus norvegicus",
            "synonyms": ["cellular tumor antigen p53"],
        },
        {
            "category": "gene_search_result",
            "symbol": "tp53",
            "name": "tumor protein p53",
            "curie": "Xenbase:XB-GENE-484286",
            "species": "Xenopus tropicalis",
            "synonyms": ["tumor suppressor p53"],
        },
        {"category": "go_search_result", "name": "p53 binding", "curie": "GO:0002039"},
    ],
}


def _resp():
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status.return_value = None
    r.json.return_value = _ALLIANCE
    return r


class TestRGDSearch(unittest.TestCase):
    def test_rgd_keeps_only_rat_genes_and_no_category_param(self):
        from tooluniverse.rgd_tool import RGDTool

        tool = RGDTool(
            {"name": "RGD_search_genes", "type": "RGDTool", "fields": {"endpoint_type": "search_genes"}}
        )
        with patch.object(tool.session, "get", return_value=_resp()) as get:
            result = tool.run({"query": "Tp53", "endpoint_type": "search_genes"})
        # never send the dead category=gene param
        self.assertNotIn("category", get.call_args.kwargs.get("params", {}))
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["rgd_id"], "3889")
        self.assertEqual(result["data"][0]["symbol"], "Tp53")


class TestXenbaseSearch(unittest.TestCase):
    def test_xenbase_keeps_only_frog_genes(self):
        from tooluniverse.xenbase_tool import XenbaseTool

        tool = XenbaseTool(
            {
                "name": "Xenbase_search_genes",
                "type": "XenbaseTool",
                "fields": {"endpoint_type": "search_genes"},
            }
        )
        with patch(
            "tooluniverse.xenbase_tool.requests.get", return_value=_resp()
        ) as get:
            result = tool.run({"query": "tp53", "endpoint_type": "search_genes"})
        self.assertNotIn("category", get.call_args.kwargs.get("params", {}))
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["gene_id"], "Xenbase:XB-GENE-484286")


if __name__ == "__main__":
    unittest.main()
