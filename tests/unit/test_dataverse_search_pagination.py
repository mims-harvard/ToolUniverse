import json
from pathlib import Path
from unittest.mock import Mock, patch

from tooluniverse.base_rest_tool import BaseRESTTool


CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "src/tooluniverse/data/dataverse_tools.json"
)


def config():
    return next(
        c
        for c in json.loads(CONFIG_PATH.read_text())
        if c["name"] == "Dataverse_search_datasets"
    )


def response(status=200, *, headers=None, payload=None, text=""):
    result = Mock(status_code=status, headers=headers or {}, text=text)
    result.json.return_value = payload
    return result


def test_dataverse_extracts_data_and_exposes_exact_offset_continuation():
    payload = {
        "status": "OK",
        "data": {
            "q": "climate change",
            "total_count": 120,
            "start": 3,
            "count_in_response": 3,
            "items": [
                {"name": "A", "type": "dataset"},
                {"name": "B", "type": "dataset"},
                {"name": "C", "type": "dataset"},
            ],
        },
    }
    tool = BaseRESTTool(config())
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry",
        return_value=response(payload=payload),
    ) as request:
        result = tool.run(
            {"q": "climate change", "type": "dataset", "per_page": 3, "start": 3}
        )

    assert result["status"] == "success"
    assert result["data"] == payload["data"]
    assert result["metadata"] == {
        "returned": 3,
        "reported_count_in_response": 3,
        "total_results": 120,
        "total_results_is_exact": True,
        "start": 3,
        "per_page": 3,
        "has_more": True,
        "next_start": 6,
        "truncated": True,
        "result_set_complete": False,
        "pagination_scope": "dataverse_exact_start_offset",
    }
    assert request.call_args.kwargs["params"]["start"] == 3


def test_dataverse_waf_202_is_not_reported_as_empty_success():
    tool = BaseRESTTool(config())
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry",
        return_value=response(
            202, headers={"x-amzn-waf-action": "challenge"}, text=""
        ),
    ):
        result = tool.run({"q": "climate"})

    assert result["status"] == "error"
    assert result["status_code"] == 202
    assert result["waf_action"] == "challenge"
    assert "AWS WAF challenge" in result["error"]


def test_dataverse_rejects_values_the_api_coerces_or_fails_on():
    tool = BaseRESTTool(config())
    with patch("tooluniverse.base_rest_tool.request_with_retry") as request:
        assert tool.run({"q": "x", "per_page": 0})["parameter"] == "per_page"
        assert tool.run({"q": "x", "per_page": 1001})["parameter"] == "per_page"
        assert tool.run({"q": "x", "start": -1})["parameter"] == "start"
        assert tool.run({"q": "x", "type": "bogus"})["parameter"] == "type"
    request.assert_not_called()
