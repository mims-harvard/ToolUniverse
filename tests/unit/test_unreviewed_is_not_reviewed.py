"""An entryType of "unreviewed" contains the substring "reviewed".

Round eleven of the field-axis sweep added `reviewed` to UniProt search hits
because Swiss-Prot against TrEMBL is the biggest quality distinction in
UniProt and the row did not say which. It derived the flag as
``"reviewed" in entry_type.lower()`` -- and "UniProtKB unreviewed (TrEMBL)"
contains "reviewed", so every unreviewed entry was reported as reviewed. The
field was worse than its absence: absent, a caller checks; present and
wrong, it does not.

Measured live before the fix: Gene_Name TP53 -> UniProtKB answers 114
accessions, of which one is Swiss-Prot and 113 are TrEMBL, and all 114 came
back `reviewed: true`.

Two tools derived it the same way, so both are covered here.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.uniprot_idmapping_tool import UniProtIDMappingTool, _entry_summary
from tooluniverse.uniprot_tool import UniProtRESTTool

pytestmark = pytest.mark.unit

_REVIEWED = "UniProtKB reviewed (Swiss-Prot)"
_UNREVIEWED = "UniProtKB unreviewed (TrEMBL)"


def test_the_id_mapping_summary_calls_trembl_unreviewed():
    assert _entry_summary({"entryType": _REVIEWED})["reviewed"] is True
    assert _entry_summary({"entryType": _UNREVIEWED})["reviewed"] is False
    # No entryType at all stays unknown rather than guessing either way.
    assert _entry_summary({})["reviewed"] is None


def _search_tool():
    """The formatted path belongs to `UniProt_search`, whose config carries
    `search_type: "search"`; the per-accession tools pass the entry through."""
    return UniProtRESTTool(
        {
            "name": "UniProt_search",
            "type": "UniProtRESTTool",
            "fields": {
                "endpoint": "https://rest.uniprot.org/uniprotkb/search",
                "search_type": "search",
                "format": "json",
            },
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _response(body):
    resp = MagicMock()
    resp.status_code = 200
    resp.headers = {"content-type": "application/json", "x-total-results": "2"}
    resp.text = json.dumps(body)
    resp.json.return_value = body
    resp.raise_for_status.return_value = None
    return resp


_TWO_HITS = {
    "results": [
        {
            "primaryAccession": "P04637",
            "uniProtkbId": "P53_HUMAN",
            "entryType": _REVIEWED,
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Cellular tumor antigen p53"}}
            },
            "organism": {"scientificName": "Homo sapiens", "taxonId": 9606},
            "sequence": {"length": 393},
        },
        {
            "primaryAccession": "A0A087WT22",
            "uniProtkbId": "A0A087WT22_HUMAN",
            "entryType": _UNREVIEWED,
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Cellular tumor antigen p53"}}
            },
            "organism": {"scientificName": "Homo sapiens", "taxonId": 9606},
            "sequence": {"length": 187},
        },
    ]
}


def test_a_uniprot_search_hit_is_not_reviewed_just_because_it_says_unreviewed():
    tool = _search_tool()
    with patch(
        "tooluniverse.uniprot_tool.requests.get", return_value=_response(_TWO_HITS)
    ):
        out = tool.run({"query": "TP53", "limit": 2})

    entries = out["data"]["results"]
    by_accession = {entry["accession"]: entry for entry in entries}
    assert by_accession["P04637"]["reviewed"] is True
    assert by_accession["A0A087WT22"]["reviewed"] is False
