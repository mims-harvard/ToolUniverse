"""Regression tests for UniParc's official search page-size boundary."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.uniparc_tool import UniParcTool


def _tool():
    return UniParcTool(
        {"name": "UniParc_search", "fields": {"endpoint": "search"}}
    )


def test_official_500_size_is_forwarded_without_old_ten_record_cap():
    response = MagicMock()
    response.json.return_value = {"results": [{"uniParcId": "UPI1"}]}
    response.headers = {"x-total-results": "1000"}
    response.raise_for_status.return_value = None
    with patch(
        "tooluniverse.uniparc_tool.requests.get", return_value=response
    ) as get:
        result = _tool().run({"query": "gene:TP53", "size": 500})

    assert result["status"] == "success"
    assert get.call_args.kwargs["params"]["size"] == 500


@pytest.mark.parametrize("size", [0, 501, -1, True, 1.5, "bad"])
def test_invalid_sizes_error_before_request(size):
    with patch("tooluniverse.uniparc_tool.requests.get") as get:
        result = _tool().run({"query": "gene:TP53", "size": size})

    assert result["status"] == "error"
    assert "1 to 500" in result["error"]
    get.assert_not_called()


def test_config_matches_official_limit():
    config_path = (
        Path(__file__).parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "uniparc_tools.json"
    )
    configs = {item["name"]: item for item in json.loads(config_path.read_text())}
    size = configs["UniParc_search"]["parameter"]["properties"]["size"]

    assert size["minimum"] == 1
    assert size["maximum"] == 500
