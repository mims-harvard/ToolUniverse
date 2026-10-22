import json
from pathlib import Path
from unittest.mock import Mock, patch

from tooluniverse.base_rest_tool import BaseRESTTool


_CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "src/tooluniverse/data/ceda_tools.json"
)


def _config():
    return json.loads(_CONFIG_PATH.read_text())[0]


def _response():
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "count": 3076,
        "next": "https://catalogue.ceda.ac.uk/api/v2/observations.json?abstract__icontains=climate+model&limit=3&offset=6",
        "previous": None,
        "results": [{"ob_id": 1}, {"ob_id": 2}, {"ob_id": 3}],
    }
    return response


def test_ceda_maps_q_to_explicit_icontains_field_and_exact_continuation():
    tool = BaseRESTTool(_config())
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry", return_value=_response()
    ) as request:
        result = tool.run(
            {
                "q": "climate model",
                "search_field": "abstract",
                "limit": 3,
                "offset": 3,
            }
        )

    sent = request.call_args.kwargs["params"]
    assert sent["abstract__icontains"] == "climate model"
    assert "q" not in sent and "search_field" not in sent
    assert result["metadata"]["total_results"] == 3076
    assert result["metadata"]["next_offset"] == 6
    assert result["metadata"]["applied_search_filter"] == "abstract__icontains"


def test_ceda_rejects_invalid_field_and_windows_before_network():
    tool = BaseRESTTool(_config())
    with patch("tooluniverse.base_rest_tool.request_with_retry") as request:
        assert tool.run({"q": "x", "search_field": "all"})["status"] == "error"
        assert tool.run({"limit": 0})["status"] == "error"
        assert tool.run({"limit": 101})["status"] == "error"
        assert tool.run({"offset": -1})["status"] == "error"
        assert tool.run({"offset": False})["status"] == "error"
    request.assert_not_called()
