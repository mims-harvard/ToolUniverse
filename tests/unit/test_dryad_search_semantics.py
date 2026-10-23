import json
from pathlib import Path
from unittest.mock import Mock, patch

from tooluniverse.base_rest_tool import BaseRESTTool


_CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "src/tooluniverse/data/dryad_tools.json"
)


def _config():
    configs = json.loads(_CONFIG_PATH.read_text())
    return next(
        config for config in configs if config["name"] == "Dryad_search_datasets"
    )


def _files_config():
    configs = json.loads(_CONFIG_PATH.read_text())
    return next(
        config for config in configs if config["name"] == "Dryad_get_dataset_files"
    )


def _response():
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "count": 3,
        "total": 6968,
        "_links": {
            "next": {"href": "/api/v2/search?page=3&per_page=3&q=climate+change"}
        },
        "_embedded": {
            "stash:datasets": [
                {"id": 158763},
                {"id": 160338},
                {"id": 169400},
            ]
        },
    }
    return response


def test_dryad_uses_real_search_endpoint_and_exact_hal_continuation():
    config = _config()
    assert config["fields"]["endpoint"].endswith("/api/v2/search")
    assert not config["fields"]["endpoint"].endswith("/datasets")

    tool = BaseRESTTool(config)
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry", return_value=_response()
    ) as request:
        result = tool.run({"q": "climate change", "per_page": 3, "page": 2})

    assert result["status"] == "success"
    assert result["metadata"]["returned"] == 3
    assert result["metadata"]["total_results"] == 6968
    assert result["metadata"]["total_pages"] == 2323
    assert result["metadata"]["next_page"] == 3
    assert result["metadata"]["next_url"].startswith("/api/v2/search")
    assert result["metadata"]["embedded_record_key"] == "stash:datasets"
    sent = request.call_args.kwargs["params"]
    assert sent == {"q": "climate change", "per_page": 3, "page": 2}


def test_dryad_rejects_values_upstream_would_silently_coerce():
    tool = BaseRESTTool(_config())
    with patch("tooluniverse.base_rest_tool.request_with_retry") as request:
        assert tool.run({"q": "x", "page": 0})["status"] == "error"
        assert tool.run({"q": "x", "page": True})["status"] == "error"
        assert tool.run({"q": "x", "per_page": 101})["status"] == "error"
        assert tool.run({"q": "x", "per_page": False})["status"] == "error"
    request.assert_not_called()


def test_dryad_file_listing_uses_file_records_for_exact_continuation():
    response = Mock(status_code=200)
    response.json.return_value = {
        "count": 3,
        "total": 58,
        "_links": {"next": {"href": "/api/v2/versions/104/files?page=2&per_page=3"}},
        "_embedded": {
            "stash:files": [
                {"id": 1, "path": "a.tif"},
                {"id": 2, "path": "b.tif"},
                {"id": 3, "path": "c.tif"},
            ]
        },
    }
    tool = BaseRESTTool(_files_config())

    with patch(
        "tooluniverse.base_rest_tool.request_with_retry", return_value=response
    ) as request:
        result = tool.run({"version_id": 104, "per_page": 3, "page": 1})

    assert result["status"] == "success"
    assert result["metadata"]["returned"] == 3
    assert result["metadata"]["total_results"] == 58
    assert result["metadata"]["total_pages"] == 20
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_page"] == 2
    assert result["metadata"]["embedded_record_key"] == "stash:files"
    assert request.call_args.kwargs["params"] == {"per_page": 3, "page": 1}


def test_dryad_file_listing_rejects_silent_page_coercion():
    tool = BaseRESTTool(_files_config())
    with patch("tooluniverse.base_rest_tool.request_with_retry") as request:
        assert tool.run({"version_id": 104, "page": 0})["parameter"] == "page"
        assert tool.run({"version_id": 104, "per_page": 101})["parameter"] == "per_page"
    request.assert_not_called()
