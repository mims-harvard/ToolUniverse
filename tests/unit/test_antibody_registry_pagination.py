"""Regression tests for Antibody Registry search pagination."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.antibody_registry_tool import AntibodyRegistryTool


def _tool():
    return AntibodyRegistryTool(
        {"name": "AntibodyRegistry_search", "fields": {"operation": "search"}}
    )


def _response(payload):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = payload
    return response


def test_search_forwards_official_500_max_and_reports_next_page():
    payload = {
        "items": [{"abId": index} for index in range(500)],
        "page": 1,
        "totalElements": 2351,
    }
    with patch(
        "tooluniverse.antibody_registry_tool.requests.get",
        return_value=_response(payload),
    ) as get:
        result = _tool().run({"query": "GFAP", "size": 500, "page": 1})

    assert get.call_args.kwargs["params"]["size"] == 500
    assert len(result["data"]) == 500
    assert result["metadata"] == {
        "source": "Antibody Registry (antibodyregistry.org)",
        "query": "GFAP",
        "total_matches": 2351,
        "total_pages": 5,
        "returned": 500,
        "size": 500,
        "page": 1,
        "has_more": True,
        "truncated": True,
        "next_page": 2,
    }


def test_last_page_is_marked_complete():
    payload = {
        "items": [{"abId": 2351}],
        "page": 5,
        "totalElements": 2351,
    }
    with patch(
        "tooluniverse.antibody_registry_tool.requests.get",
        return_value=_response(payload),
    ):
        result = _tool().run({"query": "GFAP", "size": 500, "page": 5})

    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["truncated"] is False
    assert result["metadata"]["next_page"] is None


@pytest.mark.parametrize(
    "arguments",
    [
        {"query": "GFAP", "size": 0},
        {"query": "GFAP", "size": 501},
        {"query": "GFAP", "page": 0},
        {"query": "GFAP", "page": -1},
        {"query": "GFAP", "size": 1.5},
    ],
)
def test_invalid_pagination_errors_instead_of_being_changed(arguments):
    with patch("tooluniverse.antibody_registry_tool.requests.get") as get:
        result = _tool().run(arguments)

    assert result["status"] == "error"
    get.assert_not_called()


def test_config_matches_real_api_limit_and_documents_navigation():
    config_path = (
        Path(__file__).parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "antibody_registry_tools.json"
    )
    configs = {item["name"]: item for item in json.loads(config_path.read_text())}
    search = configs["AntibodyRegistry_search"]

    assert search["parameter"]["properties"]["size"]["maximum"] == 500
    assert "next_page" in search["description"]
