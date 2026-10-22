import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool


_CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "src/tooluniverse/data/identifiers_org_tools.json"
)


def _config(name):
    configs = json.loads(_CONFIG_PATH.read_text())
    return next(config for config in configs if config["name"] == name)


def _response(page=1, size=3, total=30):
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "_embedded": {
            "namespaces": [
                {"prefix": "unigene"},
                {"prefix": "tair.gene"},
                {"prefix": "ncbigene"},
            ]
        },
        "page": {
            "size": size,
            "totalElements": total,
            "totalPages": 10,
            "number": page,
        },
    }
    return response


@pytest.mark.parametrize(
    "name,args",
    [
        ("IdentifiersOrg_search_namespaces", {"content": "gene"}),
        ("IdentifiersOrg_list_namespaces", {}),
    ],
)
def test_identifiers_org_uses_exact_spring_page_metadata(name, args):
    tool = BaseRESTTool(_config(name))
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry", return_value=_response()
    ) as request:
        result = tool.run({**args, "page": 1, "size": 3})

    assert result["status"] == "success"
    assert result["metadata"]["returned"] == 3
    assert result["metadata"]["total_results"] == 30
    assert result["metadata"]["total_pages"] == 10
    assert result["metadata"]["page"] == 1
    assert result["metadata"]["next_page"] == 2
    sent = request.call_args.kwargs["params"]
    assert sent["page"] == 1 and sent["size"] == 3


def test_invalid_spring_pages_are_not_silently_coerced_by_upstream():
    tool = BaseRESTTool(_config("IdentifiersOrg_list_namespaces"))
    with patch("tooluniverse.base_rest_tool.request_with_retry") as request:
        assert tool.run({"page": -1})["status"] == "error"
        assert tool.run({"page": True})["status"] == "error"
        assert tool.run({"size": 0})["status"] == "error"
        assert tool.run({"size": 1001})["status"] == "error"
        assert tool.run({"size": False})["status"] == "error"
    request.assert_not_called()
