from unittest.mock import MagicMock, patch

from tooluniverse.mydisease_tool import MyDiseaseTool


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    return response


def test_ctd_annotations_after_first_twenty_are_recoverable():
    chemicals = [{"name": f"Chemical {i}"} for i in range(167)]
    pathways = [{"name": f"Pathway {i}"} for i in range(984)]
    tool = MyDiseaseTool(
        {"name": "MyDisease_get_disease", "fields": {"endpoint": "get_disease"}}
    )

    with patch(
        "tooluniverse.mydisease_tool.requests.get",
        return_value=_response(
            {
                "_id": "MONDO:0005148",
                "ctd": {
                    "chemical_related_to_disease": chemicals,
                    "pathway_related_to_disease": pathways,
                },
            }
        ),
    ):
        result = tool.run(
            {
                "disease_id": "MONDO:0005148",
                "annotation_limit": 3,
                "annotation_offset": 20,
            }
        )

    ctd = result["data"]["ctd"]
    assert [x["name"] for x in ctd["chemicals"]] == [
        "Chemical 20",
        "Chemical 21",
        "Chemical 22",
    ]
    assert ctd["total_chemicals"] == 167
    assert ctd["chemicals_count"] == 3
    assert ctd["chemicals_next_offset"] == 23
    assert [x["name"] for x in ctd["pathways"]] == [
        "Pathway 20",
        "Pathway 21",
        "Pathway 22",
    ]


def test_search_forwards_start_as_biothings_from():
    tool = MyDiseaseTool(
        {"name": "MyDisease_search_diseases", "fields": {"endpoint": "search_diseases"}}
    )
    with patch(
        "tooluniverse.mydisease_tool.requests.get",
        return_value=_response({"total": 45, "hits": [{"_id": "MONDO:2"}]}),
    ) as get:
        result = tool.run({"query": "breast cancer", "size": 1, "start": 1})

    assert get.call_args.kwargs["params"]["from"] == 1
    assert result["data"]["next_start"] == 2
