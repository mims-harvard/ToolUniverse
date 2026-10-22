"""Regressions for GWAS Catalog v2 start/size pagination."""

from unittest.mock import Mock

import pytest

from tooluniverse.gwas_sumstats_tool import GWASSumStatsTool

pytestmark = pytest.mark.unit


def _tool(endpoint):
    return GWASSumStatsTool(
        {"name": f"test_{endpoint}", "fields": {"endpoint_type": endpoint}}
    )


def _response(payload):
    response = Mock(status_code=200)
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


def test_list_studies_maps_start_to_page_and_reports_exact_total(monkeypatch):
    payload = {
        "_embedded": {"studies": [{"accessionId": "GCST3"}, {"accessionId": "GCST4"}]},
        "page": {"size": 2, "totalElements": 5, "totalPages": 3, "number": 1},
    }
    requested = {}

    def get(url, params, timeout):
        requested.update({"url": url, "params": params, "timeout": timeout})
        return _response(payload)

    monkeypatch.setattr("tooluniverse.gwas_sumstats_tool.requests.get", get)
    result = _tool("list_studies").run({"size": 2, "start": 2})
    assert requested["params"] == {"size": 2, "page": 1}
    assert [row["study_accession"] for row in result["data"]] == ["GCST3", "GCST4"]
    metadata = result["metadata"]
    assert metadata["total_results"] == 5
    assert metadata["total_is_exact"] is True
    assert metadata["has_more"] is True
    assert metadata["truncated"] is True
    assert metadata["next_start"] == 4


def test_last_page_has_no_next_start(monkeypatch):
    payload = {
        "_embedded": {"studies": [{"accessionId": "GCST5"}]},
        "page": {"size": 2, "totalElements": 5, "totalPages": 3, "number": 2},
    }
    monkeypatch.setattr(
        "tooluniverse.gwas_sumstats_tool.requests.get",
        lambda *args, **kwargs: _response(payload),
    )
    metadata = _tool("list_studies").run({"size": 2, "start": 4})["metadata"]
    assert metadata["has_more"] is False
    assert metadata["next_start"] is None
    assert metadata["total_results"] == 5


def test_trait_studies_forwards_page(monkeypatch):
    payload = {"_embedded": {"studies": []}, "page": {"totalElements": 3}}
    requested = {}

    def get(url, params, timeout):
        requested.update(params)
        return _response(payload)

    monkeypatch.setattr("tooluniverse.gwas_sumstats_tool.requests.get", get)
    result = _tool("get_trait_studies").run(
        {"trait": "type 2 diabetes", "size": 3, "start": 3}
    )
    assert requested == {"efoTrait": "type 2 diabetes", "size": 3, "page": 1}
    assert result["metadata"]["total_results"] == 3
    assert result["metadata"]["has_more"] is False


def test_size_above_old_silent_cap_is_forwarded(monkeypatch):
    requested = {}

    def get(url, params, timeout):
        requested.update(params)
        return _response({"_embedded": {"studies": []}, "page": {"totalElements": 0}})

    monkeypatch.setattr("tooluniverse.gwas_sumstats_tool.requests.get", get)
    _tool("list_studies").run({"size": 500})
    assert requested["size"] == 500


@pytest.mark.parametrize(
    "arguments",
    [
        {"size": 0},
        {"size": 1001},
        {"size": True},
        {"start": -1},
        {"start": 1.5},
        {"size": 10, "start": 5},
    ],
)
def test_invalid_list_pagination_is_explicit(arguments):
    result = _tool("list_studies").run(arguments)
    assert result["status"] == "error"
