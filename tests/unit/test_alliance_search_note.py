"""Alliance_search_genes distinguishes 'no gene' from 'searched a concept'.

Regression: the Alliance autocomplete matches gene symbols/synonyms, not
descriptive names. A query like 'insulin' returns GO terms and diseases but no
gene, so the tool returned an indistinguishable empty list (and the docs/example
falsely claimed 'insulin' returns INS). When no gene matched but other entity
types did, the tool should add a metadata note pointing the caller at the gene
symbol. A symbol query like 'INS' must still return genes.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _tool():
    from tooluniverse.alliance_genome_tool import AllianceGenomeTool

    return AllianceGenomeTool(
        {
            "name": "Alliance_search_genes",
            "type": "AllianceGenomeTool",
            "fields": {"endpoint_type": "search_genes"},
        }
    )


def _resp(results):
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status.return_value = None
    r.json.return_value = {"results": results}
    return r


class TestAllianceSearchNote(unittest.TestCase):
    def test_concept_query_adds_actionable_note(self):
        tool = _tool()
        non_gene = [
            {"category": "go_search_result", "name": "insulin binding"},
            {"category": "disease_search_result", "name": "insulinoma"},
        ]
        with patch(
            "tooluniverse.alliance_genome_tool.requests.get",
            return_value=_resp(non_gene),
        ):
            result = tool.run({"query": "insulin"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"], [])
        note = result["metadata"].get("note", "")
        self.assertIn("INS", note)
        self.assertIn("go", note)  # surfaces the categories that did match

    def test_symbol_query_returns_genes_without_note(self):
        tool = _tool()
        genes = [
            {"category": "gene_search_result", "symbol": "INS", "curie": "HGNC:6081"},
            {
                "category": "gene_search_result",
                "symbol": "Ins1",
                "curie": "RGD:2915",
            },
        ]
        with patch(
            "tooluniverse.alliance_genome_tool.requests.get",
            return_value=_resp(genes),
        ):
            result = tool.run({"query": "INS", "limit": 10})
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 2)
        self.assertEqual(result["data"][0]["gene_id"], "HGNC:6081")
        self.assertNotIn("note", result["metadata"])


if __name__ == "__main__":
    unittest.main()
