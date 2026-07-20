"""Regression guard for Fix-R23C-1: AOPWiki's /aops and /events endpoints
return HTTP 200 with a body like
{"message": "This AOP does not exist.", "status": "unprocessable_entity"}
for an invalid id -- confirmed live for both endpoints. The existing
not-found check only matched numeric status codes (404, 500), which never
appear in this API's error body, so an invalid id silently produced a
status:"success" response with every field null/empty instead of an error.
"""

from unittest.mock import patch

import pytest

from tooluniverse.aopwiki_tool import AOPWikiDetailTool

pytestmark = pytest.mark.unit

_NOT_FOUND_BODY = {
    "message": "This AOP does not exist.",
    "status": "unprocessable_entity",
}
_EVENT_NOT_FOUND_BODY = {
    "message": "This event does not exist.",
    "status": "unprocessable_entity",
}

_REAL_AOP = {
    "id": 1,
    "title": "Uncharacterized liver damage leading to hepatocellular carcinoma",
    "short_name": "Liver damage and hepatocellular carcinoma",
    "created_at": "2016-11-29T18:41:15.000-05:00",
    "updated_at": "2023-04-29T16:02:54.000-04:00",
    "aop_stressors": [],
    "aop_mies": [],
    "aop_kes": [],
    "aop_aos": [],
}


class TestAopNotFound:
    def test_invalid_aop_id_returns_error_not_empty_success(self):
        tool = AOPWikiDetailTool({"settings": {}})

        with patch("tooluniverse.aopwiki_tool._get_json", return_value=_NOT_FOUND_BODY):
            result = tool.run({"aop_id": 999999})

        assert result["status"] == "error"
        assert "999999" in result["error"]

    def test_valid_aop_id_still_succeeds(self):
        tool = AOPWikiDetailTool({"settings": {}})

        with patch("tooluniverse.aopwiki_tool._get_json", return_value=_REAL_AOP):
            result = tool.run({"aop_id": 1})

        assert result["status"] == "success"
        assert result["data"]["id"] == 1
        assert result["data"]["title"].startswith("Uncharacterized liver damage")


class TestEventNotFound:
    def test_invalid_event_id_returns_error_not_empty_success(self):
        tool = AOPWikiDetailTool({"settings": {"endpoint_kind": "event"}})

        with patch(
            "tooluniverse.aopwiki_tool._get_json", return_value=_EVENT_NOT_FOUND_BODY
        ):
            result = tool.run({"event_id": 9999999})

        assert result["status"] == "error"
        assert "9999999" in result["error"]
