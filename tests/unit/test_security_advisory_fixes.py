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
# Path 4: module-pivot / FFI sandbox escape must be blocked
#
# The allowed scientific modules transitively expose dangerous stdlib modules as
# plain, non-dunder attributes (numpy.ctypeslib -> ctypes -> CDLL -> native code,
# matplotlib.os / .subprocess, random._os, collections._sys, enum's `bltns` alias
# of builtins -> getattr). None require a dunder, a forbidden import, or a
# forbidden call, so they bypassed the earlier checks. They are now blocked by the
# DANGEROUS_ATTRIBUTE_NAMES denylist (normalized: leading underscores stripped,
# lower-cased), which is sound because getattr/globals/vars/eval/exec are withheld
# so attribute access is only ever the literal obj.name the AST can see.
# --------------------------------------------------------------------------- #


MODULE_PIVOT_ESCAPES = [
    # ctypes -> native code execution (the confirmed RCE)
    "libc = numpy.ctypeslib.ctypes.CDLL(None)\nresult = libc.getpid()",
    # os / subprocess reached straight off matplotlib
    "result = matplotlib.os.system('id')",
    "result = matplotlib.subprocess.check_output(['id'])",
    # os reached via random's private alias (underscore-normalized to 'os')
    "result = random._os.system('id')",
    # sys reached via collections' private alias
    "result = collections._sys.modules",
    # builtins reached via the enum module's `bltns` alias, then getattr back
    "result = re.enum.bltns.getattr([], 'append')",
]


@pytest.mark.parametrize("code", MODULE_PIVOT_ESCAPES)
def test_module_pivot_escape_blocked(code):
    result = _run(code)
    assert result["status"] == "error", f"escape not blocked: {code!r}"
    assert "Forbidden" in result["data"]["error"]


@pytest.mark.parametrize(
    "code,expected",
    [
        # legit numeric attrs that resemble nothing dangerous keep working
        ("import numpy as np\nresult = int(np.random.RandomState(0).randint(5, 6))", 5),
        ("import numpy as np\nresult = float(np.trace(np.eye(3)))", 3.0),
        ("import numpy as np\nresult = float(np.trace(np.linalg.inv(np.eye(2))))", 2.0),
    ],
)
def test_numeric_attributes_not_false_positived(code, expected):
    result = _run(code)
    assert result["status"] == "success", result["data"].get("error")
    assert result["data"]["result"] == expected


def test_dangerous_attribute_normalization():
    """Underscore/case-alias forms normalize to the same denied name; legit
    numeric attribute names are not flagged."""
    is_bad = BasePythonExecutor._is_dangerous_attribute
    assert is_bad("os") and is_bad("_os") and is_bad("__os")  # noqa: PT018
    assert is_bad("CDLL") and is_bad("ctypeslib") and is_bad("bltns")  # noqa: PT018
    assert not is_bad("random")  # numpy.random
    assert not is_bad("signal")  # scipy.signal
    assert not is_bad("trace")  # numpy.trace
    assert not is_bad("compile")  # re.compile (handled separately as a call)


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


# --------------------------------------------------------------------------- #
# Client can authenticate against a token-protected server
# --------------------------------------------------------------------------- #


def test_client_sends_bearer_token_from_arg():
    from tooluniverse.http_client import ToolUniverseClient

    client = ToolUniverseClient("http://x:8080", api_token="abc")
    assert client.session.headers.get("Authorization") == "Bearer abc"


def test_client_reads_token_from_env(monkeypatch):
    monkeypatch.setenv(ss.API_TOKEN_ENV, "envtok")
    from tooluniverse.http_client import ToolUniverseClient

    client = ToolUniverseClient("http://x:8080")
    assert client.session.headers.get("Authorization") == "Bearer envtok"


def test_client_no_auth_header_without_token(monkeypatch):
    monkeypatch.delenv(ss.API_TOKEN_ENV, raising=False)
    from tooluniverse.http_client import ToolUniverseClient

    client = ToolUniverseClient("http://x:8080")
    assert "Authorization" not in client.session.headers


# --------------------------------------------------------------------------- #
# Tool Graph Web UI: loopback + debugger guards
# --------------------------------------------------------------------------- #


def _graph_ui(tmp_path):
    pytest.importorskip("flask")
    from tooluniverse.tool_graph_web_ui import ToolGraphWebUI

    graph_file = tmp_path / "graph.json"
    graph_file.write_text('{"nodes": [], "edges": []}')
    return ToolGraphWebUI(str(graph_file))


def test_graph_ui_refuses_remote_bind_without_token(tmp_path, monkeypatch):
    monkeypatch.delenv(ss.API_TOKEN_ENV, raising=False)
    ui = _graph_ui(tmp_path)
    monkeypatch.setattr(ui.app, "run", lambda **kw: None)  # must not be reached
    with pytest.raises(RuntimeError):
        ui.run(host="0.0.0.0")


def test_graph_ui_refuses_remote_debugger_even_with_token(tmp_path, monkeypatch):
    monkeypatch.setenv(ss.API_TOKEN_ENV, "tok")
    ui = _graph_ui(tmp_path)
    monkeypatch.setattr(ui.app, "run", lambda **kw: None)
    with pytest.raises(RuntimeError):
        ui.run(host="0.0.0.0", debug=True)


def test_graph_ui_loopback_default_runs(tmp_path, monkeypatch):
    monkeypatch.delenv(ss.API_TOKEN_ENV, raising=False)
    ui = _graph_ui(tmp_path)
    called = {}
    monkeypatch.setattr(ui.app, "run", lambda **kw: called.update(kw))
    ui.run()  # defaults: host=127.0.0.1, debug=False
    assert called["host"] == "127.0.0.1"
    assert called["debug"] is False
