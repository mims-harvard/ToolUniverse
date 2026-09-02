"""ChEMBL tools must not issue unprotected HTTP calls.

Most of chem_tool.py's outbound calls used a bare ``requests.get`` with no
retry and, in five cases, no timeout at all — so a ChEMBL outage that hangs
rather than erroring could block the caller indefinitely. ``request_with_retry``
was already imported in the module but applied to only 3 of the 10 call sites.

These tests pin the invariant (every call retried and bounded) rather than the
particular call sites, so new code cannot quietly reintroduce a bare request.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

requests = pytest.importorskip("requests")

CHEM_TOOL = pathlib.Path(__file__).resolve().parents[2] / "src/tooluniverse/chem_tool.py"


def _calls(func_name: str):
    tree = ast.parse(CHEM_TOOL.read_text())
    return [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and (
            getattr(n.func, "id", None) == func_name
            or getattr(n.func, "attr", None) == func_name
        )
    ]


def test_no_bare_requests_get_remains():
    """Every outbound call goes through the retry helper."""
    bare = [n.lineno for n in _calls("get") if getattr(getattr(n.func, "value", None), "id", "") == "requests"]
    assert bare == [], f"unprotected requests.get at lines {bare}"


def test_every_request_has_a_timeout():
    """An outage that hangs must not block the caller forever."""
    missing = [
        n.lineno for n in _calls("request_with_retry")
        if "timeout" not in {k.arg for k in n.keywords}
    ]
    assert missing == [], f"request_with_retry without timeout at lines {missing}"


def test_all_call_sites_are_retried():
    assert len(_calls("request_with_retry")) >= 10


def test_chembl_tool_has_session_and_timeout():
    """ChEMBLTool previously had neither, unlike ChEMBLRESTTool."""
    from tooluniverse.chem_tool import ChEMBLTool

    tool = ChEMBLTool({"name": "t", "type": "ChEMBLTool"})
    assert isinstance(tool.session, requests.Session)
    assert isinstance(tool.timeout, (int, float)) and tool.timeout > 0


# --------------------------------------------------------------------------
# Behaviour of the helper itself on the failure mode we actually hit
# --------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.headers = {}

    def json(self):
        return {"molecules": []}


class _FakeSession:
    """Records attempts and replays a scripted sequence of status codes."""

    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return _FakeResponse(self.statuses[min(len(self.calls) - 1, len(self.statuses) - 1)])


def test_retries_on_500_then_succeeds():
    """A transient 500 (ChEMBL's failure mode) is retried, not surfaced."""
    from tooluniverse.http_utils import request_with_retry

    session = _FakeSession([500, 500, 200])
    resp = request_with_retry(
        session, "GET", "https://example.invalid/x", timeout=5,
        max_attempts=3, backoff_seconds=0.0,
    )
    assert resp.status_code == 200
    assert len(session.calls) == 3, "should have retried twice before succeeding"


def test_gives_up_after_max_attempts_and_returns_last_response():
    """A sustained outage returns the 500 rather than retrying forever."""
    from tooluniverse.http_utils import request_with_retry

    session = _FakeSession([500])
    resp = request_with_retry(
        session, "GET", "https://example.invalid/x", timeout=5,
        max_attempts=3, backoff_seconds=0.0,
    )
    assert resp.status_code == 500
    assert len(session.calls) == 3


def test_timeout_is_forwarded_to_the_transport():
    from tooluniverse.http_utils import request_with_retry

    session = _FakeSession([200])
    request_with_retry(session, "GET", "https://example.invalid/x", timeout=7)
    assert session.calls[0][2]["timeout"] == 7


def test_success_is_not_retried():
    from tooluniverse.http_utils import request_with_retry

    session = _FakeSession([200])
    request_with_retry(session, "GET", "https://example.invalid/x", timeout=5)
    assert len(session.calls) == 1
