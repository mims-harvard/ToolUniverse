"""proteins_api_search must never answer a findable query with a silent empty.

Two defects produced the same harm -- ``status: success``, ``count: 0``, no
explanation -- for queries whose data demonstrably exists upstream:

1. The empty-result field-swap retry was asymmetric. ``_build_params`` routes
   any query longer than 10 characters to ``protein=``, but the retry that
   swaps the field while keeping the caller's organism/taxid scoping was
   guarded on the gene->protein direction only. A scoped ``protein=`` query
   (e.g. ``blaCTX-M-15`` in *Klebsiella pneumoniae*, 11 characters, which only
   matches under ``gene=``) therefore got no retry at all.
2. A purely numeric ``organism`` was sent to the API's ``organism=``
   parameter, which takes an organism *name* ("Organism name" vs "Organism
   taxon ID" in https://www.ebi.ac.uk/proteins/api/doc/), so
   ``organism='9606'`` matched nothing. It is now routed to ``taxid=`` and the
   response discloses the correction.
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


class TestSymmetricFieldSwapRetry(unittest.TestCase):
    """Defect 1: a scoped protein= query must be retried as gene=."""

    def test_scoped_protein_query_retries_as_gene(self):
        tool = _make_tool()
        hit = [{"accession": "A0A077JMT3", "id": "A0A077JMT3_KLEPN"}]
        # protein=blaCTX-M-15 is empty upstream; gene=blaCTX-M-15 is the hit.
        tool.session.get = MagicMock(side_effect=[_resp(200, []), _resp(200, hit)])

        result = tool.run(
            {
                "query": "blaCTX-M-15",
                "organism": "Klebsiella pneumoniae",
                "size": 3,
            }
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["data"][0]["accession"], "A0A077JMT3")
        self.assertEqual(tool.session.get.call_count, 2)

        first_params = tool.session.get.call_args_list[0].kwargs["params"]
        self.assertEqual(first_params.get("protein"), "blaCTX-M-15")

        retry_params = tool.session.get.call_args_list[1].kwargs["params"]
        self.assertEqual(retry_params.get("gene"), "blaCTX-M-15")
        self.assertNotIn("protein", retry_params)
        # The caller's scoping must survive the swap (see the wheat/insect
        # incident recorded in the retry helper).
        self.assertEqual(retry_params.get("organism"), "Klebsiella pneumoniae")
        self.assertEqual(retry_params.get("size"), 3)
        # The caller scoped the query, so no human default was ever injected.
        self.assertNotIn("taxid", retry_params)

    def test_scoped_gene_query_still_retries_as_protein(self):
        """The gene->protein direction (the one that already worked) is kept."""
        tool = _make_tool()
        tool.session.get = MagicMock(
            side_effect=[_resp(200, []), _resp(200, [{"accession": "X"}])]
        )

        result = tool.run({"query": "FT1", "organism": "Triticum aestivum"})

        self.assertEqual(result["count"], 1)
        retry_params = tool.session.get.call_args_list[1].kwargs["params"]
        self.assertEqual(retry_params.get("protein"), "FT1")
        self.assertNotIn("gene", retry_params)
        self.assertEqual(retry_params.get("organism"), "Triticum aestivum")

    def test_accession_query_is_not_retried_under_a_name_field(self):
        """An accession lookup must not be re-issued as gene=/protein=."""
        tool = _make_tool()
        tool.session.get = MagicMock(return_value=_resp(200, []))

        result = tool.run({"query": "P05067"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 0)
        self.assertEqual(tool.session.get.call_count, 1)

    def test_no_upstream_match_under_either_field_stays_empty_without_crashing(self):
        tool = _make_tool()
        tool.session.get = MagicMock(return_value=_resp(200, []))

        result = tool.run(
            {"query": "KPC-2 carbapenemase", "organism": "Klebsiella pneumoniae"}
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 0)
        # Exactly one retry: the symmetric protein->gene swap.
        self.assertEqual(tool.session.get.call_count, 2)


class TestNumericOrganismIsATaxid(unittest.TestCase):
    """Defect 2: organism='9606' must not silently return nothing."""

    def test_numeric_organism_routes_to_taxid(self):
        tool = _make_tool()
        params = tool._build_params({"query": "JAK2", "organism": "9606"})
        self.assertEqual(params.get("taxid"), "9606")
        self.assertNotIn("organism", params)

    def test_numeric_organism_accepts_int_and_surrounding_whitespace(self):
        tool = _make_tool()
        self.assertEqual(
            tool._build_params({"query": "JAK2", "organism": 9606}).get("taxid"), "9606"
        )
        self.assertEqual(
            tool._build_params({"query": "JAK2", "organism": " 9606 "}).get("taxid"),
            "9606",
        )

    def test_named_organism_is_untouched(self):
        tool = _make_tool()
        params = tool._build_params(
            {"query": "blaKPC", "organism": "Klebsiella pneumoniae"}
        )
        self.assertEqual(params.get("organism"), "Klebsiella pneumoniae")
        self.assertNotIn("taxid", params)

    def test_numeric_organism_returns_hits_and_discloses_the_correction(self):
        tool = _make_tool()
        hit = [{"accession": "O60674", "id": "JAK2_HUMAN"}]
        tool.session.get = MagicMock(return_value=_resp(200, hit))

        result = tool.run({"gene": "JAK2", "organism": "9606"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["data"][0]["accession"], "O60674")
        # Silent input mutation is its own defect: the response must say so.
        self.assertIn("normalization_note", result)
        note = result["normalization_note"]
        self.assertIn("9606", note)
        self.assertIn("organism", note)
        self.assertIn("taxid", note)

        sent = tool.session.get.call_args_list[0].kwargs["params"]
        self.assertEqual(sent.get("taxid"), "9606")
        self.assertNotIn("organism", sent)

    def test_no_normalization_note_when_organism_is_a_name(self):
        tool = _make_tool()
        tool.session.get = MagicMock(return_value=_resp(200, [{"accession": "I7ACB1"}]))

        result = tool.run({"query": "KPC-2", "organism": "Klebsiella pneumoniae"})

        self.assertEqual(result["count"], 1)
        self.assertNotIn("normalization_note", result)

    def test_numeric_organism_disables_the_human_default_like_a_taxid(self):
        """A caller-supplied numeric organism is scoping, not the tool's default."""
        tool = _make_tool()
        params = tool._build_params({"query": "blaKPC", "organism": "573"})
        self.assertEqual(params.get("taxid"), "573")


class TestPriorFixesStillHold(unittest.TestCase):
    """Guards for Feature-69A-007, Feature-81B-007 and Fix-T3A-008."""

    def test_human_default_still_applied_to_bare_name_search(self):
        tool = _make_tool()
        self.assertEqual(tool._build_params({"query": "TP53"}).get("taxid"), "9606")

    def test_short_query_still_routes_to_gene(self):
        tool = _make_tool()
        self.assertEqual(tool._build_params({"query": "CYP2D6"}).get("gene"), "CYP2D6")

    def test_accession_still_routes_to_accession(self):
        tool = _make_tool()
        params = tool._build_params({"query": "P05067"})
        self.assertEqual(params.get("accession"), "P05067")
        self.assertNotIn("taxid", params)


if __name__ == "__main__":
    unittest.main()
