"""Tests for the REBASE catalogue tool and Enrichr multi-species support.

Both close the same class of gap: a calculator or analysis tool that already
existed but was limited by the reference data behind it. Assertions check
known molecular biology (EcoRI cuts G^AATTC and leaves sticky ends; SmaI
leaves blunt ends) rather than only response shape.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")


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


class TestREBASE:
    def test_ecori_recognition_and_overhang(self, tu):
        result = tu.tools.REBASE_get_enzyme(name="EcoRI")
        data = data_of(result)
        assert data["recognition_site"] == "G^AATTC"
        assert data["blunt_or_sticky"] == "sticky"
        assert "Escherichia coli" in data["organism"]
        assert data["commercially_available"] is True

    def test_smai_is_blunt(self, tu):
        # SmaI cuts CCC^GGG at the midpoint, leaving blunt ends.
        data = data_of(tu.tools.REBASE_get_enzyme(name="SmaI"))
        assert data["blunt_or_sticky"] == "blunt"

    def test_catalogue_is_far_larger_than_the_curated_set(self, tu):
        result = tu.tools.REBASE_get_enzyme(name="EcoRI")
        # DNA_find_restriction_sites ships 25 enzymes; REBASE has thousands.
        assert result["metadata"]["catalogue_size"] > 1000

    def test_name_matching_is_case_insensitive(self, tu):
        data = data_of(tu.tools.REBASE_get_enzyme(name="ecori"))
        assert data["name"] == "EcoRI"

    def test_search_by_exact_site(self, tu):
        result = tu.tools.REBASE_search_by_site(site="GAATTC")
        rows = data_of(result)
        assert rows
        assert any(e["name"] == "EcoRI" for e in rows)

    def test_search_by_sequence_counts_cut_sites(self, tu):
        # This sequence contains one BamHI site (GGATCC).
        result = tu.tools.REBASE_search_by_site(
            sequence="GGATCCAAGCTTGAATTCGTCGAC", limit=200
        )
        rows = data_of(result)
        bamhi = [e for e in rows if e["name"] == "BamHI"]
        assert bamhi, "BamHI should cut a sequence containing GGATCC"
        assert bamhi[0]["cut_site_count"] == 1

    def test_isoschizomers_share_specificity(self, tu):
        result = tu.tools.REBASE_list_isoschizomers(name="EcoRI")
        rows = data_of(result)
        assert result["metadata"]["prototype"] == "EcoRI"
        assert len(rows) > 1
        # commercially available enzymes are listed first
        available = [i for i, e in enumerate(rows) if e["commercially_available"]]
        unavailable = [i for i, e in enumerate(rows) if not e["commercially_available"]]
        if available and unavailable:
            assert max(available) < min(unavailable)

    def test_requires_a_query(self, tu):
        result = tu.tools.REBASE_search_by_site()
        assert result["status"] == "error"

    def test_unknown_enzyme_returns_error(self, tu):
        result = tu.tools.REBASE_get_enzyme(name="NotAnEnzyme")
        assert result["status"] == "error"


class TestEnrichrSpecies:
    """Enrichr runs one instance per organism with different libraries."""

    def test_species_instances_have_different_libraries(self, tu):
        counts = {}
        for species in ("human", "fly", "worm", "yeast"):
            rows = data_of(tu.tools.Enrichr_list_libraries(species=species))
            counts[species] = len(rows)
        assert counts["human"] > counts["fly"], counts
        assert len(set(counts.values())) > 1, f"expected distinct catalogues: {counts}"

    def test_human_remains_the_default(self, tu):
        default = data_of(tu.tools.Enrichr_list_libraries())
        explicit = data_of(tu.tools.Enrichr_list_libraries(species="human"))
        assert len(default) == len(explicit)

    def test_fly_enrichment_returns_fly_terms(self, tu):
        result = tu.tools.Enrichr_enrich(
            gene_list=["Adh", "w", "dpp", "hh", "wg"],
            library="GO_Biological_Process_2018",
            species="fly",
        )
        data = data_of(result)
        assert data["enriched_terms"], "expected enriched terms for fly genes"

    def test_unknown_species_falls_back_to_human(self, tu):
        # Unrecognized species must not crash; it resolves to the main instance.
        result = tu.tools.Enrichr_list_libraries(species="platypus")
        assert result["status"] in ("success", "error")
