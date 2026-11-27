"""mcp_client_tool has to work on MCP Python SDK 1.x and on 2.x.

Two things changed in 2.0, and only one of them raises:

* ``streamablehttp_client`` was removed in favour of ``streamable_http_client``,
  which yields a 2-tuple and takes one pre-built httpx2 client instead of
  ``headers`` / ``timeout`` / ``sse_read_timeout`` / ``httpx_client_factory``.
  That one fails loudly, at import.
* every protocol field was renamed to snake_case, with the camelCase wire
  spelling left only on the Pydantic alias, so ``model_dump()`` stops emitting
  ``isError`` / ``structuredContent`` / ``inputSchema`` unless it is asked for
  ``by_alias=True``. Every reader in this package asks for the wire spelling,
  and asks with ``.get()``. That one fails silently: a failed remote call comes
  back with no ``isError`` key at all and is handed to the caller as a success.

Measured, on the same CallToolResult:

    mcp 1.30.0  model_dump keys: content, isError, meta, structuredContent
    mcp 2.3.0   model_dump keys: content, is_error, meta, result_type,
                                 structured_content

These tests supply both module shapes and both dump spellings themselves, so
they keep the same power whichever SDK version happens to be installed.
"""

import asyncio
import types
from contextlib import asynccontextmanager

import pytest

from tooluniverse import mcp_client_tool as mct

pytestmark = pytest.mark.unit


class _StubClient:
    """Stands in for the httpx/httpx2 AsyncClient the factory builds."""

    def __init__(self, headers, timeout, auth):
        self.headers = headers
        self.timeout = timeout
        self.auth = auth
        self.closed = False
        self.event_hooks = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        self.closed = True
        return False


class _Recorder:
    def __init__(self):
        self.calls = []
        self.clients = []

    def factory(self, headers=None, timeout=None, auth=None):
        client = _StubClient(headers, timeout, auth)
        self.clients.append(client)
        return client


def _v2_module(recorder):
    @asynccontextmanager
    async def streamable_http_client(
        url,
        *,
        http_client=None,
        terminate_on_close=True,
        max_sse_event_size=1024 * 1024,
    ):
        recorder.calls.append(
            {
                "url": url,
                "kwargs": {
                    "http_client": http_client,
                    "max_sse_event_size": max_sse_event_size,
                },
            }
        )
        yield ("read-v2", "write-v2")

    return types.SimpleNamespace(streamable_http_client=streamable_http_client)


def _v1_module(recorder):
    @asynccontextmanager
    async def streamablehttp_client(url, **kwargs):
        recorder.calls.append({"url": url, "kwargs": kwargs})
        # v1 yielded a third element, the get_session_id callback.
        yield ("read-v1", "write-v1", lambda: "session-id")

    return types.SimpleNamespace(streamablehttp_client=streamablehttp_client)


def _use(monkeypatch, module):
    # The branch is chosen from the module itself, so supplying the module is
    # the whole of the setup: there is no flag to keep in step with it.
    monkeypatch.setattr(mct, "_streamable_http", module)


def _open(**kwargs):
    async def go():
        async with mct._open_streamable_http(**kwargs) as streams:
            return streams

    return asyncio.run(go())


def test_the_v2_transport_is_handed_one_client_carrying_the_timeouts(monkeypatch):
    recorder = _Recorder()
    _use(monkeypatch, _v2_module(recorder))

    streams = _open(
        endpoint="https://example.test/mcp/",
        headers={"Authorization": "Bearer t"},
        timeout=30,
        sse_read_timeout=960,
        client_factory=recorder.factory,
    )

    assert streams == ("read-v2", "write-v2")
    assert len(recorder.calls) == 1
    client = recorder.clients[0]
    assert recorder.calls[0]["url"] == "https://example.test/mcp/"
    assert recorder.calls[0]["kwargs"]["http_client"] is client
    assert client.headers == {"Authorization": "Bearer t"}
    # The long read for tools/call exists because a 330s call died at 300s.
    # v2 has no sse_read_timeout argument, so it has to survive as the read
    # half of the client's timeout -- a bare client would default to 5s.
    assert client.timeout.read == 960
    assert client.timeout.connect == 30
    # On this path the client is ours, so we have to close it.
    assert client.closed
    # 2.0's 1 MiB ceiling on one SSE event is a ceiling on one tool result,
    # and v1 had none. Leaving the default would make the upgrade itself the
    # reason a large result started failing.
    assert recorder.calls[0]["kwargs"]["max_sse_event_size"] is None


def test_the_v1_transport_keeps_its_keyword_arguments(monkeypatch):
    recorder = _Recorder()
    _use(monkeypatch, _v1_module(recorder))

    streams = _open(
        endpoint="https://example.test/mcp/",
        headers={"Authorization": "Bearer t"},
        timeout=30,
        sse_read_timeout=960,
        client_factory=recorder.factory,
    )

    # The third element is dropped, not passed on.
    assert streams == ("read-v1", "write-v1")
    kwargs = recorder.calls[0]["kwargs"]
    assert kwargs["headers"] == {"Authorization": "Bearer t"}
    assert kwargs["timeout"] == 30
    assert kwargs["sse_read_timeout"] == 960
    assert kwargs["httpx_client_factory"] == recorder.factory
    # On this path the library builds and owns the client.
    assert recorder.clients == []


def test_without_a_long_read_both_paths_keep_the_v1_default(monkeypatch):
    recorder = _Recorder()
    _use(monkeypatch, _v1_module(recorder))
    _open(
        endpoint="https://example.test/mcp/",
        timeout=30,
        sse_read_timeout=None,
        client_factory=recorder.factory,
    )
    # Absent, so streamablehttp_client applies its own read=300.
    assert "sse_read_timeout" not in recorder.calls[0]["kwargs"]

    recorder = _Recorder()
    _use(monkeypatch, _v2_module(recorder))
    _open(
        endpoint="https://example.test/mcp/",
        timeout=30,
        sse_read_timeout=None,
        client_factory=recorder.factory,
    )
    # v2 has no default worth having, so state v1's.
    assert recorder.clients[0].timeout.read == 300


class _SnakeCaseResult:
    """A 2.x result: the wire spelling lives only on the alias."""

    def model_dump(self, mode=None, by_alias=False):
        content = [{"type": "text", "text": "boom"}]
        if by_alias:
            return {"content": content, "isError": True, "structuredContent": None}
        return {"content": content, "is_error": True, "structured_content": None}


class _StubSession:
    def __init__(self, read_stream, write_stream):
        self.streams = (read_stream, write_stream)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def initialize(self):
        return None

    async def call_tool(self, name, arguments):
        return _SnakeCaseResult()


def test_a_failed_call_is_still_reported_as_a_failure(monkeypatch):
    recorder = _Recorder()
    _use(monkeypatch, _v2_module(recorder))
    monkeypatch.setattr(mct, "ClientSession", _StubSession)

    client = mct.BaseMCPClient("https://example.test/mcp/")
    dumped = asyncio.run(
        client._make_mcp_request("tools/call", {"name": "t", "arguments": {}})
    )

    # The dump has to carry the wire spelling, because that is what every
    # reader in this package asks for.
    assert "isError" in dumped
    assert "is_error" not in dumped
    # And the whole point: the failure is not swallowed.
    assert mct._unwrap_mcp_tool_result(dumped) == {"status": "error", "error": "boom"}


def test_a_modern_function_without_the_new_argument_is_still_callable(monkeypatch):
    # Measured: mcp 1.30 ships streamable_http_client too, yielding a 3-tuple
    # and taking no max_sse_event_size. Passing the argument on the strength
    # of the function's name alone is a TypeError.
    recorder = _Recorder()

    @asynccontextmanager
    async def streamable_http_client(url, *, http_client=None, terminate_on_close=True):
        recorder.calls.append({"url": url, "kwargs": {"http_client": http_client}})
        yield ("read", "write", lambda: "session-id")

    _use(
        monkeypatch,
        types.SimpleNamespace(streamable_http_client=streamable_http_client),
    )

    factory = _Recorder().factory
    streams = _open(
        endpoint="https://example.test/mcp/",
        timeout=30,
        sse_read_timeout=None,
        client_factory=factory,
    )

    assert streams == ("read", "write")
    assert "max_sse_event_size" not in recorder.calls[0]["kwargs"]


def test_the_old_transport_is_preferred_wherever_it_still_exists(monkeypatch):
    # 1.30 has both names. Taking the new one there would change the path
    # this package already runs on every supported 1.x, for no gain: the new
    # path exists for 2.0, where the old name is gone.
    recorder = _Recorder()
    both = _v1_module(recorder)
    both.streamable_http_client = _v2_module(recorder).streamable_http_client
    _use(monkeypatch, both)

    streams = _open(
        endpoint="https://example.test/mcp/",
        timeout=30,
        sse_read_timeout=960,
        client_factory=recorder.factory,
    )

    assert streams == ("read-v1", "write-v1")
    assert recorder.calls[0]["kwargs"]["sse_read_timeout"] == 960


def test_the_transport_is_chosen_by_the_attribute_not_a_version_string():
    # A version string is a claim about the package; the attribute is a fact
    # about the function that is about to be called.
    import mcp.client.streamable_http as installed

    assert mct._SDK_HAS_LEGACY_TRANSPORT is hasattr(installed, "streamablehttp_client")
    name = (
        "streamablehttp_client"
        if mct._SDK_HAS_LEGACY_TRANSPORT
        else "streamable_http_client"
    )
    assert callable(getattr(installed, name))
