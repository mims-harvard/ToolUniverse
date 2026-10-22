from unittest.mock import patch

import pytest

from tooluniverse.ncbi_sra_tool import NCBISRATool


pytestmark = pytest.mark.unit


def _tool():
    return NCBISRATool(
        {
            "name": "NCBI_SRA_search_runs",
            "parameter": {
                "properties": {"operation": {"const": "search"}},
            },
        }
    )


def test_search_forwards_offset_and_exposes_exact_continuation():
    reply = {
        "status": "success",
        "data": {
            "esearchresult": {
                "count": "7",
                "idlist": ["203", "204"],
            }
        },
        "url": "https://eutils/esearch.fcgi",
    }
    tool = _tool()
    with patch.object(tool, "_make_request", return_value=reply) as request:
        result = tool.run({"study": "SRP000001", "limit": 2, "offset": 2})

    params = request.call_args.args[1]
    assert params["retmax"] == 2
    assert params["retstart"] == 2
    assert result["data"]["count"] == 7
    assert result["data"]["returned"] == 2
    assert result["data"]["offset"] == 2
    assert result["data"]["limit"] == 2
    assert result["data"]["has_more"] is True
    assert result["data"]["next_offset"] == 4
    assert result["data"]["truncated"] is True


def test_search_empty_page_has_no_false_continuation():
    reply = {
        "status": "success",
        "data": {"esearchresult": {"count": "7", "idlist": []}},
    }
    tool = _tool()
    with patch.object(tool, "_make_request", return_value=reply):
        result = tool.run({"study": "SRP000001", "limit": 2, "offset": 8})

    assert result["data"]["has_more"] is False
    assert result["data"]["next_offset"] is None


@pytest.mark.parametrize("limit", [0, 101, True, 1.5, "20"])
def test_search_rejects_invalid_limits_before_network(limit):
    tool = _tool()
    with patch.object(tool, "_make_request") as request:
        result = tool.run({"study": "SRP000001", "limit": limit})

    assert result["status"] == "error"
    assert result["parameter"] == "limit"
    request.assert_not_called()


@pytest.mark.parametrize("offset", [-1, True, 1.5, "2"])
def test_search_rejects_invalid_offsets_before_network(offset):
    tool = _tool()
    with patch.object(tool, "_make_request") as request:
        result = tool.run({"study": "SRP000001", "offset": offset})

    assert result["status"] == "error"
    assert result["parameter"] == "offset"
    request.assert_not_called()
