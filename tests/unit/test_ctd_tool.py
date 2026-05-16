"""Unit tests for the CTD tool."""

from unittest.mock import Mock, patch

import pytest

from tooluniverse.ctd_tool import CTD_REQUEST_HEADERS, CTDTool


def make_ctd_tool(input_type="gene", report_type="diseases_curated"):
    """Create a CTD tool with a small deterministic config."""

    return CTDTool(
        {
            "name": "CTD_get_gene_diseases",
            "type": "CTDTool",
            "fields": {
                "input_type": input_type,
                "report_type": report_type,
            },
        }
    )


def make_response(text, json_value=None, content_type="application/json"):
    """Create a mock requests response."""

    response = Mock()
    response.status_code = 200
    response.url = "https://ctdbase.org/tools/batchQuery.go?inputTerms=TP53"
    response.text = text
    response.headers = {"content-type": content_type}
    response.raise_for_status.return_value = None
    if json_value is None:
        response.json.side_effect = ValueError("not json")
    else:
        response.json.return_value = json_value
    return response


@pytest.mark.unit
@patch("tooluniverse.ctd_tool.requests.get")
def test_ctd_non_json_response_includes_diagnostics(mock_get):
    """HTML responses should include enough context to debug API failures."""

    mock_get.return_value = make_response(
        "<!DOCTYPE html><html><head><title>CTD</title></head></html>",
        content_type="text/html;charset=UTF-8",
    )
    tool = make_ctd_tool()

    result = tool.run({"input_terms": "TP53"})

    assert result["status"] == "error"
    assert result["error"] == "CTD API returned non-JSON response"
    assert result["status_code"] == 200
    assert result["content_type"] == "text/html;charset=UTF-8"
    assert result["request_url"].startswith("https://ctdbase.org/tools/batchQuery.go")
    assert result["response_snippet"].startswith("<!DOCTYPE html>")
    assert result["metadata"] == {
        "input_type": "gene",
        "report_type": "diseases_curated",
        "query": "TP53",
    }
    assert result["retryable"] is True
    assert "request_url" in result["suggestion"]


@pytest.mark.unit
@patch("tooluniverse.ctd_tool.requests.get")
def test_ctd_human_verification_response_is_non_retryable(mock_get):
    """CAPTCHA pages should be reported as a blocked access state."""

    mock_get.return_value = make_response(
        "<html><title>Verify you are a human</title><body>captcha</body></html>",
        content_type="text/html;charset=UTF-8",
    )
    tool = make_ctd_tool()

    result = tool.run({"input_terms": "TP53"})

    assert result["status"] == "error"
    assert result["error"] == (
        "CTD API blocked programmatic access with human verification"
    )
    assert result["retryable"] is False
    assert "OpenTargets" in result["suggestion"]
    assert "FAERS" in result["suggestion"]


@pytest.mark.unit
@patch("tooluniverse.ctd_tool.requests.get")
def test_ctd_request_asks_for_json(mock_get):
    """CTD requests should ask the API for JSON explicitly."""

    mock_get.return_value = make_response("[]", json_value=[])
    tool = make_ctd_tool()

    tool.run({"input_terms": "TP53"})

    assert mock_get.call_args.kwargs["headers"] == CTD_REQUEST_HEADERS


@pytest.mark.unit
@patch("tooluniverse.ctd_tool.requests.get")
def test_ctd_empty_response_reuses_metadata(mock_get):
    """Empty CTD responses should include query metadata."""

    mock_get.return_value = make_response("[]", json_value=[])
    tool = make_ctd_tool()

    result = tool.run({"input_terms": "BRCA1"})

    assert result == {
        "status": "success",
        "data": [],
        "metadata": {
            "input_type": "gene",
            "report_type": "diseases_curated",
            "query": "BRCA1",
            "total_results": 0,
        },
    }


@pytest.mark.unit
@patch("tooluniverse.ctd_tool.requests.get")
def test_ctd_non_json_response_keeps_normalized_query_metadata(mock_get):
    """Error metadata should preserve mitochondrial gene normalization details."""

    mock_get.return_value = make_response(
        "<html>temporary CTD page</html>",
        content_type="text/html;charset=UTF-8",
    )
    tool = make_ctd_tool()

    result = tool.run({"input_terms": "MT-ND5"})

    assert result["metadata"]["query"] == "MT-ND5"
    assert result["metadata"]["normalized_query"] == "ND5"
    assert "mitochondrial genes" in result["metadata"]["note"]
    assert mock_get.call_args.kwargs["params"]["inputTerms"] == "ND5"
