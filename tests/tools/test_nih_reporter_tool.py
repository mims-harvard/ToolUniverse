"""Tests for the NIH RePORTER tool.

ToolUniverse had no funding-landscape layer; RePORTER indexes ~3 million
NIH-funded projects since 1985. The API's text-search parameter is
`advanced_text_search`, not the more obviously named `text_search`, which
is silently accepted but matches every record in the database (confirmed
during development: empty criteria and a `text_search` query returned the
identical total). Tests assert both that search actually filters and that
requested fields are genuinely populated, since a naming mismatch in
`include_fields` (e.g. 'OrgName' instead of 'Organization') is silently
dropped rather than erroring.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

CRISPR_PROJECT_NUM = "5R21EB036298-03"
CRISPR_APPL_ID = 11326711


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
        assert "NIHReporter_search_projects" in names
        assert "NIHReporter_get_project" in names


class TestSearchProjects:
    def test_search_actually_filters(self, tu):
        # Regression guard: a wrong search-field name matches everything.
        specific = tu.tools.NIHReporter_search_projects(
            query="CRISPR gene editing", limit=1
        )
        broad_total = specific["metadata"]["total_matching"]
        assert broad_total < 100_000

    def test_finds_known_project(self, tu):
        rows = data_of(
            tu.tools.NIHReporter_search_projects(
                query="CRISPR gene editing", limit=25
            )
        )
        assert any(r["project_num"] == CRISPR_PROJECT_NUM for r in rows)

    def test_fiscal_year_filter_narrows_results(self, tu):
        unfiltered = tu.tools.NIHReporter_search_projects(query="CRISPR", limit=1)
        filtered = tu.tools.NIHReporter_search_projects(
            query="CRISPR", fiscal_year=2024, limit=1
        )
        assert (
            filtered["metadata"]["total_matching"]
            < unfiltered["metadata"]["total_matching"]
        )

    def test_organization_field_is_populated(self, tu):
        # Regression guard for the OrgName vs Organization include_fields bug.
        rows = data_of(
            tu.tools.NIHReporter_search_projects(query="CRISPR", limit=5)
        )
        assert any(r["organization"] for r in rows)

    def test_limit_is_respected(self, tu):
        rows = data_of(
            tu.tools.NIHReporter_search_projects(query="cancer", limit=3)
        )
        assert len(rows) <= 3

    def test_unmatched_query(self, tu):
        result = tu.tools.NIHReporter_search_projects(
            query="zzzznotarealresearchterm12345"
        )
        assert result["status"] == "error"

    def test_missing_query(self, tu):
        assert tu.tools.NIHReporter_search_projects(query="")["status"] == "error"


class TestGetProject:
    def test_get_by_project_num(self, tu):
        data = data_of(
            tu.tools.NIHReporter_get_project(project_num=CRISPR_PROJECT_NUM)
        )
        assert "CRISPR" in data["title"]
        assert data["organization"]

    def test_get_by_appl_id_matches_project_num_lookup(self, tu):
        by_num = data_of(
            tu.tools.NIHReporter_get_project(project_num=CRISPR_PROJECT_NUM)
        )
        by_id = data_of(tu.tools.NIHReporter_get_project(appl_id=CRISPR_APPL_ID))
        assert by_num["title"] == by_id["title"]

    def test_unknown_project_num(self, tu):
        result = tu.tools.NIHReporter_get_project(project_num="NOTAREALPROJECT")
        assert result["status"] == "error"

    def test_missing_identifiers(self, tu):
        result = tu.tools.NIHReporter_get_project(project_num="")
        assert result["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("NIHReporter_search_projects", {"query": ""}),
            ("NIHReporter_get_project", {"project_num": ""}),
            ("NIHReporter_get_project", {"project_num": "NOTAREALPROJECT"}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
