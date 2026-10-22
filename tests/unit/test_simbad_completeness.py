from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.simbad_tool import SIMBADAdvancedTool, SIMBADTool


pytestmark = pytest.mark.unit


def _response(text="", payload=None, status=200):
    response = MagicMock()
    response.status_code = status
    response.text = text
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def _script_rows(count):
    return "\n".join(
        f"Object {index} | 00 00 00 +00 00 00 | Star" for index in range(count)
    )


def test_identifier_response_rows_are_exactly_paginated():
    tool = SIMBADTool({})
    response = _response(text=_script_rows(5))
    with patch("tooluniverse.simbad_tool.requests.post", return_value=response):
        first = tool.run(
            {"query_type": "identifier", "identifier": "NGC 10*", "max_results": 2}
        )
        second = tool.run(
            {
                "query_type": "identifier",
                "identifier": "NGC 10*",
                "max_results": 2,
                "offset": 2,
            }
        )
    assert first["metadata"]["total_matches_in_response"] == 5
    assert first["metadata"]["next_offset"] == 2
    assert first["metadata"]["upstream_result_set_complete"] is None
    first_ids = {item["main_id"] for item in first["data"]["results"]}
    second_ids = {item["main_id"] for item in second["data"]["results"]}
    assert first_ids.isdisjoint(second_ids)


def test_script_error_retains_upstream_message():
    response = _response(
        text="::error::::::::::::::::::::::::\n\n[3] 'bad id': No known catalog could be found"
    )
    with patch("tooluniverse.simbad_tool.requests.post", return_value=response):
        result = SIMBADTool({}).run(
            {"query_type": "identifier", "identifier": "bad id"}
        )
    assert result["status"] == "error"
    assert "No known catalog" in result["data"]["upstream_error"]
    assert result["data"]["error"] == "SIMBAD script error"


@pytest.mark.parametrize(
    "arguments",
    [
        {"query_type": "identifier", "identifier": "NGC*", "max_results": 0},
        {"query_type": "identifier", "identifier": "NGC*", "offset": -1},
        {"query_type": "coordinates", "ra": 361, "dec": 0},
    ],
)
def test_invalid_simple_query_controls_are_rejected_before_network(arguments):
    with patch("tooluniverse.simbad_tool.requests.post") as post:
        result = SIMBADTool({}).run(arguments)
    assert result["status"] == "error"
    post.assert_not_called()


def test_tap_json_uses_plus_one_probe_and_reports_overflow():
    payload = {
        "metadata": [{"name": "main_id"}],
        "data": [["A"], ["B"], ["C"]],
    }
    with patch(
        "tooluniverse.simbad_tool.requests.post",
        return_value=_response(payload=payload),
    ) as post:
        result = SIMBADAdvancedTool({}).run(
            {"adql_query": "SELECT main_id FROM basic", "max_results": 2}
        )
    assert post.call_args.kwargs["data"]["MAXREC"] == 3
    assert result["data"]["results"]["data"] == [["A"], ["B"]]
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["result_set_complete"] is False


def test_tap_votable_surfaces_query_status_overflow():
    xml = (
        '<VOTABLE><RESOURCE><INFO name="QUERY_STATUS" value="OK"/>'
        '<INFO name="QUERY_STATUS" value="OVERFLOW"/></RESOURCE></VOTABLE>'
    )
    with patch(
        "tooluniverse.simbad_tool.requests.post",
        return_value=_response(text=xml),
    ):
        result = SIMBADAdvancedTool({}).run(
            {
                "adql_query": "SELECT main_id FROM basic",
                "max_results": 2,
                "format": "votable",
            }
        )
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["overflow_detection"] == "VOTable_QUERY_STATUS"


def test_tap_invalid_json_is_an_error_not_text_success():
    response = _response(text="not json")
    response.json.side_effect = ValueError("bad json")
    with patch("tooluniverse.simbad_tool.requests.post", return_value=response):
        result = SIMBADAdvancedTool({}).run({"adql_query": "SELECT main_id FROM basic"})
    assert result["status"] == "error"
    assert "invalid JSON" in result["data"]["error"]
