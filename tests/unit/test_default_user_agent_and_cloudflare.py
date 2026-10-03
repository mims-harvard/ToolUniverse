"""Three 403s with three different causes.

Triaging the 2026-10-03 sweep turned up three categories failing with 403, and
they needed three different answers:

  conoserver  nginx blocks the literal "python-requests" User-Agent. Measured
              on /download/conoserver_protein.xml.gz: 52 bytes of HTML by
              default, 856975 bytes of the export with any other User-Agent,
              including an empty one. Fixed: 5 failures -> 5 passing.
  wormbase    Cloudflare managed challenge. 403 and cf-mitigated: challenge
  foodb       for all four User-Agents tried, the requests default,
              ToolUniverse, curl and a current Chrome string. Nothing to
              implement; named in the error and recorded in broken_apis.

The same blocked-User-Agent rule had already broken every TDC dataset load
through Harvard Dataverse, so the default belongs in the shared HTTP helper
rather than in each tool: request_with_retry set no headers of its own, and
only 99 of the 551 tool modules mention a User-Agent at all.
"""

import json
from pathlib import Path

import pytest

from tooluniverse.http_utils import (
    DEFAULT_USER_AGENT,
    cloudflare_challenge,
    request_with_retry,
    with_user_agent,
)

pytestmark = pytest.mark.unit

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"


class _Resp:
    def __init__(self, status_code=200, headers=None, text=""):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text


class _Session:
    def __init__(self, response=None):
        self.calls = []
        self._response = response or _Resp()

    def request(self, method, url, **kwargs):
        self.calls.append(kwargs)
        return self._response


def test_the_default_user_agent_is_not_the_blocked_string():
    assert "python-requests" not in DEFAULT_USER_AGENT
    assert "ToolUniverse" in DEFAULT_USER_AGENT


def test_request_with_retry_sends_a_user_agent():
    session = _Session()

    request_with_retry(session, "GET", "https://example.invalid/")

    sent = session.calls[0]["headers"]
    assert sent["User-Agent"] == DEFAULT_USER_AGENT


def test_a_caller_keeps_its_own_user_agent():
    session = _Session()

    request_with_retry(
        session, "GET", "https://example.invalid/", headers={"User-Agent": "Mine/2.0"}
    )

    assert session.calls[0]["headers"]["User-Agent"] == "Mine/2.0"


def test_other_headers_are_preserved():
    session = _Session()

    request_with_retry(
        session,
        "GET",
        "https://example.invalid/",
        headers={"Accept": "application/json"},
    )

    sent = session.calls[0]["headers"]
    assert sent["Accept"] == "application/json"
    assert sent["User-Agent"] == DEFAULT_USER_AGENT


@pytest.mark.parametrize("spelling", ["User-Agent", "user-agent", "USER-AGENT"])
def test_the_caller_header_is_matched_whatever_its_case(spelling):
    merged = with_user_agent({spelling: "Mine/3.0"})

    assert merged[spelling] == "Mine/3.0"
    assert len([k for k in merged if k.lower() == "user-agent"]) == 1


def test_a_cloudflare_challenge_is_recognised():
    resp = _Resp(
        403,
        {"cf-mitigated": "challenge", "Server": "cloudflare"},
        "<html>Just a moment...</html>",
    )

    message = cloudflare_challenge(resp)

    assert message
    assert "JavaScript challenge" in message
    assert "not a problem with your credentials" in message


def test_a_cloudflare_challenge_without_the_header_is_still_recognised():
    resp = _Resp(
        403,
        {"Server": "cloudflare"},
        "<title>Just a moment...</title>Enable JavaScript and cookies",
    )

    assert cloudflare_challenge(resp)


def test_an_ordinary_403_is_not_called_a_challenge():
    """A real permission error must not be explained away."""
    resp = _Resp(403, {"Server": "nginx"}, '{"error": "API key is missing"}')

    assert cloudflare_challenge(resp) is None


def test_a_success_is_not_a_challenge():
    assert cloudflare_challenge(_Resp(200, {"Server": "cloudflare"})) is None


def test_a_missing_response_is_not_a_challenge():
    """The detector runs on error paths and must never raise."""
    assert cloudflare_challenge(None) is None


def test_conoserver_goes_through_the_shared_helper():
    source = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "tooluniverse"
        / "conoserver_tool.py"
    ).read_text("utf-8")

    assert "request_with_retry(" in source
    assert "requests.get(_URL" not in source, (
        "the bare call sent the blocked User-Agent and had no retry"
    )


@pytest.mark.parametrize("slug", ["wormbase_rest", "foodb"])
def test_the_challenged_apis_are_recorded_with_their_evidence(slug):
    entry = json.loads((DATA / "broken_apis" / f"{slug}.json").read_text("utf-8"))

    assert "cf-mitigated" in entry["failure_mode"]
    assert entry["retry_count"] >= 3
    assert entry["retry_after"]
    assert entry["affected_tools"], "the retirement should name the tools"
    assert "ConoServer" in entry["root_cause"], (
        "the contrast is the point: that one was a User-Agent block and fixable"
    )


@pytest.mark.parametrize(
    ("module", "name"),
    [("wormbase_tool.py", "WormBase"), ("foodb_tool.py", "FooDB")],
)
def test_both_tools_name_the_challenge_instead_of_a_bare_403(module, name):
    source = (
        Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / module
    ).read_text("utf-8")

    assert "cloudflare_challenge(" in source
    assert f"{name} is unreachable" in source
