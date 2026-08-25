"""proteins_api_search must not answer a gene symbol with a different entity.

``proteins_api_search`` defaults a bare name search to the human taxon so human
hits rank first, then retries when that comes back empty. The retry order tried
a *different field* before it tried a *wider organism*, so a gene symbol with no
human ortholog was answered with an unrelated human protein:

    proteins_api_search {"query": "ben-1"}   ->  BANP_HUMAN (taxid 9606)

``ben-1`` is the C. elegans beta-tubulin whose loss confers benzimidazole
resistance. Confirmed against the live EBI Proteins API:

    gene=ben-1&taxid=9606     -> []                      (no human ben-1)
    gene=ben-1                -> Q18817_CAEEL, taxid 6239 (correct)
    protein=ben-1&taxid=9606  -> BANP_HUMAN               (matches the free-text
                                 description "BEN domain-containing protein 1")

So the empty human gene search fell through to a free-text protein search that
still carried the human bias, and returned a different entity's annotations as
if they were the requested protein -- with no note saying anything had changed.

The fix tries "same field, drop the human default this tool added itself" first,
accepted only when some hit's gene symbol is exactly the query. That gate is
what keeps a genuine protein-name query ("insulin") from being dragged off to a
non-human gene that merely resembles it.
"""

import unittest
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


def _make_tool():
    from tooluniverse.proteins_api_tool import ProteinsAPIRESTTool

    return ProteinsAPIRESTTool(
        {"name": "proteins_api_search", "type": "ProteinsAPIRESTTool", "fields": {}}
    )


def _resp(status_code, payload):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = payload
    r.url = "https://www.ebi.ac.uk/proteins/api/proteins"
    r.raise_for_status.return_value = None
    return r


# Shapes taken from the live API responses quoted in the module docstring.
BEN1_WORM = [
    {
        "accession": "Q18817",
        "id": "Q18817_CAEEL",
        "organism": {"taxonomy": 6239},
        "gene": [
            {
                "name": {"value": "ben-1"},
                "olnNames": [{"value": "C54C6.2"}],
                "orfNames": [{"value": "CELE_C54C6.2"}],
            }
        ],
    }
]
BANP_HUMAN = [
    {
        "accession": "Q8N9N5",
        "id": "BANP_HUMAN",
        "organism": {"taxonomy": 9606},
        "gene": [{"name": {"value": "BANP"}, "synonyms": [{"value": "BEND1"}]}],
    }
]
INSULIN_LIKE_NONHUMAN = [
    {
        "accession": "A0A0D6DR34",
        "id": "A0A0D6DR34_BLAGE",
        "organism": {"taxonomy": 6973},
        "gene": [{"name": {"value": "ILP 1"}}],
    }
]
INSULIN_HUMAN = [
    {
        "accession": "A0A087WTD4",
        "id": "A0A087WTD4_HUMAN",
        "organism": {"taxonomy": 9606},
        "gene": [{"name": {"value": "IGFBP3"}}],
    }
]


def _ben1_tool():
    """Tool wired for: 1. gene=ben-1&taxid=9606 -> empty;
    2. gene=ben-1 with the human default dropped -> the real ben-1."""
    tool = _make_tool()
    tool.session.get = MagicMock(side_effect=[_resp(200, []), _resp(200, BEN1_WORM)])
    return tool


class TestGeneSymbolNotSwappedToFreeText(unittest.TestCase):
    def test_non_human_gene_symbol_returns_that_gene_not_a_human_lookalike(self):
        tool = _ben1_tool()

        result = tool.run({"query": "ben-1", "size": 5})

        self.assertEqual(result["status"], "success")
        ids = [e["id"] for e in result["data"]]
        self.assertIn("Q18817_CAEEL", ids)
        self.assertNotIn(
            "BANP_HUMAN", ids, "answered a gene symbol with an unrelated human protein"
        )
        # The organism actually changed, so the caller must be told.
        self.assertIn("note", result)
        self.assertIn("widened", result["note"].lower())

    def test_widened_same_field_is_tried_before_swapping_to_protein(self):
        """Ordering, asserted directly: the second call keeps gene=."""
        tool = _ben1_tool()

        tool.run({"query": "ben-1", "size": 5})

        second = tool.session.get.call_args_list[1].kwargs["params"]
        self.assertEqual(second.get("gene"), "ben-1")
        self.assertNotIn("protein", second)
        self.assertNotIn("taxid", second)

    def test_protein_name_query_is_not_dragged_to_a_lookalike_gene(self):
        """The exact-gene-match gate stops the new candidate over-firing.

        Live API: ``gene=insulin`` (widened) returns 'ILP 1' and 'similar to
        Insulin receptor' -- nothing whose gene symbol is exactly 'insulin'.
        That must be rejected so the human protein-name search still wins.
        """
        tool = _make_tool()
        # 1. gene=insulin&taxid=9606 -> empty
        # 2. gene=insulin widened -> hits, but no exact gene symbol match
        # 3. protein=insulin&taxid=9606 -> human insulin-family proteins
        tool.session.get = MagicMock(
            side_effect=[
                _resp(200, []),
                _resp(200, INSULIN_LIKE_NONHUMAN),
                _resp(200, INSULIN_HUMAN),
            ]
        )

        result = tool.run({"query": "insulin", "size": 5})

        ids = [e["id"] for e in result["data"]]
        self.assertEqual(ids, ["A0A087WTD4_HUMAN"])
        self.assertNotIn("note", result)

    def test_exact_gene_match_reads_synonyms_and_locus_names(self):
        from tooluniverse.proteins_api_tool import _has_exact_gene_match

        self.assertTrue(_has_exact_gene_match(BEN1_WORM, "ben-1"))
        self.assertTrue(_has_exact_gene_match(BEN1_WORM, "BEN-1"))
        self.assertTrue(_has_exact_gene_match(BEN1_WORM, "C54C6.2"))
        self.assertTrue(_has_exact_gene_match(BANP_HUMAN, "BEND1"))
        self.assertFalse(_has_exact_gene_match(BANP_HUMAN, "ben-1"))
        self.assertFalse(_has_exact_gene_match(INSULIN_LIKE_NONHUMAN, "insulin"))
        self.assertFalse(_has_exact_gene_match([], "ben-1"))
        self.assertFalse(_has_exact_gene_match(None, "ben-1"))

    def test_caller_supplied_organism_disables_the_new_candidate(self):
        """The tool may only drop the human default it added itself."""
        tool = _ben1_tool()

        tool.run({"query": "ben-1", "taxid": "6239", "size": 5})

        second = tool.session.get.call_args_list[1].kwargs["params"]
        self.assertEqual(second.get("taxid"), "6239")


if __name__ == "__main__":
    unittest.main()
