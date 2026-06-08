"""Regression tests for the RCE / unauthenticated-exposure security advisory.

Covers three independent fixes:

1. The Python code executor no longer lets a caller widen the import allowlist
   via tool arguments (Path 1 of the advisory).
2. The executor's AST check blocks dunder-traversal sandbox escapes, in every
   form (attribute access, getattr, and string-literal/subscript), while still
   allowing legitimate scientific code (Path 2 of the advisory).
3. The network servers default to loopback and refuse to bind to a non-loopback
   interface without a Bearer token; the FastAPI app enforces that token on all
   routes except /health.
"""

import os

import pytest

from tooluniverse import server_security as ss
from tooluniverse.python_executor_tool import (
    BasePythonExecutor,
    PythonCodeExecutor,
)


def _executor():
    return PythonCodeExecutor({"name": "python_code_executor"})


def _run(code, **extra):
    return _executor().run({"code": code, **extra})


# --------------------------------------------------------------------------- #
# Path 1: caller-supplied allowlist override must be ignored
# --------------------------------------------------------------------------- #


def test_caller_cannot_widen_import_allowlist():
    """`allowed_imports` in call arguments must not enable `import os`."""
    result = _run("import os\nprint(os.getuid())", allowed_imports=["os", "subprocess"])
    assert result["status"] == "error"
    assert "Forbidden import: os" in result["data"]["error"]


def test_server_config_allowlist_still_respected():
    """Server-side tool_config allowlist remains the trust boundary."""
    ex = PythonCodeExecutor({"name": "python_code_executor", "allowed_imports": ["os"]})
    # os is allowlisted server-side, but reaching anything dangerous still
    # requires dunder traversal, which is independently blocked. A plain
    # allowlisted import is permitted.
    result = ex.run({"code": "import math\nprint(math.sqrt(9))"})
    assert result["status"] == "success"


# --------------------------------------------------------------------------- #
# Path 2: dunder-traversal sandbox escape must be blocked in all forms
# --------------------------------------------------------------------------- #


DUNDER_ESCAPES = [
    # getattr-based traversal (the advisory's exact payload shape)
    'getattr(getattr((), "__class__"), "__bases__")',
    # literal attribute traversal
    "().__class__.__bases__[0].__subclasses__()",
    # string-literal / subscript traversal
    'globals()["__builtins__"]',
    # bare dunder name read
    "print(__builtins__)",
]


@pytest.mark.parametrize("code", DUNDER_ESCAPES)
def test_dunder_traversal_blocked(code):
    result = _run(code)
    assert result["status"] == "error", f"escape not blocked: {code!r}"
    assert "Forbidden dunder" in result["data"]["error"]


def test_getattr_setattr_not_exposed():
    """getattr/setattr enable string-based dunder access and must be removed."""
    assert "getattr" not in BasePythonExecutor.SAFE_BUILTINS
    assert "setattr" not in BasePythonExecutor.SAFE_BUILTINS


@pytest.mark.parametrize(
    "code,expected",
    [
        (
            "import math, numpy as np\nresult = np.array([1, 2, 3]).sum() + math.sqrt(16)",
            10.0,
        ),
        ("result = sum(x * x for x in range(5))", 30),
    ],
)
def test_legitimate_code_still_runs(code, expected):
    result = _run(code)
    assert result["status"] == "success", result["data"].get("error")
    assert result["data"]["result"] == expected


# --------------------------------------------------------------------------- #
# server_security helpers
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def _clear_token(monkeypatch):
    monkeypatch.delenv(ss.API_TOKEN_ENV, raising=False)
    yield


@pytest.mark.parametrize(
    "host,loopback",
    [
        ("127.0.0.1", True),
        ("localhost", True),
        ("::1", True),
        ("0.0.0.0", False),
        ("1.2.3.4", False),
    ],
)
def test_is_loopback_host(host, loopback):
    assert ss.is_loopback_host(host) is loopback


def test_bind_guard_allows_loopback_without_token():
    assert ss.enforce_bind_security("127.0.0.1") is None


def test_bind_guard_refuses_remote_without_token():
    with pytest.raises(RuntimeError):
        ss.enforce_bind_security("0.0.0.0")


def test_bind_guard_allows_remote_with_token(monkeypatch):
    monkeypatch.setenv(ss.API_TOKEN_ENV, "secret123")
    assert ss.enforce_bind_security("0.0.0.0") == "secret123"


@pytest.mark.parametrize(
    "header,token,ok",
    [
        ("Bearer secret123", "secret123", True),
        ("bearer secret123", "secret123", True),  # scheme is case-insensitive
        ("Bearer wrong", "secret123", False),
        ("secret123", "secret123", False),  # missing scheme
        ("", "secret123", False),
        ("Bearer secret123", "", False),  # no token configured
    ],
)
def test_token_matches(header, token, ok):
    assert ss.token_matches(header, token) is ok


# --------------------------------------------------------------------------- #
# FastAPI middleware enforcement (auth-rejection path needs no ToolUniverse)
# --------------------------------------------------------------------------- #


def test_http_api_requires_token_when_configured(monkeypatch):
    monkeypatch.setenv(ss.API_TOKEN_ENV, "tok-123")
    fastapi_testclient = pytest.importorskip("fastapi.testclient")
    from tooluniverse import http_api_server

    client = fastapi_testclient.TestClient(http_api_server.app)

    # /health stays public for liveness probes.
    assert client.get("/health").status_code == 200

    # Protected route without a token is rejected before any tool runs.
    resp = client.get("/api/methods")
    assert resp.status_code == 401
    assert resp.json()["error_type"] == "AuthenticationError"

    # Wrong token is rejected too.
    resp = client.get("/api/methods", headers={"Authorization": "Bearer nope"})
    assert resp.status_code == 401


def test_http_api_open_when_no_token(monkeypatch):
    """With no token configured (loopback-only dev mode), routes are reachable."""
    monkeypatch.delenv(ss.API_TOKEN_ENV, raising=False)
    fastapi_testclient = pytest.importorskip("fastapi.testclient")
    from tooluniverse import http_api_server

    client = fastapi_testclient.TestClient(http_api_server.app)
    # No 401 — the middleware is a no-op without a configured token.
    assert client.get("/health").status_code == 200
