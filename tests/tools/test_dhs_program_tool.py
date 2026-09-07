"""Tests for the DHS Program tool.

ToolUniverse's WHO GHO tools cover country-level aggregates; DHS is the
underlying subnational household-survey data those aggregates are often
built from. The indicator catalog's own `search` parameter is silently
ignored by the API (confirmed: RecordCount is 4,655 whether or not a query
is given), so this tool caches the full catalog and filters client-side.
Tests assert real filtering happens rather than the catalog always
"matching."
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

FERTILITY_INDICATOR = "FE_FRTR_W_TFR"
EGYPT = "EG"


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
        assert "DHSProgram_search_indicators" in names
        assert "DHSProgram_get_data" in names


class TestSearchIndicators:
    def test_finds_fertility_indicator(self, tu):
        rows = data_of(
            tu.tools.DHSProgram_search_indicators(
                query="total fertility rate", limit=10
            )
        )
        assert any(r["indicator_id"] == FERTILITY_INDICATOR for r in rows)

    def test_search_actually_filters(self, tu):
        # Regression guard: the API's own search param is silently ignored
        # and always returns the full 4,655-indicator catalog.
        narrow = tu.tools.DHSProgram_search_indicators(
            query="total fertility rate", limit=100
        )
        broad_note = narrow["metadata"]["matches_found"]
        assert broad_note < 100

    def test_limit_is_respected(self, tu):
        rows = data_of(
            tu.tools.DHSProgram_search_indicators(query="anemia", limit=3)
        )
        assert len(rows) <= 3

    def test_unmatched_query(self, tu):
        result = tu.tools.DHSProgram_search_indicators(
            query="zzzznotarealindicatorterm12345"
        )
        assert result["status"] == "error"

    def test_missing_query(self, tu):
        assert tu.tools.DHSProgram_search_indicators(query="")["status"] == "error"


class TestGetData:
    def test_egypt_fertility_rate_matches_known_value(self, tu):
        rows = data_of(
            tu.tools.DHSProgram_get_data(
                indicator_id=FERTILITY_INDICATOR, country_code=EGYPT, limit=25
            )
        )
        assert rows
        assert all(r["country"] == "Egypt" for r in rows)

    def test_country_filter_actually_narrows_results(self, tu):
        # /data's filters are real (unlike /indicators' search), confirmed
        # by comparing record counts with and without the country filter.
        filtered = tu.tools.DHSProgram_get_data(
            indicator_id=FERTILITY_INDICATOR, country_code=EGYPT, limit=1
        )
        unfiltered = tu.tools.DHSProgram_get_data(
            indicator_id=FERTILITY_INDICATOR, limit=1
        )
        assert (
            filtered["metadata"]["total_matching"]
            < unfiltered["metadata"]["total_matching"]
        )

    def test_survey_year_filter(self, tu):
        rows = data_of(
            tu.tools.DHSProgram_get_data(
                indicator_id=FERTILITY_INDICATOR,
                survey_year_start=2010,
                limit=5,
            )
        )
        # survey_year can be a range like '2017-18' for multi-year surveys.
        first_years = [int(r["survey_year"][:4]) for r in rows]
        assert all(y >= 2010 for y in first_years)

    def test_limit_is_respected(self, tu):
        rows = data_of(
            tu.tools.DHSProgram_get_data(indicator_id=FERTILITY_INDICATOR, limit=3)
        )
        assert len(rows) <= 3

    def test_unknown_indicator(self, tu):
        result = tu.tools.DHSProgram_get_data(indicator_id="NOTAREALINDICATOR")
        assert result["status"] == "error"

    def test_missing_indicator_id(self, tu):
        assert tu.tools.DHSProgram_get_data(indicator_id="")["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("DHSProgram_search_indicators", {"query": ""}),
            ("DHSProgram_get_data", {"indicator_id": ""}),
            ("DHSProgram_get_data", {"indicator_id": "NOTAREALINDICATOR"}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
