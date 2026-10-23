import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool


_CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "src/tooluniverse/data/biotools_registry_tools.json"
)


def _config(name):
    configs = json.loads(_CONFIG_PATH.read_text())
    return next(config for config in configs if config["name"] == name)


def _response():
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "count": 275,
        "next": "?page=3",
        "previous": "?page=1",
        "list": [{"biotoolsID": "a"}, {"biotoolsID": "b"}, {"biotoolsID": "c"}],
    }
    return response


@pytest.mark.parametrize(
    "name,args,filter_key",
    [
        ("BioTools_search", {"q": "blast"}, "q"),
        ("BioTools_search_by_topic", {"topic": "Proteomics"}, "topic"),
        (
            "BioTools_search_by_operation",
            {"operation": "Sequence alignment"},
            "operation",
        ),
        ("BioTools_search_by_type", {"toolType": "Web API"}, "toolType"),
    ],
)
def test_biotools_uses_real_per_page_and_rebuilds_filter_preserving_next_url(
    name, args, filter_key
):
    tool = BaseRESTTool(_config(name))
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry", return_value=_response()
    ) as request:
        result = tool.run({**args, "page": 2, "size": 3, "format": "json"})

    sent = request.call_args.kwargs["params"]
    assert sent["per_page"] == 3
    assert "size" not in sent
    assert result["metadata"]["total_results"] == 275
    assert result["metadata"]["total_pages"] == 92
    assert result["metadata"]["next_page"] == 3
    assert result["metadata"]["upstream_next"] == "?page=3"
    assert result["metadata"]["upstream_links_drop_filters"] is True
    assert result["metadata"]["continuation_parameters"][filter_key] == args[filter_key]
    assert result["metadata"]["continuation_parameters"]["per_page"] == 3
    assert f"{filter_key}=" in result["data"]["next"]


def test_biotools_rejects_values_upstream_would_ignore_or_coerce():
    tool = BaseRESTTool(_config("BioTools_search"))
    with patch("tooluniverse.base_rest_tool.request_with_retry") as request:
        assert tool.run({"q": "x", "page": 0})["status"] == "error"
        assert tool.run({"q": "x", "page": True})["status"] == "error"
        assert tool.run({"q": "x", "size": 101})["status"] == "error"
        assert tool.run({"q": "x", "size": False})["status"] == "error"
        assert tool.run({"q": "x", "format": "xml"})["status"] == "error"
    request.assert_not_called()
