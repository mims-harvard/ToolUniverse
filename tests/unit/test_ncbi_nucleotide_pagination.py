from unittest.mock import patch

import pytest

from tooluniverse.ncbi_nucleotide_tool import NCBINucleotideSearchTool


pytestmark = pytest.mark.unit


def _tool():
    return NCBINucleotideSearchTool(
        {
            "name": "NCBI_search_nucleotide",
            "parameter": {
                "properties": {"operation": {"const": "search"}},
            },
        }
    )


def test_search_forwards_offset_and_exposes_exact_continuation():
    search = {
        "status": "success",
        "data": {
            "esearchresult": {
                "count": "8",
                "idlist": ["103", "104"],
            }
        },
        "url": "https://eutils/esearch.fcgi",
    }
    fetch = {"status": "success", "data": "ABC.1\nDEF.2\n"}
    tool = _tool()
    with patch.object(tool, "_make_request", side_effect=[search, fetch]) as request:
        result = tool.run({"query": "BRCA1[Gene]", "limit": 2, "offset": 2})

    assert request.call_args_list[0].args[1]["retmax"] == 2
    assert request.call_args_list[0].args[1]["retstart"] == 2
    assert request.call_args_list[1].args[1]["id"] == "103,104"
    assert result["data"]["accessions"] == ["ABC.1", "DEF.2"]
    assert result["data"]["count"] == 8
    assert result["data"]["returned"] == 2
    assert result["data"]["offset"] == 2
    assert result["data"]["has_more"] is True
    assert result["data"]["next_offset"] == 4
    assert result["data"]["truncated"] is True


def test_search_empty_page_has_no_false_continuation():
    search = {
        "status": "success",
        "data": {"esearchresult": {"count": "8", "idlist": []}},
    }
    tool = _tool()
    with patch.object(tool, "_make_request", return_value=search) as request:
        result = tool.run({"query": "BRCA1[Gene]", "limit": 2, "offset": 8})

    assert request.call_count == 1
    assert result["data"]["has_more"] is False
    assert result["data"]["next_offset"] is None


@pytest.mark.parametrize("limit", [0, 101, True, 1.5, "20"])
def test_search_rejects_invalid_limits_before_network(limit):
    tool = _tool()
    with patch.object(tool, "_make_request") as request:
        result = tool.run({"query": "BRCA1[Gene]", "limit": limit})

    assert result["status"] == "error"
    assert result["parameter"] == "limit"
    request.assert_not_called()


@pytest.mark.parametrize("offset", [-1, True, 1.5, "2"])
def test_search_rejects_invalid_offsets_before_network(offset):
    tool = _tool()
    with patch.object(tool, "_make_request") as request:
        result = tool.run({"query": "BRCA1[Gene]", "offset": offset})

    assert result["status"] == "error"
    assert result["parameter"] == "offset"
    request.assert_not_called()
