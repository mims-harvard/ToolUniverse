"""Regression guard for Fix-R23B-3: EBIProteinsEpitopeTool's `iedb_ids`
field was always empty. Confirmed live for P0DTC2 (SARS-CoV-2 spike): the
IEDB epitope ID actually lives under a feature's top-level "xrefs" array
({"name": "IEDB", "id": "1220"}), not under "evidences.source" (which only
ever carries PubMed references) -- the code only checked the latter. Every
one of 1143 EPITOPE features for P0DTC2 has its own description naming a
specific epitope ID (e.g. "epitope ID 1220") that the field should have
surfaced.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.ebi_proteins_epitope_tool import EBIProteinsEpitopeTool

pytestmark = pytest.mark.unit

_RAW_FEATURE = {
    "type": "EPITOPE",
    "description": "AEVQIDRLI is a linear peptidic epitope (epitope ID 1220) tested in 5 T cell assays and 7 MHC ligand assays.",
    "begin": "989",
    "end": "997",
    "xrefs": [
        {
            "name": "IEDB",
            "id": "1220",
            "url": "https://www.iedb.org/epitope/1220",
        }
    ],
    "evidences": [
        {
            "code": "ECO:0000213",
            "source": {"name": "PubMed", "id": "35383307"},
        }
    ],
    "epitopeSequence": "AEVQIDRLI",
    "matchScore": 100,
}


def _tool():
    return EBIProteinsEpitopeTool({"name": "ebi_epitope_test"})


def _resp(json_body):
    r = MagicMock()
    r.json.return_value = json_body
    r.raise_for_status = MagicMock()
    return r


class TestIedbIdsFromXrefs:
    def test_iedb_id_extracted_from_xrefs(self):
        tool = _tool()
        resp = _resp({"accession": "P0DTC2", "features": [_RAW_FEATURE]})

        with patch(
            "tooluniverse.ebi_proteins_epitope_tool.requests.get", return_value=resp
        ):
            result = tool.run({"accession": "P0DTC2"})

        assert result["status"] == "success"
        epitope = result["data"]["epitopes"][0]
        assert epitope["iedb_ids"] == ["1220"]
        assert epitope["pmids"] == ["35383307"]

    def test_feature_with_no_xrefs_gets_empty_iedb_ids(self):
        tool = _tool()
        feature = dict(_RAW_FEATURE)
        feature["xrefs"] = []
        resp = _resp({"accession": "P0DTC2", "features": [feature]})

        with patch(
            "tooluniverse.ebi_proteins_epitope_tool.requests.get", return_value=resp
        ):
            result = tool.run({"accession": "P0DTC2"})

        assert result["data"]["epitopes"][0]["iedb_ids"] == []
