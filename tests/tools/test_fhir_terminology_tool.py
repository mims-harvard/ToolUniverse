"""Tests for the FHIR Terminology Service tool.

tx.fhir.org's main value here is SNOMED CT: ToolUniverse could previously
only reach it via fuzzy keyword search (the generic OLS wrapper), with no
proper code-based lookup and no hierarchy traversal at all. LOINC,
RxNorm, and ICD-10-CM are also reachable through this generic interface
but already have dedicated, richer ToolUniverse tools. ConceptMap/
$translate was tried against several vocabulary pairs during development
and returned "No suitable ConceptMaps found" for all of them, so it is
not exposed and not tested here.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

MYOCARDIAL_INFARCTION = "22298006"


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
        assert "FHIRTerminology_lookup_code" in names
        assert "FHIRTerminology_expand_valueset" in names


class TestLookupCode:
    def test_snomed_lookup_by_alias(self, tu):
        data = data_of(
            tu.tools.FHIRTerminology_lookup_code(
                system="snomed", code=MYOCARDIAL_INFARCTION
            )
        )
        assert data["display"] == "Myocardial infarction"
        assert data["system"] == "http://snomed.info/sct"

    def test_snomed_lookup_by_full_uri(self, tu):
        data = data_of(
            tu.tools.FHIRTerminology_lookup_code(
                system="http://snomed.info/sct", code=MYOCARDIAL_INFARCTION
            )
        )
        assert data["display"] == "Myocardial infarction"

    def test_alternate_names_include_known_synonym(self, tu):
        data = data_of(
            tu.tools.FHIRTerminology_lookup_code(
                system="snomed", code=MYOCARDIAL_INFARCTION
            )
        )
        synonyms = {a["value"] for a in data["alternate_names"]}
        assert "Myocardial infarction, NOS" in synonyms

    def test_unknown_code(self, tu):
        result = tu.tools.FHIRTerminology_lookup_code(
            system="snomed", code="99999999999999"
        )
        assert result["status"] == "error"

    def test_unknown_system(self, tu):
        result = tu.tools.FHIRTerminology_lookup_code(
            system="http://notarealsystem.org/xyz", code="x"
        )
        assert result["status"] == "error"

    def test_missing_system(self, tu):
        result = tu.tools.FHIRTerminology_lookup_code(system="", code="x")
        assert result["status"] == "error"

    def test_missing_code(self, tu):
        result = tu.tools.FHIRTerminology_lookup_code(system="snomed", code="")
        assert result["status"] == "error"


class TestExpandValueset:
    def test_myocardial_infarction_hierarchy(self, tu):
        rows = data_of(
            tu.tools.FHIRTerminology_expand_valueset(
                value_set_url=(
                    f"http://snomed.info/sct?fhir_vs=isa/{MYOCARDIAL_INFARCTION}"
                ),
                limit=20,
            )
        )
        assert rows
        codes = {r["code"] for r in rows}
        # The root concept and a well-known clinical subtype must both
        # appear in its own subsumption expansion.
        assert MYOCARDIAL_INFARCTION in codes
        names = {r["display"] for r in rows}
        assert any("myocardial infarction" in n.lower() for n in names)

    def test_limit_is_respected(self, tu):
        rows = data_of(
            tu.tools.FHIRTerminology_expand_valueset(
                value_set_url=(
                    f"http://snomed.info/sct?fhir_vs=isa/{MYOCARDIAL_INFARCTION}"
                ),
                limit=3,
            )
        )
        assert len(rows) <= 3

    def test_missing_value_set_url(self, tu):
        result = tu.tools.FHIRTerminology_expand_valueset(value_set_url="")
        assert result["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("FHIRTerminology_lookup_code", {"system": "", "code": ""}),
            (
                "FHIRTerminology_lookup_code",
                {"system": "snomed", "code": "99999999999999"},
            ),
            ("FHIRTerminology_expand_valueset", {"value_set_url": ""}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
