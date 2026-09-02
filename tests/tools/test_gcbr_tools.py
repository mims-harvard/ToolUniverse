"""Unit tests for Global Core Biodata Resource tools.

Covers DDBJ (INSDC third member), BacDive (strain phenotypes), and
Orphadata (rare diseases). Assertions focus on the normalization these
tools perform, since all three upstream APIs return fields that are
sometimes scalars, sometimes lists, and sometimes nested objects.
"""

import pytest
from tooluniverse import ToolUniverse


EXPECTED_TOOLS = [
    "DDBJ_get_entry",
    "DDBJ_get_cross_references",
    "DDBJ_search_entries",
    "BacDive_search_by_taxon",
    "BacDive_get_strain",
    "Orphadata_get_disorder",
    "Orphadata_search_by_name",
    "Orphadata_get_epidemiology",
    "Orphadata_get_phenotypes",
]


@pytest.fixture(scope="module")
def tu():
    instance = ToolUniverse()
    instance.load_tools()
    return instance


# These upstreams are occasionally unreachable from CI. A transport failure is
# not a defect in the tool, so skip rather than fail; a structured error
# response (bad accession, unknown ID) is still asserted on normally.
TRANSIENT = ("timed out", "Failed to connect", "returned HTTP 5")


def data_of(result):
    """Return result['data'], skipping the test on a transient upstream failure."""
    if result.get("status") == "error":
        error = str(result.get("error", ""))
        if any(t in error for t in TRANSIENT):
            pytest.skip(f"upstream temporarily unavailable: {error[:80]}")
        pytest.fail(f"unexpected error response: {error[:200]}")
    return result["data"]


class TestRegistration:
    def test_tools_load(self, tu):
        names = {t.get("name") for t in tu.all_tools if isinstance(t, dict)}
        missing = [n for n in EXPECTED_TOOLS if n not in names]
        assert not missing, f"Tools failed to register: {missing}"

    def test_names_within_mcp_limit(self):
        assert not [n for n in EXPECTED_TOOLS if len(n) > 55]


class TestDDBJ:
    """DDBJ returns list-or-scalar fields; the tool must normalize them."""

    @pytest.mark.parametrize(
        "accession,expected_type",
        [
            ("DRP000001", "sra-study"),
            ("PRJDB3490", "bioproject"),
            ("SAMD00000001", "biosample"),
            ("DRX000001", "sra-experiment"),
            ("JGAS000001", "jga-study"),
            ("E-GEAD-1000", "gea"),
            ("MTBKS102", "metabobank"),
        ],
    )
    def test_entry_type_inferred_from_prefix(self, tu, accession, expected_type):
        result = tu.tools.DDBJ_get_entry(accession=accession)
        data_of(result)
        assert result["metadata"]["entry_type"] == expected_type

    def test_search_entries_actually_filters(self, tu):
        # Regression guard: several DDBJ-adjacent list endpoints (M-CSA,
        # MediaDive, DHS Program) silently ignore their search parameter
        # elsewhere in this codebase; confirm this one really filters.
        narrow = tu.tools.DDBJ_search_entries(
            entry_type="gea", keywords="daptomycin", limit=10
        )
        rows = data_of(narrow)
        assert rows
        assert narrow["metadata"]["total_matching"] < 100

    def test_search_entries_organism_filter(self, tu):
        result = tu.tools.DDBJ_search_entries(
            entry_type="bioproject",
            keywords="lung cancer",
            organism_taxid=9606,
            limit=5,
        )
        rows = data_of(result)
        assert rows

    def test_search_entries_unmatched_query(self, tu):
        result = tu.tools.DDBJ_search_entries(
            entry_type="gea", keywords="zzzznotarealterm12345"
        )
        assert result["status"] == "error"

    def test_search_entries_requires_valid_entry_type(self, tu):
        result = tu.tools.DDBJ_search_entries(
            entry_type="notarealtype", keywords="test"
        )
        assert result["status"] == "error"

    def test_organism_flattened_to_name_and_taxid(self, tu):
        # Upstream returns {"identifier": ..., "name": ...}
        result = tu.tools.DDBJ_get_entry(accession="PRJDB3490")
        data = data_of(result)
        assert isinstance(data["organism"], str)
        assert data["taxonomy_id"] is not None

    def test_list_valued_fields_are_always_lists(self, tu):
        result = tu.tools.DDBJ_get_entry(accession="DRX000001")
        data = data_of(result)
        for field in ("organization", "instrument_model", "platform",
                      "library_strategy", "library_source"):
            assert isinstance(data[field], list), f"{field} should be a list"

    def test_cross_references_filter_and_count(self, tu):
        result = tu.tools.DDBJ_get_cross_references(
            accession="DRP000001", reference_type="sra-run", limit=5
        )
        assert all(x["type"] == "sra-run" for x in data_of(result))
        assert "counts_by_type" in result["metadata"]

    def test_unrecognized_accession_explains_prefixes(self, tu):
        result = tu.tools.DDBJ_get_entry(accession="NOPE123")
        assert result["status"] == "error"
        assert "entry_type" in result["error"]


class TestBacDive:
    def test_search_by_taxon(self, tu):
        result = tu.tools.BacDive_search_by_taxon(
            genus="Bacillus", species="subtilis", limit=3
        )
        rows = data_of(result)
        assert 0 < len(rows) <= 3
        assert all("bacdive_id" in s for s in rows)

    def test_get_strain_phenotype(self, tu):
        result = tu.tools.BacDive_get_strain(bacdive_id=24493)
        data = data_of(result)
        assert data["bacdive_id"] == 24493
        assert data["genus"]
        # the point of BacDive: phenotype, not just taxonomy
        assert isinstance(data["culture_temperatures"], list)
        assert isinstance(data["oxygen_tolerance"], list)

    def test_unknown_strain_returns_error(self, tu):
        result = tu.tools.BacDive_get_strain(bacdive_id=999999999)
        assert result["status"] == "error"


class TestOrphadata:
    def test_get_disorder_with_cross_references(self, tu):
        result = tu.tools.Orphadata_get_disorder(orphacode=558)
        data = data_of(result)
        assert data["preferred_term"] == "Marfan syndrome"
        sources = {r["source"] for r in data["external_references"]}
        assert sources, "expected cross-references to OMIM/ICD/MeSH etc."

    def test_search_by_name_returns_orphacode(self, tu):
        result = tu.tools.Orphadata_search_by_name(name="Marfan syndrome")
        assert any(d["orphacode"] == 558 for d in data_of(result))

    def test_epidemiology(self, tu):
        rows = data_of(tu.tools.Orphadata_get_epidemiology(orphacode=558))
        assert rows
        assert "prevalence_class" in rows[0]

    def test_phenotypes_unwrap_nested_disorder(self, tu):
        # This service nests associations one level deeper than the others
        result = tu.tools.Orphadata_get_phenotypes(orphacode=558, limit=5)
        rows = data_of(result)
        assert rows, "phenotype list should not be empty"
        first = rows[0]
        assert first["hpo_id"].startswith("HP:")
        assert first["frequency"]

    def test_unknown_orphacode_returns_error(self, tu):
        result = tu.tools.Orphadata_get_disorder(orphacode=99999999)
        assert result["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("DDBJ_get_entry", {"accession": "BADACC"}),
            ("BacDive_get_strain", {"bacdive_id": 999999999}),
            ("Orphadata_get_disorder", {"orphacode": 99999999}),
            ("Orphadata_search_by_name", {"name": "zzzznotadisease"}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
