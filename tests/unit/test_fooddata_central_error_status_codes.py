"""Regression guard for Fix-R15A-1: FoodDataCentralTool extracted the HTTP
status code from a caught HTTPError with `if e.response else "unknown"`.
`requests.Response` overrides `__bool__` to return `self.ok`, which is
False for any 4xx/5xx status -- so this check was always false-y for a real
HTTP error response (confirmed live and via a direct requests repro),
making the 403/429-specific branches below it unreachable dead code. Every
error surfaced as a generic "HTTP error unknown: <raw body>" instead of the
specific, actionable message that branch was written to produce.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.fooddata_central_tool import FoodDataCentralTool

pytestmark = pytest.mark.unit


def _tool():
    return FoodDataCentralTool(
        {"name": "FoodDataCentral_search_foods", "fields": {"operation": "search"}}
    )


def _http_error(status_code, body=""):
    response = MagicMock()
    response.status_code = status_code
    response.text = body
    # __bool__ mirrors the real requests.Response quirk: False for any
    # non-2xx status, even though the response object itself is real.
    response.__bool__ = lambda self: 200 <= status_code < 400
    error = requests.exceptions.HTTPError(response=response)
    return error


def test_429_status_reaches_the_rate_limit_branch(monkeypatch):
    tool = _tool()

    def fake_search(arguments):
        raise _http_error(429, '{"error":{"code":"OVER_RATE_LIMIT"}}')

    monkeypatch.setattr(tool, "_search_foods", fake_search)

    result = tool.run({"query": "almonds"})

    assert result["status"] == "error"
    assert "rate limit" in result["error"].lower()
    assert "unknown" not in result["error"]


def test_429_with_demo_key_hints_at_personal_key(monkeypatch):
    tool = _tool()
    tool.api_key = "DEMO_KEY"

    monkeypatch.setattr(
        tool, "_search_foods", lambda arguments: (_ for _ in ()).throw(_http_error(429))
    )

    result = tool.run({"query": "almonds"})

    assert "FDC_API_KEY" in result["error"]


def test_429_with_personal_key_omits_demo_key_hint(monkeypatch):
    tool = _tool()
    tool.api_key = "some-real-personal-key"

    monkeypatch.setattr(
        tool, "_search_foods", lambda arguments: (_ for _ in ()).throw(_http_error(429))
    )

    result = tool.run({"query": "almonds"})

    assert "FDC_API_KEY" not in result["error"]


def test_403_status_reaches_the_invalid_key_branch(monkeypatch):
    tool = _tool()

    monkeypatch.setattr(
        tool, "_search_foods", lambda arguments: (_ for _ in ()).throw(_http_error(403))
    )

    result = tool.run({"query": "almonds"})

    assert "invalid or missing" in result["error"]


def test_other_status_codes_still_report_the_real_code(monkeypatch):
    tool = _tool()

    monkeypatch.setattr(
        tool, "_search_foods", lambda arguments: (_ for _ in ()).throw(_http_error(500, "boom"))
    )

    result = tool.run({"query": "almonds"})

    assert "500" in result["error"]
