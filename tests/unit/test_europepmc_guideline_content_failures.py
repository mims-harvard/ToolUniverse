"""A failed per-record content fetch must not sink or corrupt a guideline search.

Observed live: one PubMed efetch that failed for a single record ended the whole
EuropePMC_Guidelines_Search with "local variable 'ET' referenced before
assignment", because a function-local import made ``ET`` unbound in the
``except ET.ParseError`` clause. Had it not crashed, the error message would have
been returned as that record's abstract.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from tooluniverse.unified_guideline_tools import (
    EuropePMCGuidelinesTool,
    _ContentUnavailable,
)

pytestmark = pytest.mark.unit

TITLE = "Clinical practice guideline for analgesia after hip fracture"
SHORT = "Recommendations for perioperative pain control."
LONG = "Guideline recommendation text. " * 12
ABSTRACT_XML = f"<PubmedArticle><Abstract><AbstractText>{LONG}</AbstractText></Abstract></PubmedArticle>"
FULLTEXT_XML = (
    "<article><body><sec><title>Recommendations</title>"
    "<p>Offer a nerve block at admission.</p></sec></body></article>"
)


def _response(content="", status_code=200, payload=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content.encode()
    resp.json.return_value = payload
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"{status_code} Client Error"
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def _session(abstract, fulltext=None):
    """Route session.get by URL. Each argument is a response or an exception."""

    def get(url, params=None, timeout=None):
        if "efetch" in url:
            source = abstract
        elif "fullTextXML" in url:
            source = fulltext if fulltext is not None else _response(status_code=404)
        else:
            return _response(
                payload={
                    "hitCount": 1,
                    "resultList": {
                        "result": [
                            {"title": TITLE, "pubType": "Guideline", "pmid": "123"}
                        ]
                    },
                }
            )
        if isinstance(source, Exception):
            raise source
        return source

    return get


def _search(abstract, fulltext=None):
    tool = EuropePMCGuidelinesTool({"name": "EuropePMC_Guidelines_Search"})
    with patch.object(tool.session, "get", side_effect=_session(abstract, fulltext)):
        return tool.run({"query": "hip fracture analgesia", "limit": 1})


@pytest.mark.parametrize(
    "failure",
    [
        requests.exceptions.ConnectionError("connection reset"),
        _response(status_code=429),
    ],
)
def test_a_failed_abstract_fetch_keeps_the_search_and_the_record(failure):
    result = _search(failure)
    assert result["status"] == "success"
    (row,) = result["data"]
    assert row["title"] == TITLE
    assert row["abstract"] == "" and row["content"] == ""
    assert "PMID 123" in row["content_unavailable"][0]


def test_an_error_message_is_never_returned_as_abstract_text():
    row = _search(_response(status_code=429))["data"][0]
    assert "Error" not in row["abstract"]
    assert "429" in row["content_unavailable"][0]


def test_the_abstract_helper_raises_a_content_error_not_unbound_local():
    tool = EuropePMCGuidelinesTool({"name": "EuropePMC_Guidelines_Search"})
    with patch.object(
        tool.session, "get", side_effect=requests.exceptions.ConnectionError("down")
    ):
        with pytest.raises(_ContentUnavailable, match="ConnectionError"):
            tool._get_europepmc_abstract("123")


def test_a_failed_full_text_fetch_keeps_the_short_abstract():
    short = _response(
        f"<PubmedArticle><AbstractText>{SHORT}</AbstractText></PubmedArticle>"
    )
    row = _search(short, fulltext=requests.exceptions.Timeout("slow"))["data"][0]
    assert row["abstract"] == SHORT
    assert "Timeout" in row["content_unavailable"][0]


def test_no_full_text_available_keeps_the_short_abstract_and_is_not_an_error():
    short = _response(
        f"<PubmedArticle><AbstractText>{SHORT}</AbstractText></PubmedArticle>"
    )
    row = _search(short, fulltext=_response(status_code=404))["data"][0]
    assert row["abstract"] == SHORT
    assert "content_unavailable" not in row


def test_available_full_text_still_replaces_a_short_abstract():
    short = _response(
        f"<PubmedArticle><AbstractText>{SHORT}</AbstractText></PubmedArticle>"
    )
    row = _search(short, fulltext=_response(FULLTEXT_XML))["data"][0]
    assert row["abstract"] == "Recommendations: Offer a nerve block at admission."


def test_a_complete_abstract_is_used_without_asking_for_full_text():
    row = _search(_response(ABSTRACT_XML))["data"][0]
    assert row["abstract"] == LONG.strip()
    assert "content_unavailable" not in row


def test_malformed_abstract_xml_is_still_a_visible_search_error():
    result = _search(_response("<PubmedArticle><AbstractText>unterminated"))
    assert result["status"] == "error"
    assert "parse Europe PMC abstract XML" in result["error"]
