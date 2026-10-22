"""Scientific tokens, residue IDs and authors are not credential failures."""

import contextlib
import importlib
import io
import json
import sys
from types import SimpleNamespace

import pytest

from tooluniverse.base_tool import BaseTool
from tooluniverse.exceptions import ToolAuthError, ToolRateLimitError

pytestmark = pytest.mark.unit


class SyntheticAtomFailure(BaseTool):
    def run(self, arguments):
        raise AssertionError(
            "Input transform failed: No representative atom (CB) found. Token: A 1 ALA"
        )


@pytest.fixture
def tool():
    return SyntheticAtomFailure({"name": "Synthetic_atom_error"})


@pytest.mark.parametrize(
    "message",
    [
        "No representative atom (CB) found. Token: A 1 ALA",
        "Invalid token at position 3 in an expression",
        "Model token count exceeds the supported context size",
        "Tokenization failed for the input sequence",
        "Author lookup failed",
        "Missing auth_seq_id in an atom table",
        "Structure contains 401 residues",
        "403 features were returned",
        "Coordinate 0.401 is outside the expected range",
        "Distance 0.403 is too short",
    ],
)
def test_scientific_text_does_not_imply_credentials(tool, message):
    assert not isinstance(tool.handle_error(Exception(message)), ToolAuthError)


@pytest.mark.parametrize(
    "message",
    [
        "Authentication failed",
        "Authorization required",
        "401 Unauthorized",
        "403 Forbidden",
        "Auth failed",
        "Invalid API key",
        "API_KEY missing",
        "Access token rejected",
        "Bearer token expired",
        "Token expired",
        "Expired token",
        "Invalid token",
        "HTTP/1.1 401",
        "status_code=403",
        "401",
        "403",
    ],
)
def test_explicit_credential_failures_still_auth(tool, message):
    assert isinstance(tool.handle_error(Exception(message)), ToolAuthError)


@pytest.mark.parametrize("status", [401, 403])
def test_http_status_is_authoritative_even_without_status_in_text(tool, status):
    exception = Exception("Request rejected")
    exception.response = SimpleNamespace(
        status_code=status, json=lambda: {"message": "Credentials rejected"}
    )
    result = tool.handle_error(exception)
    assert isinstance(result, ToolAuthError)
    assert "Credentials rejected" in str(result)


def test_token_budget_error_keeps_rate_limit_classification(tool):
    assert isinstance(
        tool.handle_error(Exception("Token limit exceeded")), ToolRateLimitError
    )


def test_cli_preserves_synthetic_model_failure_without_auth_advice(monkeypatch, capsys):
    cli = importlib.import_module("tooluniverse.cli")
    # Use the real execute_tool router, with no external tool/service invocation.
    with contextlib.redirect_stdout(io.StringIO()):
        tu = cli._get_tu()
        tu.register_custom_tool(
            SyntheticAtomFailure,
            tool_name="SyntheticAtomFailure",
            tool_config={
                "name": "Synthetic_atom_error",
                "type": "SyntheticAtomFailure",
                "description": "Public synthetic atom-transform failure",
                "parameter": {"type": "object", "properties": {}},
            },
            instantiate=True,
        )
    monkeypatch.setattr(cli, "_get_tu", lambda: tu)
    monkeypatch.setattr(
        sys, "argv", ["tu", "run", "Synthetic_atom_error", "{}", "--json"]
    )
    with pytest.raises(SystemExit) as exit_info:
        cli.main()
    assert exit_info.value.code == 1
    result = json.loads(capsys.readouterr().out)
    assert result["error_details"]["type"] == "ToolServerError"
    assert "No representative atom" in result["error"]
    assert "Check API key configuration" not in result["error_details"]["next_steps"]
