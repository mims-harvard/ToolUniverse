from unittest.mock import Mock, patch

from tooluniverse.civic_tool import CIViCTool


def _config(name, root):
    return {
        "name": name,
        "fields": {
            "query": f"query Search($limit: Int, $after: String) {{ {root}(first: $limit, after: $after) {{ totalCount nodes {{ id }} pageInfo {{ hasNextPage endCursor }} }} }}",
            "operation_name": "Search",
        },
    }


def _response(root, ids, total, has_more, cursor):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "data": {
            root: {
                "nodes": [{"id": item} for item in ids],
                "totalCount": total,
                "pageInfo": {"hasNextPage": has_more, "endCursor": cursor},
            }
        }
    }
    return response


@patch("tooluniverse.civic_tool.requests.post")
def test_variant_search_follows_server_pages(mock_post):
    mock_post.side_effect = [
        _response("variants", range(100), 250, True, "cursor-100"),
        _response("variants", range(100, 150), 250, True, "cursor-150"),
    ]
    result = CIViCTool(_config("civic_search_variants", "variants")).run({"limit": 150})

    assert len(result["data"]["variants"]["nodes"]) == 150
    assert result["metadata"]["total_results"] == 250
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_cursor"] == "cursor-150"
    assert mock_post.call_args_list[1].kwargs["json"]["variables"]["after"] == "cursor-100"


@patch("tooluniverse.civic_tool.requests.post")
def test_evidence_search_accepts_continuation_cursor(mock_post):
    mock_post.return_value = _response("evidenceItems", [100, 101], 102, False, "cursor-end")
    result = CIViCTool(_config("civic_search_evidence_items", "evidenceItems")).run(
        {"limit": 10, "after": "cursor-100"}
    )

    assert [node["id"] for node in result["data"]["evidenceItems"]["nodes"]] == [100, 101]
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_cursor"] is None
    assert mock_post.call_args.kwargs["json"]["variables"]["after"] == "cursor-100"


@patch("tooluniverse.civic_tool.requests.post")
def test_gene_search_exposes_exact_total_and_continuation_cursor(mock_post):
    mock_post.return_value = _response("genes", [4244, 16656, 16535], 734, True, "Mw")
    result = CIViCTool(_config("civic_search_genes", "genes")).run(
        {"limit": 3, "after": "previous-cursor"}
    )

    assert result["metadata"]["returned"] == 3
    assert result["metadata"]["total_results"] == 734
    assert result["metadata"]["total_results_is_exact"] is True
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_cursor"] == "Mw"
    assert mock_post.call_args.kwargs["json"]["variables"]["after"] == "previous-cursor"
