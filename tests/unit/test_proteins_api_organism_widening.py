"""proteins_api_search organism-widening fix (Feature-007B-1/2/3).

A bare gene/protein-name search defaults to the human taxon (taxid=9606) so
human hits rank first. That silently returned an empty success for non-human
queries (e.g. bacterial ``blaKPC``). The tool now auto-widens to all organisms
when the human-filtered search is empty, and surfaces an explanatory ``note``.
Human queries (e.g. TP53) must keep their human-first behaviour unchanged.
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


class TestOrganismWidening(unittest.TestCase):
    def test_bacterial_query_widens_when_human_empty(self):
        """blaKPC: human-filtered call is empty, widened call returns hits."""
        tool = _make_tool()
        bacterial_hit = [{"accession": "Q9F663", "id": "BLKPC_KLEPN"}]
        # Main call (gene=blaKPC&taxid=9606) and the human-kept protein retry are
        # both empty (no human protein named blaKPC); the taxid-dropped retry hits.
        tool.session.get = MagicMock(
            side_effect=[_resp(200, []), _resp(200, []), _resp(200, bacterial_hit)]
        )

        result = tool.run({"query": "blaKPC", "size": 3})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 1)
        self.assertIn("note", result)
        self.assertIn("widened", result["note"].lower())
        self.assertGreaterEqual(tool.session.get.call_count, 2)

    def test_human_query_stays_human_first_without_note(self):
        """TP53: human call returns hits, so no widening and no note."""
        tool = _make_tool()
        human_hit = [{"accession": "P04637", "id": "P53_HUMAN"}]
        tool.session.get = MagicMock(return_value=_resp(200, human_hit))

        result = tool.run({"query": "TP53", "size": 2})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 1)
        self.assertNotIn("note", result)
        # No empty result -> no retry needed.
        self.assertEqual(tool.session.get.call_count, 1)

    def test_explicit_organism_is_not_overridden(self):
        """An explicit organism scopes the query and disables auto-widening."""
        tool = _make_tool()
        params = tool._build_params(
            {"query": "blaKPC", "organism": "Klebsiella pneumoniae"}
        )
        self.assertEqual(params.get("organism"), "Klebsiella pneumoniae")
        self.assertNotIn("taxid", params)  # human default not injected

    def test_explicit_taxid_disables_human_default(self):
        tool = _make_tool()
        params = tool._build_params({"query": "blaKPC", "taxid": "573"})
        self.assertEqual(params.get("taxid"), "573")


if __name__ == "__main__":
    unittest.main()
