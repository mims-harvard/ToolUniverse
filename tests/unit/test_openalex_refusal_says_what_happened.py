"""An OpenAlex refusal has to say what the upstream refused, in `error`.

The REST wrapper used to answer a non-200 with `error` = "OpenAlex API error" and
put the status code, the upstream's body and the URL in sibling keys. Everything
a caller needed was present, and the one field an agent reads carried none of it.

Measured on 2026-11-27 while typing return schemas against live data: five
OpenAlex tools answered nothing, and all they said was "OpenAlex API error".
Their actual reply was HTTP 429 with "This request has no API key, so it counts
against the free daily budget shared by everyone on your network's IP address,
and that budget is used up ($0 remaining; resets at midnight UTC)." A retry was
hopeless and a key was the remedy, and neither fact reached the caller.

OPENALEX_API_KEY is already an optional credential in this project, so a budget
refusal names it -- the one thing the upstream's own message cannot know.
"""

from unittest.mock import MagicMock

import pytest

from tooluniverse.openalex_tool import OpenAlexRESTTool


def _tool():
    return OpenAlexRESTTool(
        {
            "name": "openalex_search_authors",
            "type": "OpenAlexRESTTool",
            "fields": {
                "path": "/authors",
                "path_params": [],
                "param_map": {"per_page": "per-page"},
                "default_params": {},
            },
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _reply(status, body, text=None, url="https://api.openalex.org/authors?search=x"):
    response = MagicMock()
    response.status_code = status
    response.url = url
    if body is None:
        response.json.side_effect = ValueError("not json")
        response.text = text if text is not None else "<html>gateway</html>"
    else:
        response.json.return_value = body
        import json as _json

        response.text = text if text is not None else _json.dumps(body)
    return response


def _run(monkeypatch, response, arguments=None):
    monkeypatch.setattr(
        "tooluniverse.openalex_tool.request_with_retry",
        lambda *args, **kwargs: response,
    )
    return _tool().run(arguments or {"search": "x"})


_BUDGET = {
    "error": "Rate limit exceeded",
    "message": (
        "Insufficient budget. This request has no API key, so it counts against "
        "the free daily budget shared by everyone on your network's IP address, "
        "and that budget is used up ($0 remaining; resets at midnight UTC). Use "
        "your own key instead: add ?api_key=YOUR_KEY to the URL."
    ),
}


def test_a_budget_refusal_names_the_status_the_reason_and_the_key(monkeypatch):
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    out = _run(monkeypatch, _reply(429, _BUDGET))
    assert out["status"] == "error"
    message = out["error"]
    assert "429" in message
    assert "budget" in message
    assert "midnight UTC" in message
    assert "OPENALEX_API_KEY" in message


def test_the_key_hint_is_left_out_when_a_key_is_already_configured(monkeypatch):
    """Telling someone who has a key to set one is noise, not help."""
    monkeypatch.setenv("OPENALEX_API_KEY", "already-set")
    out = _run(monkeypatch, _reply(429, _BUDGET))
    assert "429" in out["error"]
    assert "OPENALEX_API_KEY" not in out["error"]


def test_a_key_quoted_back_by_the_upstream_is_redacted(monkeypatch):
    """The quote now flows into `error`, so it is a new place a key can leak.

    The URL was already redacted before this change; the upstream's own body was
    not quoted at all. OpenAlex's 429 tells the caller to "add ?api_key=... to
    the URL", and a proxy or a mirror echoing the real one would put it there.
    """
    monkeypatch.setenv("OPENALEX_API_KEY", "openalex-secret-sentinel")
    body = {
        "message": (
            "Insufficient budget. Use your own key instead: add "
            "?api_key=openalex-secret-sentinel to the URL."
        )
    }
    out = _run(monkeypatch, _reply(429, body))
    assert "openalex-secret-sentinel" not in out["error"]
    assert "[REDACTED]" in out["error"]
    assert "openalex-secret-sentinel" not in str(out)


def test_a_non_json_body_still_carries_the_status(monkeypatch):
    """A gateway's HTML page is not a message, and the code is what is left."""
    out = _run(monkeypatch, _reply(502, None, text="<html>Bad Gateway</html>"))
    assert "502" in out["error"]
    assert out["status_code"] == 502


def test_the_sibling_fields_are_still_there(monkeypatch):
    """Callers that read status_code, detail or url must keep working."""
    out = _run(monkeypatch, _reply(429, _BUDGET))
    assert out["status_code"] == 429
    assert "Insufficient budget" in out["detail"]
    assert out["url"].startswith("https://api.openalex.org/authors")


def test_a_long_upstream_message_is_cut_at_a_sentence(monkeypatch):
    long_message = ("Sentence one is here. " * 40).strip()
    out = _run(monkeypatch, _reply(400, {"message": long_message}))
    quoted = out["error"].split("-- ", 1)[1]
    assert quoted.endswith(".")
    assert "Sentence one is here" in quoted
    assert len(quoted) <= 320


@pytest.mark.parametrize("status", [400, 403, 404, 500, 503])
def test_every_refusal_names_its_status(monkeypatch, status):
    out = _run(monkeypatch, _reply(status, {"message": "upstream said so."}))
    assert str(status) in out["error"]
    assert "upstream said so." in out["error"]
