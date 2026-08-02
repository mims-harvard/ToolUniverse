from __future__ import annotations

import copy
import json
import socket
from pathlib import Path

import pytest

from tooluniverse import vsd_source_intelligence as intelligence
from tooluniverse.vsd_source_intelligence import (
    VSDSourceIntelligenceError,
    assess_catalog_coverage,
    configured_source_inventory,
    crawl_source_candidates,
    load_trusted_source_catalog,
    prepare_core_handoff,
    render_core_issue,
    snapshot_source_candidate,
    submit_core_handoff,
    validate_core_handoff,
    validate_source_scan,
    validate_trusted_source_catalog,
    write_core_handoff,
    write_scan_report,
    write_snapshot_manifest,
)

pytestmark = pytest.mark.unit

HOST = "api.reporter.nih.gov"
SEED = f"https://{HOST}/docs"


class _ToolUniverse:
    tool_files: dict[str, str] = {}

    def __init__(self, *, existing: bool = True):
        self.all_tools = (
            [
                {
                    "name": "ExistingReporterSearch",
                    "type": "VSDReviewedOperationTool",
                    "vsd_operation": {
                        "endpoint": f"https://{HOST}/v2/projects/search",
                        "method": "POST",
                    },
                }
            ]
            if existing
            else []
        )


def _routes() -> dict[str, tuple[bytes, str]]:
    html = f"""
    <html><head>
      <link rel="service-desc" href="/openapi.json">
      <script type="application/ld+json">{{"distribution": "/events/asyncapi.yaml"}}</script>
    </head><body>
      <a href="/openapi.json">duplicate</a>
      <a href="/graphql/schema.graphql">graphql</a>
      <a href="/collections/rare.postman_collection.json">postman</a>
      <a href="/soap/service.wsdl">wsdl</a>
      <a href="/grpc/rare.proto">grpc</a>
      <a href="/.well-known/server.mcp.json">mcp</a>
      <a href="/private/secret.openapi.json">blocked</a>
      <a href="https://outside.example/openapi.json">outside</a>
      <a href="/openapi.json?token=secret">query</a>
    </body></html>
    """.encode()
    return {
        f"https://{HOST}/robots.txt": (
            b"User-agent: *\nDisallow: /private\n",
            "text/plain",
        ),
        SEED: (html, "text/html; charset=utf-8"),
        f"https://{HOST}/openapi.json": (
            json.dumps(
                {
                    "openapi": "3.1.0",
                    "info": {"title": "Rare Disease Grants", "version": "1"},
                    "paths": {},
                }
            ).encode(),
            "application/json",
        ),
        f"https://{HOST}/graphql/schema.graphql": (
            b"type Query { grants(disease: String!): [Grant!]! }\ntype Grant { id: ID! }",
            "application/graphql",
        ),
        f"https://{HOST}/events/asyncapi.yaml": (
            b"asyncapi: 3.0.0\ninfo:\n  title: Grant events\n  version: '1'\nchannels: {}\n",
            "application/yaml",
        ),
        f"https://{HOST}/collections/rare.postman_collection.json": (
            b'{"info":{"schema":"https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},"item":[]}',
            "application/json",
        ),
        f"https://{HOST}/soap/service.wsdl": (
            b'<definitions xmlns="http://schemas.xmlsoap.org/wsdl/" name="RareService"></definitions>',
            "application/wsdl+xml",
        ),
        f"https://{HOST}/grpc/rare.proto": (
            b'syntax = "proto3"; service RareService {}',
            "text/plain",
        ),
        f"https://{HOST}/.well-known/server.mcp.json": (
            b'{"serverUrl":"https://api.reporter.nih.gov/mcp","tools":[]}',
            "application/json",
        ),
    }


def _fetcher(routes: dict[str, tuple[bytes, str]]):
    def fetch(url: str, timeout: float, max_bytes: int):
        assert 1 <= timeout <= 60
        try:
            raw, content_type = routes[url]
        except KeyError as exc:
            raise VSDSourceIntelligenceError("fixture route missing") from exc
        if len(raw) > max_bytes:
            raise VSDSourceIntelligenceError("fixture exceeds requested bytes")
        return raw, {
            "url": url,
            "status_code": 200,
            "content_type": content_type,
            "response_bytes": len(raw),
            "headers": {"content-type": content_type},
            "peer_ip": "203.0.113.10",
            "redirects": 0,
        }

    return fetch


def _scan():
    catalog = load_trusted_source_catalog()
    inventory = configured_source_inventory(_ToolUniverse())
    return crawl_source_candidates(
        [SEED],
        catalog=catalog,
        inventory=inventory,
        max_pages=20,
        max_depth=2,
        fetcher=_fetcher(_routes()),
        scanned_at="2026-08-01T12:00:00+00:00",
    )


def test_catalog_has_fifty_one_unique_inert_authoritative_sources():
    catalog = load_trusted_source_catalog()
    assert len(catalog["sources"]) == 51
    assert len({item["source_id"] for item in catalog["sources"]}) == 51
    assert len({item["domain"] for item in catalog["sources"]}) == 51
    assert all(item["execution_allowed"] is False for item in catalog["sources"])
    assert all(
        item["review_state"] == "trusted_for_candidate_discovery"
        for item in catalog["sources"]
    )
    assert {item["access"] for item in catalog["sources"]} == {
        "public",
        "registration",
        "controlled",
        "mixed",
    }
    assert {item["trust_basis"] for item in catalog["sources"]} == {
        "official_government",
        "official_project",
        "official_standards_body",
    }

    tampered = copy.deepcopy(catalog)
    tampered["sources"][0]["execution_allowed"] = True
    with pytest.raises(VSDSourceIntelligenceError, match="execution boundary"):
        validate_trusted_source_catalog(tampered)


def test_inventory_and_catalog_coverage_find_exact_host_duplicates():
    catalog = load_trusted_source_catalog()
    inventory = configured_source_inventory(_ToolUniverse())
    coverage = assess_catalog_coverage(catalog, inventory)
    reporter = next(
        item for item in coverage["sources"] if item["source_id"] == "nih_reporter"
    )
    assert reporter == {
        "source_id": "nih_reporter",
        "domain": HOST,
        "coverage": "existing_host",
        "existing_tools": ["ExistingReporterSearch"],
    }
    assert coverage["existing_host_count"] == 1
    assert coverage["candidate_gap_count"] == len(catalog["sources"]) - 1

    tampered = copy.deepcopy(inventory)
    tampered["hosts"][0]["host"] = "changed.example"
    with pytest.raises(VSDSourceIntelligenceError, match="identity"):
        intelligence.validate_source_inventory(tampered)


def test_bounded_scan_discovers_seven_formats_and_enforces_robots_and_host_scope():
    report = _scan()
    assert report["candidate_count"] == 7
    assert report["pages_fetched"] == 8
    assert report["blocked_count"] == 1
    assert report["blocked_urls"] == [f"https://{HOST}/private/secret.openapi.json"]
    assert {item["format_hint"] for item in report["candidates"]} == {
        "openapi",
        "graphql",
        "asyncapi",
        "postman",
        "wsdl",
        "protobuf",
        "mcp",
    }
    assert len({item["url"] for item in report["candidates"]}) == 7
    assert all(
        item["trusted_source_id"] == "nih_reporter" for item in report["candidates"]
    )
    assert all(item["coverage"] == "existing_host" for item in report["candidates"])
    assert all(
        item["existing_tools"] == ["ExistingReporterSearch"]
        for item in report["candidates"]
    )
    assert all(
        item["approval_state"] == "unreviewed_source_candidate"
        for item in report["candidates"]
    )
    assert all(item["execution_allowed"] is False for item in report["candidates"])
    assert all("outside.example" not in item["url"] for item in report["candidates"])

    tampered = copy.deepcopy(report)
    tampered["candidates"][0]["quality_score"] = 100
    with pytest.raises(VSDSourceIntelligenceError, match="identity"):
        validate_source_scan(tampered)

    recomputed = copy.deepcopy(report)
    recomputed["raw_search_log"] = "must never cross the artifact boundary"
    body = {
        key: value
        for key, value in recomputed.items()
        if key not in {"scan_id", "scan_sha256"}
    }
    recomputed["scan_sha256"] = intelligence._digest(body)
    recomputed["scan_id"] = recomputed["scan_sha256"][:16]
    with pytest.raises(VSDSourceIntelligenceError, match="object"):
        validate_source_scan(recomputed)


def test_scan_fails_closed_on_unsafe_bounds_and_private_dns(monkeypatch):
    with pytest.raises(VSDSourceIntelligenceError, match="without credentials"):
        crawl_source_candidates([f"{SEED}?token=value"], fetcher=_fetcher(_routes()))
    with pytest.raises(VSDSourceIntelligenceError, match="robots.txt"):
        crawl_source_candidates(
            [SEED], respect_robots=False, fetcher=_fetcher(_routes())
        )
    with pytest.raises(VSDSourceIntelligenceError, match="max_pages"):
        crawl_source_candidates([SEED], max_pages=101, fetcher=_fetcher(_routes()))

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))
        ],
    )
    with pytest.raises(VSDSourceIntelligenceError, match="prohibited address"):
        intelligence._public_addresses("private.example")


def test_unavailable_robots_is_recorded_and_does_not_silently_disappear():
    routes = _routes()
    routes.pop(f"https://{HOST}/robots.txt")
    report = crawl_source_candidates(
        [SEED],
        max_pages=1,
        max_depth=0,
        fetcher=_fetcher(routes),
        scanned_at="2026-08-01T12:00:00+00:00",
    )
    assert report["robots_status"] == {HOST: "unavailable_default_allow"}
    assert report["pages_fetched"] == 1


def test_report_snapshot_and_handoff_are_content_addressed_and_local(
    tmp_path, monkeypatch
):
    report = _scan()
    report_file = write_scan_report(report, tmp_path / "history")
    assert json.loads(report_file.read_text(encoding="utf-8")) == report
    with pytest.raises(VSDSourceIntelligenceError, match="already exists"):
        write_scan_report(report, tmp_path / "history")

    openapi = next(
        item for item in report["candidates"] if item["format_hint"] == "openapi"
    )
    snapshot = snapshot_source_candidate(
        report,
        openapi["candidate_id"],
        tmp_path / "snapshots",
        fetcher=_fetcher(_routes()),
    )
    snapshot_path = tmp_path / "snapshots" / snapshot["snapshot_file"]
    assert snapshot_path.exists()
    assert (
        snapshot["content_sha256"]
        == intelligence.hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
    )
    assert snapshot["execution_allowed"] is False
    manifest_path = write_snapshot_manifest(
        snapshot, tmp_path / "snapshot-manifest.json"
    )
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == snapshot

    with pytest.raises(VSDSourceIntelligenceError, match="consent"):
        prepare_core_handoff(
            [report],
            [openapi["candidate_id"]],
            reviewed_by="VSD Maintainer",
            decision_note="Reviewed source metadata and selected one contract lead.",
            consent=False,
        )
    handoff = prepare_core_handoff(
        [report],
        [openapi["candidate_id"]],
        reviewed_by="VSD Maintainer",
        decision_note="Reviewed source metadata and selected one contract lead.",
        consent=True,
        snapshots=[snapshot],
        created_at="2026-08-01T13:00:00+00:00",
    )
    assert handoff["execution_allowed"] is False
    assert "pages" not in handoff
    assert "response_bytes" not in handoff["candidates"][0]
    handoff_path = write_core_handoff(handoff, tmp_path / "handoff.json")
    assert validate_core_handoff(json.loads(handoff_path.read_text())) == handoff
    title, body = render_core_issue(handoff)
    assert handoff["handoff_id"] in title
    assert "No tool was generated, registered, approved, or executed" in body
    assert openapi["url"] in body

    recomputed_handoff = copy.deepcopy(handoff)
    recomputed_handoff["raw_private_notes"] = "must not be accepted"
    handoff_body = {
        key: value
        for key, value in recomputed_handoff.items()
        if key not in {"handoff_id", "handoff_sha256"}
    }
    recomputed_handoff["handoff_sha256"] = intelligence._digest(handoff_body)
    recomputed_handoff["handoff_id"] = recomputed_handoff["handoff_sha256"][:16]
    with pytest.raises(VSDSourceIntelligenceError, match="object"):
        validate_core_handoff(recomputed_handoff)

    with pytest.raises(VSDSourceIntelligenceError, match="confirmation"):
        submit_core_handoff(handoff, confirm=False)
    monkeypatch.setenv("TOOLUNIVERSE_VSD_GITHUB_TOKEN", "github_test_token_1234567890")
    captured = {}

    def requester(token, issue_title, issue_body):
        captured.update(token=token, title=issue_title, body=issue_body)
        return {
            "number": 9001,
            "html_url": "https://github.com/mims-harvard/ToolUniverse/issues/9001",
        }

    result = submit_core_handoff(handoff, confirm=True, requester=requester)
    assert result["data"]["issue_number"] == 9001
    assert captured["token"] == "github_test_token_1234567890"
    assert captured["token"] not in captured["body"]
    assert result["data"]["repository"] == "mims-harvard/ToolUniverse"


def test_snapshot_rejects_unselected_candidates(tmp_path):
    report = _scan()
    with pytest.raises(VSDSourceIntelligenceError, match="exactly one"):
        snapshot_source_candidate(
            report,
            "0" * 16,
            tmp_path,
            fetcher=_fetcher(_routes()),
        )


class _FakeSocket:
    def __init__(self, address="203.0.113.10"):
        self.address = address

    def getpeername(self):
        return self.address, 443

    def settimeout(self, value):
        self.timeout = value


class _FakeRaw:
    def __init__(self, content, address="203.0.113.10"):
        self.content = content
        self.offset = 0
        self.decode_content = False
        self._connection = type("Connection", (), {"sock": _FakeSocket(address)})()

    def read(self, size, decode_content=False):
        del decode_content
        chunk = self.content[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


class _FakeResponse:
    def __init__(self, content, *, status=200, headers=None, address="203.0.113.10"):
        self.status_code = status
        self.headers = headers or {"Content-Type": "application/json"}
        self.raw = _FakeRaw(content, address)
        self.closed = False
        self.is_redirect = status in {301, 302, 303, 307, 308}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise intelligence.requests.HTTPError("failed")

    def close(self):
        self.closed = True


class _FakeSession:
    def __init__(self, response):
        self.response = response
        self.trust_env = True
        self.mounted = None
        self.request = None
        self.closed = False

    def mount(self, prefix, adapter):
        self.mounted = (prefix, adapter)

    def get(self, url, **kwargs):
        self.request = ("GET", url, kwargs)
        return self.response

    def post(self, url, **kwargs):
        self.request = ("POST", url, kwargs)
        return self.response

    def close(self):
        self.closed = True


def test_production_fetch_pins_dns_disables_proxy_and_refuses_redirects(monkeypatch):
    raw = b'{"openapi":"3.1.0"}'
    response = _FakeResponse(
        raw,
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(raw)),
        },
    )
    session = _FakeSession(response)
    monkeypatch.setattr(intelligence.requests, "Session", lambda: session)
    monkeypatch.setattr(
        intelligence, "_public_addresses", lambda host: ("203.0.113.10",)
    )
    monkeypatch.setattr(intelligence, "_require_global_ip", lambda *_, **__: None)
    content, metadata = intelligence._fetch_https(
        "https://provider.example/openapi.json", 10, 100
    )
    assert content == raw
    assert metadata["peer_ip"] == "203.0.113.10"
    assert session.trust_env is False
    assert session.mounted[0] == "https://"
    assert session.request[2]["allow_redirects"] is False
    assert session.request[2]["stream"] is True
    assert session.closed and response.closed

    redirected = _FakeResponse(b"", status=302)
    redirected_session = _FakeSession(redirected)
    monkeypatch.setattr(intelligence.requests, "Session", lambda: redirected_session)
    with pytest.raises(VSDSourceIntelligenceError, match="redirects"):
        intelligence._fetch_https("https://provider.example/openapi.json", 10, 100)


def test_github_handoff_transport_is_fixed_pinned_and_proxy_free(monkeypatch):
    payload = json.dumps(
        {
            "number": 12,
            "html_url": "https://github.com/mims-harvard/ToolUniverse/issues/12",
        }
    ).encode()
    response = _FakeResponse(
        payload,
        status=201,
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(payload)),
        },
    )
    session = _FakeSession(response)
    monkeypatch.setattr(intelligence.requests, "Session", lambda: session)
    monkeypatch.setattr(
        intelligence, "_public_addresses", lambda host: ("203.0.113.10",)
    )
    monkeypatch.setattr(intelligence, "_require_global_ip", lambda *_, **__: None)
    result = intelligence._github_issue_request(
        "github_test_token_1234567890", "Reviewed source candidates", "Body"
    )
    assert result["number"] == 12
    assert session.trust_env is False
    assert session.request[0] == "POST"
    assert session.request[1] == (
        "https://api.github.com/repos/mims-harvard/ToolUniverse/issues"
    )
    assert session.request[2]["allow_redirects"] is False
    assert session.request[2]["stream"] is True
    assert session.request[2]["headers"]["Authorization"].startswith("Bearer ")
    assert session.closed and response.closed


def test_bounded_stream_policy_errors_use_source_intelligence_error(monkeypatch):
    def fail_stream(*_, **__):
        raise intelligence.VSDPolicyError("bounded stream expired")

    monkeypatch.setattr(intelligence, "_response_chunks", fail_stream)
    monkeypatch.setattr(
        intelligence, "_public_addresses", lambda host: ("203.0.113.10",)
    )
    monkeypatch.setattr(intelligence, "_require_global_ip", lambda *_, **__: None)

    fetch_response = _FakeResponse(b"{}", headers={"Content-Length": "2"})
    fetch_session = _FakeSession(fetch_response)
    monkeypatch.setattr(intelligence.requests, "Session", lambda: fetch_session)
    with pytest.raises(VSDSourceIntelligenceError, match="bounded stream expired"):
        intelligence._fetch_https("https://provider.example/openapi.json", 10, 100)
    assert fetch_session.closed and fetch_response.closed

    github_response = _FakeResponse(b"{}", status=201, headers={"Content-Length": "2"})
    github_session = _FakeSession(github_response)
    monkeypatch.setattr(intelligence.requests, "Session", lambda: github_session)
    with pytest.raises(VSDSourceIntelligenceError, match="bounded stream expired"):
        intelligence._github_issue_request("test-token", "Title", "Body")
    assert github_session.closed and github_response.closed
