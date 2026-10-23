from unittest.mock import MagicMock, patch

from tooluniverse.pubchem_bioassay_tool import PubChemBioAssayTool


def _tool(endpoint):
    return PubChemBioAssayTool(
        {"name": f"PubChemBioAssay_{endpoint}", "fields": {"endpoint": endpoint}}
    )


def _response(payload):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


@patch("tooluniverse.pubchem_bioassay_tool.requests.get")
def test_gene_search_pages_every_selected_aid(mock_get):
    aids = list(range(100, 110))
    summaries = [
        {"AID": aid, "Name": f"Assay {aid}", "Target": []} for aid in aids[3:7]
    ]
    mock_get.side_effect = [
        _response({"IdentifierList": {"AID": aids}}),
        _response({"AssaySummaries": {"AssaySummary": summaries}}),
    ]

    data = _tool("search_by_gene").run(
        {"gene_symbol": "TP53", "limit": 4, "offset": 3}
    )["data"]

    assert data["total_assays"] == 10
    assert data["returned"] == 4
    assert data["has_more"] is True
    assert data["next_offset"] == 7
    assert [item["aid"] for item in data["assays"]] == [103, 104, 105, 106]
    assert "/103,104,105,106/summary/JSON" in mock_get.call_args_list[1].args[0]


@patch("tooluniverse.pubchem_bioassay_tool.requests.get")
def test_get_assay_preserves_all_text_sections(mock_get):
    descr = {
        "aid": {"id": 504832},
        "description": [f"description {i}" for i in range(8)],
        "protocol": [f"protocol {i}" for i in range(4)],
        "comment": [f"comment {i}" for i in range(6)],
    }
    mock_get.return_value = _response(
        {"PC_AssayContainer": [{"assay": {"descr": descr}}]}
    )

    data = _tool("get_assay").run({"aid": 504832})["data"]

    assert data["description_count"] == len(data["description"]) == 8
    assert data["protocol_count"] == len(data["protocol"]) == 4
    assert data["comment_count"] == len(data["comment"]) == 6
