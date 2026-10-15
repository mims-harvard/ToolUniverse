"""GtoPdb's REST service is key-gated; the bulk CSVs are not.

Every path under https://www.guidetopharmacology.org/services answers 401
"API key is missing", and seven ways of sending a key all come back with that
same body -- there is no mechanism to implement, documented or discoverable.
The bulk files under /DATA carry the same records and are open, so the four
tools that can be served from them are, and the two disease tools are retired
because GtoPdb publishes no open disease file.

These tests use recorded CSV fragments. The real files are a few MB and a unit
test should not download them.
"""

import json
from pathlib import Path

import pytest

import tooluniverse.gtopdb_tool as gtopdb

pytestmark = pytest.mark.unit

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"

# Shapes copied from the real files, including the version banner that has to be
# skipped and the markup GtoPdb puts in names.
TARGETS_CSV = (
    '"# GtoPdb Version: 2026.3 - published: 2026-09-16"\n'
    '"Type","Family id","Family name","Target id","Target name","Subunit id",'
    '"Subunit name","Target systematic name","Target abbreviated name",'
    '"synonyms","HGNC id","HGNC symbol"\n'
    '"gpcr","1","5-HT receptors","1","5-HT<sub>1A</sub> receptor","","","",'
    '"5-HT1A","serotonin receptor|EGFR-like","HGNC:5286","HTR1A"\n'
    '"catalytic_receptor","2","Tyrosine kinases","1797",'
    '"epidermal growth factor receptor","","","","EGFR","","HGNC:3236","EGFR"\n'
    '"enzyme","3","Oxidoreductases","2486",'
    '"Dopamine beta-hydroxylase","","","","DBH","","HGNC:2689","DBH"\n'
)

LIGANDS_CSV = (
    '"# GtoPdb Version: 2026.3 - published: 2026-09-16"\n'
    '"Ligand ID","Name","Species","Type","Approved","Withdrawn","Labelled",'
    '"Radioactive","PubChem SID","PubChem CID","UniProt ID","Ensembl ID",'
    '"ChEMBL ID"\n'
    '"1613","apomorphine","","Synthetic organic","yes","","","","","6005","",'
    '"","CHEMBL category"\n'
    '"1627","morphine","","Natural product","yes","","","","","5288826","","",""\n'
    '"7093","oxycodone","","Synthetic organic","yes","","","","","5284603","","",""\n'
)

INTERACTIONS_CSV = (
    '"# GtoPdb Version: 2026.3 - published: 2026-09-16"\n'
    '"Target","Target ID","Target Subunit IDs","Target Gene Symbol",'
    '"Target UniProt ID","Target Species","Ligand ID","Ligand","Ligand Type",'
    '"Approved","Type","Action","Affinity Units","Affinity High",'
    '"Affinity Median","Affinity Low","Selectivity","Primary Target"\n'
    '"KRAS","2486","","KRAS","P01116","Human","11111","AMG 510",'
    '"Synthetic organic","yes","Inhibitor","Inhibition","pIC50","8.1","8.0",'
    '"7.9","","t"\n'
    '"KRAS","2486","","KRAS","P01116","Rat","11112","other","Synthetic organic",'
    '"","Inhibitor","Inhibition","pIC50","7.0","7.0","7.0","","f"\n'
)

PHYSCHEM_CSV = (
    '"# GtoPdb Version: 2026.3 - published: 2026-09-16"\n'
    '"Ligand ID","Ligand Name","HBond Acceptors","HBond Donors",'
    '"Rotatable Bonds","TPSA","Mol Weight","XLogP","LipinskiRO5"\n'
    '"4139","example ligand","3","1","4","62.3","314.4","2.7","1"\n'
)

FIXTURES = {
    gtopdb.TARGETS_FILE: TARGETS_CSV,
    gtopdb.LIGANDS_FILE: LIGANDS_CSV,
    gtopdb.INTERACTIONS_FILE: INTERACTIONS_CSV,
    gtopdb.PHYSCHEM_FILE: PHYSCHEM_CSV,
}


@pytest.fixture(autouse=True)
def _recorded_bulk(monkeypatch):
    gtopdb.clear_bulk_cache()
    calls = []

    class _Response:
        status_code = 200

        def __init__(self, text):
            self.text = text

    def fake_request(session, method, url, **kwargs):
        name = url.rsplit("/", 1)[-1]
        calls.append(name)
        assert name in FIXTURES, f"unexpected download: {url}"
        return _Response(FIXTURES[name])

    monkeypatch.setattr(gtopdb, "request_with_retry", fake_request)
    yield calls
    gtopdb.clear_bulk_cache()


def _tool(name):
    config = {
        t["name"]: t
        for t in json.loads((DATA / "gtopdb_tools.json").read_text("utf-8"))
    }[name]
    return gtopdb.GtoPdbRESTTool(config)


def test_the_version_banner_is_not_read_as_the_header():
    rows = gtopdb.load_bulk(gtopdb.TARGETS_FILE)

    assert len(rows) == 3
    assert rows[0]["Target id"] == "1", (
        "the first line is a quoted '# GtoPdb Version' banner; reading it as "
        "the header makes every column name wrong"
    )


def test_each_file_is_downloaded_once_per_process(_recorded_bulk):
    gtopdb.load_bulk(gtopdb.TARGETS_FILE)
    gtopdb.load_bulk(gtopdb.TARGETS_FILE)
    gtopdb.load_bulk(gtopdb.TARGETS_FILE)

    assert _recorded_bulk == [gtopdb.TARGETS_FILE]


def test_an_exact_hit_is_not_buried_under_synonym_matches():
    """Searching "EGFR" led with PKR1, because EGFR is in its synonyms."""
    result = _tool("GtoPdb_search_targets").run({"name": "EGFR"})

    targets = result["data"]["targets"]
    assert result["data"]["total_matches"] == 2
    assert targets[0]["geneSymbol"] == "EGFR", [t["geneSymbol"] for t in targets]


def test_markup_in_a_name_does_not_hide_the_record():
    """GtoPdb writes "5-HT<sub>1A</sub> receptor"; users type "5-HT1A"."""
    result = _tool("GtoPdb_search_targets").run({"name": "5-HT1A"})

    targets = result["data"]["targets"]
    assert len(targets) == 1
    assert targets[0]["name"] == "5-HT1A receptor"
    assert targets[0]["rawName"] == "5-HT<sub>1A</sub> receptor"


def test_a_target_type_is_matched_against_the_slug_gtopdb_uses():
    """The file says "gpcr"; callers say "GPCR" or "G protein coupled receptor"."""
    for spelling in ("GPCR", "gpcr", "G protein coupled receptor"):
        result = _tool("GtoPdb_search_targets").run({"type": spelling})
        assert result["data"]["total_matches"] == 1, spelling

    unknown = _tool("GtoPdb_search_targets").run({"type": "not-a-type"})
    assert unknown["status"] == "error"
    # The message lists GtoPdb's canonical spellings, not the record slugs.
    assert "GPCR" in unknown["error"]
    assert "GPCR" in unknown["valid_types"]


def test_approved_is_the_word_yes_not_a_boolean():
    result = _tool("GtoPdb_search_ligands").run({"name": "morphine"})

    ligands = result["data"]["ligands"]
    assert ligands[0]["name"] == "morphine", [lig["name"] for lig in ligands]
    assert ligands[0]["approved"] is True
    assert all(isinstance(lig["approved"], bool) for lig in ligands)


def test_species_filters_the_interaction_rows():
    tool = _tool("GtoPdb_get_interactions")

    human = tool.run({"gene_symbol": "KRAS", "species": "Human"})
    assert human["data"]["total_matches"] == 1
    assert human["data"]["interactions"][0]["targetSpecies"] == "Human"

    either = tool.run({"gene_symbol": "KRAS"})
    assert either["data"]["total_matches"] == 2


def test_a_ligand_with_no_interactions_says_why():
    """oxycodone is approved, exists, and has no row in interactions.csv."""
    result = _tool("GtoPdb_get_interactions").run({"ligandId": 7093})

    assert result["status"] == "success"
    assert result["data"]["total_matches"] == 0
    note = result["data"]["note"]
    assert "11278 of the 13991" in note
    assert "no such" in note, "the note has to rule out 'this ligand is unknown'"


def test_a_search_with_no_filter_is_refused():
    """13991 ligands is not a search result."""
    assert _tool("GtoPdb_search_ligands").run({})["status"] == "error"
    assert _tool("GtoPdb_search_targets").run({})["status"] == "error"
    assert _tool("GtoPdb_get_interactions").run({})["status"] == "error"


def test_ligand_properties_takes_either_spelling_of_the_id():
    tool = _tool("GtoPdb_get_ligand_properties")

    for arguments in ({"ligand_id": 4139}, {"ligandId": 4139}):
        result = tool.run(arguments)
        # Numeric, as /molecularProperties returned it -- not the CSV's string.
        assert result["data"]["properties"]["molecularWeight"] == 314.4, arguments


def test_the_disease_tools_are_retired_with_their_evidence():
    names = {
        t["name"]
        for t in json.loads((DATA / "gtopdb_tools.json").read_text("utf-8"))
    }
    assert "GtoPdb_search_diseases" not in names
    assert "GtoPdb_get_disease_associations" not in names

    retired = json.loads(
        (DATA / "broken_apis" / "gtopdb_rest.json").read_text("utf-8")
    )
    assert retired["retry_count"] >= 3
    assert retired["retry_after"]
    assert "DATA" in retired["workaround"]
    for name in ("GtoPdb_search_diseases", "GtoPdb_get_disease_associations"):
        assert name in retired["affected_tools"]


def test_no_tool_still_points_at_the_key_gated_service():
    source = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "tooluniverse"
        / "gtopdb_tool.py"
    ).read_text("utf-8")

    assert "guidetopharmacology.org/DATA" in source
    assert "/services" not in source.split('"""', 2)[2], (
        "a /services URL outside the module docstring means a tool is still "
        "calling the 401 endpoint"
    )
