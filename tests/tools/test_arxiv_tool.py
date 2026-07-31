"""
Unit tests for ArXivTool's search-query construction.

Covers the AND-by-default tokenization of unprefixed, non-boolean multi-word
queries: adding more space-separated keywords narrows results (every token
must match) rather than broadening them. This is intentional but easy to
trip over -- callers who want broader recall across synonyms must join them
with an explicit `OR`.
"""

import json

import pytest


@pytest.fixture
def tool():
    with open("src/tooluniverse/data/arxiv_tools.json") as f:
        tools = json.load(f)
    tool_config = next(t for t in tools if t["name"] == "ArXiv_search_papers")

    from tooluniverse.arxiv_tool import ArXivTool

    return ArXivTool(tool_config)


class TestBuildSearchQuery:
    def test_single_keyword(self, tool):
        assert tool._build_search_query("transformers") == "all:transformers"

    def test_multi_keyword_is_anded(self, tool):
        """Space-separated keywords are ANDed (all must match) -- narrows,
        not broadens. More synonyms make the query stricter, not looser."""
        query = tool._build_search_query("quantum computing hardware")
        assert query == "all:quantum AND all:computing AND all:hardware"

    def test_quoted_phrase_kept_intact(self, tool):
        query = tool._build_search_query('"neural networks" transformers')
        assert query == 'all:"neural networks" AND all:transformers'

    def test_explicit_or_passed_through(self, tool):
        """Callers who want broader recall across synonyms must write OR
        explicitly -- the tool does not add it automatically."""
        query = tool._build_search_query('"machine learning" OR "deep learning"')
        assert query == '"machine learning" OR "deep learning"'

    def test_field_prefix_passed_through(self, tool):
        assert tool._build_search_query("cat:cs.AI") == "cat:cs.AI"

    def test_single_prefix_multiword_value_autoquoted(self, tool):
        assert tool._build_search_query("au:Shanghua Gao") == 'au:"Shanghua Gao"'


class TestDateRangeSemantics:
    """date_from/date_to filter on arXiv's submittedDate, i.e. the date of
    the FIRST version -- a paper revised/updated after date_from but
    originally submitted before it will still be excluded."""

    def test_date_range_uses_submitted_date_field(self, tool):
        search_query = tool._build_search_query("quantum computing")
        assert "submittedDate" not in search_query  # asserted separately in _search

    def test_search_appends_submitted_date_clause(self, tool, monkeypatch):
        captured = {}

        def fake_request(session, method, url, params, **kwargs):
            captured["params"] = params

            class Resp:
                status_code = 200
                text = '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
                reason = "OK"

            return Resp()

        monkeypatch.setattr("tooluniverse.arxiv_tool.request_with_retry", fake_request)
        monkeypatch.setattr(tool, "_respect_rate_limit", lambda: None)

        tool._search(
            "quantum computing", 5, "submittedDate", "descending", "2025-01-01", None
        )

        assert (
            "submittedDate:[20250101000000 TO 29991231235959]"
            in captured["params"]["search_query"]
        )
