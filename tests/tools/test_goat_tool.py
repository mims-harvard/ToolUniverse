"""Tests for the GoaT (Genomes on a Tree) tool.

GoaT indexes genome sequencing status across the Earth BioGenome Project,
Darwin Tree of Life, VGP, and ERGA against NCBI taxonomy; ToolUniverse's
taxonomy tools return classification, not assembly status. Tests assert a
real, known genome record: the African lion is a chromosome-level
assembly with 38 chromosomes.

The API rejects the standard form-encoded query string requests.get()
produces by default (space as '+' instead of '%20'), so this also guards
against a regression back to passing a raw params dict.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

LION = "Panthera leo"
LION_TAXID = "9689"


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
        assert "GoaT_get_species" in names


class TestGetSpecies:
    def test_lion_is_a_chromosome_level_assembly(self, tu):
        rows = data_of(tu.tools.GoaT_get_species(taxon=LION))
        assert rows
        row = rows[0]
        assert row["scientific_name"] == LION
        assert row["assembly_level"] == "Chromosome"
        assert row["chromosome_number"] == 38
        assert row["common_name"] == "African lion"

    def test_query_by_name_contains_a_space(self, tu):
        # Regression guard: the query has a literal space in it, which the
        # GoaT API rejects if form-encoded as '+' instead of '%20'.
        result = tu.tools.GoaT_get_species(taxon=LION)
        assert result["status"] == "success"

    def test_numeric_taxon_id_matches_name_lookup(self, tu):
        by_name = data_of(tu.tools.GoaT_get_species(taxon=LION))[0]
        by_id = data_of(tu.tools.GoaT_get_species(taxon=LION_TAXID))[0]
        assert by_name["taxon_id"] == by_id["taxon_id"] == LION_TAXID

    def test_include_descendants_expands_a_genus_query(self, tu):
        rows = data_of(
            tu.tools.GoaT_get_species(
                taxon="9688", include_descendants=True, limit=10
            )
        )
        assert len(rows) >= 2

    def test_limit_is_respected(self, tu):
        rows = data_of(
            tu.tools.GoaT_get_species(
                taxon="9688", include_descendants=True, limit=1
            )
        )
        assert len(rows) <= 1

    def test_unknown_taxon(self, tu):
        result = tu.tools.GoaT_get_species(taxon="Zzznotarealspecies12345")
        assert result["status"] == "error"

    def test_missing_taxon(self, tu):
        assert tu.tools.GoaT_get_species(taxon="")["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("GoaT_get_species", {"taxon": ""}),
            ("GoaT_get_species", {"taxon": "Zzznotarealspecies12345"}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
