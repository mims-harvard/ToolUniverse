"""Regression guard: PubMed_search_articles must disclose that NCBI did not
run the query as submitted.

NCBI esearch silently drops quoted phrases it cannot match and answers a
broader query instead, reporting this in
``esearchresult.warninglist.quotedphrasesnotfound``. The tool previously read
only ``idlist`` and ``count``, so a query containing an unmatchable phrase
returned the results of a *different* query with nothing in the response to
say so. The warning data is now propagated into ``metadata``.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.pubmed_tool import PubMedRESTTool

pytestmark = pytest.mark.unit


def _tool():
    return PubMedRESTTool(
        {
            "name": "PubMed_search_articles",
            "fields": {
                "endpoint": (
                    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
                ),
                "db": "pubmed",
                "retmode": "json",
            },
        }
    )


def _esearch_response(esearch_result):
    resp = MagicMock()
    resp.status_code = 200
    resp.url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    resp.json.return_value = {"esearchresult": esearch_result}
    return resp


def _run(esearch_result, summaries):
    """Run the tool against a mocked esearch payload (no network)."""
    tool = _tool()
    with (
        patch.object(tool, "_enforce_rate_limit"),
        patch.object(tool, "_fetch_summaries", return_value=summaries),
        patch(
            "tooluniverse.pubmed_tool.request_with_retry",
            return_value=_esearch_response(esearch_result),
        ),
    ):
        return tool.run({"query": '"JAK2 V617F thrombosis unicornwombatxyz"'})


WARNING_LIST = {
    "quotedphrasesnotfound": ['"JAK2 V617F thrombosis unicornwombatxyz"'],
    "phrasesignored": ["and"],
    "outputmessages": ["No items found."],
}

ARTICLE = {
    "pmid": "42567343",
    "title": "Something about JAK2",
    "authors": [],
    "journal": "J Test",
    "url": "https://pubmed.ncbi.nlm.nih.gov/42567343/",
}


def test_unmatched_quoted_phrase_disclosed_in_metadata():
    result = _run(
        {
            "idlist": ["42567343"],
            "count": "540",
            "querytranslation": "jak2[All Fields] AND v617f[All Fields]",
            "warninglist": WARNING_LIST,
        },
        {"status": "success", "data": [ARTICLE]},
    )

    metadata = result["metadata"]
    # Existing semantics are untouched.
    assert result["status"] == "success"
    assert metadata["count"] == 1
    assert metadata["total"] == 540

    # The mismatch is unmissable at the top level of metadata.
    assert metadata["query_not_executed_as_submitted"] is True
    assert "BROADER" in metadata["warning"]

    assert metadata["quoted_phrases_not_found"] == [
        '"JAK2 V617F thrombosis unicornwombatxyz"'
    ]
    assert metadata["phrases_ignored"] == ["and"]
    assert metadata["executed_query"] == "jak2[All Fields] AND v617f[All Fields]"


def test_unmatched_quoted_phrase_disclosed_on_empty_result():
    result = _run(
        {
            "idlist": [],
            "count": "0",
            "querytranslation": "jak2[All Fields]",
            "warninglist": {
                "quotedphrasesnotfound": ['"unicornwombatxyz"'],
                "phrasesignored": [],
                "outputmessages": [],
            },
        },
        {"status": "success", "data": []},
    )

    metadata = result["metadata"]
    assert result["data"] == []
    assert metadata["total"] == 0
    assert metadata["query_not_executed_as_submitted"] is True
    assert metadata["quoted_phrases_not_found"] == ['"unicornwombatxyz"']
    assert metadata["executed_query"] == "jak2[All Fields]"
    # Empty warning categories are not emitted as noise.
    assert "phrases_ignored" not in metadata
    assert "ncbi_messages" not in metadata


@pytest.mark.parametrize(
    "warninglist",
    [
        None,
        {},
        {"quotedphrasesnotfound": [], "phrasesignored": [], "outputmessages": []},
    ],
    ids=["absent", "empty-dict", "all-empty-lists"],
)
def test_no_warning_keys_when_ncbi_reports_none(warninglist):
    esearch_result = {
        "idlist": ["42567343"],
        "count": "540",
        "querytranslation": "jak2[All Fields] AND v617f[All Fields]",
    }
    if warninglist is not None:
        esearch_result["warninglist"] = warninglist

    metadata = _run(esearch_result, {"status": "success", "data": [ARTICLE]})[
        "metadata"
    ]

    # Unaffected queries keep their original response shape exactly.
    assert set(metadata) == {"count", "total", "query", "source"}


def test_no_warning_keys_on_empty_result_without_warnings():
    metadata = _run(
        {"idlist": [], "count": "0"},
        {"status": "success", "data": []},
    )["metadata"]

    assert set(metadata) == {"count", "total", "query", "source"}
