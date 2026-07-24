"""Unit tests for BioModels REST response handling."""

from unittest.mock import MagicMock

from tooluniverse.biomodels_tool import BioModelsRESTTool


def _tool():
    return BioModelsRESTTool(
        {
            "name": "biomodels_search",
            "fields": {"endpoint": "https://www.ebi.ac.uk/biomodels/search"},
        }
    )


def test_biomodels_non_json_response_returns_diagnostic():
    response = MagicMock()
    response.json.side_effect = ValueError("not json")
    response.text = "<html>Moved</html>"
    response.headers = {"Content-Type": "text/html"}

    result = _tool()._process_response(response, "https://example.test")

    assert result["status"] == "error"
    assert "non-JSON" in result["error"]
    assert result["content_type"] == "text/html"
    assert result["response_snippet"] == "<html>Moved</html>"
    assert result["retryable"] is True
    assert "BioModels" in result["suggestion"]
