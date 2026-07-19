"""Regression guard for Fix-R28-3 in uniprot_tool.py: protein_name was
always empty for unreviewed (TrEMBL) UniProtKB entries -- over 99% of the
database. Reviewed (Swiss-Prot) entries have a `recommendedName`, but
unreviewed entries have no such field at all; their name lives under
`submissionNames` (a list) instead. Confirmed live for Q53707 (mecA/PBP2'
from Staphylococcus aureus): recommendedName is absent, and the real name
("MecA PBP2' (penicillin binding protein 2')") is
submissionNames[0].fullName.value. Both `_compact_entry` and the
`_handle_search` formatter only ever read `recommendedName`, so this
silently blanked protein_name for the overwhelming majority of real-world
UniProt searches.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.uniprot_tool import UniProtRESTTool, _protein_name

pytestmark = pytest.mark.unit

_UNREVIEWED_ENTRY = {
    "entryType": "UniProtKB unreviewed (TrEMBL)",
    "primaryAccession": "Q53707",
    "uniProtkbId": "Q53707_STAAU",
    "proteinDescription": {
        "submissionNames": [
            {"fullName": {"value": "MecA PBP2' (penicillin binding protein 2')"}},
            {"fullName": {"value": "PBP2A"}},
        ]
    },
    "genes": [{"geneName": {"value": "mecA"}}],
    "organism": {"scientificName": "Staphylococcus aureus"},
    "sequence": {"length": 668},
}

_REVIEWED_ENTRY = {
    "entryType": "UniProtKB reviewed (Swiss-Prot)",
    "primaryAccession": "P0A6M8",
    "uniProtkbId": "EFTU_ECOLI",
    "proteinDescription": {
        "recommendedName": {"fullName": {"value": "Elongation factor Tu"}}
    },
    "genes": [{"geneName": {"value": "tufA"}}],
    "organism": {"scientificName": "Escherichia coli"},
    "sequence": {"length": 394},
}


class TestProteinNameHelper:
    def test_falls_back_to_submission_name_when_no_recommended_name(self):
        name = _protein_name(_UNREVIEWED_ENTRY["proteinDescription"])
        assert name == "MecA PBP2' (penicillin binding protein 2')"

    def test_prefers_recommended_name_when_present(self):
        name = _protein_name(_REVIEWED_ENTRY["proteinDescription"])
        assert name == "Elongation factor Tu"

    def test_empty_when_neither_present(self):
        assert _protein_name({}) == ""


def _tool():
    return UniProtRESTTool(
        {
            "fields": {
                "endpoint": "https://rest.uniprot.org/uniprotkb/search",
                "search_type": "search",
            },
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _resp(payload):
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status = MagicMock()
    r.json.return_value = payload
    return r


class TestCompactEntryFallback:
    def test_compact_entry_uses_submission_name(self):
        tool = _tool()
        result = tool._compact_entry(_UNREVIEWED_ENTRY)
        assert (
            result["data"]["protein_name"]
            == "MecA PBP2' (penicillin binding protein 2')"
        )


class TestSearchFormatterFallback:
    def test_search_results_use_submission_name_fallback(self):
        tool = _tool()
        payload = {"results": [_UNREVIEWED_ENTRY, _REVIEWED_ENTRY]}
        with patch(
            "tooluniverse.uniprot_tool.requests.get", return_value=_resp(payload)
        ):
            result = tool.run({"query": "mecA"})

        names = [r["protein_name"] for r in result["data"]["results"]]
        assert "MecA PBP2' (penicillin binding protein 2')" in names
        assert "Elongation factor Tu" in names
        assert "" not in names
