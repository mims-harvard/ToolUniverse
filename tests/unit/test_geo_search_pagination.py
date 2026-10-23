from unittest.mock import patch

import pytest

from tooluniverse.geo_tool import GEOSearchDatasets


pytestmark = pytest.mark.unit


def _tool():
    return GEOSearchDatasets(
        {
            "name": "geo_search_datasets",
            "fields": {"endpoint": "/esearch.fcgi"},
            "parameter": {"properties": {}},
        }
    )


def test_search_forwards_offset_and_exposes_exact_continuation():
    reply = {
        "status": "success",
        "data": {
            "esearchresult": {
                "count": "9",
                "idlist": ["303", "304"],
            }
        },
        "url": "https://eutils/esearch.fcgi",
    }
    tool = _tool()
    with patch.object(tool, "_make_request", return_value=reply) as request:
        result = tool.run({"query": "cancer", "limit": 2, "offset": 2})

    params = request.call_args.args[1]
    assert params["retmax"] == 2
    assert params["retstart"] == 2
    assert "(gse[ETYP] OR gds[ETYP])" in params["term"]
    assert result["metadata"] == {
        "total_results": 9,
        "returned": 2,
        "offset": 2,
        "limit": 2,
        "record_type": "both",
        "has_more": True,
        "next_offset": 4,
        "truncated": True,
    }


def test_search_empty_page_has_no_false_continuation():
    reply = {
        "status": "success",
        "data": {"esearchresult": {"count": "9", "idlist": []}},
    }
    tool = _tool()
    with patch.object(tool, "_make_request", return_value=reply):
        result = tool.run({"query": "cancer", "limit": 2, "offset": 10})

    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None


@pytest.mark.parametrize(
    ("record_type", "clause"),
    [
        ("series", "gse[ETYP]"),
        ("curated_dataset", "gds[ETYP]"),
        ("both", "(gse[ETYP] OR gds[ETYP])"),
    ],
)
def test_search_uses_upstream_dataset_type_filter(record_type, clause):
    tool = _tool()
    params = tool._build_params({"query": "cancer", "record_type": record_type})

    assert clause in params["term"]


def test_search_rejects_unknown_record_type_before_network():
    tool = _tool()
    with patch.object(tool, "_make_request") as request:
        result = tool.run({"query": "cancer", "record_type": "sample"})

    assert result["status"] == "error"
    assert result["parameter"] == "record_type"
    request.assert_not_called()


@pytest.mark.parametrize("limit", [0, 501, True, 1.5, "50"])
def test_search_rejects_invalid_limits_instead_of_clamping(limit):
    tool = _tool()
    with patch.object(tool, "_make_request") as request:
        result = tool.run({"query": "cancer", "limit": limit})

    assert result["status"] == "error"
    assert result["parameter"] == "limit"
    request.assert_not_called()


@pytest.mark.parametrize("offset", [-1, True, 1.5, "2"])
def test_search_rejects_invalid_offsets_before_network(offset):
    tool = _tool()
    with patch.object(tool, "_make_request") as request:
        result = tool.run({"query": "cancer", "offset": offset})

    assert result["status"] == "error"
    assert result["parameter"] == "offset"
    request.assert_not_called()
