"""Wikidata_SPARQL_query / DBpedia_SPARQL_query only applied max_results when the
query had no LIMIT, so ``max_results=2`` on a query ending ``LIMIT 5`` returned 5 rows
although the parameter is documented as a result-limit override."""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.dbpedia_tool import DBpediaSPARQLTool
from tooluniverse.wikidata_sparql_tool import WikidataSPARQLTool

pytestmark = pytest.mark.unit

BINDINGS = {"results": {"bindings": [{"x": {"value": f"v{i}"}} for i in range(5)]}}


def _run(tool, module, arguments):
    response = MagicMock()
    response.json.return_value = BINDINGS
    with patch(f"tooluniverse.{module}.requests.get", return_value=response) as get:
        result = tool.run(arguments)
    return result, get.call_args.kwargs["params"]["query"]


CASES = [
    (WikidataSPARQLTool, "wikidata_sparql_tool"),
    (DBpediaSPARQLTool, "dbpedia_tool"),
]


@pytest.mark.parametrize("cls,module", CASES)
def test_max_results_caps_a_query_that_already_has_a_limit(cls, module):
    rows, query = _run(
        cls({"name": "x"}),
        module,
        {"sparql": "SELECT ?x WHERE {} LIMIT 5", "max_results": 2},
    )
    assert [r["x"] for r in rows] == ["v0", "v1"]
    assert query.count("LIMIT") == 1  # the query itself is left alone


@pytest.mark.parametrize("cls,module", CASES)
def test_max_results_still_appends_a_limit_when_the_query_has_none(cls, module):
    rows, query = _run(
        cls({"name": "x"}), module, {"sparql": "SELECT ?x WHERE {}", "max_results": 3}
    )
    assert query.rstrip().endswith("LIMIT 3")
    assert len(rows) == 3  # capped on the client side too


@pytest.mark.parametrize("cls,module", CASES)
def test_without_max_results_every_row_is_returned(cls, module):
    rows, _ = _run(cls({"name": "x"}), module, {"sparql": "SELECT ?x WHERE {} LIMIT 5"})
    assert len(rows) == 5
