"""A borrowed model may run for minutes; the client must wait as long as the platform does.

Measured through `tu run` on a borrowed machine: a model call that took 330 seconds failed at
300 with "Cancelled via cancel scope ...; reason: deadline exceeded" -- the MCP library's
default read limit -- although the platform allowed it.
"""

from __future__ import annotations

import asyncio
import contextlib
import types

import pytest

from tooluniverse import mcp_client_tool
from tooluniverse.mcp_client_tool import (
    _DEFAULT_SSE_READ_TIMEOUT,
    REMOTE_CALL_READ_TIMEOUT,
    BaseMCPClient,
    describe_remote_call_failure,
)


class Stop(Exception):
    pass


def captured_read_timeout(monkeypatch, method, *, v2):
    """The read limit this call ends up with, on either generation of the SDK.

    MCP SDK 1.x takes sse_read_timeout as an argument and applies its own
    read=300 when it is absent. 2.0 removed the argument: the limit has to
    travel as the read half of the httpx2 client's timeout instead. Both are
    exercised here, because the wait is the behaviour this file protects and
    the transport underneath it is not.
    """
    seen = {}

    if v2:

        @contextlib.asynccontextmanager
        async def fake_client(endpoint, *, http_client=None, **kwargs):
            seen["read"] = http_client.timeout.read
            raise Stop
            yield  # pragma: no cover

        module = types.SimpleNamespace(streamable_http_client=fake_client)
    else:

        @contextlib.asynccontextmanager
        async def fake_client(endpoint, **kwargs):
            # Absent means the library applies its own read=300.
            seen["read"] = kwargs.get("sse_read_timeout")
            raise Stop
            yield  # pragma: no cover

        module = types.SimpleNamespace(streamablehttp_client=fake_client)

    monkeypatch.setattr(mcp_client_tool, "_streamable_http", module)
    client = BaseMCPClient(
        server_url="https://api.example/relay/x/mcp", transport="http"
    )
    with pytest.raises(Stop):
        asyncio.run(
            client._make_mcp_request(method, {"name": "predict", "arguments": {}})
        )
    return seen["read"]


@pytest.mark.parametrize("v2", [False, True], ids=["sdk1", "sdk2"])
def test_a_tool_call_waits_past_the_platforms_cap(monkeypatch, v2):
    assert captured_read_timeout(monkeypatch, "tools/call", v2=v2) == (
        REMOTE_CALL_READ_TIMEOUT
    )
    assert REMOTE_CALL_READ_TIMEOUT > 15 * 60


@pytest.mark.parametrize("v2", [False, True], ids=["sdk1", "sdk2"])
def test_listing_tools_keeps_the_short_limit(monkeypatch, v2):
    # A wedged server must not hold a load for a quarter of an hour.
    read = captured_read_timeout(monkeypatch, "tools/list", v2=v2)
    # On 1.x the argument is absent, so the library's own read=300 applies; on
    # 2.0 there is no library default worth having, so the same number is
    # stated outright.
    assert read == (_DEFAULT_SSE_READ_TIMEOUT if v2 else None)
    assert _DEFAULT_SSE_READ_TIMEOUT < REMOTE_CALL_READ_TIMEOUT


def test_a_deadline_is_said_plainly_and_warns_against_running_twice():
    error = Exception(
        "Cancelled via cancel scope eaf598772680; reason: deadline exceeded"
    )

    message = describe_remote_call_failure(
        error, "https://api.example/relay/x/mcp", "lab_predict"
    )

    assert "cancel scope" not in message
    assert "lab_predict" in message and "may still be running" in message
