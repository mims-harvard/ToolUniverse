"""Tests for the NCI EVS terminology tool.

Built as a sibling to the existing NCIt-only NCIThesaurusTool (same
public API, api-evsrest.nci.nih.gov) rather than modifying it, since
CTCAE, ICD-10-CM/ICD-9-CM, RadLex, and NDF-RT/MedRT had no dedicated
tool anywhere in ToolUniverse. Tests assert known clinical facts survive
the round trip, and that MedDRA -- listed in the API's own terminology
metadata but blocked with HTTP 403 on every query, since it is a
separately licensed vocabulary -- fails with an explanatory error rather
than a raw HTTP error.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

FEBRILE_NEUTROPENIA = "C143481"


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
        assert "NCIEVS_search_terminology" in names
        assert "NCIEVS_get_concept" in names


class TestSearchTerminology:
    def test_ctcae_grades_a_known_adverse_event(self, tu):
        rows = data_of(
            tu.tools.NCIEVS_search_terminology(
                terminology="ctcae5", term="neutropenia", limit=10
            )
        )
        assert any(r["code"] == FEBRILE_NEUTROPENIA for r in rows)
        assert any("Grade" in (r["name"] or "") for r in rows)

    def test_radlex_finds_fracture_terms(self, tu):
        # ICD-10-CM is intentionally not exercised here: ICD10Tool already
        # covers it via the same NLM Clinical Tables backend.
        rows = data_of(
            tu.tools.NCIEVS_search_terminology(
                terminology="radlex", term="fracture", limit=10
            )
        )
        assert rows
        assert all("fracture" in (r["name"] or "").lower() for r in rows)

    def test_limit_is_respected(self, tu):
        rows = data_of(
            tu.tools.NCIEVS_search_terminology(
                terminology="radlex", term="fracture", limit=3
            )
        )
        assert len(rows) <= 3

    def test_meddra_is_blocked_with_explanation(self, tu):
        result = tu.tools.NCIEVS_search_terminology(
            terminology="mdr", term="myocardial infarction"
        )
        assert result["status"] == "error"
        assert "licensed" in result["error"].lower()

    def test_unknown_terminology(self, tu):
        result = tu.tools.NCIEVS_search_terminology(
            terminology="notarealterm", term="x"
        )
        assert result["status"] == "error"

    def test_missing_terminology(self, tu):
        result = tu.tools.NCIEVS_search_terminology(terminology="", term="x")
        assert result["status"] == "error"

    def test_missing_term(self, tu):
        result = tu.tools.NCIEVS_search_terminology(terminology="ctcae5", term="")
        assert result["status"] == "error"


class TestGetConcept:
    def test_febrile_neutropenia_definition_and_meddra_crossref(self, tu):
        data = data_of(
            tu.tools.NCIEVS_get_concept(
                terminology="ctcae5", code=FEBRILE_NEUTROPENIA
            )
        )
        assert data["name"] == "Febrile neutropenia"
        assert "ANC" in data["definition"]
        assert data["properties"]["MedDRA_Code"]

    def test_unknown_code(self, tu):
        result = tu.tools.NCIEVS_get_concept(terminology="icd10cm", code="NOTREAL")
        assert result["status"] == "error"

    def test_meddra_get_concept_is_also_blocked(self, tu):
        result = tu.tools.NCIEVS_get_concept(terminology="mdr", code="10016288")
        assert result["status"] == "error"
        assert "licensed" in result["error"].lower()


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("NCIEVS_search_terminology", {"terminology": "", "term": "x"}),
            ("NCIEVS_search_terminology", {"terminology": "ctcae5", "term": ""}),
            ("NCIEVS_search_terminology", {"terminology": "mdr", "term": "x"}),
            ("NCIEVS_get_concept", {"terminology": "", "code": "x"}),
            ("NCIEVS_get_concept", {"terminology": "icd10cm", "code": "NOTREAL"}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
