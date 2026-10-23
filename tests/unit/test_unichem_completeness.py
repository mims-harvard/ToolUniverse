from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.unichem_tool import UniChemTool


pytestmark = pytest.mark.unit


def _tool(endpoint):
    return UniChemTool({"fields": {"endpoint_type": endpoint}})


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    return response


def _compound(inchi, sources):
    return {"inchi": {"inchi": inchi, "formula": "C2H6O"}, "sources": sources}


def test_all_compounds_and_duplicate_source_records_are_preserved():
    payload = {
        "response": "Success",
        "totalCompounds": "2",
        "notFound": [],
        "compounds": [
            _compound(
                "InChI=1S/one",
                [
                    {"id": 1, "shortName": "chembl", "compoundId": "A"},
                    {"id": 1, "shortName": "chembl", "compoundId": "B"},
                ],
            ),
            _compound(
                "InChI=1S/two",
                [{"id": 22, "shortName": "pubchem", "compoundId": "2"}],
            ),
        ],
    }
    with patch(
        "tooluniverse.unichem_tool.requests.post", return_value=_response(payload)
    ):
        result = _tool("search_compound").run(
            {"compound": "example", "type": "inchikey"}
        )
    data = result["data"]
    assert data["total_compounds"] == 2
    assert data["returned_compounds"] == 2
    assert len(data["compounds"]) == 2
    assert data["compounds"][0]["source_record_count"] == 2
    assert data["compounds"][0]["unique_source_count"] == 1
    assert data["compounds"][0]["duplicate_source_records"] == 1
    assert data["compounds"][0]["sources"][0]["source_id"] == 1


def test_compound_count_mismatch_is_explicit():
    payload = {
        "response": "Success",
        "totalCompounds": "2",
        "compounds": [_compound("InChI=1S/one", [])],
    }
    with patch(
        "tooluniverse.unichem_tool.requests.post", return_value=_response(payload)
    ):
        result = _tool("search_compound").run(
            {"compound": "example", "type": "inchikey"}
        )
    assert result["status"] == "error"
    assert result["reported_total"] == 2


def test_sources_reported_total_is_validated():
    payload = {
        "totalSources": "2",
        "sources": [{"sourceID": 1, "name": "chembl"}],
    }
    with patch(
        "tooluniverse.unichem_tool.requests.get", return_value=_response(payload)
    ):
        result = _tool("list_sources").run({})
    assert result["status"] == "error"
    assert "conflicts" in result["error"]


@pytest.mark.parametrize(
    "arguments,error",
    [
        ({"compound": 25, "type": "inchikey"}, "non-empty string"),
        ({"compound": "X", "type": "name"}, "type must be"),
        ({"compound": "CHEMBL25", "type": "sourceID"}, "positive integer"),
        (
            {"compound": "X", "type": "inchikey", "sourceID": 1},
            "only valid",
        ),
    ],
)
def test_invalid_search_arguments_are_rejected_before_network(arguments, error):
    with patch("tooluniverse.unichem_tool.requests.post") as post:
        result = _tool("search_compound").run(arguments)
    assert result["status"] == "error"
    assert error in result["error"]
    post.assert_not_called()


def test_connectivity_count_mismatch_is_explicit():
    payload = {
        "response": "Success",
        "searchedCompound": {},
        "totalCompounds": 1,
        "totalSources": 2,
        "sources": [{"id": 1}],
    }
    with patch(
        "tooluniverse.unichem_tool.requests.post", return_value=_response(payload)
    ):
        result = _tool("connectivity_search").run({"compound": "X", "type": "inchikey"})
    assert result["status"] == "error"
    assert "totalSources" in result["error"]
