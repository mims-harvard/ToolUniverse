from unittest.mock import Mock, patch

from tooluniverse.civic_tool import CIViCTool


def _config():
    return {
        "name": "civic_get_variant",
        "fields": {
            "query": "query Get($variant_id: Int!, $molecular_profile_limit: Int, $molecular_profile_after: String) { variant(id: $variant_id) { id molecularProfiles(first: $molecular_profile_limit, after: $molecular_profile_after) { totalCount nodes { id } pageInfo { hasNextPage endCursor } } } }",
            "operation_name": "Get",
        },
    }


def _response(ids, total, has_more, cursor):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "data": {
            "variant": {
                "id": 12,
                "molecularProfiles": {
                    "totalCount": total,
                    "nodes": [{"id": item} for item in ids],
                    "pageInfo": {"hasNextPage": has_more, "endCursor": cursor},
                },
            }
        }
    }
    return response


@patch("tooluniverse.civic_tool.requests.post")
def test_variant_nested_profiles_expose_cursor_and_exact_total(mock_post):
    mock_post.return_value = _response([4230, 4321], 40, True, "cursor-7")
    result = CIViCTool(_config()).run(
        {
            "variant_id": 12,
            "molecular_profile_limit": 2,
            "molecular_profile_after": "cursor-5",
        }
    )

    expected = {
        "molecular_profiles_returned": 2,
        "molecular_profiles_total_results": 40,
        "molecular_profiles_total_results_is_exact": True,
        "molecular_profiles_has_more": True,
        "next_molecular_profile_cursor": "cursor-7",
    }
    assert {key: result["metadata"][key] for key in expected} == expected
    variables = mock_post.call_args.kwargs["json"]["variables"]
    assert variables["molecular_profile_limit"] == 2
    assert variables["molecular_profile_after"] == "cursor-5"


@patch("tooluniverse.civic_tool.requests.post")
def test_variant_nested_profiles_last_page_clears_cursor(mock_post):
    mock_post.return_value = _response([999], 40, False, "server-end")
    result = CIViCTool(_config()).run(
        {
            "variant_id": 12,
            "molecular_profile_limit": 5,
            "molecular_profile_after": "cursor-39",
        }
    )
    assert result["metadata"]["molecular_profiles_has_more"] is False
    assert result["metadata"]["next_molecular_profile_cursor"] is None
