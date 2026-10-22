"""Regression tests for Complex Portal's reliable 500-result boundary."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.complex_portal_tool import ComplexPortalTool


def _tool():
    return ComplexPortalTool(
        {"name": "ComplexPortal_search_complexes", "fields": {"operation": "search_complexes"}}
    )


def test_500_is_forwarded_without_old_100_result_cap():
    response = MagicMock()
    response.json.return_value = {"elements": [], "totalNumberOfResults": 19311}
    response.raise_for_status.return_value = None
    with patch(
        "tooluniverse.complex_portal_tool.requests.get", return_value=response
    ) as get:
        result = _tool().run({"query": "protein", "species": "", "number": 500})

    assert result["status"] == "success"
    assert get.call_args.kwargs["params"]["number"] == 500
    assert result["data"]["number"] == 500


@pytest.mark.parametrize(
    "arguments",
    [
        {"query": "protein", "number": 0},
        {"query": "protein", "number": 501},
        {"query": "protein", "first": -1},
        {"query": "protein", "number": 1.5},
        {"query": "protein", "first": True},
    ],
)
def test_invalid_pagination_errors_instead_of_being_changed(arguments):
    with patch("tooluniverse.complex_portal_tool.requests.get") as get:
        result = _tool().run(arguments)

    assert result["status"] == "error"
    get.assert_not_called()


def test_config_uses_verified_boundary():
    config_path = (
        Path(__file__).parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "complex_portal_tools.json"
    )
    configs = {item["name"]: item for item in json.loads(config_path.read_text())}
    number = configs["ComplexPortal_search_complexes"]["parameter"]["properties"]["number"]

    assert number["minimum"] == 1
    assert number["maximum"] == 500
