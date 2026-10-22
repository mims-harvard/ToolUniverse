"""Regression tests for recoverable GtoPdb interaction pagination."""

from unittest.mock import MagicMock, patch

from tooluniverse.gtopdb_tool import GtoPdbRESTTool


def test_interactions_apply_offset_after_filtering_and_expose_continuation():
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = [
        {"interactionId": i, "targetId": 1797, "ligandId": 1000 + i}
        for i in range(7)
    ]
    tool = GtoPdbRESTTool(
        {
            "name": "GtoPdb_get_interactions",
            "fields": {
                "endpoint": "https://www.guidetopharmacology.org/services/interactions",
                "params": {},
            },
        }
    )

    with patch(
        "tooluniverse.gtopdb_tool.request_with_retry", return_value=response
    ) as request:
        result = tool.run({"targetId": 1797, "limit": 3, "offset": 3})

    requested_url = request.call_args.args[2]
    assert "limit=" not in requested_url
    assert "offset=" not in requested_url
    assert [row["interactionId"] for row in result["data"]] == [3, 4, 5]
    assert result["total_available"] == 7
    assert result["returned"] == 3
    assert result["offset"] == 3
    assert result["has_more"] is True
    assert result["next_offset"] == 6
