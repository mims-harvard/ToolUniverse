"""Regression guard: BV-BRC searches must report the upstream match count.

Every BV-BRC search operation computed ``metadata.total_results`` as
``len(results)`` -- the number of rows on the page just returned. It therefore
always equalled the requested ``limit``, so a caller counting how widespread a
resistance gene is could not tell "these are all the matches" from "there are
hundreds more". Confirmed live: ``BVBRC_search_genome_features`` for gene
blaOXA-48 reported ``total_results: 3`` at ``limit=3`` and ``10`` at
``limit=10``, while BV-BRC's own ``Content-Range: items 0-3/13`` response
header stated the true total.

Fixed by reading ``Content-Range`` in ``_make_request_with_total`` and building
every search's metadata through the shared ``_search_metadata`` helper, which
separates ``returned_results`` (this page) from ``total_results`` (upstream)
and flags truncation explicitly.

These tests never touch the network.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.bvbrc_tool import BVBRCTool

pytestmark = pytest.mark.unit


def _feature_tool():
    return BVBRCTool(
        {
            "name": "bvbrc_test_features",
            "fields": {"data_type": "genome_feature", "action": "search"},
        }
    )


def _genome_tool():
    return BVBRCTool(
        {
            "name": "bvbrc_test_genomes",
            "fields": {"data_type": "genome", "action": "search"},
        }
    )


def _rows(n):
    return [{"patric_id": f"fig|562.{i}.peg.1", "gene": "blaOXA-48"} for i in range(n)]


def _fake_get(rows, response_headers):
    def fake_get(url, headers=None, timeout=None, **kwargs):
        r = MagicMock()
        r.raise_for_status = MagicMock()
        r.json.return_value = rows
        r.headers = response_headers
        return r

    return fake_get


def _run(tool, arguments, rows, response_headers):
    with patch(
        "tooluniverse.bvbrc_tool.requests.get",
        side_effect=_fake_get(rows, response_headers),
    ):
        return tool.run(arguments)


def test_total_results_comes_from_content_range_not_page_size():
    result = _run(
        _feature_tool(),
        {"gene": "blaOXA-48", "limit": 3},
        _rows(3),
        {"Content-Range": "items 0-3/26"},
    )

    assert result["status"] == "success"
    meta = result["metadata"]
    assert meta["total_results"] == 26
    assert meta["returned_results"] == 3
    assert len(result["data"]) == 3


def test_truncation_is_flagged_with_actionable_note():
    meta = _run(
        _feature_tool(),
        {"gene": "blaOXA-48", "limit": 3},
        _rows(3),
        {"Content-Range": "items 0-3/26"},
    )["metadata"]

    assert meta["truncated"] is True
    assert "26" in meta["truncation_note"]
    assert "limit" in meta["truncation_note"]


def test_upstream_total_is_stable_across_limits():
    small = _run(
        _feature_tool(),
        {"gene": "blaOXA-48", "limit": 3},
        _rows(3),
        {"Content-Range": "items 0-3/26"},
    )["metadata"]
    large = _run(
        _feature_tool(),
        {"gene": "blaOXA-48", "limit": 10},
        _rows(10),
        {"Content-Range": "items 0-10/26"},
    )["metadata"]

    assert small["total_results"] == large["total_results"] == 26
    assert small["returned_results"] == 3
    assert large["returned_results"] == 10


def test_complete_result_set_is_not_flagged_as_truncated():
    meta = _run(
        _feature_tool(),
        {"gene": "blaOXA-48", "limit": 25},
        _rows(4),
        {"Content-Range": "items 0-4/4"},
    )["metadata"]

    assert meta["total_results"] == 4
    assert meta["returned_results"] == 4
    assert meta["truncated"] is False
    assert "truncation_note" not in meta


def test_shared_helper_applies_to_other_search_operations():
    meta = _run(
        _genome_tool(),
        {"keyword": "Klebsiella pneumoniae", "limit": 2},
        _rows(2),
        {"Content-Range": "items 0-2/48384"},
    )["metadata"]

    assert meta["total_results"] == 48384
    assert meta["returned_results"] == 2
    assert meta["truncated"] is True
    assert meta["query"] == "Klebsiella pneumoniae"


@pytest.mark.parametrize(
    "response_headers",
    [
        {},
        {"Content-Range": ""},
        {"Content-Range": "items 0-3/*"},
        {"Content-Range": "totally malformed"},
        {"Content-Range": "items 0-3/not-a-number"},
        {"Content-Range": None},
        {"Content-Range": 12345},
    ],
)
def test_missing_or_malformed_header_degrades_gracefully(response_headers):
    result = _run(
        _feature_tool(),
        {"gene": "blaOXA-48", "limit": 10},
        _rows(3),
        response_headers,
    )

    assert result["status"] == "success"
    assert len(result["data"]) == 3
    meta = result["metadata"]
    # Falls back to the page count, says so, and does not over-claim truncation.
    assert meta["total_results"] == 3
    assert meta["returned_results"] == 3
    assert meta["truncated"] is False
    assert "did not report a total" in meta["total_results_note"]


def test_full_page_without_header_warns_more_may_exist():
    meta = _run(
        _feature_tool(),
        {"gene": "blaOXA-48", "limit": 3},
        _rows(3),
        {},
    )["metadata"]

    assert meta["truncated"] is True
    assert "may exist" in meta["truncation_note"]


def test_header_smaller_than_page_is_ignored():
    """A nonsensical upstream total must never undercount the rows returned."""
    meta = _run(
        _feature_tool(),
        {"gene": "blaOXA-48", "limit": 10},
        _rows(5),
        {"Content-Range": "items 0-5/2"},
    )["metadata"]

    assert meta["total_results"] == 5
    assert meta["returned_results"] == 5


def test_parse_content_range_total_never_raises():
    parse = BVBRCTool._parse_content_range_total
    assert parse("items 0-3/26") == 26
    assert parse("items 0-3/*") is None
    assert parse("") is None
    assert parse(None) is None
    assert parse(object()) is None
    assert parse("items 0-3/-1") is None


def test_single_record_get_metadata_is_untouched():
    tool = BVBRCTool(
        {"name": "bvbrc_test_get", "fields": {"data_type": "genome", "action": "get"}}
    )
    result = _run(
        tool,
        {"genome_id": "562.85926"},
        [{"genome_id": "562.85926", "genome_name": "Escherichia coli"}],
        {"Content-Range": "items 0-1/1"},
    )

    assert result["status"] == "success"
    assert result["metadata"] == {"source": "BV-BRC", "query_genome_id": "562.85926"}
