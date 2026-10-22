"""Regressions for GWAS Summary Statistics HAL start pagination."""

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


def test_list_studies_forwards_start_and_exposes_hal_next(monkeypatch):
    payload = {
        "_embedded": {
            "studies": [[{"study_accession": "GCST3"}], [{"study_accession": "GCST4"}]]
        },
        "_links": {"next": {"href": "http://example.test/studies?start=4&size=2"}},
    }
    requested = {}

    def get(url, params, timeout):
        requested.update({"url": url, "params": params, "timeout": timeout})
        return _response(payload)

    monkeypatch.setattr("tooluniverse.gwas_sumstats_tool.requests.get", get)
    result = _tool("list_studies").run({"size": 2, "start": 2})
    assert requested["params"] == {"size": 2, "start": 2}
    assert [row["study_accession"] for row in result["data"]] == ["GCST3", "GCST4"]
    assert result["metadata"]["total_results"] is None
    assert result["metadata"]["total_is_exact"] is False
    assert result["metadata"]["matches_lower_bound"] == 5
    assert result["metadata"]["next_start"] == 4
    assert result["metadata"]["navigation_repaired"] is False


def test_non_monotonic_hal_next_is_repaired(monkeypatch):
    payload = {
        "_embedded": {"studies": [{"study_accession": "GCST4"}]},
        "_links": {"next": {"href": "http://example.test/studies?start=3&size=1"}},
    }
    monkeypatch.setattr(
        "tooluniverse.gwas_sumstats_tool.requests.get",
        lambda *args, **kwargs: _response(payload),
    )
    metadata = _tool("list_studies").run({"size": 1, "start": 3})["metadata"]
    assert metadata["upstream_next_start"] == 3
    assert metadata["next_start"] == 4
    assert metadata["navigation_repaired"] is True


def test_region_forwards_start_and_preserves_upstream_order(monkeypatch):
    payload = {
        "_embedded": {
            "associations": {
                "0": {"variant_id": "rs-high", "p_value": 0.5},
                "1": {"variant_id": "rs-low", "p_value": 1e-9},
            }
        },
        "_links": {},
    }
    requested = {}

    def get(url, params, timeout):
        requested.update(params)
        return _response(payload)

    monkeypatch.setattr("tooluniverse.gwas_sumstats_tool.requests.get", get)
    result = _tool("get_region_associations").run(
        {"chromosome": 9, "bp_lower": 1, "bp_upper": 2, "size": 2, "start": 4}
    )
    assert requested["start"] == 4
    assert [row["variant_id"] for row in result["data"]] == ["rs-high", "rs-low"]
    assert result["metadata"]["total_results"] == 6
    assert result["metadata"]["total_is_exact"] is True
    assert result["metadata"]["has_more"] is False


def test_trait_studies_forwards_start(monkeypatch):
    payload = {"_embedded": {"studies": []}, "_links": {}}
    requested = {}

    def get(url, params, timeout):
        requested.update(params)
        return _response(payload)

    monkeypatch.setattr("tooluniverse.gwas_sumstats_tool.requests.get", get)
    result = _tool("get_trait_studies").run(
        {"trait_id": "EFO_0001359", "size": 3, "start": 3}
    )
    assert requested == {"size": 3, "start": 3}
    assert result["metadata"]["total_results"] == 3


@pytest.mark.parametrize(
    "arguments",
    [
        {"size": 0},
        {"size": 1001},
        {"size": True},
        {"start": -1},
        {"start": 1.5},
    ],
)
def test_invalid_list_pagination_is_explicit(arguments):
    result = _tool("list_studies").run(arguments)
    assert result["status"] == "error"
