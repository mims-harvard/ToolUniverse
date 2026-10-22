"""WorldBank_search_indicators ignored the keyword.

``/v2/indicator`` has no text search, so the tool listed the same first page of all
29,544 indicators for every query ("GDP" returned LAC Equity Lab poverty rows). The
tool now searches the World Development Indicators catalog (~1,500 rows) itself.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse import worldbank_tool
from tooluniverse.worldbank_tool import WorldBankIndicatorSearchTool

pytestmark = pytest.mark.unit

DATA = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _ind(code, name, note=""):
    return {"id": code, "name": name, "sourceNote": note, "unit": ""}


CATALOG = [
    _ind("NE.TRD.GNFS.ZS", "Trade (% of GDP)"),
    _ind("NY.GDP.MKTP.CD", "GDP (current US$)"),
    _ind("SP.DYN.LE00.IN", "Life expectancy at birth, total (years)"),
    _ind("SH.IMM.MEAS", "Immunization, measles", "Vaccination coverage of children"),
    _ind("SP.POP.TOTL", "Population, total"),
]


def _search(arguments):
    tool = WorldBankIndicatorSearchTool({"name": "WorldBank_search_indicators"})
    with patch.object(tool, "_wdi_catalog", return_value=CATALOG):
        return tool.run(arguments)


def test_config_uses_the_search_tool_type():
    tools = json.loads((DATA / "worldbank_tools.json").read_text(encoding="utf-8"))
    config = next(t for t in tools if t["name"] == "WorldBank_search_indicators")
    assert config["type"] == "WorldBankIndicatorSearchTool"


def test_only_indicators_matching_the_keyword_are_returned():
    meta, items = _search({"query": "population"})["data"]
    assert [i["id"] for i in items] == ["SP.POP.TOTL"]
    assert meta["total"] == 1


def test_name_starting_with_the_query_outranks_a_shorter_name_that_merely_contains_it():
    _, items = _search({"query": "GDP"})["data"]
    assert [i["id"] for i in items] == ["NY.GDP.MKTP.CD", "NE.TRD.GNFS.ZS"]


def test_every_word_must_match_and_description_words_count():
    assert _search({"query": "life expectancy"})["data"][1][0]["id"] == "SP.DYN.LE00.IN"
    assert _search({"query": "life measles"})["data"][1] == []
    assert _search({"query": "vaccination"})["data"][1][0]["id"] == "SH.IMM.MEAS"


def test_nonsense_returns_an_empty_success_and_per_page_caps_the_list():
    result = _search({"query": "zzqxjvwk"})
    assert result["status"] == "success" and result["data"][1] == []
    assert _search({"query": "GDP", "per_page": 1})["count"] == 1


def test_blank_query_is_an_error():
    assert _search({"query": "  "})["status"] == "error"


def _page(items, page, pages):
    response = MagicMock()
    response.json.return_value = [{"page": page, "pages": pages}, items]
    return response


def test_catalog_is_downloaded_page_by_page_once_and_cached():
    tool = WorldBankIndicatorSearchTool({"name": "WorldBank_search_indicators"})
    responses = [_page(CATALOG[:3], 1, 2), _page(CATALOG[3:], 2, 2)]
    with (
        patch.object(worldbank_tool, "_catalog", []),
        patch(
            "tooluniverse.worldbank_tool.request_with_retry", side_effect=responses
        ) as request,
    ):
        first = tool.run({"query": "population"})
        second = tool.run({"query": "GDP"})
    assert request.call_count == 2  # two pages, fetched once for both searches
    assert [c.kwargs["params"]["page"] for c in request.call_args_list] == [1, 2]
    assert first["data"][1][0]["id"] == "SP.POP.TOTL"  # found on the second page
    assert second["data"][1][0]["id"] == "NY.GDP.MKTP.CD"


# Pagination contract: the search pages locally over the ranked matches and
# says how to continue, instead of silently stopping at per_page.


def test_different_queries_produce_different_hits_with_continuation():
    gdp = _search({"query": "GDP", "per_page": 1, "offset": 0})
    population = _search({"query": "population", "per_page": 1, "offset": 0})
    assert gdp["data"][1][0]["id"] == "NY.GDP.MKTP.CD"
    assert population["data"][1][0]["id"] == "SP.POP.TOTL"
    assert gdp["metadata"]["total_results"] == 2
    assert gdp["metadata"]["has_more"] is True
    assert gdp["metadata"]["next_offset"] == 1
    assert gdp["metadata"]["result_set_complete"] is False
    assert gdp["metadata"]["total_results_is_exact"] is True


def test_second_local_page_reaches_later_match():
    result = _search({"query": "GDP", "per_page": 1, "offset": 1})
    assert result["data"][1][0]["id"] == "NE.TRD.GNFS.ZS"
    assert result["data"][0]["offset"] == 1
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"query": "", "per_page": 10}, "query"),
        ({"query": "x", "per_page": 0}, "per_page"),
        ({"query": "x", "per_page": 1001}, "per_page"),
        ({"query": "x", "offset": -1}, "offset"),
        ({"query": "x", "offset": 1.5}, "offset"),
    ],
)
def test_invalid_search_pagination_is_explicit(arguments, parameter):
    tool = WorldBankIndicatorSearchTool({"name": "WorldBank_search_indicators"})
    with patch.object(tool, "_wdi_catalog") as catalog:
        result = tool.run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
    catalog.assert_not_called()
