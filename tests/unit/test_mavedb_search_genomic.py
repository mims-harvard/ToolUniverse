"""Regression tests for MaveDB search totals and genomic-location counting.

Two confirmed defects (mocked HTTP):

* ``MaveDB_search_score_sets`` computed ``total_results`` from the post-``limit``
  slice, so a query understated how many matches exist (5 shown when 62 exist),
  and it exposed no target-gene field -- a full-text hit on a different gene
  (query "BRCA1" matching "BRCA1-Associated Protein 1"/BAP1) looked on-target.
* ``MaveDB_get_mapped_variants`` counted any non-null postMapped as
  ``n_with_genomic_location``; protein-anchored (NP_/NM_) mappings, which have no
  genomic coordinates, inflated the count for protein-level DMS score sets.

The count was then fixed by reading the postMapped sequenceReference label, and
that fix stopped working when MaveDB retired ``/mapped-variants`` for
``/variant-details``: the successor route sends a refgetAccession and no label,
so a label test counts zero genomic variants on a score set where every one is
projected. The count now comes from MaveDB's own ``mapped.genomic`` projection,
and this test pins that, over newline-delimited JSON, which is what the route
returns.
"""

import json
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


def _ndjson_resp(records):
    """A /variant-details response: one JSON object per line, no array."""
    r = MagicMock()
    r.status_code = 200
    r.text = "\n".join(json.dumps(record) for record in records)
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
    def test_protein_only_projection_not_counted_as_genomic(self):
        """Only a record carrying mapped.genomic counts toward the genomic total."""
        tool = _mavedb()
        records = [
            {
                # protein-level DMS variant MaveDB could not project onto the
                # genome: postMapped exists, mapped.genomic does not.
                "urn": "v1",
                "assayLevel": "protein",
                "clingenAlleleId": None,
                "postMapped": {
                    "id": "a",
                    "state": {"sequence": "M"},
                    "location": {
                        "start": 1,
                        "end": 2,
                        "sequenceReference": {
                            "refgetAccession": "SQ.protein-only"
                        },
                    },
                },
                "mapped": {"protein": {"hgvs": "NP_203524.1:p.Met1?"}},
            },
            {
                "urn": "v2",
                "assayLevel": "cdna",
                "clingenAlleleId": "CA1",
                "postMapped": {
                    "id": "b",
                    "state": {"sequence": "A"},
                    "location": {
                        "start": 100,
                        "end": 101,
                        "sequenceReference": {"refgetAccession": "SQ.cdna"},
                    },
                },
                "mapped": {
                    "genomic": {"hgvs": "NC_000017.11:g.100A>C"},
                    "cdna": {"hgvs": "NM_1.1:c.100A>C"},
                },
            },
        ]
        with patch.object(tool.session, "get", return_value=_ndjson_resp(records)):
            out = tool._get_mapped_variants({"urn": "urn:mavedb:x"})
        data = out["data"]
        self.assertEqual(data["total_mapped_variants"], 2)
        self.assertEqual(data["n_with_genomic_location"], 1)
        self.assertEqual(data["n_with_clingen_allele_id"], 1)
        rows = {row["variant_urn"]: row for row in data["mapped_variants"]}
        self.assertIsNone(rows["v1"]["genomic_hgvs"])
        self.assertEqual(rows["v2"]["genomic_hgvs"], "NC_000017.11:g.100A>C")
        # The label a postMapped allele no longer carries must not be the
        # signal: both rows read None there, yet exactly one is genomic.
        self.assertIsNone(rows["v1"]["post_mapped"]["sequence_reference_label"])
        self.assertIsNone(rows["v2"]["post_mapped"]["sequence_reference_label"])

    def test_single_json_array_body_still_parses(self):
        """A JSON array body is accepted too, so the format is not a hard dependency."""
        tool = _mavedb()
        body = [{"urn": "v1", "mapped": {"genomic": {"hgvs": "NC_1.1:g.1A>C"}}}]
        r = MagicMock()
        r.status_code = 200
        r.text = json.dumps(body)
        with patch.object(tool.session, "get", return_value=r):
            out = tool._get_mapped_variants({"urn": "urn:mavedb:x"})
        self.assertEqual(out["data"]["total_mapped_variants"], 1)
        self.assertEqual(out["data"]["n_with_genomic_location"], 1)

    def test_retired_route_reports_the_successor_upstream_names(self):
        """A 410 passes MaveDB's own migration note through to the caller."""
        tool = _mavedb()
        r = MagicMock()
        r.status_code = 410
        r.json.return_value = {
            "detail": "GET /score-sets/urn:mavedb:x/variant-details has been "
            "removed. Use GET /score-sets/urn:mavedb:x/something-else instead."
        }
        with patch.object(tool.session, "get", return_value=r):
            out = tool._get_mapped_variants({"urn": "urn:mavedb:x"})
        self.assertEqual(out["status"], "error")
        self.assertIn("410", out["error"])
        self.assertIn("something-else", out["error"])

    def test_unparseable_ndjson_line_is_reported_not_swallowed(self):
        """A non-JSON line yields an error naming the line, not an empty result."""
        tool = _mavedb()
        r = MagicMock()
        r.status_code = 200
        r.text = '{"urn": "v1"}\n<html>503</html>'
        with patch.object(tool.session, "get", return_value=r):
            out = tool._get_mapped_variants({"urn": "urn:mavedb:x"})
        self.assertEqual(out["status"], "error")
        self.assertIn("line 2", out["error"])


if __name__ == "__main__":
    unittest.main()
