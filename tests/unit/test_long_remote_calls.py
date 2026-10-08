"""A borrowed model may run for minutes; the client must wait as long as the platform does.

Measured through `tu run` on a borrowed machine: a model call that took 330 seconds failed at
300 with "Cancelled via cancel scope ...; reason: deadline exceeded" -- the MCP library's
default read limit -- although the platform allowed it.
"""

from __future__ import annotations

import asyncio
import contextlib

import pytest

from tooluniverse import mcp_client_tool
from tooluniverse.mcp_client_tool import (
    REMOTE_CALL_READ_TIMEOUT,
    BaseMCPClient,
    describe_remote_call_failure,
)


class Stop(Exception):
    pass


def captured_read_timeout(monkeypatch, method):
    seen = {}

    @contextlib.asynccontextmanager
    async def fake_client(endpoint, **kwargs):
        seen.update(kwargs)
        raise Stop
        yield  # pragma: no cover

    monkeypatch.setattr(mcp_client_tool, "streamablehttp_client", fake_client)
    client = BaseMCPClient(server_url="https://api.example/relay/x/mcp", transport="http")
    with pytest.raises(Stop):
        asyncio.run(client._make_mcp_request(method, {"name": "predict", "arguments": {}}))
    return seen.get("sse_read_timeout", "library default")


def test_a_tool_call_waits_past_the_platforms_cap(monkeypatch):
    assert captured_read_timeout(monkeypatch, "tools/call") == REMOTE_CALL_READ_TIMEOUT
    assert REMOTE_CALL_READ_TIMEOUT > 15 * 60


def test_listing_tools_keeps_the_short_limit(monkeypatch):
    # A wedged server must not hold a load for a quarter of an hour.
    assert captured_read_timeout(monkeypatch, "tools/list") == "library default"


def test_a_deadline_is_said_plainly_and_warns_against_running_twice():
    error = Exception("Cancelled via cancel scope eaf598772680; reason: deadline exceeded")

    message = describe_remote_call_failure(error, "https://api.example/relay/x/mcp", "lab_predict")

    assert "cancel scope" not in message
    assert "lab_predict" in message and "may still be running" in message
