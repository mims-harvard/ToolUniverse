from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.rcsb_search_tool import RCSBSearchTool


pytestmark = pytest.mark.unit


def _tool():
    return RCSBSearchTool({"name": "PDB_search_similar_structures"})


def _response(payload, status=200):
    response = MagicMock()
    response.status_code = status
    response.content = b"response"
    response.json.return_value = payload
    return response


@pytest.mark.parametrize(
    "arguments,error",
    [
        ({"query": 123}, "query must be a string"),
        ({"query": "kinase", "search_type": 1}, "search_type must be a string"),
        (
            {"query": "kinase", "similarity_threshold": "0.7"},
            "similarity_threshold must be a number",
        ),
        (
            {"query": "kinase", "similarity_threshold": 1.1},
            "similarity_threshold must be a number",
        ),
        ({"query": "kinase", "max_results": 101}, "max_results must be"),
        ({"query": "kinase", "max_results": True}, "max_results must be"),
        ({"query": "kinase", "start": -1}, "start must be"),
        ({"query": "kinase", "start": "2"}, "start must be"),
    ],
)
def test_invalid_controls_are_rejected_without_network(arguments, error):
    with patch("tooluniverse.rcsb_search_tool.requests.post") as post:
        result = _tool().run(arguments)
    assert result["status"] == "error"
    assert error in result["error"]
    post.assert_not_called()


def test_pagination_is_exact_and_recoverable():
    search = _response(
        {
            "result_set": [
                {"identifier": "3AAA", "score": 0.8},
                {"identifier": "4BBB", "score": 0.7},
            ],
            "total_count": 5,
        }
    )
    graphql = _response(
        {
            "data": {
                "entries": [
                    {"rcsb_id": "3AAA", "struct": {"title": "A"}},
                    {"rcsb_id": "4BBB", "struct": {"title": "B"}},
                ]
            }
        }
    )
    with patch(
        "tooluniverse.rcsb_search_tool.requests.post",
        side_effect=[search, graphql],
    ) as post:
        result = _tool().run(
            {"query": "kinase", "search_type": "text", "max_results": 2, "start": 2}
        )
    data = result["data"]
    assert post.call_args_list[0].kwargs["json"]["request_options"]["paginate"] == {
        "start": 2,
        "rows": 2,
    }
    assert [row["rank"] for row in data["results"]] == [3, 4]
    assert data["next_start"] == 4
    assert data["has_more"] is True
    assert data["result_set_complete"] is False
    assert data["metadata_enrichment"]["complete"] is True


def test_structure_threshold_is_not_misrepresented_as_applied():
    search = _response(
        {"result_set": [{"identifier": "1ABC", "score": 1.0}], "total_count": 1}
    )
    with patch(
        "tooluniverse.rcsb_search_tool.requests.post", return_value=search
    ) as post:
        result = _tool().run(
            {
                "query": "1ABC",
                "search_type": "structure",
                "similarity_threshold": 0.95,
            }
        )
    request_parameters = post.call_args.kwargs["json"]["query"]["parameters"]
    assert "similarity_threshold" not in request_parameters
    assert result["data"]["similarity_threshold_applied"] is False
    assert "similarity_threshold" not in result["data"]
    assert result["data"]["structure_operator"] == "strict_shape_match"


def test_graphql_metadata_failure_is_explicit_but_search_rows_remain():
    search = _response(
        {"result_set": [{"identifier": "1ABC", "score": 1.0}], "total_count": 1}
    )
    graphql = _response({}, status=503)
    with patch(
        "tooluniverse.rcsb_search_tool.requests.post",
        side_effect=[search, graphql],
    ):
        result = _tool().run({"query": "kinase", "search_type": "text"})
    enrichment = result["data"]["metadata_enrichment"]
    assert len(result["data"]["results"]) == 1
    assert enrichment["complete"] is False
    assert enrichment["missing_entries"] == ["1ABC"]
    assert "HTTP 503" in enrichment["error"]


def test_empty_page_before_reported_total_is_an_error():
    search = _response({"result_set": [], "total_count": 5})
    with patch("tooluniverse.rcsb_search_tool.requests.post", return_value=search):
        result = _tool().run({"query": "kinase", "search_type": "text", "start": 2})
    assert result["status"] == "error"
    assert "empty page before total_count" in result["error"]


def test_missing_total_count_is_an_error():
    search = _response({"result_set": [{"identifier": "1ABC"}]})
    with patch("tooluniverse.rcsb_search_tool.requests.post", return_value=search):
        result = _tool().run({"query": "kinase", "search_type": "text"})
    assert result["status"] == "error"
    assert "total_count" in result["error"]
