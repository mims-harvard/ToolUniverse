"""Regression tests for NCBI genome-by-taxon continuation pagination."""

from unittest.mock import Mock

import pytest

from tooluniverse.ncbi_datasets_tool import NCBIDatasetsTool

pytestmark = pytest.mark.unit


def _tool():
    return NCBIDatasetsTool(
        {
            "name": "NCBIDatasets_list_genomes_by_taxon",
            "fields": {"endpoint_type": "genomes_by_taxon"},
        }
    )


def test_continuation_token_is_forwarded_and_returned(monkeypatch):
    response = Mock(status_code=200, headers={})
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "reports": [
            {
                "accession": "GCF_000005845.2",
                "organism": {"organism_name": "Escherichia coli", "tax_id": 562},
                "assembly_info": {},
                "assembly_stats": {},
            }
        ],
        "total_count": 482062,
        "next_page_token": "next-opaque-token",
    }
    requested = {}

    def get(url, **kwargs):
        requested.update({"url": url, **kwargs})
        return response

    monkeypatch.setattr("tooluniverse.ncbi_datasets_tool.requests.get", get)
    result = _tool().run({"taxon": "562", "limit": 101, "page_token": "previous-token"})

    assert requested["params"] == {
        "page_size": 101,
        "page_token": "previous-token",
    }
    assert result["metadata"]["total_available"] == 482062
    assert result["metadata"]["page_token_used"] == "previous-token"
    assert result["metadata"]["next_page_token"] == "next-opaque-token"
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["truncated"] is True


def test_last_page_is_reported_complete(monkeypatch):
    response = Mock(status_code=200, headers={})
    response.raise_for_status.return_value = None
    response.json.return_value = {"reports": [], "total_count": 0}
    monkeypatch.setattr(
        "tooluniverse.ncbi_datasets_tool.requests.get",
        lambda *args, **kwargs: response,
    )
    metadata = _tool().run({"taxon": "9606"})["metadata"]
    assert metadata["next_page_token"] is None
    assert metadata["has_more"] is False
    assert metadata["truncated"] is False


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"taxon": "562", "limit": 0}, "limit must be"),
        ({"taxon": "562", "limit": 1001}, "limit must be"),
        ({"taxon": "562", "limit": "100"}, "limit must be"),
        ({"taxon": "562", "limit": True}, "limit must be"),
        ({"taxon": "562", "page_token": "   "}, "page_token must be"),
        ({"taxon": "562", "page_token": 123}, "page_token must be"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, message):
    result = _tool().run(arguments)
    assert result["status"] == "error"
    assert message in result["error"]


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"gene_id": "7157", "page_size": 0}, "page_size must be"),
        ({"gene_id": "7157", "page_size": 1001}, "page_size must be"),
        ({"gene_id": "7157", "offset": -1}, "offset must be"),
        ({"gene_id": "7157", "offset": True}, "offset must be"),
    ],
)
def test_invalid_ortholog_local_pagination_is_explicit(arguments, message):
    tool = NCBIDatasetsTool(
        {
            "name": "NCBIDatasets_get_orthologs",
            "fields": {"endpoint_type": "gene_orthologs"},
        }
    )
    result = tool.run(arguments)
    assert result["status"] == "error"
    assert message in result["error"]
