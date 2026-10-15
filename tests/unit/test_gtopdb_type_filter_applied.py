"""The `type` filter has to remove records, and an unknown value has to be refused.

Written when GtoPdb's REST service ignored ?type= whenever ?name= was also
supplied, so an unrecognised value returned every record while reading as a
filtered search. That service is now key-gated everywhere and these tools read
the open bulk CSVs instead, so the half of this file about what gets pushed
upstream has no subject any more -- there is no upstream query.

What survived is the part that was never about the transport: a type filter
removes non-matching records, the vocabulary is matched case- and
spacing-insensitively, GtoPdb's own documented-but-dead values are refused with
a pointer, and `approved: false` means all ligands rather than unapproved ones.
Those are checked here against the bulk implementation, with recorded CSV rows.

Carrying them over caught two contracts the rewrite would otherwise have
broken: the Ion channel umbrella, which has no single GtoPdb value, and
`approved: false`, which the first version of the rewrite turned into a filter
for unapproved ligands.
"""

import json
from pathlib import Path

import pytest

import tooluniverse.gtopdb_tool as gtopdb

pytestmark = pytest.mark.unit

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"

TARGETS_CSV = (
    '"# GtoPdb Version: 2026.3 - published: 2026-09-16"\n'
    '"Type","Family id","Family name","Target id","Target name","Subunit id",'
    '"Subunit name","Target systematic name","Target abbreviated name",'
    '"synonyms","HGNC id","HGNC symbol"\n'
    '"gpcr","1","5-HT","377","serotonin receptor 1","","","","","","","HTR1B"\n'
    '"lgic","2","5-HT3","378","serotonin receptor 3","","","","","","","HTR3A"\n'
    '"vgic","3","Nav","379","serotonin-sensitive channel","","","","","","",'
    '"SCN1A"\n'
    '"other_ic","4","Other","380","serotonin other channel","","","","","","",'
    '"TPCN1"\n'
    '"enzyme","5","Enz","381","serotonin N-acetyltransferase","","","","","",'
    '"","AANAT"\n'
)

LIGANDS_CSV = (
    '"# GtoPdb Version: 2026.3 - published: 2026-09-16"\n'
    '"Ligand ID","Name","Species","Type","Approved","Withdrawn","Labelled",'
    '"Radioactive","PubChem SID","PubChem CID","UniProt ID","Ensembl ID",'
    '"ChEMBL ID","Ligand Subunit IDs","Ligand Subunit Name",'
    '"Ligand Subunit UniProt IDs","Ligand Subunit Ensembl IDs","IUPAC name",'
    '"INN","Synonyms","SMILES","InChIKey","InChI"\n'
    '"1","dopamine","","Metabolite","","","","","","681","","","","","","","",'
    '"","","","","",""\n'
    '"2","dopamine analogue A","","Synthetic organic","yes","","","","","","",'
    '"","","","","","","","","","","",""\n'
    '"3","dopamine analogue B","","Synthetic organic","","yes","","","","","",'
    '"","","","","","","","","","","",""\n'
    '"4","dopamine label","","Synthetic organic","","","yes","","","","","","",'
    '"","","","","","","","","",""\n'
    '"5","semaglutide","","Peptide","yes","","","","","","","","","","","","",'
    '"","","","","",""\n'
)

FIXTURES = {
    gtopdb.TARGETS_FILE: TARGETS_CSV,
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


def _tool(name):
    config = {
        t["name"]: t
        for t in json.loads((DATA / "gtopdb_tools.json").read_text("utf-8"))
    }[name]
    return gtopdb.GtoPdbRESTTool(config)


def _names(result, key):
    return [item["name"] for item in result["data"][key]]


class TestTypeFilterRemovesRecords:
    def test_a_ligand_type_filters_out_the_other_types(self):
        result = _tool("GtoPdb_search_ligands").run(
            {"name": "dopamine", "type": "Metabolite"}
        )

        assert _names(result, "ligands") == ["dopamine"]

    def test_semaglutide_keeps_its_record_under_peptide(self):
        result = _tool("GtoPdb_search_ligands").run(
            {"name": "semaglutide", "type": "Peptide"}
        )

        assert _names(result, "ligands") == ["semaglutide"]

    def test_the_wrong_type_returns_nothing_rather_than_everything(self):
        result = _tool("GtoPdb_search_ligands").run(
            {"name": "semaglutide", "type": "Metabolite"}
        )

        assert result["data"]["total_matches"] == 0
        assert "note" in result["data"]

    @pytest.mark.parametrize(
        "spelling", ["Metabolite", "metabolite", "METABOLITE", " metabolite "]
    )
    def test_the_vocabulary_is_matched_insensitively(self, spelling):
        result = _tool("GtoPdb_search_ligands").run(
            {"name": "dopamine", "type": spelling}
        )

        assert _names(result, "ligands") == ["dopamine"]

    @pytest.mark.parametrize(
        ("pseudo_type", "expected"),
        [
            ("Approved", ["dopamine analogue A"]),
            ("Withdrawn", ["dopamine analogue B"]),
            ("Labelled", ["dopamine label"]),
            ("Labeled", ["dopamine label"]),
        ],
    )
    def test_the_boolean_pseudo_types_match_record_flags(self, pseudo_type, expected):
        """Approved, Withdrawn and Labelled are flags, not `type` values."""
        result = _tool("GtoPdb_search_ligands").run(
            {"name": "dopamine", "type": pseudo_type}
        )

        assert _names(result, "ligands") == expected


class TestTargetTypes:
    def test_a_target_type_filters_out_the_other_types(self):
        result = _tool("GtoPdb_search_targets").run(
            {"name": "serotonin", "type": "GPCR"}
        )

        assert [t["targetId"] for t in result["data"]["targets"]] == [377]

    def test_the_ion_channel_umbrella_covers_all_three_record_types(self):
        """GtoPdb has no single value for this; it spans lgic, vgic, other_ic."""
        result = _tool("GtoPdb_search_targets").run(
            {"name": "serotonin", "type": "Ion channel"}
        )

        assert sorted(t["targetId"] for t in result["data"]["targets"]) == [
            378,
            379,
            380,
        ]

    @pytest.mark.parametrize(
        ("spelling", "expected"),
        [
            ("CatalyticReceptor", "CatalyticReceptor"),
            ("Catalytic receptor", "CatalyticReceptor"),
            ("Nuclear receptor", "NHR"),
            ("Other protein", "OtherProtein"),
        ],
    )
    def test_the_alias_spellings_resolve(self, spelling, expected):
        spec = gtopdb._TARGET_TYPE_SPECS[gtopdb._norm_type(spelling)]

        assert spec.canonical == expected

    def test_accessory_protein_is_accepted_and_says_what_is_missing(self):
        """REST returned 10 records with an empty type; the CSV has none."""
        result = _tool("GtoPdb_search_targets").run({"type": "Accessory protein"})

        assert result["status"] == "success"
        assert result["data"]["total_matches"] == 0
        assert "no accessory proteins" in result["data"]["note"]


class TestInvalidTypeIsRefused:
    def test_a_garbage_type_is_an_error_not_an_unfiltered_result(self):
        result = _tool("GtoPdb_search_ligands").run(
            {"name": "dopamine", "type": "not-a-type"}
        )

        assert result["status"] == "error"
        assert "not-a-type" in result["error"]

    def test_the_error_lists_the_real_vocabulary(self):
        result = _tool("GtoPdb_search_ligands").run({"type": "nonsense"})

        for expected in ("Peptide", "Metabolite", "Synthetic organic"):
            assert expected in result["error"]
        assert "Peptide" in result["valid_types"]

    @pytest.mark.parametrize(
        ("dead_value", "pointer"),
        [("endogenous peptide", "Peptide"), ("inn", "Approved")],
    )
    def test_a_documented_but_dead_value_is_refused_with_a_pointer(
        self, dead_value, pointer
    ):
        """GtoPdb's own docs list these and no record carries them."""
        result = _tool("GtoPdb_search_ligands").run(
            {"name": "dopamine", "type": dead_value}
        )

        assert result["status"] == "error"
        assert pointer in result["error"]

    def test_an_invalid_target_type_is_refused(self):
        result = _tool("GtoPdb_search_targets").run({"type": "Metabolite"})

        assert result["status"] == "error"
        assert "GPCR" in result["error"]


class TestNoTypeMeansNoFiltering:
    def test_a_search_without_a_type_returns_every_match(self):
        result = _tool("GtoPdb_search_ligands").run({"name": "dopamine"})

        assert result["data"]["total_matches"] == 4

    def test_an_empty_string_type_is_treated_as_omitted(self):
        result = _tool("GtoPdb_search_ligands").run({"name": "dopamine", "type": ""})

        assert result["status"] == "success"
        assert result["data"]["total_matches"] == 4


class TestApprovedFilter:
    def test_approved_true_keeps_only_approved_records(self):
        result = _tool("GtoPdb_search_ligands").run(
            {"name": "dopamine", "approved": True}
        )

        assert _names(result, "ligands") == ["dopamine analogue A"]

    def test_approved_false_means_all_ligands_as_documented(self):
        """The parameter is 'approved drugs only (true) or all ligands
        (false/omit)', so false is not a filter for unapproved ligands."""
        explicit = _tool("GtoPdb_search_ligands").run(
            {"name": "dopamine", "approved": False}
        )
        omitted = _tool("GtoPdb_search_ligands").run({"name": "dopamine"})

        assert explicit["data"]["total_matches"] == 4
        assert _names(explicit, "ligands") == _names(omitted, "ligands")

    def test_approved_combines_with_a_type(self):
        result = _tool("GtoPdb_search_ligands").run(
            {"name": "dopamine", "type": "Synthetic organic", "approved": True}
        )

        assert _names(result, "ligands") == ["dopamine analogue A"]
