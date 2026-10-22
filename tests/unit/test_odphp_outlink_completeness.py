from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.odphp_tool import ODPHPOutlinkFetch


pytestmark = pytest.mark.unit


def _response(text="", status=200, content_type="text/html", payload=None):
    response = MagicMock()
    response.status_code = status
    response.text = text
    response.headers = {"Content-Type": content_type}
    response.json.return_value = payload
    return response


def test_json_example_returns_content_instead_of_empty_text():
    response = _response(
        content_type="application/json",
        payload={"Result": {"Error": "False", "Title": "Blood pressure"}},
    )
    with patch("tooluniverse.odphp_tool.requests.get", return_value=response):
        result = ODPHPOutlinkFetch({}).run(
            {"urls": ["https://health.gov/example.json"]}
        )
    item = result["results"][0]
    assert "Blood pressure" in item["text"]
    assert item["title"] == "(JSON Document)"
    assert item["text_truncated"] is False


def test_json_application_error_is_not_reported_as_complete():
    response = _response(
        content_type="application/json",
        payload={"Result": {"Error": "API version 3 is no longer supported"}},
    )
    with patch("tooluniverse.odphp_tool.requests.get", return_value=response):
        result = ODPHPOutlinkFetch({}).run(
            {"urls": ["https://health.gov/deprecated.json"]}
        )
    assert "no longer supported" in result["results"][0]["error"]
    assert result["metadata"]["failed_urls"] == 1
    assert result["metadata"]["requested_scope_complete"] is False


def test_character_cap_is_explicit():
    response = _response(text="<html><main>abcdefghij</main></html>")
    with patch("tooluniverse.odphp_tool.requests.get", return_value=response):
        result = ODPHPOutlinkFetch({}).run(
            {"urls": ["https://health.gov/article"], "max_chars": 4}
        )
    item = result["results"][0]
    assert item["text"] == "abcd"
    assert item["original_text_chars"] == 10
    assert item["text_truncated"] is True


def test_more_than_three_urls_is_rejected_before_network():
    with patch("tooluniverse.odphp_tool.requests.get") as get:
        result = ODPHPOutlinkFetch({}).run(
            {"urls": [f"https://health.gov/{index}" for index in range(4)]}
        )
    assert result["status"] == "error"
    get.assert_not_called()


@pytest.mark.parametrize(
    "arguments",
    [
        {"urls": ["ftp://example.org/file"]},
        {"urls": ["https://health.gov/x"], "max_chars": 0},
        {"urls": ["https://health.gov/x"], "return_html": "false"},
    ],
)
def test_invalid_controls_are_rejected_before_network(arguments):
    with patch("tooluniverse.odphp_tool.requests.get") as get:
        result = ODPHPOutlinkFetch({}).run(arguments)
    assert result["status"] == "error"
    get.assert_not_called()


def test_http_failure_marks_requested_scope_incomplete():
    response = _response(text="not found", status=404)
    with patch("tooluniverse.odphp_tool.requests.get", return_value=response):
        result = ODPHPOutlinkFetch({}).run({"urls": ["https://health.gov/missing"]})
    assert result["results"][0]["error"] == "HTTP 404 fetching URL"
    assert result["metadata"]["failed_urls"] == 1
    assert result["metadata"]["requested_scope_complete"] is False
