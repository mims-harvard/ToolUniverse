"""GtoPdb now rejects keyless requests (HTTP 401); the key goes in GTP-API-Key.

All HTTP is mocked at request_with_retry so no network access is needed.
"""

from unittest.mock import Mock, patch

from tooluniverse.gtopdb_tool import GtoPdbRESTTool

ENDPOINT = "https://www.guidetopharmacology.org/services/ligands"


def _make_tool():
    return GtoPdbRESTTool({"fields": {"endpoint": ENDPOINT}})


def _response(status_code, payload, text=None):
    resp = Mock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.text = text if text is not None else str(payload)
    return resp


def test_key_from_env_is_sent_in_gtp_api_key_header(monkeypatch):
    monkeypatch.setenv("GTOPDB_API_KEY", "abc123")
    tool = _make_tool()
    assert tool.session.headers["GTP-API-Key"] == "abc123"


def test_key_set_after_construction_is_picked_up_on_run(monkeypatch):
    monkeypatch.delenv("GTOPDB_API_KEY", raising=False)
    tool = _make_tool()
    assert "GTP-API-Key" not in tool.session.headers
    monkeypatch.setenv("GTOPDB_API_KEY", "late-key")
    with patch(
        "tooluniverse.gtopdb_tool.request_with_retry",
        return_value=_response(200, []),
    ):
        tool.run({"name": "aspirin"})
    assert tool.session.headers["GTP-API-Key"] == "late-key"


def test_removed_key_stops_being_sent(monkeypatch):
    monkeypatch.setenv("GTOPDB_API_KEY", "abc123")
    tool = _make_tool()
    monkeypatch.delenv("GTOPDB_API_KEY")
    with patch(
        "tooluniverse.gtopdb_tool.request_with_retry",
        return_value=_response(200, []),
    ):
        tool.run({"name": "aspirin"})
    assert "GTP-API-Key" not in tool.session.headers


def test_401_without_key_returns_actionable_hint(monkeypatch):
    monkeypatch.delenv("GTOPDB_API_KEY", raising=False)
    tool = _make_tool()
    body = '{"message":"API key is missing. In order to use the GtoPdb Web Services you must register."}'
    with patch(
        "tooluniverse.gtopdb_tool.request_with_retry",
        return_value=_response(401, {}, text=body),
    ):
        result = tool.run({"name": "aspirin"})
    assert result["status"] == "error"
    assert result["status_code"] == 401
    # upstream sends {"message": ...}; the readable text must surface, not raw JSON
    assert "API key is missing" in result["error"]
    assert not result["error"].startswith('GtoPdb API error: {"message"')
    assert "GTOPDB_API_KEY" in result["hint"]
    assert "GTP-API-Key" in result["hint"]


def test_non_401_error_has_no_key_hint(monkeypatch):
    monkeypatch.setenv("GTOPDB_API_KEY", "abc123")
    tool = _make_tool()
    with patch(
        "tooluniverse.gtopdb_tool.request_with_retry",
        return_value=_response(500, {}, text='{"error":"boom"}'),
    ):
        result = tool.run({"name": "aspirin"})
    assert result["status"] == "error"
    assert "hint" not in result
