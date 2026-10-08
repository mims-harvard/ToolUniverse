"""Calling a published tool someone connected from the marketplace.

Driven as a consumer against a local platform: connecting to a published tool needs no key, so
`tu connect <url>` succeeded silently and the key was first mentioned at call time -- possibly
by an assistant, long after the person had left the terminal. The call-time message then said
"set the variable", which in practice means one shell. And for anyone who also shares a
machine, TOOLUNIVERSE_SERVICE_KEY holds the computer-only key, which this tool sent and the
platform refused with a sentence that assumed the reader knew there were two kinds of key.
"""

from __future__ import annotations

import io
import json
import os
import urllib.error

import pytest

from tooluniverse.platform_remote_tool import PlatformRemoteTool
from tooluniverse.remote_connections import BORROWER_KEY_ENV, api_keys_page

KEY = "tu-sk-" + "c" * 60
DEFAULT = "https://tooluniverse-backend.onrender.com"


@pytest.fixture
def clean_env(monkeypatch):
    for name in (BORROWER_KEY_ENV, "TOOLUNIVERSE_SERVICE_KEY"):
        monkeypatch.delenv(name, raising=False)


def tool(base_url: str = DEFAULT) -> PlatformRemoteTool:
    return PlatformRemoteTool({
        "name": "remote_shared_model",
        "type": "PlatformRemoteTool",
        "resource_id": "8faedc52-c800-4072-ab29-e0999cf29f74",
        "base_url": base_url,
        "parameter": {"type": "object", "properties": {}},
    })


def test_without_a_key_it_says_where_to_keep_one(clean_env):
    result = tool().run({})

    assert result["status"] == "error"
    message = result["error"]
    assert BORROWER_KEY_ENV in message
    assert ".tooluniverse/.env" in message and "every terminal" in message
    # The page's own name for the thing to create.
    assert "connection key" in message
    assert "https://connect.aiscientist.tools/api-keys" in message


def test_a_self_hosted_platform_is_not_sent_to_the_public_site(clean_env):
    message = tool("http://127.0.0.1:8000").run({})["error"]

    assert "aiscientist.tools" not in message


def test_the_account_key_is_preferred_over_the_sharing_key(clean_env, monkeypatch):
    monkeypatch.setenv("TOOLUNIVERSE_SERVICE_KEY", "tu-sk-" + "d" * 60)
    monkeypatch.setenv(BORROWER_KEY_ENV, KEY)

    assert PlatformRemoteTool._api_key_and_source() == (KEY, BORROWER_KEY_ENV)


def test_a_computer_only_key_refusal_is_translated(clean_env, monkeypatch):
    monkeypatch.setenv("TOOLUNIVERSE_SERVICE_KEY", KEY)
    body = json.dumps({"detail": "This computer-only connection can only register or "
                                 "reconnect its bound remote server"}).encode()

    def refuse(*args, **kwargs):
        raise urllib.error.HTTPError(DEFAULT + "/tools/call", 403, "", {}, io.BytesIO(body))

    t = tool()
    monkeypatch.setattr(t._opener, "open", refuse)

    message = t.run({})["error"]

    assert "TOOLUNIVERSE_SERVICE_KEY holds this computer's sharing connection" in message
    assert BORROWER_KEY_ENV in message and ".tooluniverse/.env" in message


def test_other_refusals_keep_the_platforms_own_words(clean_env, monkeypatch):
    monkeypatch.setenv(BORROWER_KEY_ENV, KEY)
    body = json.dumps({"detail": "call limit reached"}).encode()

    def refuse(*args, **kwargs):
        raise urllib.error.HTTPError(DEFAULT + "/tools/call", 402, "", {}, io.BytesIO(body))

    t = tool()
    monkeypatch.setattr(t._opener, "open", refuse)

    assert t.run({})["error"] == "call limit reached"


def test_the_site_mapping_is_shared_with_the_cli():
    """One table, so the CLI and the tool cannot name different sites."""
    from tooluniverse import cli

    assert cli._api_keys_page(DEFAULT) == api_keys_page(DEFAULT)
    assert cli.BORROWER_KEY_ENV == BORROWER_KEY_ENV


# ── connecting a published tool says the key is needed, while someone is looking ──


def test_connecting_a_published_tool_with_no_key_says_so(tmp_path, monkeypatch, capsys,
                                                         clean_env):
    from tooluniverse import cli

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "_read_stored_remote_key", lambda: "")
    monkeypatch.setattr(cli, "_platform_request", lambda *a, **k: {
        "tool_type": "remote-mcp", "name": "Shared Model", "description": "x",
        "input_schema": "{}"})
    import sys

    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)

    cli.cmd_connect(type("A", (), {
        "target": "8faedc52-c800-4072-ab29-e0999cf29f74", "service": DEFAULT,
        "name": None, "auth_env": None, "platform": True})())

    out = capsys.readouterr().out
    assert "Connected" in out
    assert "Running this tool needs an API key" in out
    # The connect already worked; telling them to run it again would be wrong.
    assert "run this again" not in out
    os.environ.pop(BORROWER_KEY_ENV, None)
