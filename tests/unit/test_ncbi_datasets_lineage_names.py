"""Regression guard for Fix-R12B-1: NCBIDatasets_get_taxonomy's `lineage`
field is a bare list of ancestor tax_ids with no names or ranks attached --
confirmed this is exactly what NCBI's own Datasets v2 API returns (not
something dropped by this tool), and that NCBI's endpoint accepts a
comma-joined batch of tax_ids in a single extra request. `lineage_names`
resolves the whole lineage's organism_name/rank in one additional call
rather than one call per ancestor, without changing the existing `lineage`
field's shape (still bare ints, for backward compatibility).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.ncbi_datasets_tool import NCBIDatasetsTool

pytestmark = pytest.mark.unit


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def _tool():
    return NCBIDatasetsTool(
        {
            "name": "NCBIDatasets_get_taxonomy",
            "fields": {"endpoint_type": "taxonomy"},
        }
    )


PRIMARY_NODE_RESPONSE = {
    "taxonomy_nodes": [
        {
            "taxonomy": {
                "tax_id": 9601,
                "organism_name": "Pongo abelii",
                "genbank_common_name": "Sumatran orangutan",
                "rank": "SPECIES",
                "blast_name": "primates",
                "lineage": [9604, 9599],
                "children": [],
                "counts": [],
            }
        }
    ]
}

LINEAGE_ENRICHMENT_RESPONSE = {
    "taxonomy_nodes": [
        {"taxonomy": {"tax_id": 9604, "organism_name": "Hominidae", "rank": "FAMILY"}},
        {"taxonomy": {"tax_id": 9599, "organism_name": "Pongo", "rank": "GENUS"}},
    ]
}


def test_lineage_names_enriched_in_root_first_order(monkeypatch):
    tool = _tool()
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            return _FakeResponse(200, PRIMARY_NODE_RESPONSE)
        return _FakeResponse(200, LINEAGE_ENRICHMENT_RESPONSE)

    monkeypatch.setattr("tooluniverse.ncbi_datasets_tool.requests.get", fake_get)

    result = tool.run({"tax_id": "9601"})

    assert result["status"] == "success"
    assert result["data"]["lineage"] == [9604, 9599]
    assert result["data"]["lineage_names"] == [
        {"tax_id": 9604, "organism_name": "Hominidae", "rank": "FAMILY"},
        {"tax_id": 9599, "organism_name": "Pongo", "rank": "GENUS"},
    ]
    # Enrichment call batches all ancestor tax_ids into one comma-joined request.
    assert "9604,9599" in calls[1]


def test_lineage_names_empty_for_root_with_no_ancestors(monkeypatch):
    tool = _tool()
    root_response = {
        "taxonomy_nodes": [
            {
                "taxonomy": {
                    "tax_id": 1,
                    "organism_name": "root",
                    "rank": "NO RANK",
                    "lineage": [],
                }
            }
        ]
    }

    def fake_get(url, **kwargs):
        return _FakeResponse(200, root_response)

    monkeypatch.setattr("tooluniverse.ncbi_datasets_tool.requests.get", fake_get)

    result = tool.run({"tax_id": "1"})

    assert result["data"]["lineage_names"] == []


def test_lineage_names_degrades_gracefully_on_enrichment_failure(monkeypatch):
    tool = _tool()
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            return _FakeResponse(200, PRIMARY_NODE_RESPONSE)
        raise __import__("requests").exceptions.ConnectionError("boom")

    monkeypatch.setattr("tooluniverse.ncbi_datasets_tool.requests.get", fake_get)

    result = tool.run({"tax_id": "9601"})

    # The primary lookup already succeeded; enrichment failure must not
    # fail the whole tool call, and the bare-id `lineage` stays intact.
    assert result["status"] == "success"
    assert result["data"]["lineage"] == [9604, 9599]
    assert result["data"]["lineage_names"] == []


def test_lineage_names_falls_back_per_id_when_partially_resolved(monkeypatch):
    tool = _tool()
    calls = []
    partial_response = {
        "taxonomy_nodes": [
            {"taxonomy": {"tax_id": 9604, "organism_name": "Hominidae", "rank": "FAMILY"}}
        ]
    }

    def fake_get(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            return _FakeResponse(200, PRIMARY_NODE_RESPONSE)
        return _FakeResponse(200, partial_response)

    monkeypatch.setattr("tooluniverse.ncbi_datasets_tool.requests.get", fake_get)

    result = tool.run({"tax_id": "9601"})

    assert result["data"]["lineage_names"] == [
        {"tax_id": 9604, "organism_name": "Hominidae", "rank": "FAMILY"},
        {"tax_id": 9599, "organism_name": None, "rank": None},
    ]
