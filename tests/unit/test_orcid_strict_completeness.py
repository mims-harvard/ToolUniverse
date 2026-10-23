from unittest.mock import patch

import pytest

from tooluniverse.orcid_tool import ORCIDTool


pytestmark = pytest.mark.unit


def _tool():
    return ORCIDTool({})


@pytest.mark.parametrize(
    "orcid,error",
    [(1, "format"), ("0000-0002-1825-0098", "checksum"), ("bad", "format")],
)
def test_invalid_orcid_is_rejected_before_network(orcid, error):
    with patch.object(ORCIDTool, "_make_request") as request:
        result = _tool().run({"operation": "get_profile", "orcid": orcid})
    assert result["status"] == "error"
    assert error in result["error"]
    request.assert_not_called()


def test_works_returns_every_summary_not_only_first_per_group():
    payload = {
        "group": [
            {
                "external-ids": {"external-id": [{"value": "doi"}]},
                "work-summary": [
                    {"put-code": 1, "title": {"title": {"value": "A"}}},
                    {"put-code": 2, "title": {"title": {"value": "A copy"}}},
                ],
            },
            {"work-summary": [{"put-code": 3, "title": {"title": {"value": "B"}}}]},
        ]
    }
    with patch.object(
        ORCIDTool, "_make_request", return_value={"ok": True, "data": payload}
    ):
        result = _tool().run({"operation": "get_works", "orcid": "0000-0002-1825-0097"})
    assert [work["put_code"] for work in result["data"]] == [1, 2, 3]
    assert result["metadata"]["work_group_count"] == 2
    assert result["metadata"]["work_summary_count"] == 3
    assert result["metadata"]["all_group_summaries_returned"] is True


@pytest.mark.parametrize(
    "arguments,error",
    [
        ({"query": 1}, "query"),
        ({"query": "Smith", "start": True}, "start"),
        ({"query": "Smith", "rows": 201}, "rows"),
    ],
)
def test_search_rejects_invalid_controls_before_network(arguments, error):
    arguments["operation"] = "search_researchers"
    with patch.object(ORCIDTool, "_make_request") as request:
        result = _tool().run(arguments)
    assert result["status"] == "error"
    assert error in result["error"]
    request.assert_not_called()


def test_search_reports_exact_continuation_metadata():
    payload = {
        "num-found": 5,
        "expanded-result": [
            {"orcid-id": "0000-0002-1825-0097"},
            {"orcid-id": "0000-0001-5109-3700"},
        ],
    }
    with patch.object(
        ORCIDTool, "_make_request", return_value={"ok": True, "data": payload}
    ):
        result = _tool().run(
            {"operation": "search_researchers", "query": "Smith", "start": 2, "rows": 2}
        )
    assert result["metadata"] == {
        "start": 2,
        "rows": 2,
        "returned": 2,
        "total_found": 5,
        "has_more": True,
        "next_start": 4,
        "page_complete": True,
    }
