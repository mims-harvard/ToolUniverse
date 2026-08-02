from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from tooluniverse import vsd_tool


class _FakeSocket:
    def __init__(self, address: str = "93.184.216.34"):
        self.address = address

    def getpeername(self):
        return (self.address, 443)


class _FakeResponse:
    def __init__(
        self,
        payload=None,
        *,
        status_code: int = 200,
        headers=None,
        peer_address: str = "93.184.216.34",
        body: bytes | None = None,
    ):
        if body is None:
            body = json.dumps(payload if payload is not None else {}).encode()
        self._body = body
        self.status_code = status_code
        self.headers = {"Content-Type": "application/json", **(headers or {})}
        self.raw = SimpleNamespace(
            _connection=SimpleNamespace(sock=_FakeSocket(peer_address))
        )
        self.closed = False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size):
        del chunk_size
        yield self._body

    def close(self):
        self.closed = True


class _FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.trust_env = True
        self.closed = False

    def get(self, url, **kwargs):
        self.requests.append((url, kwargs))
        return self.responses.pop(0)

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def _public_dns(monkeypatch):
    monkeypatch.setattr(
        vsd_tool,
        "_resolve_public_addresses",
        lambda host, port: ("93.184.216.34",),
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://api.fda.gov/drug/label.json",
        "https://user:password@api.fda.gov/drug/label.json",
        "https://127.0.0.1/data",
        "https://169.254.169.254/latest/meta-data",
        "https://localhost/data",
        "https://api.fda.gov:8443/data",
        "https://api.fda.gov/data?api_key=do-not-store",
        "https://api.fda.gov/data#fragment",
    ],
)
def test_validate_source_url_rejects_unsafe_shapes(url):
    with pytest.raises(vsd_tool.VSDPolicyError):
        vsd_tool.validate_source_url(url)


def test_validate_source_url_rejects_unallowlisted_host():
    with pytest.raises(vsd_tool.VSDPolicyError, match="not allowlisted"):
        vsd_tool.validate_source_url("https://example.com/data.json")


def test_validate_source_url_rejects_private_dns(monkeypatch):
    def private_resolver(host, port):
        del port
        address = "10.0.0.5"
        vsd_tool._require_global_ip(address, context=f"Source host {host!r}")
        return (address,)

    monkeypatch.setattr(vsd_tool, "_resolve_public_addresses", private_resolver)

    with pytest.raises(vsd_tool.VSDPolicyError, match="prohibited address"):
        vsd_tool.validate_source_url("https://api.fda.gov/drug/label.json")


def test_custom_host_requires_explicit_opt_in(monkeypatch):
    monkeypatch.setenv("TOOLUNIVERSE_VSD_ALLOWED_HOSTS", "api.example.org")
    assert (
        vsd_tool.validate_source_url("https://api.example.org/data")
        == "https://api.example.org/data"
    )


def test_query_params_reject_credentials():
    for key in ("api_key", "key", "jwt", "session_id"):
        with pytest.raises(vsd_tool.VSDPolicyError, match="Credential-like"):
            vsd_tool._validated_params({key: "do-not-store"})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_query_params_reject_non_finite_numbers(value):
    with pytest.raises(vsd_tool.VSDPolicyError, match="non-finite"):
        vsd_tool._validated_params({"limit": value})


def test_query_params_reject_control_characters():
    with pytest.raises(vsd_tool.VSDPolicyError, match="control characters"):
        vsd_tool._validated_params({"query": "safe\r\nX-Injected: value"})


def test_safe_get_rejects_redirect_to_private_address():
    response = _FakeResponse(
        status_code=302,
        headers={"Location": "https://127.0.0.1/latest/meta-data"},
    )
    session = _FakeSession([response])

    with pytest.raises(vsd_tool.VSDPolicyError, match="IP-literal"):
        vsd_tool._safe_get_json(
            "https://api.fda.gov/start",
            session=session,
        )
    assert response.closed is True


def test_safe_get_rejects_private_connected_peer():
    session = _FakeSession([_FakeResponse({}, peer_address="10.1.2.3")])

    with pytest.raises(vsd_tool.VSDPolicyError, match="Connected peer"):
        vsd_tool._safe_get_json(
            "https://api.fda.gov/drug/label.json",
            session=session,
        )


def test_safe_get_rejects_oversized_decompressed_body():
    body = b'{"data":"' + (b"x" * vsd_tool._MAX_RESPONSE_BYTES) + b'"}'
    session = _FakeSession([_FakeResponse(body=body)])

    with pytest.raises(vsd_tool.VSDPolicyError, match="1 MB"):
        vsd_tool._safe_get_json(
            "https://api.fda.gov/drug/label.json",
            session=session,
        )


@pytest.mark.parametrize("value", ["not-a-number", "-1"])
def test_safe_get_rejects_invalid_content_length(value):
    session = _FakeSession([_FakeResponse({}, headers={"Content-Length": value})])

    with pytest.raises(vsd_tool.VSDPolicyError, match="invalid Content-Length"):
        vsd_tool._safe_get_json(
            "https://api.fda.gov/drug/label.json",
            session=session,
        )


def test_registration_rejects_oversized_metadata(monkeypatch):
    monkeypatch.setattr(
        vsd_tool,
        "_safe_get_json",
        lambda endpoint, params: ({}, {"url": endpoint}),
    )
    tool = vsd_tool.VSDRegisterSource({})

    with pytest.raises(vsd_tool.VSDPolicyError, match="name"):
        tool.run(
            {
                "source_id": "too_long_name",
                "endpoint": "https://api.fda.gov/drug/label.json",
                "name": "x" * 201,
            }
        )


def test_registration_rejects_metadata_control_characters(monkeypatch):
    monkeypatch.setattr(
        vsd_tool,
        "_safe_get_json",
        lambda endpoint, params: ({}, {"url": endpoint}),
    )
    tool = vsd_tool.VSDRegisterSource({})

    with pytest.raises(vsd_tool.VSDPolicyError, match="control characters"):
        tool.run(
            {
                "source_id": "unsafe_name",
                "endpoint": "https://api.fda.gov/drug/label.json",
                "name": "safe\nforged log line",
            }
        )


def test_admin_catalog_end_to_end_register_query_and_remove(monkeypatch, tmp_path):
    monkeypatch.setenv("TOOLUNIVERSE_VSD_DIR", str(tmp_path))
    calls = []

    def fake_safe_get(url, params=None, **kwargs):
        del kwargs
        calls.append((url, params or {}))
        return (
            {"items": [{"id": 1}]},
            {
                "url": url,
                "status_code": 200,
                "content_type": "application/json",
                "response_bytes": 20,
                "peer_ip": "93.184.216.34",
                "redirects": 0,
            },
        )

    monkeypatch.setattr(vsd_tool, "_safe_get_json", fake_safe_get)

    discovery = vsd_tool.VSDDiscoverSources({}).run({"query": "WHO"})
    assert discovery["data"]["sources"][0]["source_id"] == "who_gho"

    registration = vsd_tool.VSDRegisterSource({}).run(
        {
            "source_id": "who_gho",
            "endpoint": "https://ghoapi.azureedge.net/api/Indicator",
            "name": "WHO GHO",
            "default_params": {"$top": 1},
        }
    )
    assert registration["data"]["registered"] is True
    assert (tmp_path / "sources.json").exists()

    listed = vsd_tool.VSDListSources({}).run({})
    assert [source["source_id"] for source in listed["data"]["sources"]] == ["who_gho"]

    queried = vsd_tool.VSDQuerySource({}).run(
        {"source_id": "who_gho", "params": {"$select": "Code"}}
    )
    assert queried["data"]["result"]["items"][0]["id"] == 1
    assert calls[-1][1] == {"$top": 1, "$select": "Code"}

    removed = vsd_tool.VSDRemoveSource({}).run({"source_id": "who_gho"})
    assert removed["data"] == {"removed": True, "source_id": "who_gho"}
