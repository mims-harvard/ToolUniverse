from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.odphp_tool import ODPHPRESTTool


pytestmark = pytest.mark.unit


def _response(payload):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = payload
    return response


def _tool():
    return ODPHPRESTTool({"fields": {"endpoint": "/topicsearch.json"}})


def test_string_false_is_not_treated_as_an_error():
    response = _response(
        {
            "Result": {
                "Error": "False",
                "Total": 1,
                "Query": {"TopicId": "30606"},
                "Resources": {"Resource": [{"Id": "30606"}]},
            }
        }
    )
    with patch("tooluniverse.odphp_tool.requests.get", return_value=response):
        result = _tool()._make_request({"topicId": "30606"})
    assert result["status"] == "success"
    assert result["metadata"]["returned_records"] == 1
    assert result["metadata"]["result_set_complete"] is True


def test_http_200_application_error_is_explicit():
    response = _response({"Result": {"Error": "API version 3 is no longer supported"}})
    with patch("tooluniverse.odphp_tool.requests.get", return_value=response):
        result = _tool()._make_request()
    assert result["status"] == "error"
    assert "no longer supported" in result["error"]
    assert result["metadata"]["requested_scope_complete"] is False


def test_ignored_query_parameter_is_explicit():
    response = _response(
        {
            "Result": {
                "Error": "False",
                "Total": 0,
                "Query": {"CategoryId": None},
            }
        }
    )
    with patch("tooluniverse.odphp_tool.requests.get", return_value=response):
        result = _tool()._make_request({"categoryId": "15"})
    assert result["status"] == "error"
    assert result["parameter_mismatches"] == [
        {"parameter": "categoryId", "requested": "15", "returned": None}
    ]
    assert result["metadata"]["requested_scope_complete"] is False


def test_count_mismatch_is_exposed_in_completeness_metadata():
    response = _response(
        {
            "Result": {
                "Error": "False",
                "Total": 2,
                "Query": {"Keyword": "blood pressure"},
                "Resources": {"Resource": [{"Id": "1"}]},
            }
        }
    )
    with patch("tooluniverse.odphp_tool.requests.get", return_value=response):
        result = _tool()._make_request({"keyword": "blood pressure"})
    assert result["status"] == "success"
    assert result["metadata"]["reported_total"] == 2
    assert result["metadata"]["returned_records"] == 1
    assert result["metadata"]["result_set_complete"] is False


def test_myhealthfinder_total_includes_resources_and_callouts():
    response = _response(
        {
            "Result": {
                "Error": "False",
                "Total": 3,
                "Query": {"Age": "45"},
                "Resources": {"All": {"Resource": [{"Id": "1"}, {"Id": "2"}]}},
                "Callouts": {"All": {"Resource": [{"Type": "Link"}]}},
            }
        }
    )
    with patch("tooluniverse.odphp_tool.requests.get", return_value=response):
        result = _tool()._make_request({"age": 45})
    assert result["metadata"]["returned_records"] == 3
    assert result["metadata"]["result_set_complete"] is True
