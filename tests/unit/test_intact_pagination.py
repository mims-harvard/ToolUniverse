from unittest.mock import MagicMock

from tooluniverse.intact_tool import IntActRESTTool


def _response(n=5, total=932):
    response = MagicMock()
    response.json.return_value = {
        "hitCount": total,
        "entries": [
            {"id": f"EBI-{i}", "source": "intact", "fields": {}} for i in range(n)
        ],
    }
    response.url = "https://example.test/intact"
    return response


def test_documented_first_offset_is_forwarded_as_ebi_start():
    tool = IntActRESTTool({"name": "intact_search_interactions", "fields": {}})
    tool.session.get = MagicMock(return_value=_response())

    result = tool.run({"query": "P04637", "max": 5, "first": 10})

    assert tool.session.get.call_args.kwargs["params"]["start"] == 10
    assert result["metadata"]["start"] == 10
    assert result["metadata"]["next_start"] == 15


def test_interactor_metadata_keeps_every_fetched_interaction_id():
    tool = IntActRESTTool({"name": "intact_get_interactor", "fields": {}})
    tool.session.get = MagicMock(return_value=_response(n=25))

    result = tool._use_ebi_search(
        {"identifier": "P04637", "size": 25}, "intact_get_interactor"
    )

    assert result["metadata"]["count"] == 25
    assert len(result["metadata"]["interaction_ids"]) == 25
    assert result["metadata"]["next_start"] == 25
