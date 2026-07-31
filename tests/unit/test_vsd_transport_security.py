from __future__ import annotations

import json
import time
from types import SimpleNamespace

import pytest
import requests

from tooluniverse import vsd_tool

pytestmark = pytest.mark.unit


class _Socket:
    def __init__(self, address: str):
        self.address = address

    def getpeername(self):
        return (self.address, 443)


class _Response:
    def __init__(
        self,
        *,
        peer_address: str = "93.184.216.34",
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        fail_if_read: bool = False,
        body: bytes | None = None,
        read_delay: float = 0,
    ):
        self.status_code = status_code
        self.headers = {"Content-Type": "application/json", **(headers or {})}
        self.raw = SimpleNamespace(
            _connection=SimpleNamespace(sock=_Socket(peer_address))
        )
        self.fail_if_read = fail_if_read
        self.body = body or json.dumps({"ok": True}).encode()
        self.read_delay = read_delay
        self.closed = False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        del chunk_size
        if self.fail_if_read:
            raise AssertionError("encoded response must be rejected before reading")
        if self.read_delay:
            time.sleep(self.read_delay)
        yield self.body

    def close(self):
        self.closed = True


class _Session:
    def __init__(self, response: _Response):
        self.response = response
        self.trust_env = True
        self.adapters = {}
        self.request = None

    def mount(self, prefix, adapter):
        self.adapters[prefix] = adapter

    def get(self, url, **kwargs):
        self.request = (url, kwargs)
        return self.response


def test_request_pins_the_single_vetted_dns_result(monkeypatch):
    """A request resolves once and connects only to that vetted address."""
    resolutions = []

    def resolver(host, port):
        resolutions.append((host, port))
        if len(resolutions) > 1:
            return ("10.0.0.7",)
        return ("93.184.216.34",)

    monkeypatch.setattr(vsd_tool, "_resolve_public_addresses", resolver)
    session = _Session(_Response())

    payload, metadata = vsd_tool._safe_get_json(
        "https://api.fda.gov/drug/label.json", session=session
    )

    assert payload == {"ok": True}
    assert metadata["peer_ip"] == "93.184.216.34"
    assert resolutions == [("api.fda.gov", 443)]
    adapter = session.adapters["https://"]
    assert adapter.address == "93.184.216.34"
    assert adapter.hostname == "api.fda.gov"
    assert session.request[1]["headers"]["Accept-Encoding"] == "identity"


def test_pinned_adapter_preserves_tls_and_http_hostname():
    """IP pinning retains hostname validation and the original Host header."""
    adapter = vsd_tool._PinnedHTTPSAdapter("api.fda.gov", "93.184.216.34")
    request = requests.Request("GET", "https://api.fda.gov/drug/label.json").prepare()

    host_params, pool_kwargs = adapter.build_connection_pool_key_attributes(
        request, True, None
    )
    adapter.add_headers(request)

    assert host_params == {
        "scheme": "https",
        "host": "93.184.216.34",
        "port": 443,
    }
    assert pool_kwargs["cert_reqs"] == "CERT_REQUIRED"
    assert pool_kwargs["assert_hostname"] == "api.fda.gov"
    assert pool_kwargs["server_hostname"] == "api.fda.gov"
    assert request.headers["Host"] == "api.fda.gov"


def test_public_peer_must_equal_the_vetted_connection_target(monkeypatch):
    """Reject a connected peer that differs from the selected public address."""
    monkeypatch.setattr(
        vsd_tool,
        "_resolve_public_addresses",
        lambda host, port: ("93.184.216.34",),
    )
    response = _Response(peer_address="8.8.8.8")

    with pytest.raises(vsd_tool.VSDPolicyError, match="did not match"):
        vsd_tool._safe_get_json(
            "https://api.fda.gov/drug/label.json",
            session=_Session(response),
        )

    assert response.closed is True


@pytest.mark.parametrize("encoding", ["gzip", "br", "identity, gzip"])
def test_non_identity_content_encoding_is_rejected_before_reading(
    monkeypatch, encoding
):
    """Reject encoded bodies before decompression or body consumption."""
    monkeypatch.setattr(
        vsd_tool,
        "_resolve_public_addresses",
        lambda host, port: ("93.184.216.34",),
    )
    response = _Response(headers={"Content-Encoding": encoding}, fail_if_read=True)

    with pytest.raises(vsd_tool.VSDPolicyError, match="non-identity"):
        vsd_tool._safe_get_json(
            "https://api.fda.gov/drug/label.json",
            session=_Session(response),
        )

    assert response.closed is True


def test_redirect_to_an_allowlisted_host_is_still_forbidden(monkeypatch):
    """Reject redirects even when the destination hostname is allowlisted."""
    monkeypatch.setattr(
        vsd_tool,
        "_resolve_public_addresses",
        lambda host, port: ("93.184.216.34",),
    )
    response = _Response(
        status_code=302,
        headers={"Location": "https://api.fda.gov/other.json"},
    )

    with pytest.raises(vsd_tool.VSDPolicyError, match="redirects are not allowed"):
        vsd_tool._safe_get_json(
            "https://api.fda.gov/drug/label.json",
            session=_Session(response),
        )

    assert response.closed is True


def test_total_deadline_stops_a_slow_stream(monkeypatch):
    """Enforce a wall-clock deadline across response body consumption."""
    monkeypatch.setattr(
        vsd_tool,
        "_resolve_public_addresses",
        lambda host, port: ("93.184.216.34",),
    )
    response = _Response(read_delay=0.03)

    with pytest.raises(vsd_tool.VSDPolicyError, match="total timeout"):
        vsd_tool._safe_get_json(
            "https://api.fda.gov/drug/label.json",
            timeout=0.01,
            session=_Session(response),
        )

    assert response.closed is True


@pytest.mark.parametrize("constant", [b"NaN", b"Infinity", b"-Infinity"])
def test_nonstandard_json_numbers_are_rejected(monkeypatch, constant):
    """Reject JavaScript number constants that are invalid standard JSON."""
    monkeypatch.setattr(
        vsd_tool,
        "_resolve_public_addresses",
        lambda host, port: ("93.184.216.34",),
    )
    response = _Response(body=b'{"value":' + constant + b"}")

    with pytest.raises(vsd_tool.VSDPolicyError, match="non-standard JSON"):
        vsd_tool._safe_get_json(
            "https://api.fda.gov/drug/label.json",
            session=_Session(response),
        )


def test_credential_like_source_path_is_rejected(monkeypatch):
    """Reject source paths that appear to contain embedded credentials."""
    monkeypatch.setattr(
        vsd_tool,
        "_resolve_public_addresses",
        lambda host, port: ("93.184.216.34",),
    )

    with pytest.raises(vsd_tool.VSDPolicyError, match="source paths"):
        vsd_tool.validate_source_url(
            "https://api.fda.gov/v1/sk_live_example_secret/records"
        )


def test_deceptive_non_json_media_type_is_rejected(monkeypatch):
    """Do not accept a media type merely because its text contains json."""
    monkeypatch.setattr(
        vsd_tool,
        "_resolve_public_addresses",
        lambda host, port: ("93.184.216.34",),
    )
    response = _Response(headers={"Content-Type": "text/notjson"})

    with pytest.raises(vsd_tool.VSDPolicyError, match="non-JSON content type"):
        vsd_tool._safe_get_json(
            "https://api.fda.gov/drug/label.json",
            session=_Session(response),
        )


@pytest.mark.parametrize("timeout", [True, 0, -1, float("inf")])
def test_timeout_must_be_positive_and_finite(timeout):
    """Reject booleans, nonpositive values, and infinite timeouts."""
    with pytest.raises(ValueError, match="positive finite"):
        vsd_tool._safe_get_json(
            "https://api.fda.gov/drug/label.json",
            timeout=timeout,
            session=_Session(_Response()),
        )
