"""Regression tests for the DNS-rebinding advisory (GHSA-vx97-q3mm-h3r9).

A server bound to loopback is not, by itself, safe from remote browsers: DNS
rebinding lets a malicious webpage resolve its own origin to 127.0.0.1 and
become an in-browser client of a loopback-bound server, with a Host header
naming the attacker's domain (not "localhost") and, for fetch/XHR calls, a
matching Origin header. The prior bind-time-only guard
(``enforce_bind_security``) did not defend against this because it only ever
inspects the *configured bind address*, never the *inbound request*.

Covers four independent wirings of the same fix:

1. ``server_security.is_loopback_authority`` / ``is_loopback_origin`` — the
   request-time helpers.
2. The FastAPI app's ``guard_host_and_origin`` middleware, which rejects a
   loopback-bound request whose Host/Origin do not name loopback.
3. FastMCP-based servers (the main SMCP server and every standalone
   ``remote/*`` MCP tool server) opting in to FastMCP's own
   ``host_origin_protection="auto"`` via ``run()`` / ``run_fastmcp_server``.
4. ``ToolGraphWebUI``'s Flask ``before_request`` hook, which reuses the same
   helpers directly (Flask has no FastMCP-equivalent built-in) — found while
   verifying the fix for #531 and tracked separately as #557, since
   ``POST /api/load_graph`` deserializes a caller-supplied pickle path and was
   reachable with a spoofed Host/Origin exactly like the original report.
"""

import pytest

from tooluniverse import server_security as ss


@pytest.fixture(autouse=True)
def _clear_token(monkeypatch):
    monkeypatch.delenv(ss.API_TOKEN_ENV, raising=False)
    yield


# --------------------------------------------------------------------------- #
# server_security helpers
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "authority,loopback",
    [
        ("127.0.0.1", True),
        ("127.0.0.1:7000", True),
        ("localhost", True),
        ("localhost:7000", True),
        ("[::1]:7000", True),
        ("evil.example", False),
        ("evil.example:7000", False),
        ("0.0.0.0", False),
        ("", False),
        (None, False),
    ],
)
def test_is_loopback_authority(authority, loopback):
    assert ss.is_loopback_authority(authority) is loopback


@pytest.mark.parametrize(
    "origin,loopback",
    [
        ("http://127.0.0.1:7000", True),
        ("http://localhost:7000", True),
        ("http://[::1]:7000", True),
        ("http://evil.example", False),
        ("https://evil.example", False),
        ("null", False),
        ("", False),
        (None, False),
    ],
)
def test_is_loopback_origin(origin, loopback):
    assert ss.is_loopback_origin(origin) is loopback


def test_run_fastmcp_server_defaults_host_origin_protection(monkeypatch):
    captured = {}

    class _FakeServer:
        def run(self, **kwargs):
            captured.update(kwargs)

    ss.run_fastmcp_server(_FakeServer(), host="127.0.0.1", port=9000)

    assert captured["host_origin_protection"] == "auto"
    assert captured["transport"] == "streamable-http"


def test_run_fastmcp_server_respects_explicit_override(monkeypatch):
    captured = {}

    class _FakeServer:
        def run(self, **kwargs):
            captured.update(kwargs)

    ss.run_fastmcp_server(
        _FakeServer(), host="127.0.0.1", port=9000, host_origin_protection=False
    )

    assert captured["host_origin_protection"] is False


# --------------------------------------------------------------------------- #
# FastAPI app: guard_host_and_origin middleware
# --------------------------------------------------------------------------- #


def _client(base_url="http://127.0.0.1"):
    fastapi_testclient = pytest.importorskip("fastapi.testclient")
    from tooluniverse import http_api_server

    return fastapi_testclient.TestClient(http_api_server.app, base_url=base_url)


def test_guard_rejects_dns_rebinding_host():
    """A loopback-bound server must reject a Host naming the attacker's domain."""
    client = _client()
    resp = client.get("/health", headers={"Host": "evil.example"})
    assert resp.status_code == 421


def test_guard_allows_loopback_host():
    client = _client()
    resp = client.get("/health")
    assert resp.status_code == 200


def test_guard_rejects_cross_origin_browser_request():
    client = _client()
    resp = client.get("/health", headers={"Origin": "http://evil.example"})
    assert resp.status_code == 403


def test_guard_allows_loopback_origin():
    client = _client()
    resp = client.get("/health", headers={"Origin": "http://127.0.0.1:7000"})
    assert resp.status_code == 200


def test_guard_skipped_on_explicit_non_loopback_bind():
    """An operator who opted into a non-loopback bind (token required to get
    here at all) is not subject to the loopback Host/Origin allowlist — that
    guard exists to protect the *default* loopback trust boundary, not to
    constrain a deliberately-exposed deployment."""
    client = _client(base_url="http://testserver")
    resp = client.get("/health", headers={"Host": "evil.example"})
    assert resp.status_code == 200


# --------------------------------------------------------------------------- #
# SMCP.run(): opts in to FastMCP's own host/origin guard
# --------------------------------------------------------------------------- #


def test_smcp_run_defaults_host_origin_protection_to_auto(monkeypatch):
    from fastmcp import FastMCP

    from tooluniverse.smcp import SMCP

    captured = {}

    def fake_parent_run(self, *args, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(FastMCP, "run", fake_parent_run)

    server = object.__new__(SMCP)
    server._tooluniverse_banner_shown = True  # skip the banner thread
    server.run(transport="streamable-http", host="127.0.0.1", port=7000)

    assert captured["host_origin_protection"] == "auto"


def test_smcp_run_respects_explicit_host_origin_protection(monkeypatch):
    from fastmcp import FastMCP

    from tooluniverse.smcp import SMCP

    captured = {}

    def fake_parent_run(self, *args, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(FastMCP, "run", fake_parent_run)

    server = object.__new__(SMCP)
    server._tooluniverse_banner_shown = True
    server.run(
        transport="http",
        host="127.0.0.1",
        port=7000,
        host_origin_protection=False,
    )

    assert captured["host_origin_protection"] is False


def test_smcp_run_stdio_does_not_set_host_origin_protection(monkeypatch):
    from fastmcp import FastMCP

    from tooluniverse.smcp import SMCP

    captured = {}

    def fake_parent_run(self, *args, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(FastMCP, "run", fake_parent_run)

    server = object.__new__(SMCP)
    server._tooluniverse_banner_shown = True
    server.run(transport="stdio")

    assert "host_origin_protection" not in captured


# --------------------------------------------------------------------------- #
# ToolGraphWebUI: Flask before_request guard (#557)
# --------------------------------------------------------------------------- #


def _graph_ui_client():
    pytest.importorskip("flask")
    from tooluniverse.tool_graph_web_ui import ToolGraphWebUI

    ui = ToolGraphWebUI(graph_data_path=None)
    return ui, ui.app.test_client()


def test_graph_ui_rejects_dns_rebinding_host():
    """Default-constructed UI defaults to loopback (matching run()'s default),
    so the guard is active without needing to actually start the server."""
    _, client = _graph_ui_client()
    resp = client.get("/api/stats", headers={"Host": "evil.example"})
    assert resp.status_code == 421


def test_graph_ui_allows_loopback_host():
    _, client = _graph_ui_client()
    resp = client.get("/api/stats")
    assert resp.status_code == 404  # no graph loaded; guard let it through


def test_graph_ui_rejects_cross_origin_browser_request():
    _, client = _graph_ui_client()
    resp = client.get("/api/stats", headers={"Origin": "http://evil.example"})
    assert resp.status_code == 403


def test_graph_ui_allows_loopback_origin():
    _, client = _graph_ui_client()
    resp = client.get("/api/stats", headers={"Origin": "http://127.0.0.1:5000"})
    assert resp.status_code == 404


def test_graph_ui_dangerous_load_graph_endpoint_is_also_guarded():
    """POST /api/load_graph deserializes a caller-supplied pickle path — the
    endpoint the original finding centered on."""
    _, client = _graph_ui_client()
    resp = client.post(
        "/api/load_graph",
        json={"path": "/tmp/anything.pkl"},
        headers={"Host": "evil.example"},
    )
    assert resp.status_code == 421


def test_graph_ui_skipped_on_explicit_non_loopback_bind():
    ui, client = _graph_ui_client()
    ui._bind_host = "0.0.0.0"  # what run() would set for an explicit remote bind
    resp = client.get("/api/stats", headers={"Host": "evil.example"})
    assert resp.status_code == 404  # guard is a no-op; not what rejected it


def test_graph_ui_run_sets_bind_host(monkeypatch):
    pytest.importorskip("flask")
    from tooluniverse.tool_graph_web_ui import ToolGraphWebUI

    ui = ToolGraphWebUI(graph_data_path=None)
    monkeypatch.setattr(ui.app, "run", lambda **kw: None)  # don't actually bind
    ui.run(host="127.0.0.1", port=5000)
    assert ui._bind_host == "127.0.0.1"
