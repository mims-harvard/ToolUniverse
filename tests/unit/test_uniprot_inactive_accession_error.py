"""Regression guard for Fix-R20A-3: UniProtRESTTool's JSONPath-extraction
endpoints (get_organism_by_accession, get_sequence_by_accession,
get_function_by_accession, get_subcellular_location_by_accession, and
siblings using extract_path) surfaced a confusing raw
"No data found for JSONPath: ..." error for a real-but-inactive/deleted
UniProt accession, instead of explaining *why* -- unlike
UniProt_get_entry_by_accession, which already handles the same accession
gracefully (returns status:success with entryType:"Inactive" and empty
fields).

Confirmed live for Q9ZZZ9 (a real, UniProt-deleted accession -- HTTP 200,
entryType:"Inactive", inactiveReason: {inactiveReasonType: "DELETED",
deletedReason: "Not part of a reference proteome"}). Fixed by checking
entryType before running extract_path's JSONPath and returning a clear,
actionable error citing the real inactive reason.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.uniprot_tool import UniProtRESTTool

pytestmark = pytest.mark.unit


def _tool(extract_path="organism.scientificName"):
    return UniProtRESTTool(
        {
            "name": "uniprot_test",
            "fields": {
                "endpoint": "https://rest.uniprot.org/uniprotkb/{accession}.json",
                "extract_path": extract_path,
            },
        }
    )


def _resp(json_body, status_code=200):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body
    return r


_INACTIVE_ENTRY = {
    "entryType": "Inactive",
    "primaryAccession": "Q9ZZZ9",
    "inactiveReason": {
        "inactiveReasonType": "DELETED",
        "deletedReason": "Not part of a reference proteome",
    },
}


def test_inactive_accession_gives_clear_reason_not_raw_jsonpath_error():
    tool = _tool("organism.scientificName")

    with patch(
        "tooluniverse.uniprot_tool.requests.get", return_value=_resp(_INACTIVE_ENTRY)
    ):
        result = tool.run({"accession": "Q9ZZZ9"})

    assert result["status"] == "error"
    assert "inactive" in result["error"].lower()
    assert "DELETED" in result["error"]
    assert "Not part of a reference proteome" in result["error"]
    assert "JSONPath" not in result["error"]


@pytest.mark.parametrize(
    "extract_path",
    [
        "organism.scientificName",
        "sequence.value",
        "comments[?(@.commentType=='FUNCTION')].texts[*].value",
        (
            "comments[?(@.commentType=="
            "'SUBCELLULAR LOCATION')].subcellularLocations[*].location.value"
        ),
    ],
)
def test_all_extract_path_variants_handle_inactive_entry(extract_path):
    tool = _tool(extract_path)

    with patch(
        "tooluniverse.uniprot_tool.requests.get", return_value=_resp(_INACTIVE_ENTRY)
    ):
        result = tool.run({"accession": "Q9ZZZ9"})

    assert result["status"] == "error"
    assert "inactive" in result["error"].lower()


def test_active_accession_extraction_unaffected():
    tool = _tool("organism.scientificName")
    active_entry = {
        "entryType": "UniProtKB reviewed (Swiss-Prot)",
        "organism": {"scientificName": "Homo sapiens"},
    }

    with patch(
        "tooluniverse.uniprot_tool.requests.get", return_value=_resp(active_entry)
    ):
        result = tool.run({"accession": "P00533"})

    assert result == "Homo sapiens"


def test_merged_inactive_reason_without_deleted_detail():
    """Some inactive entries are MERGED (not DELETED) and carry a
    mergeDemergeTo list instead of deletedReason -- make sure that shape is
    also handled without crashing."""
    tool = _tool("organism.scientificName")
    merged_entry = {
        "entryType": "Inactive",
        "inactiveReason": {
            "inactiveReasonType": "MERGED",
            "mergeDemergeTo": ["P12345"],
        },
    }

    with patch(
        "tooluniverse.uniprot_tool.requests.get", return_value=_resp(merged_entry)
    ):
        result = tool.run({"accession": "Q0OLD1"})

    assert result["status"] == "error"
    assert "MERGED" in result["error"]
