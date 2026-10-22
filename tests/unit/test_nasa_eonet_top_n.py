import json
from pathlib import Path
from unittest.mock import Mock, patch

from tooluniverse.base_rest_tool import BaseRESTTool


_CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "src/tooluniverse/data/nasa_eonet_tools.json"
)


def _config():
    configs = json.loads(_CONFIG_PATH.read_text())
    return next(config for config in configs if config["name"] == "NASAEONET_get_events")


def _response(count):
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "title": "EONET Events",
        "events": [{"id": f"EONET_{i}"} for i in range(count)],
    }
    return response


def test_eonet_uses_lookahead_and_does_not_claim_full_top_n_is_complete():
    tool = BaseRESTTool(_config())
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry", return_value=_response(4)
    ) as request:
        result = tool.run({"status": "OPEN", "category": "wildfires", "limit": 3})

    assert len(result["data"]["events"]) == 3
    assert result["metadata"]["total_results"] is None
    assert result["metadata"]["matches_lower_bound"] == 4
    assert result["metadata"]["upstream_truncated"] is True
    assert result["metadata"]["pagination_supported"] is False
    sent = request.call_args.kwargs["params"]
    assert sent["limit"] == 4
    assert sent["status"] == "open"


def test_short_eonet_page_has_exact_total_and_is_complete():
    tool = BaseRESTTool(_config())
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry", return_value=_response(2)
    ):
        result = tool.run({"category": "volcanoes", "limit": 3})

    assert result["metadata"]["total_results"] == 2
    assert result["metadata"]["total_results_is_exact"] is True
    assert result["metadata"]["result_set_complete"] is True


def test_eonet_rejects_filters_upstream_would_silently_ignore():
    tool = BaseRESTTool(_config())
    with patch("tooluniverse.base_rest_tool.request_with_retry") as request:
        assert tool.run({"status": "bogus"})["status"] == "error"
        assert tool.run({"category": "bogus"})["status"] == "error"
        assert tool.run({"limit": 0})["status"] == "error"
        assert tool.run({"limit": True})["status"] == "error"
        assert tool.run({"limit": 1001})["status"] == "error"
    request.assert_not_called()
