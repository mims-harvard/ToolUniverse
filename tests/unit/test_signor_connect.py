"""Unit tests for SIGNOR_connect_proteins (causal sub-network connection).

The connect endpoint (``type=connect``) returns the same 28-column TSV format
as ``getData.php`` single-id queries, with no header row. These tests mock the
HTTP layer so they run offline, covering TSV parsing and the error paths.
"""

import pytest

from tooluniverse.signor_tool import SIGNORTool


def _tool():
    return SIGNORTool(
        {
            "name": "SIGNOR_connect_proteins",
            "type": "SIGNORTool",
            "fields": {"operation": "connect_proteins"},
            "parameter": {
                "type": "object",
                "properties": {},
                "required": ["proteins"],
            },
        }
    )


class _FakeResp:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


# Two real-shaped rows from the live connect response (28 tab-separated columns).
_SAMPLE_TSV = (
    "HRAS\tprotein\tP01112\tUNIPROT\tBRAF\tprotein\tP15056\tUNIPROT\t"
    "up-regulates\tbinding\t\t\t9606\t\t\t\t\t\t\t\t\t18098337\tt\t\t"
    "lperfetto\tBRAF kinase is a downstream target.\tSIGNOR-160043\t0.877\n"
    "PRKACA\tprotein\tP17612\tUNIPROT\tPTPN11\tprotein\tQ06124\tUNIPROT\t"
    "down-regulates activity\tphosphorylation\tThr73\tYGGEKFAtLAELVQY\t9606\t"
    "BTO:0002181\t\t\t\t\t\t\t\t25802336\tt\t\tmiannu\tPKA phosphorylates Shp2.\t"
    "SIGNOR-276891\t0.448\n"
)


def test_connect_parses_interactions(monkeypatch):
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        return _FakeResp(_SAMPLE_TSV)

    tool = _tool()
    monkeypatch.setattr(tool.session, "get", fake_get)

    out = tool.run({"proteins": ["P01112", "P15056", "Q06124"], "level": 2})

    assert out["status"] == "success"
    assert captured["params"]["type"] == "connect"
    assert captured["params"]["level"] == 2
    # Proteins joined with comma delimiter
    assert captured["params"]["proteins"] == "P01112,P15056,Q06124"

    data = out["data"]
    assert len(data) == 2
    first = data[0]
    assert first["source_entity"] == "HRAS"
    assert first["source_id"] == "P01112"
    assert first["target_entity"] == "BRAF"
    assert first["target_id"] == "P15056"
    assert first["effect"] == "up-regulates"
    assert first["mechanism"] == "binding"
    assert first["direct"] is True
    assert first["pmid"] == "18098337"
    assert first["score"] == pytest.approx(0.877)

    second = data[1]
    assert second["mechanism"] == "phosphorylation"
    assert second["residue"] == "Thr73"

    md = out["metadata"]
    assert md["proteins"] == ["P01112", "P15056", "Q06124"]
    assert md["level"] == 2
    assert md["total_interactions"] == 2
    assert md["returned"] == 2


def test_connect_accepts_delimited_string(monkeypatch):
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["params"] = params
        return _FakeResp(_SAMPLE_TSV)

    tool = _tool()
    monkeypatch.setattr(tool.session, "get", fake_get)

    out = tool.run({"proteins": "P01112+P15056,Q06124"})
    assert out["status"] == "success"
    assert captured["params"]["proteins"] == "P01112,P15056,Q06124"
    # Default level is 2
    assert captured["params"]["level"] == 2


def test_connect_requires_two_proteins():
    out = _tool().run({"proteins": ["P15056"]})
    assert out["status"] == "error"
    assert "two" in out["error"].lower()


def test_connect_rejects_invalid_level(monkeypatch):
    tool = _tool()
    # Should not even hit the network for an invalid level
    monkeypatch.setattr(
        tool.session,
        "get",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not call")),
    )
    out = tool.run({"proteins": ["P15056", "P04049"], "level": 9})
    assert out["status"] == "error"
    assert "level" in out["error"].lower()


def test_connect_empty_response_is_error(monkeypatch):
    tool = _tool()
    monkeypatch.setattr(tool.session, "get", lambda *a, **k: _FakeResp(""))
    out = tool.run({"proteins": ["P15056", "P04049"]})
    assert out["status"] == "error"
    assert "no connecting sub-network" in out["error"].lower()


def test_connect_http_error_is_error(monkeypatch):
    tool = _tool()
    monkeypatch.setattr(
        tool.session, "get", lambda *a, **k: _FakeResp("oops", status_code=500)
    )
    out = tool.run({"proteins": ["P15056", "P04049"]})
    assert out["status"] == "error"
    assert "500" in out["error"]


def test_connect_request_exception_is_handled(monkeypatch):
    import requests

    tool = _tool()

    def boom(*a, **k):
        raise requests.exceptions.ConnectionError("network down")

    monkeypatch.setattr(tool.session, "get", boom)
    out = tool.run({"proteins": ["P15056", "P04049"]})
    assert out["status"] == "error"
    assert "request error" in out["error"].lower()
