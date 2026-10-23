"""Regression tests for complete ProteomeXchange local search pagination."""

from unittest.mock import Mock

import pytest

from tooluniverse.proteomexchange_tool import ProteomeXchangeTool

pytestmark = pytest.mark.unit


def _tool():
    return ProteomeXchangeTool(
        {
            "name": "ProteomeXchange_search_datasets",
            "fields": {"endpoint_type": "search_datasets"},
            "parameter": {"properties": {}},
        }
    )


def _response(records):
    response = Mock()
    response.json.return_value = records
    response.raise_for_status.return_value = None
    return response


def test_search_filters_full_catalog_then_applies_offset(monkeypatch):
    records = [
        {
            "Dataset Identifier": f'<a href="x">PXD00000{i}</a>',
            "Title": f"Cancer study {i}",
            "Species": "Homo sapiens",
            "Keywords": "tumor proteomics",
            "LabHead": "Researcher",
        }
        for i in range(6)
    ]
    requested = {}

    def get(url, params, timeout):
        requested.update({"url": url, "params": params, "timeout": timeout})
        return _response(records)

    monkeypatch.setattr("tooluniverse.proteomexchange_tool.requests.get", get)
    result = _tool().run({"query": "cancer", "limit": 2, "offset": 2})

    assert requested["params"]["keyword"] == "cancer"
    assert [item["accession"] for item in result["data"]] == [
        "PXD000002",
        "PXD000003",
    ]
    assert result["metadata"] == {
        "source": "ProteomeXchange/ProteomeCentral",
        "total_matches": 6,
        "total_returned": 2,
        "limit": 2,
        "offset": 2,
        "has_more": True,
        "truncated": True,
        "next_offset": 4,
        "total_is_exact": True,
        "query": "cancer",
        "endpoint": "search_datasets",
        "filtering": "client_side_full_catalog",
    }


def test_search_matches_accession_and_non_title_metadata(monkeypatch):
    records = [
        {
            "Dataset Identifier": '<a href="x">PXD123456</a>',
            "Title": "Unrelated title",
            "Species": "Mus musculus",
            "Keywords": "rare-disease-marker",
        }
    ]
    monkeypatch.setattr(
        "tooluniverse.proteomexchange_tool.requests.get",
        lambda *args, **kwargs: _response(records),
    )

    assert _tool().run({"query": "PXD123456"})["data"][0]["accession"] == "PXD123456"
    assert (
        _tool().run({"query": "rare-disease-marker"})["metadata"]["total_matches"] == 1
    )


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"limit": 0}, "limit must be"),
        ({"limit": 1001}, "limit must be"),
        ({"limit": True}, "limit must be"),
        ({"offset": -1}, "offset must be"),
        ({"offset": 1.5}, "offset must be"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, message):
    result = _tool().run(arguments)
    assert result["status"] == "error"
    assert message in result["error"]
