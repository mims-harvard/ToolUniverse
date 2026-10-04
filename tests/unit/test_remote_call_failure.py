"""What an AI assistant is told when a call to a borrowed machine fails.

The error used to be str(exc). anyio wraps a single network failure in an exception group, so
an assistant whose borrowed machine had gone offline received "unhandled errors in a TaskGroup
(1 sub-exception)" and relayed it to the scientist -- measured through `tu serve`.

For the relay, the advice also has to respect whether the call may already have run: retrying
one that did would run a GPU job twice, so "safe to try again" is said only when the platform
says so explicitly.
"""

from __future__ import annotations

import sys

import httpx
import pytest

if sys.version_info < (3, 11):  # builtin from 3.11; anyio depends on the backport below it
    from exceptiongroup import BaseExceptionGroup

from tooluniverse.mcp_client_tool import describe_remote_call_failure
from tooluniverse.utils import concise_exception_message, leaf_exception

RELAY = "https://api.example/relay/abc/mcp"
TOOL = "alice_gpu_predict"


def http_error(status: int, body=None, url: str = RELAY) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", url)
    kwargs = {"json": body} if body is not None else {"content": b""}
    response = httpx.Response(status, request=request, **kwargs)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return exc
    raise AssertionError("raise_for_status did not raise")


def grouped(exc: BaseException) -> BaseException:
    """Wrapped the way anyio wraps it, which is the shape that reached the assistant."""
    return BaseExceptionGroup("unhandled errors in a TaskGroup", [exc])


# ── the wrapper is never the message ─────────────────────────────────────────────


def test_the_group_wrapper_text_never_reaches_the_caller():
    message = describe_remote_call_failure(grouped(http_error(503, {})), RELAY, TOOL)

    assert "TaskGroup" not in message
    assert "sub-exception" not in message


def test_the_leaf_is_found_through_groups_and_causes():
    inner = http_error(503, {})
    try:
        try:
            raise inner
        except httpx.HTTPStatusError as e:
            raise RuntimeError("Failed to call tool") from e
    except RuntimeError as outer:
        wrapped = grouped(outer)

    assert leaf_exception(wrapped) is inner
    assert "503" in concise_exception_message(wrapped)


# ── whether to retry is the platform's call ─────────────────────────────────────


def test_may_have_executed_says_do_not_rerun():
    message = describe_remote_call_failure(
        grouped(http_error(503, {"may_have_executed": True})), RELAY, TOOL)

    assert "Do not run it again automatically" in message
    assert "safe to try again" not in message


def test_explicitly_did_not_run_says_it_is_safe_to_retry():
    message = describe_remote_call_failure(
        grouped(http_error(503, {"may_have_executed": False})), RELAY, TOOL)

    assert "did not run" in message and "safe to try again" in message


@pytest.mark.parametrize("body", [None, {}, {"detail": "busy"}])
def test_without_the_platforms_word_it_does_not_claim_safety(body):
    """Measured: through `tu serve` the body is streamed and unreadable here.

    The first version fell through to "the call did not run" in that case -- a claim with no
    evidence, on exactly the path where a retry can run a job twice.
    """
    message = describe_remote_call_failure(grouped(http_error(503, body)), RELAY, TOOL)

    assert "safe to try again" not in message
    assert "unknown" in message


# ── other refusals ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize("status", [401, 403])
def test_a_rejected_key_names_the_variable(status):
    message = describe_remote_call_failure(
        grouped(http_error(status, {})), RELAY, TOOL, auth_env="TU_API_KEY")

    assert "TU_API_KEY" in message and ".tooluniverse/.env" in message


def test_the_owners_call_limit_is_named_as_the_owners():
    message = describe_remote_call_failure(grouped(http_error(402, {})), RELAY, TOOL)

    assert "limit" in message and "owner" in message


def test_the_tool_is_named_as_the_caller_knows_it():
    message = describe_remote_call_failure(grouped(http_error(503, {})), RELAY, TOOL)

    assert TOOL in message


# ── not a relay: no claims about owners or retrying ─────────────────────────────


def test_a_direct_mcp_server_just_gets_the_real_error():
    message = describe_remote_call_failure(
        grouped(http_error(503, {}, url="http://127.0.0.1:9000/mcp")),
        "http://127.0.0.1:9000/mcp", TOOL)

    assert "503" in message
    assert "owner" not in message and "TaskGroup" not in message


def test_a_non_http_failure_is_still_unwrapped():
    message = describe_remote_call_failure(
        grouped(ConnectionRefusedError("connection refused")), RELAY, TOOL)

    assert message == "connection refused"


# ── and the proxy tool actually uses it ──────────────────────────────────────────


def test_the_proxy_tool_reports_through_the_explainer(monkeypatch):
    """Testing the explainer alone left its one call site free to regress.

    Replacing that call with str(e) survived every test above, so this drives
    MCPProxyTool.run with a call that fails the way an offline borrowed machine does.
    """
    from tooluniverse.mcp_client_tool import MCPProxyTool

    tool = MCPProxyTool({
        "name": TOOL,
        "type": "MCPProxyTool",
        "server_url": RELAY,
        "target_tool_name": "predict",
        "transport": "http",
        "parameter": {"type": "object", "properties": {}},
    })

    async def fails(*args, **kwargs):
        raise grouped(http_error(503, {"may_have_executed": True}))

    async def no_session(*args, **kwargs):
        return None

    monkeypatch.setattr(tool, "call_tool", fails)
    monkeypatch.setattr(tool, "_close_session", no_session)

    result = tool.run({})

    assert result["status"] == "error"
    assert "TaskGroup" not in result["error"]
    assert "Do not run it again automatically" in result["error"]
    assert TOOL in result["error"]
