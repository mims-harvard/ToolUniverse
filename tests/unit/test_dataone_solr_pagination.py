import json
from pathlib import Path
from unittest.mock import Mock, patch

from tooluniverse.base_rest_tool import BaseRESTTool


_CONFIG_PATH = Path(__file__).resolve().parents[2] / "src/tooluniverse/data/dataone_tools.json"


def _config():
    return json.loads(_CONFIG_PATH.read_text())[0]


def _response():
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "response": {
            "numFound": 122092,
            "start": 3,
            "docs": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
        }
    }
    return response


def test_dataone_exposes_exact_solr_continuation_and_default_projection():
    config = _config()
    assert config["parameter"]["properties"]["fl"]["default"] == (
        "id,title,author,dateUploaded,keywords"
    )
    tool = BaseRESTTool(config)
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry", return_value=_response()
    ) as request:
        result = tool.run({"q": "climate change", "rows": 3, "start": 3})

    assert result["metadata"]["total_results"] == 122092
    assert result["metadata"]["start"] == 3
    assert result["metadata"]["next_start"] == 6
    assert result["metadata"]["total_results_is_exact"] is True
    sent = request.call_args.kwargs["params"]
    assert sent["fl"] == "id,title,author,dateUploaded,keywords"
    assert sent["rows"] == 3 and sent["start"] == 3


def test_invalid_dataone_windows_fail_before_network():
    tool = BaseRESTTool(_config())
    with patch("tooluniverse.base_rest_tool.request_with_retry") as request:
        assert tool.run({"q": "x", "rows": 0})["status"] == "error"
        assert tool.run({"q": "x", "rows": 1001})["status"] == "error"
        assert tool.run({"q": "x", "rows": True})["status"] == "error"
        assert tool.run({"q": "x", "start": -1})["status"] == "error"
        assert tool.run({"q": "x", "start": False})["status"] == "error"
    request.assert_not_called()
