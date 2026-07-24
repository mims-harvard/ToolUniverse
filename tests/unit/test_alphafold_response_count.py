"""Regression guard for Fix-R20B-1: AlphaFoldRESTTool's metadata.count was
hardcoded to 1 whenever the raw API response was a dict, since the
computation only checked `len(data) if isinstance(data, list) else 1`.
Several AlphaFold endpoints legitimately return a dict wrapping the real
result list (e.g. /uniprot/summary/{qualifier}.json returns
{"uniprot_entry": {...}, "structures": [...]} -- AlphaFold DB now serves
proteome-wide complex predictions, so a single query can have many
structures), so metadata.count was silently wrong for those endpoints
while the actual data (data.structures) was correct all along.

Confirmed live for P69905 (hemoglobin subunit alpha): 16 real structures
in data.structures, but metadata.count reported 1. Fixed by scanning a
dict response for its first list-valued field and reporting that list's
length instead.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.alphafold_tool import AlphaFoldRESTTool

pytestmark = pytest.mark.unit


def _tool(endpoint):
    return AlphaFoldRESTTool(
        {
            "name": "alphafold_test",
            "fields": {"endpoint": endpoint},
            "parameter": {"required": ["qualifier"]},
        }
    )


def _resp(json_body):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = json_body
    return r


def test_dict_response_with_nested_list_reports_real_count():
    tool = _tool("/uniprot/summary/{qualifier}.json")
    payload = {
        "uniprot_entry": {"ac": "P69905"},
        "structures": [{"summary": {"model_identifier": f"model{i}"}} for i in range(16)],
    }

    with patch("tooluniverse.alphafold_tool.requests.get", return_value=_resp(payload)):
        result = tool.run({"qualifier": "P69905"})

    assert result["status"] == "success"
    assert result["metadata"]["count"] == 16
    assert len(result["data"]["structures"]) == 16


def test_top_level_list_response_unaffected():
    tool = _tool("/prediction/{qualifier}")
    payload = [{"entryId": "AF-P61626-F1", "confidenceScore": 94.06}]

    with patch("tooluniverse.alphafold_tool.requests.get", return_value=_resp(payload)):
        result = tool.run({"qualifier": "P61626"})

    assert result["status"] == "success"
    assert result["metadata"]["count"] == 1


def test_dict_response_with_scalar_fields_only_falls_back_to_one():
    tool = _tool("/uniprot/summary/{qualifier}.json")
    payload = {"uniprot_entry": {"ac": "X"}, "note": "no list field here"}

    with patch("tooluniverse.alphafold_tool.requests.get", return_value=_resp(payload)):
        result = tool.run({"qualifier": "X"})

    assert result["status"] == "success"
    assert result["metadata"]["count"] == 1


def test_annotations_endpoint_dict_with_list_field():
    tool = _tool("/annotations/{qualifier}.json")
    payload = {
        "accession": "P69905",
        "id": "HBA_HUMAN",
        "sequence": "MVLSPADKTN",
        "annotation": [{"start": 10, "end": 10, "description": "mutagenesis"}],
    }

    with patch("tooluniverse.alphafold_tool.requests.get", return_value=_resp(payload)):
        result = tool.run({"qualifier": "P69905"})

    assert result["status"] == "success"
    assert result["metadata"]["count"] == 1
