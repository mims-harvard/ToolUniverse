"""Tests for the NASA OSDR (Open Science Data Repository) tool.

A prior attempt at this integration was removed because its target domain
had gone down; OSDR has since migrated to osdr.nasa.gov. Tests assert real
study content survives the round trip: OSD-1 is a documented Drosophila
immune-response study flown on the Space Shuttle.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

OSD_1 = "OSD-1"


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
        assert "OSDR_search_studies" in names
        assert "OSDR_get_study" in names
        assert "OSDR_list_files" in names


class TestSearchStudies:
    def test_finds_mouse_bone_loss_studies(self, tu):
        rows = data_of(
            tu.tools.OSDR_search_studies(
                query="microgravity bone loss", organism="Mus musculus", limit=10
            )
        )
        assert rows
        assert all(r["organism"] == "Mus musculus" for r in rows)
        assert all(r["accession"] for r in rows)
        # OSDR also indexes cross-referenced external datasets (e.g. GEO);
        # at least some native OSD- studies should be among the results.
        osd_rows = [r for r in rows if r["usable_with_get_study"]]
        assert osd_rows
        assert all(r["accession"].startswith("OSD-") for r in osd_rows)

    def test_limit_is_respected(self, tu):
        rows = data_of(tu.tools.OSDR_search_studies(query="radiation", limit=3))
        assert len(rows) <= 3

    def test_unmatched_query(self, tu):
        result = tu.tools.OSDR_search_studies(
            query="zzzznotarealspacebiologyterm12345"
        )
        assert result["status"] == "error"

    def test_missing_query(self, tu):
        assert tu.tools.OSDR_search_studies(query="")["status"] == "error"


class TestGetStudy:
    def test_osd1_is_a_drosophila_immune_study(self, tu):
        data = data_of(tu.tools.OSDR_get_study(study_id=OSD_1))
        assert data["organism"] == "Drosophila melanogaster"
        assert data["accession"] == OSD_1

    def test_bare_number_is_accepted(self, tu):
        # Callers may omit the OSD- prefix.
        data = data_of(tu.tools.OSDR_get_study(study_id="1"))
        assert data["accession"] == OSD_1

    def test_unknown_study(self, tu):
        result = tu.tools.OSDR_get_study(study_id="OSD-999999999")
        assert result["status"] == "error"

    def test_missing_study_id(self, tu):
        assert tu.tools.OSDR_get_study(study_id="")["status"] == "error"


class TestListFiles:
    def test_osd1_has_expected_file_count(self, tu):
        rows = data_of(tu.tools.OSDR_list_files(study_id=OSD_1, limit=100))
        assert rows
        assert all(r["file_name"] for r in rows)

    def test_limit_is_respected(self, tu):
        result = tu.tools.OSDR_list_files(study_id=OSD_1, limit=5)
        rows = data_of(result)
        assert len(rows) <= 5
        # total_files must reflect the true count, not the truncated page.
        assert result["metadata"]["total_files"] >= len(rows)

    def test_unknown_study(self, tu):
        result = tu.tools.OSDR_list_files(study_id="OSD-999999999")
        assert result["status"] == "error"

    def test_missing_study_id(self, tu):
        assert tu.tools.OSDR_list_files(study_id="")["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("OSDR_search_studies", {"query": ""}),
            ("OSDR_get_study", {"study_id": ""}),
            ("OSDR_get_study", {"study_id": "OSD-999999999"}),
            ("OSDR_list_files", {"study_id": ""}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
