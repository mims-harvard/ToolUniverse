"""Regression tests for the DNS-rebinding advisory (GHSA-vx97-q3mm-h3r9).

A server bound to loopback is not, by itself, safe from remote browsers: DNS
rebinding lets a malicious webpage resolve its own origin to 127.0.0.1 and
become an in-browser client of a loopback-bound server, with a Host header
naming the attacker's domain (not "localhost") and, for fetch/XHR calls, a
matching Origin header. The prior bind-time-only guard
(``enforce_bind_security``) did not defend against this because it only ever
inspects the *configured bind address*, never the *inbound request*.

Covers three independent wirings of the same fix:

1. ``server_security.is_loopback_authority`` / ``is_loopback_origin`` — the
   request-time helpers.
2. The FastAPI app's ``guard_host_and_origin`` middleware, which rejects a
   loopback-bound request whose Host/Origin do not name loopback.
3. FastMCP-based servers (the main SMCP server and every standalone
   ``remote/*`` MCP tool server) opting in to FastMCP's own
   ``host_origin_protection="auto"`` via ``run()`` / ``run_fastmcp_server``.
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
