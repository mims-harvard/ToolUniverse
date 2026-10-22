"""Regression tests for BioSamples' official cursor pagination."""

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.biosamples_tool import BioSamplesTool
from tooluniverse.tools.BioSamples_search import BioSamples_search
from tooluniverse.tools.BioSamples_search_by_filter import (
    BioSamples_search_by_filter,
)


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


@pytest.mark.parametrize(
    ("endpoint_type", "arguments"),
    [
        ("search", {"query": "breast cancer", "limit": 101}),
        (
            "search_by_filter",
            {"attribute": "organism", "value": "Homo sapiens", "limit": 101},
        ),
    ],
)
def test_limit_above_old_fifty_record_cap_is_forwarded(endpoint_type, arguments):
    tool = BioSamplesTool(
        {"name": f"BioSamples_{endpoint_type}", "fields": {"endpoint_type": endpoint_type}}
    )
    payload = {
        "_embedded": {"samples": [{"accession": "SAMEA1"}]},
        "page": {"size": 101, "number": 0, "totalPages": 1, "totalElements": 1},
        "_links": {},
    }
    with patch(
        "tooluniverse.biosamples_tool.requests.get",
        return_value=_response(payload),
    ) as get:
        result = tool.run(arguments)

    assert get.call_args.kwargs["params"]["size"] == 101
    assert result["metadata"]["limit"] == 101


@pytest.mark.parametrize(
    ("endpoint_type", "arguments"),
    [
        ("search", {"query": "breast cancer", "limit": 3, "cursor": "*"}),
        (
            "search_by_filter",
            {
                "attribute": "organism",
                "value": "Homo sapiens",
                "limit": 3,
                "cursor": "*",
            },
        ),
    ],
)
def test_cursor_mode_exposes_opaque_next_token(endpoint_type, arguments):
    tool = BioSamplesTool(
        {"name": f"BioSamples_{endpoint_type}", "fields": {"endpoint_type": endpoint_type}}
    )
    payload = {
        "_embedded": {
            "samples": [
                {"accession": "SAMD1"},
                {"accession": "SAMD2"},
                {"accession": "SAMD3"},
            ]
        },
        "_links": {
            "next": {
                "href": "https://www.ebi.ac.uk/biosamples/samples?cursor=opaque%2Btoken&size=3"
            }
        },
    }
    with patch(
        "tooluniverse.biosamples_tool.requests.get",
        return_value=_response(payload),
    ) as get:
        result = tool.run(arguments)

    params = get.call_args.kwargs["params"]
    assert params["cursor"] == "*"
    assert "page" not in params
    assert result["metadata"]["pagination_mode"] == "cursor"
    assert result["metadata"]["next_cursor"] == "opaque+token"
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_page"] is None


def test_page_mode_warns_when_page_cap_makes_full_result_unreachable():
    tool = BioSamplesTool(
        {"name": "BioSamples_search", "fields": {"endpoint_type": "search"}}
    )
    payload = {
        "_embedded": {"samples": [{"accession": "SAMD1"}]},
        "page": {
            "size": 3,
            "number": 0,
            "totalPages": 14239,
            "totalElements": 42715,
        },
        "_links": {
            "next": {"href": "https://www.ebi.ac.uk/biosamples/samples?page=1&size=3"},
            "cursor": {
                "href": "https://www.ebi.ac.uk/biosamples/samples?cursor=*&size=3"
            },
        },
    }
    with patch(
        "tooluniverse.biosamples_tool.requests.get",
        return_value=_response(payload),
    ):
        result = tool.run({"query": "breast cancer", "limit": 3})

    metadata = result["metadata"]
    assert metadata["cursor_start"] == "*"
    assert metadata["cursor_required_for_complete_retrieval"] is True
    assert "page 500" in metadata["warning"]


@pytest.mark.parametrize(
    "arguments",
    [
        {"query": "x", "limit": 0},
        {"query": "x", "limit": 201},
        {"query": "x", "page": -1},
        {"query": "x", "page": 501},
        {"query": "x", "page": 0, "cursor": "*"},
    ],
)
def test_invalid_or_ambiguous_pagination_is_not_silently_changed(arguments):
    tool = BioSamplesTool(
        {"name": "BioSamples_search", "fields": {"endpoint_type": "search"}}
    )
    with patch("tooluniverse.biosamples_tool.requests.get") as get:
        result = tool.run(arguments)

    assert result["status"] == "error"
    get.assert_not_called()


def test_configs_and_generated_wrappers_expose_cursor():
    config_path = (
        Path(__file__).parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "biosamples_tools.json"
    )
    configs = {item["name"]: item for item in json.loads(config_path.read_text())}

    for name, wrapper in (
        ("BioSamples_search", BioSamples_search),
        ("BioSamples_search_by_filter", BioSamples_search_by_filter),
    ):
        properties = configs[name]["parameter"]["properties"]
        assert properties["limit"]["maximum"] == 200
        assert properties["page"]["maximum"] == 500
        assert "cursor" in properties
        assert "cursor" in inspect.signature(wrapper).parameters
