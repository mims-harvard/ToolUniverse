"""ToolUniverseClient must accept the same calls as a local ToolUniverse.

The client is a drop-in stand-in for an in-process ToolUniverse, and callers
use those methods positionally -- TxAgent calls run_one_function(tool_call) and
tool_specification('CallAgent', return_prompt=True). The proxy was keyword-only,
so substituting the client raised

    method_proxy() takes 0 positional arguments but 1 was given

on the first tool call.
"""

import pytest

from tooluniverse.http_client import ToolUniverseClient

pytestmark = pytest.mark.unit


class _Recorder:
    """Stands in for requests.Session, capturing the posted payload."""

    def __init__(self):
        self.payload = None

    def post(self, url, json=None, timeout=None):
        self.payload = json

        class _R:
            status_code = 200

            @staticmethod
            def raise_for_status():
                return None

            @staticmethod
            def json():
                return {"success": True, "result": "ok", "error": None}

        return _R()


@pytest.fixture
def client(monkeypatch):
    c = ToolUniverseClient.__new__(ToolUniverseClient)
    c.base_url = "http://127.0.0.1:8000"
    c.session = _Recorder()
    return c


def test_single_positional_arg_is_bound(client):
    """run_one_function(tool_call) must reach the server as a named kwarg."""
    call = {"name": "Finish", "arguments": {}}
    client.run_one_function(call)
    kwargs = client.session.payload["kwargs"]
    assert "function_call_json" in kwargs or call in kwargs.values()


def test_positional_and_keyword_mix(client):
    """tool_specification('CallAgent', return_prompt=True) must work."""
    client.tool_specification("CallAgent", return_prompt=True)
    kwargs = client.session.payload["kwargs"]
    assert "CallAgent" in kwargs.values()
    assert kwargs.get("return_prompt") is True


def test_keyword_only_calls_still_work(client):
    """Existing keyword-only callers must be unaffected."""
    client.run_one_function(function_call_json={"name": "Finish", "arguments": {}})
    assert client.session.payload["method"] == "run_one_function"


def test_duplicate_argument_is_rejected(client):
    """Passing the same argument positionally and by name is an error."""
    with pytest.raises(TypeError, match="multiple values"):
        client.tool_specification("CallAgent", tool_name="Finish")


def test_too_many_positional_args_is_rejected(client):
    with pytest.raises(TypeError, match="positional"):
        client.run_one_function({"name": "Finish"}, "extra", "more", "still more")
