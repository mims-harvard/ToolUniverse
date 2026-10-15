"""Error and alias paths for GtoPdb_get_ligand_properties.

This file used to mock /structure + /molecularProperties and
/diseaseTargets + /diseaseLigands. Both pairs are gone: GtoPdb's REST service
answers 401 everywhere, so the four surviving tools read the open bulk CSVs
(see test_gtopdb_reads_the_open_bulk_files.py) and the two disease tools are
retired to data/broken_apis/gtopdb_rest.json.

The invariants below outlived the transport, so they are kept and pointed at
the new implementation: both spellings of the ligand ID work, a bad or missing
ID is an error rather than an exception, and a download failure comes back as
an envelope because run() must never raise.

The property names and numeric types are asserted against what the REST
endpoint used to return. They match it exactly for aspirin -- every one of the
seven values, including molecularWeight 180.0422588 and logP 1.422 -- which is
how the repoint was shown to be lossless rather than merely green.
"""

import json
from pathlib import Path

import pytest
import requests

import tooluniverse.gtopdb_tool as gtopdb

pytestmark = pytest.mark.unit

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"

# Aspirin, as GtoPdb publishes it in the two bulk files.
PHYSCHEM_CSV = (
    '"# GtoPdb Version: 2026.3 - published: 2026-09-16"\n'
    '"Ligand ID","Ligand Name","HBond Acceptors","HBond Donors",'
    '"Rotatable Bonds","TPSA","Mol Weight","XLogP","LipinskiRO5"\n'
    '"4139","aspirin","3","1","3","63.6","180.0422588","1.422","0"\n'
    '"9999","a peptide","","","","","","",""\n'
)
LIGANDS_CSV = (
    '"# GtoPdb Version: 2026.3 - published: 2026-09-16"\n'
    '"Ligand ID","Name","Species","Type","Approved","Withdrawn","Labelled",'
    '"Radioactive","PubChem SID","PubChem CID","UniProt ID","Ensembl ID",'
    '"ChEMBL ID","Ligand Subunit IDs","Ligand Subunit Name",'
    '"Ligand Subunit UniProt IDs","Ligand Subunit Ensembl IDs","IUPAC name",'
    '"INN","Synonyms","SMILES","InChIKey","InChI"\n'
    '"4139","aspirin","","Synthetic organic","yes","","","","","2244","","",'
    '"CHEMBL25","","","","","2-acetyloxybenzoic acid","aspirin",'
    '"acetylsalicylic acid","CC(=O)Oc1ccccc1C(=O)O",'
    '"BSYNRYMUTXBXSQ-UHFFFAOYSA-N","InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)'
    '9(11)12/h2-5H,1H3,(H,11,12)"\n'
    '"8888","a ligand with no properties row","","Peptide","","","","","","",'
    '"","","","","","","","","","","","",""\n'
)

# What /molecularProperties and /structure returned for ligand 4139.
REST_PROPERTIES = {
    "hydrogenBondAcceptors": 3,
    "hydrogenBondDonors": 1,
    "rotatableBonds": 3,
    "topologicalPolarSurfaceArea": 63.6,
    "molecularWeight": 180.0422588,
    "logP": 1.422,
    "lipinskisRuleOfFive": 0,
}
REST_STRUCTURE = {
    "iupacName": "2-acetyloxybenzoic acid",
    "smiles": "CC(=O)Oc1ccccc1C(=O)O",
    "inchiKey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
}

FIXTURES = {
    gtopdb.PHYSCHEM_FILE: PHYSCHEM_CSV,
    gtopdb.LIGANDS_FILE: LIGANDS_CSV,
}


class _Response:
    status_code = 200

    def __init__(self, text):
        self.text = text


@pytest.fixture(autouse=True)
def _recorded_bulk(monkeypatch):
    gtopdb.clear_bulk_cache()

    def fake_request(session, method, url, **kwargs):
        return _Response(FIXTURES[url.rsplit("/", 1)[-1]])

    monkeypatch.setattr(gtopdb, "request_with_retry", fake_request)
    yield
    gtopdb.clear_bulk_cache()


def _properties_tool():
    config = {
        t["name"]: t
        for t in json.loads((DATA / "gtopdb_tools.json").read_text("utf-8"))
    }["GtoPdb_get_ligand_properties"]
    return gtopdb.GtoPdbRESTTool(config)


def test_the_property_names_and_types_match_the_retired_rest_shape():
    result = _properties_tool().run({"ligand_id": 4139})

    assert result["data"]["properties"] == REST_PROPERTIES, (
        "these came from /molecularProperties before and callers may read them "
        "by name; the bulk column headings are spelled differently"
    )


def test_the_structure_fields_survived_the_repoint():
    """These needed a second GET to /structure and are now in ligands.csv."""
    ligand = _properties_tool().run({"ligand_id": 4139})["data"]["ligand"]

    for field, expected in REST_STRUCTURE.items():
        assert ligand[field] == expected, field


def test_either_spelling_of_the_ligand_id_works():
    tool = _properties_tool()

    snake = tool.run({"ligand_id": 4139})
    camel = tool.run({"ligandId": 4139})

    assert snake == camel
    assert snake["status"] == "success"


def test_an_unknown_ligand_is_an_error_not_an_empty_success():
    result = _properties_tool().run({"ligand_id": 999999})

    assert result["status"] == "error"
    assert "999999" in result["error"]


def test_a_missing_ligand_id_is_an_error():
    result = _properties_tool().run({})

    assert result["status"] == "error"
    assert "ligand_id" in result["error"]


def test_a_ligand_with_no_properties_row_says_so():
    """11266 of 13991 ligands have properties; peptides mostly do not."""
    result = _properties_tool().run({"ligand_id": 8888})

    assert result["status"] == "success"
    assert result["data"]["properties"] is None
    note = result["data"]["note"]
    assert "11266 have a row" in note and "13991 ligands" in note
    assert result["data"]["ligand"]["name"] == "a ligand with no properties row"


def test_a_download_failure_comes_back_as_an_envelope(monkeypatch):
    """run() must never raise, whatever the network does."""

    def boom(session, method, url, **kwargs):
        raise requests.exceptions.ConnectionError("no route to host")

    monkeypatch.setattr(gtopdb, "request_with_retry", boom)

    result = _properties_tool().run({"ligand_id": 4139})

    assert result["status"] == "error"
    assert "bulk downloads" in result["error"]


def test_a_timeout_names_the_download_rather_than_an_api_call(monkeypatch):
    def slow(session, method, url, **kwargs):
        raise requests.exceptions.Timeout("too slow")

    monkeypatch.setattr(gtopdb, "request_with_retry", slow)

    result = _properties_tool().run({"ligand_id": 4139})

    assert result["status"] == "error"
    assert "once per session" in result["error"], (
        "a few MB fetched once reads differently from a slow per-call API, and "
        "the message should say which one timed out"
    )
