from unittest.mock import patch

import pytest

from tooluniverse.dbsnp_tool import dbSNPSearchByGene


pytestmark = pytest.mark.unit


def _reply(ids=("103", "104"), count="5"):
    return {
        "status": "success",
        "data": {
            "esearchresult": {
                "count": count,
                "retmax": "2",
                "retstart": "2",
                "idlist": list(ids),
            }
        },
    }


def test_gene_search_forwards_offset_and_exposes_exact_continuation():
    tool = dbSNPSearchByGene({"name": "dbsnp_search_by_gene"})
    with patch.object(tool, "_make_request", return_value=_reply()) as request:
        result = tool.run({"gene_symbol": "BRCA1", "limit": 2, "offset": 2})

    params = request.call_args.args[1]
    assert params["retmax"] == 2
    assert params["retstart"] == 2
    assert result["data"] == {
        "variants": [
            {"refsnp_id": "rs103", "snp_id": 103},
            {"refsnp_id": "rs104", "snp_id": 104},
        ],
        "total_count": 5,
        "returned_count": 2,
        "offset": 2,
        "limit": 2,
        "has_more": True,
        "next_offset": 4,
        "truncated": True,
    }


def test_gene_search_marks_last_and_out_of_range_pages_complete():
    tool = dbSNPSearchByGene({"name": "dbsnp_search_by_gene"})
    with patch.object(tool, "_make_request", return_value=_reply(("105",), "5")):
        last = tool.run({"gene_symbol": "BRCA1", "limit": 2, "offset": 4})
    with patch.object(tool, "_make_request", return_value=_reply((), "5")):
        beyond = tool.run({"gene_symbol": "BRCA1", "limit": 2, "offset": 8})

    assert last["data"]["has_more"] is False
    assert last["data"]["next_offset"] is None
    assert last["data"]["truncated"] is False
    assert beyond["data"]["has_more"] is False
    assert beyond["data"]["next_offset"] is None


@pytest.mark.parametrize("limit", [0, 101, True, 1.5, "20"])
def test_gene_search_rejects_invalid_limits_before_network(limit):
    tool = dbSNPSearchByGene({"name": "dbsnp_search_by_gene"})
    with patch.object(tool, "_make_request") as request:
        result = tool.run({"gene_symbol": "BRCA1", "limit": limit})

    assert result["status"] == "error"
    assert result["parameter"] == "limit"
    request.assert_not_called()


@pytest.mark.parametrize("offset", [-1, True, 1.5, "2"])
def test_gene_search_rejects_invalid_offsets_before_network(offset):
    tool = dbSNPSearchByGene({"name": "dbsnp_search_by_gene"})
    with patch.object(tool, "_make_request") as request:
        result = tool.run({"gene_symbol": "BRCA1", "offset": offset})

    assert result["status"] == "error"
    assert result["parameter"] == "offset"
    request.assert_not_called()
