from unittest.mock import Mock, patch

import pytest

from tooluniverse.epigenomics_tool import EpigenomicsTool


pytestmark = pytest.mark.unit

_ENDPOINTS = (
    "geo_methylation_search",
    "geo_chipseq_search",
    "geo_rnaseq_search",
    "geo_atacseq_search",
)


def _tool(endpoint):
    return EpigenomicsTool({"name": endpoint, "fields": {"endpoint": endpoint}})


@pytest.mark.parametrize("endpoint", _ENDPOINTS)
def test_geo_searches_use_gse_filter_and_expose_exact_continuation(endpoint):
    search = {
        "esearchresult": {
            "count": "5",
            "idlist": ["401", "402"],
        }
    }
    summary = {
        "result": {
            "401": {
                "accession": "GSE401",
                "title": "series",
                "summary": "summary",
                "taxon": "Homo sapiens",
                "n_samples": 4,
            },
            # Defensive regression: an unexpected GSM must never be presented
            # as a dataset, and its omission must be quantified.
            "402": {
                "accession": "GSM402",
                "title": "sample",
            },
        }
    }
    tool = _tool(endpoint)
    with (
        patch.object(tool, "_geo_esearch", return_value=search) as esearch,
        patch.object(tool, "_geo_esummary", return_value=summary),
    ):
        result = tool.run(
            {"query": "cancer", "organism": "Homo sapiens", "limit": 2, "offset": 2}
        )

    term, limit, offset = esearch.call_args.args
    assert "gse[ETYP]" in term
    assert limit == 2
    assert offset == 2
    assert [item["accession"] for item in result["data"]["datasets"]] == ["GSE401"]
    assert result["data"]["total"] == 5
    assert result["data"]["candidate_returned"] == 2
    assert result["data"]["returned"] == 1
    assert result["data"]["omitted_records"] == 1
    assert result["data"]["has_more"] is True
    assert result["data"]["next_offset"] == 4


def test_geo_esearch_forwards_offset_to_ncbi():
    response = Mock()
    response.json.return_value = {"esearchresult": {"count": "1", "idlist": ["1"]}}
    tool = _tool("geo_rnaseq_search")

    with patch(
        "tooluniverse.epigenomics_tool._request_with_backoff", return_value=response
    ) as request:
        tool._geo_esearch("RNA-seq AND gse[ETYP]", 7, 14)

    params = request.call_args.kwargs["params"]
    assert params["retmax"] == 7
    assert params["retstart"] == 14
    response.raise_for_status.assert_called_once()


@pytest.mark.parametrize("endpoint", _ENDPOINTS)
@pytest.mark.parametrize("limit", [0, 101, True, 1.5, "20"])
def test_geo_searches_reject_invalid_limits_before_network(endpoint, limit):
    tool = _tool(endpoint)
    with patch.object(tool, "_geo_esearch") as request:
        result = tool.run({"query": "cancer", "limit": limit})

    assert result["status"] == "error"
    assert result["parameter"] == "limit"
    request.assert_not_called()


@pytest.mark.parametrize("endpoint", _ENDPOINTS)
@pytest.mark.parametrize("offset", [-1, True, 1.5, "2"])
def test_geo_searches_reject_invalid_offsets_before_network(endpoint, offset):
    tool = _tool(endpoint)
    with patch.object(tool, "_geo_esearch") as request:
        result = tool.run({"query": "cancer", "offset": offset})

    assert result["status"] == "error"
    assert result["parameter"] == "offset"
    request.assert_not_called()
