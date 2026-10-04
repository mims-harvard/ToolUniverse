"""The relay answers 402 for a used-up call limit and for an ended sharing period.

Both are the owner's to change, and neither is an outage. At call time every 402 was called a
call limit; at load time a 402 was "not reachable right now ... will load again once its owner
brings it back online", for a machine that was online all along.
"""

from __future__ import annotations

import sys

import httpx
import pytest

if sys.version_info < (3, 11):  # builtin from 3.11; anyio depends on the backport below it
    from exceptiongroup import BaseExceptionGroup

from tooluniverse.execute_function import explain_remote_load_failure
from tooluniverse.mcp_client_tool import describe_remote_call_failure

RELAY = "https://api.example/relay/abc/mcp"


def refused(detail):
    request = httpx.Request("POST", RELAY)
    response = httpx.Response(402, request=request, json={"detail": detail})
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return exc
    raise AssertionError


def test_an_ended_sharing_period_is_named():
    message = describe_remote_call_failure(refused("remote server subscription expired"),
                                           RELAY, "lab_predict")

    assert "period" in message and "extend" in message
    assert "limit" not in message


def test_a_used_up_limit_is_still_a_limit():
    message = describe_remote_call_failure(refused("call limit reached"), RELAY, "lab_predict")

    assert "limit" in message


def test_a_402_while_loading_is_not_called_an_outage():
    config = {"connection_name": "alice-gpu", "server_url": RELAY, "auth_env": "TU_API_KEY"}
    detail = "Client error '402 Payment Required' for url 'https://api.example/relay/abc/mcp'"

    message, missing = explain_remote_load_failure(config, detail, {"TU_API_KEY": "tu-sk-x"})

    assert missing is False
    assert "back online" not in message and "not reachable" not in message
    assert "owner" in message and "402" in message


# ── a refusal must not be read from digits in the relay URL ──────────────────────

UNLUCKY = "http://localhost:8000/relay/7b2e4031-a9c2-4403-8f10-5c1e2d3b4a01/mcp"


def test_digits_in_the_server_id_are_not_a_status():
    """The relay id is random; one containing "4031" or "4403" made every failure a bad key."""
    config = {"connection_name": "alice-gpu", "server_url": UNLUCKY, "auth_env": "TU_API_KEY"}
    detail = f"Client error '402 Payment Required' for url '{UNLUCKY}'"

    message, _ = explain_remote_load_failure(config, detail, {"TU_API_KEY": "tu-sk-x"})

    assert "rejected the key" not in message


def test_the_platforms_own_words_choose_the_message():
    config = {"connection_name": "alice-gpu", "server_url": RELAY, "auth_env": "TU_API_KEY"}
    env = {"TU_API_KEY": "tu-sk-x"}

    expired, _ = explain_remote_load_failure(
        config, "Failed to discover tools: the server answered HTTP 402: remote server "
        "subscription expired", env)
    limited, _ = explain_remote_load_failure(
        config, "Failed to discover tools: the server answered HTTP 402: call limit reached", env)

    assert "period" in expired and "extend" in expired
    assert "limit" not in expired
    assert "request limit" in limited and "raise" in limited


def test_a_status_lost_on_the_way_is_taken_from_the_recorded_response():
    """What reaches the caller is an empty BrokenResourceError inside an exception group."""
    import anyio

    lost = BaseExceptionGroup("unhandled errors in a TaskGroup", [anyio.BrokenResourceError()])

    message = describe_remote_call_failure(lost, RELAY, "lab_predict",
                                           recorded=(402, {"detail": "call limit reached"}))

    assert "request limit" in message


def test_leaf_exception_stops_where_the_context_was_replaced():
    from tooluniverse.utils import leaf_exception

    try:
        try:
            raise ValueError("inner detail nobody should see")
        except ValueError:
            raise RuntimeError("the explanation") from None
    except RuntimeError as exc:
        assert str(leaf_exception(exc)) == "the explanation"


def test_discovery_reports_a_refused_notification(tmp_path):
    """End to end against a local server that refuses the notification after initialize."""
    import asyncio
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    from tooluniverse.mcp_client_tool import MCPAutoLoaderTool

    class Relay(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def do_DELETE(self):
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_POST(self):
            message = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if message.get("method") == "initialize":
                code, body = 200, {"jsonrpc": "2.0", "id": message["id"], "result": {
                    "protocolVersion": "2025-06-18", "capabilities": {},
                    "serverInfo": {"name": "relay", "version": "1"}}}
            else:
                code, body = 402, {"detail": "call limit reached"}
            raw = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Relay)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/relay/abc/mcp"
    loader = MCPAutoLoaderTool({"name": "x", "server_url": url, "tool_prefix": "x_",
                                "timeout": 30})
    try:
        with pytest.raises(Exception) as caught:
            asyncio.run(loader.discover_tools())
    finally:
        server.shutdown()

    assert "HTTP 402: call limit reached" in str(caught.value)
