"""`tu test` must score list-shaped error payloads as failures.

``cmd_test`` used to guard every failure branch behind ``isinstance(result,
dict)``. Several tools return a list-shaped error payload ``[{"error": ...}]``
from ``run()`` on upstream failure (CoreTool, PMCTool, the FAERS
detail/interaction tools), so a tool that returned nothing but an error was
reported as PASSED. That silently degrades the signal of the very command the
regression harness runs each round.

These tests are hermetic in two layers: ``_get_tu`` is replaced with a stub
whose ``run_one_function`` returns a canned value, so nothing below the CLI
runs at all, and the shared ``disable_network`` fixture blocks
``Session.request`` underneath it. The stub sits at ``run_one_function``
rather than at the HTTP client because these tools reach the network through
both ``requests.get`` and ``http_utils.request_with_retry`` ->
``requests.request``; patching one of those would not be hermetic.
"""

import argparse
import json

import pytest

from tooluniverse import cli

pytestmark = pytest.mark.unit

_ERROR_PAYLOAD = [{"error": "API request failed: 503 Server Error: upstream is down"}]
_ARRAY_SCHEMA = {"type": "array", "items": {"type": "object"}}


class _StubTU:
    """Minimal stand-in for ToolUniverse: one tool, one canned result."""

    def __init__(self, tool_def, return_value):
        self.all_tool_dict = {tool_def["name"]: tool_def}
        self._return_value = return_value
        self.calls = []
        self.exit_code = 0

    def run_one_function(self, call):
        self.calls.append(call)
        return self._return_value


def _tool_def(**extra):
    tool_def = {
        "name": "FakeListTool",
        "description": "x",
        "test_examples": [{"q": "hi"}],
    }
    tool_def.update(extra)
    return tool_def


def _run_cmd_test(monkeypatch, return_value, return_schema=None, use_json=False):
    """Run cmd_test against a canned result; return the stub, exit code attached."""
    extra = {"return_schema": return_schema} if return_schema else {}
    tu = _StubTU(_tool_def(**extra), return_value)
    monkeypatch.setattr(cli, "_get_tu", lambda: tu)

    ns = argparse.Namespace(
        tool_name="FakeListTool", args_json=None, config=None, json=use_json
    )
    try:
        cli.cmd_test(ns)
    except SystemExit as exc:
        tu.exit_code = exc.code
    return tu


def test_list_shaped_error_payload_is_a_failure(monkeypatch, capsys, disable_network):
    """[{"error": ...}] must fail, not pass — and nothing below the CLI runs."""
    tu = _run_cmd_test(monkeypatch, _ERROR_PAYLOAD)
    out = capsys.readouterr().out

    assert tu.exit_code == 1
    assert "tool returned error" in out
    assert "503 Server Error" in out
    assert "1/1 test(s) failed" in out
    assert tu.calls == [{"name": "FakeListTool", "arguments": {"q": "hi"}}]


def test_list_shaped_error_payload_is_a_failure_in_json_mode(
    monkeypatch, capsys, disable_network
):
    """The --json path must report the same failure as the human path."""
    tu = _run_cmd_test(monkeypatch, _ERROR_PAYLOAD, use_json=True)
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])

    assert tu.exit_code == 1
    assert payload["status"] == "error"
    assert payload["passed"] == 0
    assert payload["failed"] == 1
    assert payload["tests"][0]["passed"] is False
    assert any("503 Server Error" in f for f in payload["tests"][0]["failures"])


@pytest.mark.parametrize(
    "case,result,exit_code,expected",
    [
        # Regression guard: openFDA count rows are data, not an error payload.
        ("count rows", [{"term": "NAUSEA", "count": 62}], 0, "All 1 test(s) passed"),
        # A row carrying both "term" and "error" is still a count row — same
        # rule as openfda_adv_tool._is_error_payload.
        (
            "count row with error key",
            [{"term": "NAUSEA", "count": 62, "error": None}],
            0,
            "All 1 test(s) passed",
        ),
        ("empty list", [], 1, "result is an empty list"),
        # Unchanged dict behaviour.
        ("empty dict", {}, 1, "result is an empty dict"),
        (
            "dict error",
            {"status": "error", "error": "upstream is down"},
            1,
            "tool returned error: upstream is down",
        ),
        (
            "dict success",
            {"status": "success", "data": {"r": 1}},
            0,
            "All 1 test(s) passed",
        ),
        ("none", None, 1, "result is None"),
    ],
)
def test_result_shape_scoring(
    monkeypatch, capsys, disable_network, case, result, exit_code, expected
):
    tu = _run_cmd_test(monkeypatch, result)

    assert tu.exit_code == exit_code, case
    assert expected in capsys.readouterr().out, case


@pytest.mark.parametrize(
    "case,result,exit_code,expected",
    [
        # Bare-list tools declare a top-level array return_schema describing the
        # list itself, so the whole result is what gets validated.
        ("schema mismatch", ["not-an-object"], 1, "return_schema mismatch"),
        (
            "schema satisfied",
            [{"term": "NAUSEA", "count": 62}],
            0,
            "All 1 test(s) passed",
        ),
    ],
)
def test_list_result_validated_against_return_schema(
    monkeypatch, capsys, disable_network, case, result, exit_code, expected
):
    tu = _run_cmd_test(monkeypatch, result, return_schema=_ARRAY_SCHEMA)

    assert tu.exit_code == exit_code, case
    assert expected in capsys.readouterr().out, case


def test_error_payload_short_circuits_schema_validation(
    monkeypatch, capsys, disable_network
):
    """An error payload is reported as an error, not as a schema mismatch."""
    tu = _run_cmd_test(
        monkeypatch, [{"error": "upstream is down"}], return_schema={"type": "object"}
    )
    out = capsys.readouterr().out

    assert tu.exit_code == 1
    assert "tool returned error: upstream is down" in out
    assert "return_schema mismatch" not in out
