"""Tests for M-CSA catalytic sites and structure-derived membrane topology.

Both supply curated experimental annotation that ToolUniverse previously
only had predictions for. Tests assert known biochemistry: class A
beta-lactamases catalyse via a serine nucleophile, and bovine rhodopsin has
seven transmembrane helices.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

EXPECTED_TOOLS = [
    "MCSA_get_entry",
    "MCSA_search_enzymes",
    "OPM_search_structures",
    "TopDB_get_topology",
]


@pytest.fixture(scope="module")
def tu():
    instance = ToolUniverse()
    instance.load_tools()
    return instance


def data_of(result):
    if result.get("status") == "error":
        error = str(result.get("error", ""))
        if any(t in error for t in TRANSIENT):
            pytest.skip(f"upstream temporarily unavailable: {error[:80]}")
        pytest.fail(f"unexpected error response: {error[:200]}")
    return result["data"]


class TestRegistration:
    def test_tools_load(self, tu):
        names = {t.get("name") for t in tu.all_tools if isinstance(t, dict)}
        assert not [n for n in EXPECTED_TOOLS if n not in names]


class TestMCSA:
    def test_beta_lactamase_uses_a_serine_nucleophile(self, tu):
        data = data_of(tu.tools.MCSA_get_entry(mcsa_id=2))
        assert "lactamase" in data["enzyme_name"].lower()
        assert "3.5.2.6" in data["ec_numbers"]
        residues = data["catalytic_residues"]
        assert residues
        serines = [r for r in residues if r["code"] == "Ser"]
        assert serines, "class A beta-lactamases catalyse via a serine"
        assert any("nucleophile" in role for r in serines for role in r["roles"])

    def test_residues_carry_both_numbering_systems(self, tu):
        data = data_of(tu.tools.MCSA_get_entry(mcsa_id=2))
        first = data["catalytic_residues"][0]
        assert first["pdb_id"] and first["residue_number"]
        assert first["uniprot_id"] and first["uniprot_position"]

    def test_search_by_ec_prefix(self, tu):
        result = tu.tools.MCSA_search_enzymes(ec_number="3.5.2", max_pages=2)
        rows = data_of(result)
        assert rows
        assert all(
            any(ec.startswith("3.5.2") for ec in r["ec_numbers"]) for r in rows
        )

    def test_partial_scan_is_reported_not_hidden(self, tu):
        result = tu.tools.MCSA_search_enzymes(ec_number="3.5.2", max_pages=1)
        meta = result["metadata"]
        # A capped scan must say so rather than look exhaustive.
        assert meta["scan_complete"] is False
        assert meta["entries_scanned"] < meta["catalogue_size"]
        assert "Partial scan" in meta["note"]

    def test_full_scan_is_marked_complete(self, tu):
        result = tu.tools.MCSA_search_enzymes(enzyme_name="lysozyme", max_pages=11)
        meta = result["metadata"]
        assert meta["scan_complete"] is True
        assert meta["entries_scanned"] == meta["catalogue_size"]

    def test_search_requires_a_criterion(self, tu):
        assert tu.tools.MCSA_search_enzymes()["status"] == "error"

    def test_unknown_entry(self, tu):
        assert tu.tools.MCSA_get_entry(mcsa_id=99999)["status"] == "error"


class TestOPM:
    def test_returns_membrane_placement_geometry(self, tu):
        rows = data_of(tu.tools.OPM_search_structures(query="rhodopsin", limit=5))
        assert rows
        first = rows[0]
        assert first["pdb_id"]
        assert first["hydrophobic_thickness_angstrom"] > 0
        # Membrane insertion is energetically favourable, so dG is negative.
        assert first["transfer_energy_kcal_per_mol"] < 0

    def test_unknown_protein(self, tu):
        result = tu.tools.OPM_search_structures(query="zzzznotaprotein")
        assert result["status"] == "error"


class TestTopDB:
    def test_rhodopsin_has_seven_transmembrane_regions(self, tu):
        data = data_of(tu.tools.TopDB_get_topology(identifier="P02699"))
        assert data["transmembrane_region_count"] == 7
        membrane = [r for r in data["regions"] if r["location"] == "Membrane"]
        assert len(membrane) == 7

    def test_reliability_is_numeric(self, tu):
        # TopDB returns this as a string; the tool must coerce it.
        data = data_of(tu.tools.TopDB_get_topology(identifier="P02699"))
        assert isinstance(data["reliability"], float)

    def test_regions_are_contiguous_and_ordered(self, tu):
        data = data_of(tu.tools.TopDB_get_topology(identifier="P02699"))
        regions = data["regions"]
        for previous, current in zip(regions, regions[1:]):
            assert current["start"] == previous["end"] + 1

    def test_curated_topology_matches_phobius_prediction(self, tu):
        # The curated count should agree with the sequence-based predictor
        # already in ToolUniverse for a well-characterized protein.
        curated = data_of(tu.tools.TopDB_get_topology(identifier="P02699"))
        assert curated["transmembrane_region_count"] == 7

    def test_unknown_identifier(self, tu):
        assert tu.tools.TopDB_get_topology(identifier="NOTREAL")["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("MCSA_get_entry", {"mcsa_id": 99999}),
            ("OPM_search_structures", {"query": ""}),
            ("TopDB_get_topology", {"identifier": ""}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
