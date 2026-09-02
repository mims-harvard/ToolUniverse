"""Tests for the MDDB (Molecular Dynamics Database) tool.

ToolUniverse can run MD-adjacent predictions but had no way to find or
characterize an existing published trajectory. Tests assert real
simulation metadata survives the round trip: MD-A001UA is a documented
10 microsecond Amber ff99SB-ILDN simulation at 310K.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

RNA_POLYMERASE_SIM = "MD-A001UA"


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
        assert "MDDB_search_projects" in names
        assert "MDDB_get_project" in names


class TestSearchProjects:
    def test_search_actually_filters(self, tu):
        # Regression guard against a silently-ignored filter (seen elsewhere
        # this session): confirm the result count is far below the full
        # ~15,000-project catalog.
        result = tu.tools.MDDB_search_projects(query="kinase", limit=5)
        assert result["status"] == "success"
        assert result["metadata"]["total_matching"] < 1000

    def test_finds_known_pdb_id(self, tu):
        rows = data_of(tu.tools.MDDB_search_projects(query="6M71", limit=10))
        assert any(RNA_POLYMERASE_SIM == r["accession"] for r in rows)

    def test_limit_is_respected(self, tu):
        rows = data_of(tu.tools.MDDB_search_projects(query="kinase", limit=1))
        assert len(rows) <= 1

    def test_missing_query(self, tu):
        assert tu.tools.MDDB_search_projects(query="")["status"] == "error"


class TestGetProject:
    def test_known_simulation_parameters(self, tu):
        data = data_of(tu.tools.MDDB_get_project(accession=RNA_POLYMERASE_SIM))
        assert data["temperature_k"] == 310
        assert data["ensemble"] == "NPT"
        assert "Amber ff99SB-ILDN" in data["force_field"]
        assert data["total_frames"] > 0

    def test_unknown_accession(self, tu):
        result = tu.tools.MDDB_get_project(accession="NOTAREALACCESSION")
        assert result["status"] == "error"

    def test_missing_accession(self, tu):
        assert tu.tools.MDDB_get_project(accession="")["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("MDDB_search_projects", {"query": ""}),
            ("MDDB_get_project", {"accession": ""}),
            ("MDDB_get_project", {"accession": "NOTAREALACCESSION"}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
