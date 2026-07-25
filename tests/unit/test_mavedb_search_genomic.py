"""Regression tests for MaveDB search totals and genomic-location counting.

Two confirmed defects (mocked HTTP):

* ``MaveDB_search_score_sets`` computed ``total_results`` from the post-``limit``
  slice, so a query understated how many matches exist (5 shown when 62 exist),
  and it exposed no target-gene field -- a full-text hit on a different gene
  (query "BRCA1" matching "BRCA1-Associated Protein 1"/BAP1) looked on-target.
* ``MaveDB_get_mapped_variants`` counted any non-null postMapped as
  ``n_with_genomic_location``; protein-anchored (NP_/NM_) mappings, which have no
  genomic coordinates, inflated the count for protein-level DMS score sets.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _mavedb():
    from tooluniverse.mavedb_tool import MaveDBTool

    return MaveDBTool({"name": "t", "type": "MaveDBTool"})


def _resp(status, json_body):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_body
    return r


class TestMaveDBSearchTotals(unittest.TestCase):
    def test_total_results_is_true_total_before_truncation(self):
        """total_results reflects all matches, not just the returned page."""
        tool = _mavedb()
        body = {
            "scoreSets": [
                {"urn": f"urn:{i}", "title": f"t{i}", "targetGenes": [{"name": "BAP1"}]}
                for i in range(10)
            ]
        }
        with patch.object(tool.session, "post", return_value=_resp(200, body)):
            out = tool._search({"query": "BRCA1", "limit": 3})
        self.assertEqual(len(out["data"]), 3)
        self.assertEqual(out["metadata"]["total_results"], 10)
        self.assertEqual(out["metadata"]["returned_results"], 3)

    def test_search_exposes_target_genes(self):
        """Each result carries its target gene(s) so off-target hits are visible."""
        tool = _mavedb()
        body = {
            "scoreSets": [
                {"urn": "urn:1", "title": "x", "targetGenes": [{"name": "BAP1"}]}
            ]
        }
        with patch.object(tool.session, "post", return_value=_resp(200, body)):
            out = tool._search({"query": "BRCA1", "limit": 5})
        self.assertEqual(out["data"][0]["target_genes"], ["BAP1"])


class TestMaveDBGenomicCount(unittest.TestCase):
    def test_protein_mapping_not_counted_as_genomic(self):
        """NP_ (protein) postMapped is excluded; only NC_ (genomic) is counted."""
        tool = _mavedb()
        body = [
            {
                "variantUrn": "v1",
                "postMapped": {
                    "id": "a",
                    "state": {"sequence": "M"},
                    "location": {
                        "start": 1,
                        "end": 2,
                        "sequenceReference": {"label": "NP_203524.1"},
                    },
                },
                "clingenAlleleId": None,
            },
            {
                "variantUrn": "v2",
                "postMapped": {
                    "id": "b",
                    "state": {"sequence": "A"},
                    "location": {
                        "start": 100,
                        "end": 101,
                        "sequenceReference": {"label": "NC_000017.11"},
                    },
                },
                "clingenAlleleId": "CA1",
            },
        ]
        with patch.object(tool.session, "get", return_value=_resp(200, body)):
            out = tool._get_mapped_variants({"urn": "urn:mavedb:x"})
        data = out["data"]
        self.assertEqual(data["total_mapped_variants"], 2)
        self.assertEqual(data["n_with_genomic_location"], 1)


if __name__ == "__main__":
    unittest.main()
