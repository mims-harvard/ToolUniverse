"""Tests for the GSA (Genome Sequence Archive) tool.

GSA has no JSON API -- only server-rendered, Chinese-labeled HTML
accession pages -- so this tool scrapes that page. These tests run
against the live site rather than a mock, since the whole point is
verifying the Chinese-label parsing (标题/项目编号/发布日期/etc.) actually
resolves to the right fields, and that both of GSA's distinct
"not found" page variants (a malformed accession's generic 404 panel,
and a well-formed-but-nonexistent accession's "does not exist" panel)
are handled the same way.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

MELANOMA_ACCESSION = "CRA002926"


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
    def test_tool_loads(self, tu):
        names = {t.get("name") for t in tu.all_tools if isinstance(t, dict)}
        assert "GSA_get_accession" in names


class TestGetAccession:
    def test_known_accession_resolves_full_record(self, tu):
        data = data_of(tu.tools.GSA_get_accession(accession=MELANOMA_ACCESSION))
        assert data["accession"] == MELANOMA_ACCESSION
        assert "melanoma" in data["title"].lower()
        assert data["bioproject_accession"] == "PRJCA003017"
        assert data["publication"]["pubmed_id"] == "32984050"
        assert data["download_urls"]["https"].endswith(MELANOMA_ACCESSION)

    def test_second_known_accession(self, tu):
        data = data_of(tu.tools.GSA_get_accession(accession="CRA000746"))
        assert data["accession"] == "CRA000746"
        assert data["title"]

    def test_accession_is_case_insensitive(self, tu):
        upper = data_of(tu.tools.GSA_get_accession(accession=MELANOMA_ACCESSION))
        lower = data_of(tu.tools.GSA_get_accession(accession=MELANOMA_ACCESSION.lower()))
        assert upper["title"] == lower["title"]

    def test_well_formed_but_nonexistent_accession(self, tu):
        result = tu.tools.GSA_get_accession(accession="CRA002828")
        assert result["status"] == "error"

    def test_malformed_accession(self, tu):
        result = tu.tools.GSA_get_accession(accession="CRA999999999")
        assert result["status"] == "error"

    def test_missing_accession(self, tu):
        result = tu.tools.GSA_get_accession(accession="")
        assert result["status"] == "error"


class TestErrorHandling:
    def test_returns_error_dict_not_exception(self, tu):
        result = tu.tools.GSA_get_accession(accession="")
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
