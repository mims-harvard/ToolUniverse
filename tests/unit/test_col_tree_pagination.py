import json
from pathlib import Path
from unittest.mock import Mock, patch

from tooluniverse.base_rest_tool import BaseRESTTool


_CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "src/tooluniverse/data/col_tools.json"
)


def _config(name):
    configs = json.loads(_CONFIG_PATH.read_text())
    return next(config for config in configs if config["name"] == name)


def _response(offset=2, total=12, records=True):
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "offset": offset,
        "limit": 2,
        "total": total,
        "result": (
            [
                {
                    "id": "3JKK",
                    "parentId": "JKL",
                    "rank": "genus",
                    "status": "accepted",
                    "name": "Catopuma",
                    "authorship": "Severtzov, 1858",
                    "childCount": 2,
                },
                {
                    "id": "4JQ8",
                    "parentId": "JKL",
                    "rank": "genus",
                    "status": "accepted",
                    "name": "Felis",
                    "authorship": "Linnaeus, 1758",
                    "childCount": 7,
                },
            ]
            if records
            else []
        ),
    }
    return response


def test_children_use_real_tree_endpoint_and_exact_continuation():
    config = _config("CoL_get_children")
    assert "/tree/{parentId}/children" in config["fields"]["endpoint"]
    assert config["fields"]["pagination"] == "col_offset"

    tool = BaseRESTTool(config)
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry", return_value=_response()
    ) as request:
        result = tool.run({"parentId": "JKL", "limit": 2, "offset": 2})

    assert result["status"] == "success"
    assert result["metadata"]["total_results"] == 12
    assert result["metadata"]["next_offset"] == 4
    assert result["data"]["result"][0]["name"] == "Catopuma"
    assert request.call_args.args[2].endswith("/tree/JKL/children")


def test_empty_deep_page_does_not_trust_col_inflated_total():
    tool = BaseRESTTool(_config("CoL_get_children"))
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry",
        return_value=_response(offset=20, total=20, records=False),
    ):
        result = tool.run({"parentId": "NOPE", "limit": 2, "offset": 20})

    assert result["metadata"]["reported_total_results"] == 20
    assert result["metadata"]["total_results"] is None
    assert result["metadata"]["total_results_is_exact"] is False
    assert "inflate total" in result["metadata"]["warning"]


def test_col_search_and_children_reject_invalid_windows():
    for name, required in (
        ("CoL_search_species", {"q": "Panthera"}),
        ("CoL_get_children", {"parentId": "JKL"}),
    ):
        tool = BaseRESTTool(_config(name))
        with patch("tooluniverse.base_rest_tool.request_with_retry") as request:
            assert tool.run({**required, "limit": 1001})["status"] == "error"
            assert tool.run({**required, "limit": True})["status"] == "error"
            assert tool.run({**required, "offset": -1})["status"] == "error"
            assert tool.run({**required, "offset": False})["status"] == "error"
        request.assert_not_called()
