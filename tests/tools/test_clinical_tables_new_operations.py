"""Tests for the new ClinicalTablesTool operations: HCPCS, star alleles,
and NPI provider/organization search.

These extend the existing ClinicalTablesTool (which already covered
rxterms, conditions, and disease_names) rather than duplicating a new
class under the same name. NPI search pairs directly with the existing
CMSOpenPaymentsTool: that tool's records are keyed by NPI with no way to
resolve who the NPI actually belongs to. The pre-existing three
operations (RxTerms_search_drugs, HealthConditions_search,
DiseaseNames_search) have no dedicated test file and are out of scope
here; a quick regression check confirms they still work unaffected.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")


@pytest.fixture(scope="module")
def tu():
    instance = ToolUniverse()
    instance.load_tools()
    return instance


def results_of(result):
    if "error" in result:
        error = str(result.get("error", ""))
        if any(t in error for t in TRANSIENT):
            pytest.skip(f"upstream temporarily unavailable: {error[:80]}")
        pytest.fail(f"unexpected error response: {error[:200]}")
    return result["results"]


class TestRegistration:
    def test_new_tools_load(self, tu):
        names = {t.get("name") for t in tu.all_tools if isinstance(t, dict)}
        assert "HCPCS_search" in names
        assert "StarAlleles_search" in names
        assert "NPIProvider_search" in names

    def test_preexisting_tool_still_works(self, tu):
        # Regression guard: extending the shared class must not break the
        # tools that were already there.
        result = tu.tools.RxTerms_search_drugs(terms="metformin", max_results=3)
        assert results_of(result)


class TestHCPCS:
    def test_finds_wheelchair_codes(self, tu):
        rows = results_of(
            tu.tools.HCPCS_search(terms="wheelchair", max_results=10)
        )
        assert rows
        assert all(r["code"] and r["display"] for r in rows)

    def test_max_results_is_respected(self, tu):
        rows = results_of(tu.tools.HCPCS_search(terms="wheelchair", max_results=2))
        assert len(rows) <= 2

    def test_missing_terms(self, tu):
        result = tu.tools.HCPCS_search(terms="")
        assert result.get("status") == "error"


class TestStarAlleles:
    def test_cyp2d6_alleles_have_known_structure(self, tu):
        rows = results_of(tu.tools.StarAlleles_search(terms="CYP2D6", max_results=5))
        assert rows
        wild_type = next(
            (r for r in rows if r["alternate_name"] == "Wild-type"), None
        )
        assert wild_type is not None
        assert wild_type["code"] == "CYP2D6*1A"

    def test_missing_terms(self, tu):
        result = tu.tools.StarAlleles_search(terms="")
        assert result.get("status") == "error"


class TestNPIProvider:
    def test_individual_provider_search(self, tu):
        rows = results_of(tu.tools.NPIProvider_search(terms="Smith", max_results=5))
        assert rows
        assert all(r["is_organization"] is False for r in rows)
        assert all(len(r["NPI"]) == 10 and r["NPI"].isdigit() for r in rows)

    def test_organization_search_returns_organizations(self, tu):
        rows = results_of(
            tu.tools.NPIProvider_search(
                terms="Mayo Clinic", organization=True, max_results=5
            )
        )
        assert rows
        assert all(r["is_organization"] is True for r in rows)
        assert all("MAYO" in r["name.full"].upper() for r in rows)

    def test_missing_terms(self, tu):
        result = tu.tools.NPIProvider_search(terms="")
        assert result.get("status") == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("HCPCS_search", {"terms": ""}),
            ("StarAlleles_search", {"terms": ""}),
            ("NPIProvider_search", {"terms": ""}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result.get("status") == "error"
        assert isinstance(result.get("error"), str) and result["error"]
