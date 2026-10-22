from unittest.mock import Mock, patch

from tooluniverse.datacite_tool import DataCiteRESTTool


def config(name="DataCite_search_dois"):
    return {
        "name": name,
        "type": "DataCiteRESTTool",
        "parameter": {
            "properties": {
                "query": {"type": "string"},
                "page_size": {"type": "integer", "default": 10},
                "page_number": {"type": "integer", "default": 1},
            }
        },
        "fields": {"endpoint": "https://api.datacite.org/dois"},
    }


def response(payload):
    result = Mock(status_code=200, text="")
    result.json.return_value = payload
    return result


def test_datacite_exposes_exact_total_and_reachable_window():
    payload = {
        "data": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
        "meta": {"total": 66907, "totalPages": 3333, "page": 1},
    }
    tool = DataCiteRESTTool(config())
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry",
        return_value=response(payload),
    ) as request:
        result = tool.run({"query": "RNA-seq", "page_size": 3, "page_number": 1})

    metadata = result["metadata"]
    assert metadata["returned"] == 3
    assert metadata["total_results"] == 66907
    assert metadata["accessible_results"] == 9999
    assert metadata["accessible_pages"] == 3333
    assert metadata["upstream_truncated"] is True
    assert metadata["next_page"] == 2
    assert metadata["warning"]
    assert request.call_args.kwargs["params"]["page[size]"] == 3
    assert request.call_args.kwargs["params"]["page[number]"] == 1


def test_datacite_small_result_can_be_complete():
    payload = {
        "data": [{"id": "only"}],
        "meta": {"total": 1, "totalPages": 1, "page": 1},
    }
    tool = DataCiteRESTTool(config())
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry",
        return_value=response(payload),
    ):
        metadata = tool.run({"query": "specific"})["metadata"]

    assert metadata["accessible_results"] == 1
    assert metadata["upstream_truncated"] is False
    assert metadata["has_more"] is False
    assert metadata["result_set_complete"] is True


def test_datacite_rejects_upstream_page_coercions():
    tool = DataCiteRESTTool(config())
    with patch("tooluniverse.base_rest_tool.request_with_retry") as request:
        assert tool.run({"query": "x", "page_size": 0})["parameter"] == "page_size"
        assert tool.run({"query": "x", "page_size": 1001})["parameter"] == "page_size"
        assert tool.run({"query": "x", "page_number": 0})["parameter"] == "page_number"
        assert tool.run({"query": "x", "page_number": True})["parameter"] == "page_number"
    request.assert_not_called()
