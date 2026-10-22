from unittest.mock import MagicMock, patch

from tooluniverse.addgene_tool import AddgeneTool


def _tool():
    tool = AddgeneTool(
        {
            "name": "Addgene_test",
            "type": "AddgeneTool",
            "parameter": {"type": "object", "properties": {}},
        }
    )
    tool.api_key = "test-token"
    return tool


def _response(payload):
    response = MagicMock(status_code=200)
    response.json.return_value = payload
    return response


def test_plasmid_search_forwards_page_and_reports_continuation():
    payload = {
        "count": 5,
        "next": "https://api.developers.addgene.org/catalog/plasmid/?page=3",
        "previous": "https://api.developers.addgene.org/catalog/plasmid/?page=1",
        "results": [{"id": 3}, {"id": 4}],
    }
    with patch("tooluniverse.addgene_tool.requests.get", return_value=_response(payload)) as get:
        result = _tool().run(
            {"operation": "search_plasmids", "query": "CRISPR", "limit": 2, "page": 2}
        )

    assert get.call_args.kwargs["params"]["page"] == 2
    assert get.call_args.kwargs["params"]["page_size"] == 2
    assert result["metadata"]["total_pages"] == 3
    assert result["metadata"]["next_page_number"] == 3
    assert result["metadata"]["truncated"] is True


def test_plasmid_search_rejects_malformed_pagination_without_request():
    with patch("tooluniverse.addgene_tool.requests.get") as get:
        for pagination in ({"page": 0}, {"page": "2"}, {"limit": True}, {"limit": 101}):
            result = _tool().run(
                {"operation": "search_plasmids", "query": "CRISPR", **pagination}
            )
            assert result["status"] == "error"
    get.assert_not_called()


def test_depositor_search_labels_page_local_counts_and_forwards_page():
    payload = {
        "count": 8,
        "next": "https://api.developers.addgene.org/catalog/plasmid/?page=3",
        "results": [
            {"id": 3, "name": "p3", "depositor": ["Feng Zhang"]},
            {"id": 4, "name": "p4", "depositor": ["Feng Zhang"]},
        ],
    }
    with patch("tooluniverse.addgene_tool.requests.get", return_value=_response(payload)) as get:
        result = _tool().run(
            {"operation": "search_depositors", "name": "Feng Zhang", "limit": 2, "page": 2}
        )

    params = get.call_args.kwargs["params"]
    assert params == {"page_size": 2, "page": 2, "pis": "Feng Zhang"}
    assert result["data"]["total_plasmids_searched"] == 2
    assert result["data"]["total_matching_plasmids"] == 8
    assert result["data"]["depositors"][0]["plasmid_count_scope"] == "current_page"
    assert result["metadata"]["next_page"] == 3


def test_institution_is_rejected_instead_of_mapped_to_article_authors():
    with patch("tooluniverse.addgene_tool.requests.get") as get:
        result = _tool().run(
            {"operation": "search_depositors", "institution": "Broad Institute"}
        )
    assert result["status"] == "error"
    assert "does not expose an institution filter" in result["error"]
    get.assert_not_called()
