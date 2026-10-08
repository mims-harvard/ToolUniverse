"""WHO_Guidelines_Search answered 403 for queries that fall through to WHO IRIS.

The tool's session sends a browser-style User-Agent (needed for www.who.int topic pages),
and the IRIS call inherited it. iris.who.int rejects that agent -- and python-requests'
default one -- with 403 but serves an identified API client: "HIV" returned
"Failed to access WHO guidelines: 403 Client Error" while curl got 27,753 matches. The IRIS
request now says it is ToolUniverse and asks for JSON.
"""

from unittest.mock import MagicMock

import pytest

from tooluniverse.unified_guideline_tools import WHOGuidelinesTool

pytestmark = pytest.mark.unit

IRIS_BODY = {
    "_embedded": {
        "searchResult": {
            "page": {"totalElements": 27753},
            "_embedded": {
                "objects": [
                    {
                        "_embedded": {
                            "indexableObject": {
                                "name": "Use of rapid HIV tests",
                                "handle": "10665/1",
                                "metadata": {},
                            }
                        }
                    }
                ]
            },
        }
    }
}


def _tool():
    tool = WHOGuidelinesTool({"name": "WHO_Guidelines_Search"})
    response = MagicMock(status_code=200)
    response.json.return_value = IRIS_BODY
    tool.session = MagicMock()
    tool.session.get.return_value = response
    return tool


def test_iris_request_identifies_tooluniverse_and_asks_for_json():
    tool = _tool()
    tool._search_iris("HIV", 2)
    (url,), kwargs = tool.session.get.call_args
    assert url == "https://iris.who.int/server/api/discover/search/objects"
    assert kwargs["headers"]["Accept"] == "application/json"
    assert kwargs["headers"]["User-Agent"].startswith("ToolUniverse/")
    assert "Mozilla" not in kwargs["headers"]["User-Agent"]
    assert kwargs["params"]["query"] == "HIV"


def test_the_session_keeps_its_browser_style_agent_for_the_topic_pages():
    tool = WHOGuidelinesTool({"name": "WHO_Guidelines_Search"})
    assert "Mozilla" in tool.session.headers["User-Agent"]
