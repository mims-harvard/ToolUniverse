"""REST tools must identify themselves rather than send the requests default.

`python-requests/<version>` is refused outright by some public APIs. Harvard
Dataverse answers 403 to it and 200 to anything else for the same URL and the
same parameters, which made every `Dataverse_get_dataset` call fail while the
request itself was well formed.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit

CONFIG = {
    "name": "Example_get",
    "type": "BaseRESTTool",
    "fields": {"endpoint": "https://example.org/api/thing"},
    "parameter": {"type": "object", "properties": {}},
}


def test_session_sends_an_identifying_user_agent():
    agent = BaseRESTTool(CONFIG).session.headers["User-Agent"]
    assert agent.startswith("ToolUniverse/")
    assert "github.com/mims-harvard/ToolUniverse" in agent


def test_it_is_not_the_requests_default():
    agent = BaseRESTTool(CONFIG).session.headers["User-Agent"]
    assert agent != requests.utils.default_user_agent()
    assert "python-requests" not in agent


def test_a_configured_user_agent_still_wins():
    """`fields.headers` is applied per request, so it overrides the session."""
    config = dict(CONFIG)
    config["fields"] = dict(CONFIG["fields"], headers={"User-Agent": "Custom/9"})
    tool = BaseRESTTool(config)

    response = MagicMock()
    response.status_code = 200
    response.headers = {"content-type": "application/json"}
    response.json.return_value = {}
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry", return_value=response
    ) as sent:
        tool.run({})

    assert sent.call_args.kwargs["headers"]["User-Agent"] == "Custom/9"


def test_version_lookup_failure_does_not_break_construction():
    with patch("importlib.metadata.version", side_effect=Exception("no metadata")):
        agent = BaseRESTTool._user_agent()
    assert agent.startswith("ToolUniverse/")
