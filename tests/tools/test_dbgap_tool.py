"""Tests for the dbGaP tool.

dbGaP no longer exists in NCBI's E-utilities (the 'gap' database was
removed); this uses a standards-based FHIR API instead, found via a
"dbGaP FHIR" label buried in the advanced-search page's HTML. The server
also rate-limits aggressively -- back-to-back requests within the same
test run triggered HTTP 429 during development even though each request
succeeded fine in isolation -- so tests here keep network calls to a
minimum rather than issuing many in quick succession.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5", "HTTP 429")

DIABETES_STUDY = "phs000681"


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
        assert "DbGaP_search_studies" in names
        assert "DbGaP_get_study" in names


class TestSearchStudies:
    def test_finds_known_study(self, tu):
        rows = data_of(tu.tools.DbGaP_search_studies(query="diabetes", limit=10))
        assert any(r["phs_id"] == DIABETES_STUDY for r in rows)

    def test_missing_query(self, tu):
        assert tu.tools.DbGaP_search_studies(query="")["status"] == "error"


class TestGetStudy:
    def test_known_study_metadata(self, tu):
        data = data_of(tu.tools.DbGaP_get_study(phs_id=DIABETES_STUDY))
        assert "Diabetes" in data["title"]
        assert data["phenotype_dataset_count"] == 4
        assert data["variable_count"] == 15

    def test_unknown_study(self, tu):
        result = tu.tools.DbGaP_get_study(phs_id="NOTAREAL")
        assert result["status"] == "error"

    def test_missing_phs_id(self, tu):
        assert tu.tools.DbGaP_get_study(phs_id="")["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("DbGaP_search_studies", {"query": ""}),
            ("DbGaP_get_study", {"phs_id": ""}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
