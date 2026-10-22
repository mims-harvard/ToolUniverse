"""Regression test for native Drugs@FDA search pagination."""

from unittest.mock import MagicMock, patch

from tooluniverse.fda_orange_book_tool import FDAOrangeBookTool


def test_search_drug_forwards_skip_and_returns_continuation():
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "meta": {"results": {"total": 272}},
        "results": [
            {
                "application_number": f"ANDA{i}",
                "sponsor_name": "Sponsor",
                "products": [],
            }
            for i in range(3, 6)
        ],
    }
    tool = FDAOrangeBookTool(
        {
            "name": "FDA_OrangeBook_search_drug",
            "parameter": {
                "properties": {
                    "operation": {"const": "search_drug", "default": "search_drug"}
                }
            },
        }
    )

    with patch(
        "tooluniverse.fda_orange_book_tool.requests.get", return_value=response
    ) as get:
        result = tool.run(
            {"generic_name": "IBUPROFEN", "limit": 3, "offset": 3}
        )["data"]

    assert get.call_args.kwargs["params"]["limit"] == 3
    assert get.call_args.kwargs["params"]["skip"] == 3
    assert [row["application_number"] for row in result["drugs"]] == [
        "ANDA3",
        "ANDA4",
        "ANDA5",
    ]
    assert result["total"] == 272
    assert result["returned"] == 3
    assert result["offset"] == 3
    assert result["has_more"] is True
    assert result["next_offset"] == 6
