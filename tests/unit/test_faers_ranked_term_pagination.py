"""Regression tests for FAERS ranked reaction/PT pagination."""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool


def _response(payload):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


def _tool(operation):
    return FAERSAnalyticsTool(
        {
            "name": f"FAERS_{operation}",
            "parameter": {
                "properties": {"operation": {"const": operation, "default": operation}}
            },
        }
    )


@pytest.mark.parametrize(
    ("operation", "list_path"),
    [
        ("filter_serious_events", ("top_serious_reactions",)),
        ("rollup_meddra_hierarchy", ("meddra_hierarchy", "PT_level")),
    ],
)
def test_ranked_terms_are_recoverably_paged(operation, list_path):
    counts = [{"term": f"TERM {i}", "count": 100 - i} for i in range(7)]
    count_response = _response({"results": counts})
    total_response = _response({"meta": {"results": {"total": 1234}}})
    responses = (
        [count_response, total_response]
        if operation == "filter_serious_events"
        else [count_response]
    )

    with patch(
        "tooluniverse.faers_analytics_tool.request_with_retry",
        side_effect=responses,
    ):
        result = _tool(operation).run(
            {
                "operation": operation,
                "drug_name": "IBUPROFEN",
                "limit": 3,
                "offset": 3,
            }
        )

    data = result["data"]
    page = data
    for key in list_path:
        page = page[key]
    labels = [row.get("reaction", row.get("preferred_term")) for row in page]
    assert labels == ["TERM 3", "TERM 4", "TERM 5"]

    metadata = (
        data if operation == "filter_serious_events" else data["meddra_hierarchy"]
    )
    assert metadata["returned"] == 3
    assert metadata["offset"] == 3
    assert metadata["has_more"] is True
    assert metadata["next_offset"] == 6
