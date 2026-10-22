"""Regression tests for recoverable GtoPdb interaction pagination."""

import json
from pathlib import Path

import pytest

import tooluniverse.gtopdb_tool as gtopdb

pytestmark = pytest.mark.unit

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"

BANNER = '"# GtoPdb Version: 2026.3 - published: 2026-09-16"\n'
INTERACTIONS_CSV = (
    BANNER + '"Target","Target ID","Target Subunit IDs","Target Gene Symbol",'
    '"Target UniProt ID","Target Species","Ligand ID","Ligand","Ligand Type",'
    '"Approved","Type","Action","Affinity Units","Affinity High",'
    '"Affinity Median","Affinity Low","Selectivity","Primary Target"\n'
    + "".join(
        f'"EGFR","1797","","EGFR","P00533","Human","{1000 + i}","ligand {i}",'
        '"Synthetic organic","","Inhibitor","Inhibition","pIC50","8","8","8",'
        '"","t"\n'
        for i in range(7)
    )
)


@pytest.fixture(autouse=True)
def _recorded_bulk(monkeypatch):
    gtopdb.clear_bulk_cache()

    class _Response:
        status_code = 200
        text = INTERACTIONS_CSV

    def fake_request(session, method, url, **kwargs):
        assert url.endswith(gtopdb.INTERACTIONS_FILE), url
        return _Response()

    monkeypatch.setattr(gtopdb, "request_with_retry", fake_request)
    yield
    gtopdb.clear_bulk_cache()


def _tool():
    config = {
        t["name"]: t
        for t in json.loads((DATA / "gtopdb_tools.json").read_text("utf-8"))
    }["GtoPdb_get_interactions"]
    return gtopdb.GtoPdbRESTTool(config)


def test_interactions_apply_offset_after_filtering_and_expose_continuation():
    result = _tool().run({"targetId": 1797, "limit": 3, "offset": 3})

    data = result["data"]
    assert [row["ligandId"] for row in data["interactions"]] == [1003, 1004, 1005]
    assert data["total_matches"] == 7
    assert data["returned"] == 3
    assert data["offset"] == 3
    assert data["has_more"] is True
    assert data["next_offset"] == 6
    assert data["result_set_complete"] is False


def test_last_page_has_no_continuation():
    data = _tool().run({"targetId": 1797, "limit": 3, "offset": 6})["data"]

    assert [row["ligandId"] for row in data["interactions"]] == [1006]
    assert data["has_more"] is False
    assert data["next_offset"] is None


def test_config_declares_offset():
    props = _tool().tool_config["parameter"]["properties"]
    assert props["offset"]["minimum"] == 0
    assert props["limit"]["maximum"] == gtopdb.MAX_LIMIT
