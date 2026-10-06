"""A 4xx from a config-driven REST tool says its status and the service's reason.

biomodels, github and modeldb failed in run 37273817054 with
"<tool> API error" and nothing else, and passed on every other machine. A 403
refusal, a 429 limit and a 404 read the same, so the report could not tell
which -- and neither could a user.
"""

from unittest.mock import MagicMock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool, _upstream_reason

pytestmark = pytest.mark.unit


def _response(status, json_body=None, text=""):
    r = MagicMock()
    r.status_code = status
    r.headers = {}
    r.text = text
    if json_body is None:
        r.json.side_effect = ValueError("not json")
    else:
        r.json.return_value = json_body
    return r


def _run(monkeypatch, response):
    tool = BaseRESTTool(
        {
            "name": "Probe_tool",
            "type": "BaseRESTTool",
            "fields": {"endpoint": "https://example.org/api/things"},
            "parameter": {"type": "object", "properties": {}},
        }
    )
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *a, **k: response,
    )
    return tool.run({})


def test_a_rate_limit_is_quoted(monkeypatch):
    result = _run(
        monkeypatch,
        _response(403, {"message": "API rate limit exceeded for 10.0.0.1."}),
    )

    assert result["status"] == "error"
    assert "API error (HTTP 403): API rate limit exceeded" in result["error"]


def test_a_plain_one_line_body_is_quoted(monkeypatch):
    result = _run(monkeypatch, _response(429, text="Too Many Requests"))

    assert result["error"].endswith("API error (HTTP 429): Too Many Requests")


def test_an_html_page_adds_only_the_status(monkeypatch):
    result = _run(monkeypatch, _response(404, text="<html><body>Not here</body></html>"))

    assert result["error"].endswith("API error (HTTP 404)")
    assert result["status_code"] == 404


@pytest.mark.parametrize(
    ("body", "text", "reason"),
    [
        ({"message": "  bad id  "}, "", "bad id"),
        ({"error": "nope"}, "", "nope"),
        ({"detail": "x" * 500}, "", "x" * 200),
        ({"results": []}, "", ""),
        (None, "line one\nline two", ""),
        (None, "", ""),
    ],
)
def test_upstream_reason(body, text, reason):
    assert _upstream_reason(_response(400, body, text)) == reason
