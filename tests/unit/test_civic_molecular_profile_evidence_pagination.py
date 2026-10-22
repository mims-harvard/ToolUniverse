from unittest.mock import Mock, patch

from tooluniverse.civic_tool import CIViCTool


def _config():
    return {
        "name": "civic_get_molecular_profile",
        "fields": {
            "query": "query Get($molecular_profile_id: Int!, $evidence_limit: Int, $evidence_after: String) { molecularProfile(id: $molecular_profile_id) { id evidenceItems(first: $evidence_limit, after: $evidence_after) { totalCount nodes { id } pageInfo { hasNextPage endCursor } } } }",
            "operation_name": "Get",
        },
    }


def _response(ids, total, has_more, cursor):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "data": {
            "molecularProfile": {
                "id": 12,
                "evidenceItems": {
                    "totalCount": total,
                    "nodes": [{"id": item} for item in ids],
                    "pageInfo": {"hasNextPage": has_more, "endCursor": cursor},
                },
            }
        }
    }
    return response


@patch("tooluniverse.civic_tool.requests.post")
def test_nested_evidence_page_exposes_exact_continuation_metadata(mock_post):
    mock_post.return_value = _response([106, 107, 105], 213, True, "cursor-6")

    result = CIViCTool(_config()).run(
        {"molecular_profile_id": 12, "evidence_limit": 3, "evidence_after": "cursor-3"}
    )

    expected = {
        "evidence_returned": 3,
        "evidence_total_results": 213,
        "evidence_total_results_is_exact": True,
        "evidence_has_more": True,
        "next_evidence_cursor": "cursor-6",
    }
    assert {key: result["metadata"][key] for key in expected} == expected
    variables = mock_post.call_args.kwargs["json"]["variables"]
    assert variables["evidence_after"] == "cursor-3"
    assert variables["evidence_limit"] == 3


@patch("tooluniverse.civic_tool.requests.post")
def test_nested_evidence_last_page_does_not_offer_stale_cursor(mock_post):
    mock_post.return_value = _response([999], 213, False, "server-end-cursor")

    result = CIViCTool(_config()).run(
        {"molecular_profile_id": 12, "evidence_limit": 3, "evidence_after": "cursor-212"}
    )

    assert result["metadata"]["evidence_has_more"] is False
    assert result["metadata"]["next_evidence_cursor"] is None
