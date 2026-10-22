import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool


_CONFIG_PATH = Path(__file__).resolve().parents[2] / "src/tooluniverse/data/idr_tools.json"


def _config(name):
    configs = json.loads(_CONFIG_PATH.read_text())
    return next(config for config in configs if config["name"] == name)


def _response(offset=2, limit=2, total=7):
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "data": [{"@id": offset}, {"@id": offset + 1}],
        "meta": {
            "offset": offset,
            "limit": limit,
            "maxLimit": 1000,
            "totalCount": total,
        },
    }
    return response


@pytest.mark.parametrize(
    "name,args",
    [
        ("IDR_list_studies", {}),
        ("IDR_get_study_datasets", {"project_id": 101}),
        ("IDR_list_dataset_images", {"dataset_id": 51}),
    ],
)
def test_idr_hierarchy_tools_expose_exact_meta_continuation(name, args):
    tool = BaseRESTTool(_config(name))
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry", return_value=_response()
    ) as request:
        result = tool.run({**args, "limit": 2, "offset": 2})

    assert result["status"] == "success"
    assert result["metadata"]["returned"] == 2
    assert result["metadata"]["total_results"] == 7
    assert result["metadata"]["total_results_is_exact"] is True
    assert result["metadata"]["next_offset"] == 4
    assert result["metadata"]["max_limit"] == 1000
    sent = request.call_args.kwargs["params"]
    assert sent["limit"] == 2
    assert sent["offset"] == 2


def test_idr_schema_and_wrappers_now_share_real_defaults():
    for name in (
        "IDR_list_studies",
        "IDR_get_study_datasets",
        "IDR_list_dataset_images",
    ):
        props = _config(name)["parameter"]["properties"]
        assert props["limit"]["default"] == 25
        assert props["offset"]["default"] == 0
        assert props["limit"]["maximum"] == 1000
        assert _config(name)["fields"]["pagination"] == "idr_meta_offset"


def test_invalid_idr_pages_fail_before_network():
    tool = BaseRESTTool(_config("IDR_list_studies"))
    with patch("tooluniverse.base_rest_tool.request_with_retry") as request:
        assert tool.run({"limit": 0})["status"] == "error"
        assert tool.run({"limit": True})["status"] == "error"
        assert tool.run({"offset": -1})["status"] == "error"
        assert tool.run({"offset": False})["status"] == "error"
    request.assert_not_called()
