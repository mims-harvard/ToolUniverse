"""A wrapper that retried three times must not report a one-attempt timeout.

Measured on 2026-11-28: MassBank's REST host accepts the connection and never
answers, and `MassBank_search_by_formula` took 92.5 seconds to return

    MassBank_search_by_formula API error: HTTPSConnectionPool(host=
    'massbank.eu', port=443): Read timed out. (read timeout=30)

`request_with_retry` had made three 30-second attempts. The only number in the
message was 30, and nothing in the reply said a retry had happened at all. Two
things follow for the caller: retrying -- the obvious next move -- spends
another 92 seconds on a host that is down, and any time budget built on the
reported figure is off by a factor of three. 97 call sites across 43 modules go
through this one helper, so all of them said it.

The same silence covers the status half: a 429 or 503 was retried, with the
service's own Retry-After honoured, and reached the caller as a bare status
code under advice to wait and try again.

Negative controls run on 2026-11-28: with the `_disclose_attempts` call removed
`test_the_message_says_it_retried` and `test_the_note_survives_the_wrapper`
fail; with `_record_attempts` removed the two response tests fail; with the
`attempts_note` block removed from base_rest_tool, `test_a_retried_status_...`
fails. `test_one_attempt_adds_nothing` and `test_a_first_try_refusal_...` fail
if the note is emitted unconditionally.
"""

from unittest.mock import MagicMock

import pytest
import requests

from tooluniverse.base_rest_tool import BaseRESTTool
from tooluniverse.http_utils import attempts_note, request_with_retry

pytestmark = pytest.mark.unit

TIMEOUT_TEXT = (
    "HTTPSConnectionPool(host='massbank.eu', port=443): "
    "Read timed out. (read timeout=30)"
)


class _Session:
    """Answers however the test asks, and counts how often it was asked."""

    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = 0

    def request(self, *_args, **_kwargs):
        self.calls += 1
        if self.outcome == "timeout":
            raise requests.exceptions.ReadTimeout(TIMEOUT_TEXT)
        response = requests.Response()
        response.status_code = self.outcome
        response._content = b"upstream body"
        return response


def _attempt(outcome, attempts=3):
    session = _Session(outcome)
    return session, request_with_retry(
        session,
        "GET",
        "https://example.org/x",
        max_attempts=attempts,
        backoff_seconds=0.001,
    )


def test_the_message_says_it_retried():
    session = _Session("timeout")
    with pytest.raises(requests.exceptions.ReadTimeout) as raised:
        request_with_retry(
            session,
            "GET",
            "https://example.org/x",
            max_attempts=3,
            backoff_seconds=0.001,
        )
    assert session.calls == 3
    text = str(raised.value)
    assert "read timeout=30" in text, "the upstream's own reason must survive"
    assert "3 attempts over" in text, text
    assert raised.value.tooluniverse_attempts == 3
    assert raised.value.tooluniverse_elapsed_seconds >= 0


def test_the_exception_class_does_not_change():
    """43 modules catch `Timeout` or `RequestException`; none may stop matching."""
    session = _Session("timeout")
    with pytest.raises(requests.exceptions.ReadTimeout) as raised:
        request_with_retry(
            session,
            "GET",
            "https://example.org/x",
            max_attempts=2,
            backoff_seconds=0.001,
        )
    exc = raised.value
    assert isinstance(exc, requests.exceptions.Timeout)
    assert isinstance(exc, requests.exceptions.RequestException)
    assert isinstance(exc, OSError)


def test_one_attempt_adds_nothing():
    session = _Session("timeout")
    with pytest.raises(requests.exceptions.ReadTimeout) as raised:
        request_with_retry(
            session,
            "GET",
            "https://example.org/x",
            max_attempts=1,
        )
    assert session.calls == 1
    assert "attempts over" not in str(raised.value)
    assert str(raised.value) == TIMEOUT_TEXT
    assert attempts_note(raised.value) == ""


def test_the_note_survives_the_wrapper():
    """Said once, not once per layer: two helpers in a row must not double it."""
    session = _Session("timeout")
    with pytest.raises(requests.exceptions.ReadTimeout) as raised:
        request_with_retry(
            session,
            "GET",
            "https://example.org/x",
            max_attempts=2,
            backoff_seconds=0.001,
        )
    exc = raised.value
    once = str(exc)
    from tooluniverse.http_utils import _disclose_attempts

    _disclose_attempts(exc, 2, 9.0)
    assert str(exc) == once
    assert once.count("attempts over") == 1


def test_a_retried_status_carries_the_count_on_the_response():
    """A retried status reaches its caller with the count attached."""
    session, response = _attempt(503)
    assert session.calls == 3
    assert response.status_code == 503
    assert response.tooluniverse_attempts == 3
    assert attempts_note(response) == (
        f"after 3 attempts over {response.tooluniverse_elapsed_seconds:.1f}s"
    )


def test_a_status_answered_first_time_carries_no_note():
    """One attempt is the normal case and must stay quiet."""
    session, response = _attempt(404)
    assert session.calls == 1
    assert response.tooluniverse_attempts == 1
    assert attempts_note(response) == ""


def test_a_response_that_refuses_the_attributes_still_returns():
    """A stub response is not worth failing a successful request over."""

    class Locked:
        __slots__ = ("status_code", "headers")

        def __init__(self):
            self.status_code = 200
            self.headers = {}

    class S:
        def request(self, *_a, **_k):
            return Locked()

    assert request_with_retry(S(), "GET", "https://example.org/x").status_code == 200


CONFIG = {
    "name": "Example_get",
    "type": "BaseRESTTool",
    "fields": {"endpoint": "https://example.org/api/thing"},
    "parameter": {"type": "object", "properties": {}},
}


def _rest_tool_against(outcome, attempts=3):
    tool = BaseRESTTool(CONFIG)
    session = _Session(outcome)
    tool.session = session
    return tool, session


def test_a_retried_status_is_disclosed_in_the_tools_refusal():
    """A 503 refusal says the wait already happened, and still explains the 503."""
    tool, session = _rest_tool_against(503)
    result = tool.run({})
    assert session.calls == 3, "the tool must really have retried"
    assert result["status"] == "error"
    assert result["status_code"] == 503
    assert "attempts over" in result["error"], result["error"]
    assert "the service is failing on its side" in result["error"], (
        "the existing 5xx explanation must not be displaced"
    )


def test_a_first_try_refusal_says_nothing_about_attempts():
    """A 404 was answered at once; claiming a retry would be a false report."""
    tool, session = _rest_tool_against(404)
    result = tool.run({})
    assert session.calls == 1
    assert result["status"] == "error"
    assert "attempts" not in result["error"], result["error"]


def test_a_timeout_through_the_tool_reports_what_it_cost():
    """End to end: the measured MassBank shape, through a real tool run."""
    tool, session = _rest_tool_against("timeout")
    result = tool.run({})
    assert session.calls == 3
    assert result["status"] == "error"
    assert "read timeout=30" in result["error"]
    assert "3 attempts over" in result["error"], result["error"]


def test_attempts_note_ignores_anything_it_cannot_read():
    """No count, or a count that is not a count, means no claim."""
    assert attempts_note(object()) == ""
    assert attempts_note(None) == ""
    stub = MagicMock()
    stub.tooluniverse_attempts = "three"
    assert attempts_note(stub) == ""
