"""A one- or two-letter token must not turn a query into a match-all."""

import pytest

from tooluniverse.single_cell_portal_tool import _phrase_query

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "query",
    ["B cell", "T cell", "NK cell", "B cell receptor", "T reg"],
)
def test_short_token_queries_are_quoted(query):
    """Unquoted, these matched on 'cell' alone and returned the whole portal."""
    effective, quoted = _phrase_query(query)
    assert quoted is True
    assert effective == f'"{query}"'


@pytest.mark.parametrize(
    "query",
    ["lung", "glioblastoma", "pancreatic islet", "lung adenocarcinoma"],
)
def test_ordinary_queries_are_left_alone(query):
    """Quoting these narrows them wrongly: 'lung adenocarcinoma' 90 -> 3."""
    effective, quoted = _phrase_query(query)
    assert quoted is False
    assert effective == query


@pytest.mark.parametrize("query", ['"B cell"', '"lung adenocarcinoma"'])
def test_an_explicit_phrase_is_not_quoted_twice(query):
    effective, quoted = _phrase_query(query)
    assert quoted is False
    assert effective == query


def test_surrounding_whitespace_is_trimmed():
    assert _phrase_query("  B cell  ") == ('"B cell"', True)
