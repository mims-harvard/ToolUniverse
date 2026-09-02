"""Tests for the BOLD Systems (Barcode of Life Data System) tool.

BOLD's standout capability is the BIN (Barcode Index Number): a
sequence-similarity DNA barcode cluster that ToolUniverse's existing
biodiversity tool (iDigBio) has no equivalent for. BOLD's own
tax:species triplet is silently ignored server-side (verified live
against several subscope-name guesses), so species-level search here
queries at genus level and filters client-side on the "species" field
of the returned records -- exercised directly below.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

LION_PROCESS_ID = "ABRMM002-06"
LION_BIN = "BOLD:AAD6819"


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
        assert "BOLDSystems_search_by_taxon" in names
        assert "BOLDSystems_search_by_bin" in names
        assert "BOLDSystems_get_record" in names


class TestSearchByTaxon:
    def test_genus_search(self, tu):
        rows = data_of(
            tu.tools.BOLDSystems_search_by_taxon(taxon_name="Panthera", rank="genus", limit=20)
        )
        assert rows
        genera = {r["genus"] for r in rows}
        assert genera == {"Panthera"}

    def test_species_filter_is_exact(self, tu):
        rows = data_of(
            tu.tools.BOLDSystems_search_by_taxon(
                taxon_name="Panthera leo", rank="species", limit=20
            )
        )
        assert rows
        # Every returned row must be the exact species, not sibling species
        # sharing the Panthera genus (the client-side filter's whole job).
        assert {r["species"] for r in rows} == {"Panthera leo"}

    def test_species_filter_excludes_other_species(self, tu):
        rows = data_of(
            tu.tools.BOLDSystems_search_by_taxon(
                taxon_name="Panthera uncia", rank="species", limit=20
            )
        )
        assert rows
        assert all(r["species"] == "Panthera uncia" for r in rows)
        assert all(r["species"] != "Panthera leo" for r in rows)

    def test_country_narrows_results(self, tu):
        all_rows = data_of(
            tu.tools.BOLDSystems_search_by_taxon(taxon_name="Panthera", rank="genus", limit=200)
        )
        india_rows = data_of(
            tu.tools.BOLDSystems_search_by_taxon(
                taxon_name="Panthera", rank="genus", country="India", limit=200
            )
        )
        assert len(india_rows) < len(all_rows)
        assert all(r["country/ocean"] == "India" for r in india_rows if r["country/ocean"])

    def test_limit_is_respected(self, tu):
        rows = data_of(
            tu.tools.BOLDSystems_search_by_taxon(taxon_name="Panthera", rank="genus", limit=3)
        )
        assert len(rows) <= 3

    def test_missing_taxon_name(self, tu):
        result = tu.tools.BOLDSystems_search_by_taxon(taxon_name="")
        assert result["status"] == "error"

    def test_invalid_rank(self, tu):
        result = tu.tools.BOLDSystems_search_by_taxon(taxon_name="Panthera", rank="phylum")
        assert result["status"] == "error"


class TestSearchByBin:
    def test_bin_search_returns_matching_records(self, tu):
        rows = data_of(tu.tools.BOLDSystems_search_by_bin(bin_id=LION_BIN, limit=50))
        assert rows
        assert all(r["bin_uri"] == LION_BIN for r in rows)

    def test_prefix_is_optional(self, tu):
        with_prefix = data_of(tu.tools.BOLDSystems_search_by_bin(bin_id=LION_BIN, limit=50))
        without_prefix = data_of(
            tu.tools.BOLDSystems_search_by_bin(bin_id="AAD6819", limit=50)
        )
        ids_with = {r["processid"] for r in with_prefix}
        ids_without = {r["processid"] for r in without_prefix}
        assert ids_with == ids_without

    def test_unknown_bin_returns_empty(self, tu):
        rows = data_of(tu.tools.BOLDSystems_search_by_bin(bin_id="BOLD:ZZZZZZZ"))
        assert rows == []

    def test_missing_bin_id(self, tu):
        result = tu.tools.BOLDSystems_search_by_bin(bin_id="")
        assert result["status"] == "error"


class TestGetRecord:
    def test_known_process_id(self, tu):
        data = data_of(tu.tools.BOLDSystems_get_record(process_id=LION_PROCESS_ID))
        assert data["species"] == "Panthera leo"
        assert data["bin_uri"] == LION_BIN

    def test_unknown_process_id(self, tu):
        result = tu.tools.BOLDSystems_get_record(process_id="NOTAREALID-99")
        assert result["status"] == "error"

    def test_missing_process_id(self, tu):
        result = tu.tools.BOLDSystems_get_record(process_id="")
        assert result["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("BOLDSystems_search_by_taxon", {"taxon_name": ""}),
            ("BOLDSystems_search_by_bin", {"bin_id": ""}),
            ("BOLDSystems_get_record", {"process_id": ""}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
