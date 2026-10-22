from unittest.mock import Mock, patch

from tooluniverse.civic_tool import CIViCTool


def _response(ids, total, has_more, cursor):
    response = Mock()
    response.json.return_value = {
        "data": {
            "gene": {
                "id": 19,
                "name": "EGFR",
                "variants": {
                    "nodes": [
                        {"id": variant_id, "name": f"V{variant_id}"}
                        for variant_id in ids
                    ],
                    "totalCount": total,
                    "pageInfo": {
                        "hasNextPage": has_more,
                        "endCursor": cursor,
                    },
                },
            }
        }
    }
    return response


@patch("tooluniverse.civic_tool.requests.post")
def test_get_variants_exposes_total_and_continuation_cursor(mock_post):
    mock_post.return_value = _response([1, 2, 3], 322, True, "cursor-3")
    tool = CIViCTool({"name": "civic_get_variants_by_gene"})

    result = tool.run({"gene_id": 19, "limit": 3})

    assert result["data"]["gene"]["variants"]["totalCount"] == 322
    assert result["metadata"]["returned"] == 3
    assert result["metadata"]["total_results"] == 322
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_cursor"] == "cursor-3"
    assert result["metadata"]["result_set_complete"] is False


@patch("tooluniverse.civic_tool.requests.post")
def test_get_variants_forwards_after_and_terminates_last_page(mock_post):
    mock_post.return_value = _response([321, 322], 322, False, "cursor-end")
    tool = CIViCTool({"name": "civic_get_variants_by_gene"})

    result = tool.run({"gene_id": 19, "limit": 3, "after": "cursor-320"})

    variables = mock_post.call_args.kwargs["json"]["variables"]
    assert variables["after"] == "cursor-320"
    assert [
        row["id"] for row in result["data"]["gene"]["variants"]["nodes"]
    ] == [321, 322]
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_cursor"] is None


@patch("tooluniverse.civic_tool.requests.post")
def test_get_variants_marks_uncapped_first_page_complete(mock_post):
    mock_post.return_value = _response([1, 2], 2, False, "cursor-end")
    tool = CIViCTool({"name": "civic_get_variants_by_gene"})

    result = tool.run({"gene_id": 19, "limit": 500})

    assert result["metadata"]["returned"] == 2
    assert result["metadata"]["result_set_complete"] is True

