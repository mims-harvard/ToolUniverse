from unittest.mock import MagicMock, patch

from tooluniverse.progenetix_tool import ProgenetixTool


def _tool(endpoint):
    return ProgenetixTool({"fields": {"endpoint": endpoint}})


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


@patch("tooluniverse.progenetix_tool.requests.get")
def test_filtering_terms_prefix_then_offset_is_recoverable(mock_get):
    mock_get.return_value = _response(
        {
            "response": {
                "filteringTerms": [
                    {"id": "NCIT:1", "label": "one"},
                    {"id": "HP:2", "label": "other"},
                    {"id": "NCIT:3", "label": "three"},
                    {"id": "NCIT:4", "label": "four"},
                ]
            }
        }
    )

    result = _tool("filtering_terms").run({"prefixes": "NCIT", "limit": 1, "offset": 1})

    data = result["data"]
    assert [row["id"] for row in data["terms"]] == ["NCIT:3"]
    assert data["total_terms"] == 3
    assert data["has_more"] is True
    assert data["next_offset"] == 2
    assert "limit" not in mock_get.call_args.kwargs["params"]


@patch("tooluniverse.progenetix_tool.requests.get")
def test_cohort_tail_page_terminates(mock_get):
    mock_get.return_value = _response(
        {
            "response": {
                "collections": [
                    {"id": f"cohort-{index}", "cohortDataTypes": []}
                    for index in range(5)
                ]
            }
        }
    )

    result = _tool("cohorts").run({"limit": 2, "offset": 4})

    data = result["data"]
    assert [row["id"] for row in data["cohorts"]] == ["cohort-4"]
    assert data["total_cohorts"] == 5
    assert data["has_more"] is False
    assert data["next_offset"] is None


def test_catalog_operations_reject_invalid_offset_before_request():
    for endpoint in ("filtering_terms", "cohorts"):
        with patch("tooluniverse.progenetix_tool.requests.get") as request:
            result = _tool(endpoint).run({"offset": -1})
        assert "non-negative" in result["error"]
        request.assert_not_called()
