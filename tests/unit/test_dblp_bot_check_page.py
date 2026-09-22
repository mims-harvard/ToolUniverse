"""DBLP_search_publications parsed the bot-check HTML page as JSON.

dblp.org now answers programmatic clients with an anti-bot page (HTTP 200,
text/html). The tool called response.json() on it and surfaced
"Validation error: Expecting value: line 1 column 1 (char 0)", which says nothing
about the cause. It must report the HTML page (and must not try to get past it).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.dblp_tool import DBLPTool

pytestmark = pytest.mark.unit


def _response(status=200, body=None, text="", reason="OK"):
    response = MagicMock(status_code=status, reason=reason, text=text)
    if body is None:
        response.json.side_effect = ValueError("Expecting value")
    else:
        response.json.return_value = body
    return response


def _run(response):
    tool = DBLPTool({"name": "DBLP_search_publications"})
    with patch("tooluniverse.dblp_tool.requests.get", return_value=response) as get:
        return tool.run({"query": "attention is all you need"}), get


def test_bot_check_page_is_reported_as_html_not_as_a_parse_error():
    result, get = _run(
        _response(text="<!doctype html><title>Making sure you're not a bot!")
    )
    assert result["status"] == "error"
    assert "HTML page instead of JSON" in result["error"]
    assert (
        "bot-check" in result["reason"] and "Crossref_search_works" in result["reason"]
    )
    assert get.call_count == 1  # no retry with other headers to get past the check


def test_normal_json_response_still_returns_publications():
    body = {
        "result": {
            "hits": {
                "hit": [
                    {
                        "info": {
                            "title": "Attention is All you Need.",
                            "authors": {"author": [{"text": "Ashish Vaswani"}]},
                            "year": "2017",
                            "venue": "NIPS",
                            "url": "https://dblp.org/rec/conf/nips/VaswaniSPUJGKP17",
                        }
                    }
                ]
            }
        }
    }
    result, _ = _run(_response(body=body))
    assert result[0]["title"] == "Attention is All you Need."
    assert result[0]["year"] == 2017
