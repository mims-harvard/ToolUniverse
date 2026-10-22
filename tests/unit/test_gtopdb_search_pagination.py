"""Every GtoPdb search match must be reachable through limit/offset."""

import json
from pathlib import Path

import pytest

import tooluniverse.gtopdb_tool as gtopdb

pytestmark = pytest.mark.unit

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"

BANNER = '"# GtoPdb Version: 2026.3 - published: 2026-09-16"\n'
TARGETS_CSV = (
    BANNER + '"Type","Family id","Family name","Target id","Target name","Subunit id",'
    '"Subunit name","Target systematic name","Target abbreviated name",'
    '"synonyms","HGNC id","HGNC symbol"\n'
    + "".join(
        f'"gpcr","1","Receptors","{i}","receptor {i}","","","","R{i}","","",""\n'
        for i in range(7)
    )
)
LIGANDS_CSV = (
    BANNER + '"Ligand ID","Name","Species","Type","Approved","Withdrawn","Labelled",'
    '"Radioactive","PubChem SID","PubChem CID","UniProt ID","Ensembl ID",'
    '"ChEMBL ID"\n'
    + "".join(
        f'"{i}","compound {i}","","Synthetic organic","","","","","","","","",""\n'
        for i in range(7)
    )
)
FIXTURES = {gtopdb.TARGETS_FILE: TARGETS_CSV, gtopdb.LIGANDS_FILE: LIGANDS_CSV}


@pytest.fixture(autouse=True)
def _recorded_bulk(monkeypatch):
    gtopdb.clear_bulk_cache()

    class _Response:
        status_code = 200

        def __init__(self, text):
            self.text = text

    def fake_request(session, method, url, **kwargs):
        return _Response(FIXTURES[url.rsplit("/", 1)[-1]])

    monkeypatch.setattr(gtopdb, "request_with_retry", fake_request)
    yield
    gtopdb.clear_bulk_cache()


def _config(name):
    configs = json.loads((DATA / "gtopdb_tools.json").read_text("utf-8"))
    return next(config for config in configs if config["name"] == name)


@pytest.mark.parametrize(
    "tool_name,arguments,key",
    [
        ("GtoPdb_search_targets", {"type": "GPCR"}, "targets"),
        ("GtoPdb_search_ligands", {"type": "Synthetic organic"}, "ligands"),
    ],
)
def test_search_pages_are_recoverable(tool_name, arguments, key):
    result = gtopdb.GtoPdbRESTTool(_config(tool_name)).run(
        {**arguments, "limit": 3, "offset": 3}
    )

    data = result["data"]
    assert len(data[key]) == 3
    assert data["total_matches"] == 7
    assert data["returned"] == 3
    assert data["offset"] == 3
    assert data["limit"] == 3
    assert data["has_more"] is True
    assert data["next_offset"] == 6
    assert data["result_set_complete"] is False


@pytest.mark.parametrize(
    "tool_name", ["GtoPdb_search_targets", "GtoPdb_search_ligands"]
)
def test_search_config_and_return_schema_expose_pagination(tool_name):
    config = _config(tool_name)
    assert {"limit", "offset"} <= set(config["parameter"]["properties"])
    properties = config["return_schema"]["properties"]
    assert {
        "total_matches",
        "returned",
        "offset",
        "limit",
        "has_more",
        "next_offset",
        "result_set_complete",
    } <= set(properties)
