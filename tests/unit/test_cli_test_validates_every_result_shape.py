"""`tu test` must check a declared return_schema whatever shape the tool answers in.

The validation step used to run only when the result was the {"status", "data"}
envelope or a bare list. Everything else was skipped, and the largest thing it
skipped was a whole family: the 50 AgenticTool and 11 ComposeTool configs. Those
tools answer either with the model's text or with {"success", "result",
"metadata"} -- which carries `success`, not `status` -- so neither branch of the
condition matched, and `tu test` never looked at their schemas.

That is not a case of thin declarations going unchecked. Those 61 schemas are the
careful ones: 49 distinct shapes across the 50 AgenticTool configs, with oneOf
branches for the text and envelope forms, `$defs` for the metadata block, and
descriptions that say which parts the model produces and which AgenticTool builds
itself. None of it had ever been tested against a result.

The guard here is the gate's own condition, exercised through `cmd_test` with the
tool's result canned, so each shape is checked without running a model.
"""

import argparse

import pytest

from tooluniverse import cli

pytestmark = pytest.mark.unit


class _StubTU:
    def __init__(self, tool_def, return_value):
        self.all_tool_dict = {tool_def["name"]: tool_def}
        self._return_value = return_value
        self.exit_code = 0

    def run_one_function(self, _call):
        return self._return_value


def _run(monkeypatch, return_value, return_schema):
    tu = _StubTU(
        {
            "name": "FakeAgenticTool",
            "description": "x",
            "test_examples": [{"q": "hi"}],
            "return_schema": return_schema,
        },
        return_value,
    )
    monkeypatch.setattr(cli, "_get_tu", lambda: tu)
    ns = argparse.Namespace(
        tool_name="FakeAgenticTool", args_json=None, config=None, json=False
    )
    try:
        cli.cmd_test(ns)
    except SystemExit as exc:
        tu.exit_code = exc.code
    return tu


# The shape AgenticTool actually returns, in both of its forms.
_AGENTIC_SCHEMA = {
    "oneOf": [
        {"type": ["string", "null"], "description": "The model's answer, as text."},
        {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "result": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "required": ["success", "result"],
        },
    ]
}


def test_a_text_answer_is_validated(monkeypatch, capsys, disable_network):
    """A bare string is neither the status envelope nor a list; it was skipped."""
    tu = _run(monkeypatch, "the model said this", _AGENTIC_SCHEMA)
    assert tu.exit_code == 0
    assert "return_schema mismatch" not in capsys.readouterr().out


def test_a_text_answer_that_contradicts_the_schema_now_fails(
    monkeypatch, capsys, disable_network
):
    tu = _run(monkeypatch, "the model said this", {"type": "object"})
    out = capsys.readouterr().out
    assert tu.exit_code == 1
    assert "return_schema mismatch" in out


def test_the_agentic_envelope_is_validated(monkeypatch, capsys, disable_network):
    """{"success", "result", "metadata"} carries `success`, not `status`."""
    tu = _run(
        monkeypatch,
        {"success": True, "result": "text", "metadata": {"model": "x"}},
        _AGENTIC_SCHEMA,
    )
    assert tu.exit_code == 0
    assert "return_schema mismatch" not in capsys.readouterr().out


def test_an_agentic_envelope_that_contradicts_the_schema_now_fails(
    monkeypatch, capsys, disable_network
):
    tu = _run(
        monkeypatch,
        {"success": True, "result": {"not": "a string"}, "metadata": {}},
        _AGENTIC_SCHEMA,
    )
    out = capsys.readouterr().out
    assert tu.exit_code == 1
    assert "return_schema mismatch" in out


def test_a_scalar_answer_is_validated(monkeypatch, capsys, disable_network):
    tu = _run(monkeypatch, 42, {"type": "string"})
    assert tu.exit_code == 1
    assert "return_schema mismatch" in capsys.readouterr().out


def test_the_status_envelope_still_has_its_inner_payload_checked(
    monkeypatch, capsys, disable_network
):
    """The behaviour this widening must not disturb: issue #246's unwrap."""
    tu = _run(
        monkeypatch,
        {"status": "success", "data": {"n": "not an integer"}},
        {"type": "object", "properties": {"n": {"type": "integer"}}},
    )
    out = capsys.readouterr().out
    assert tu.exit_code == 1
    assert "return_schema mismatch" in out


def test_a_schema_that_describes_the_envelope_is_still_taken_at_its_word(
    monkeypatch, capsys, disable_network
):
    """A schema declaring `status` and `data` together describes the envelope."""
    tu = _run(
        monkeypatch,
        {"status": "success", "data": {"n": 1}},
        {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "data": {"type": "object"},
            },
            "required": ["status", "data"],
        },
    )
    assert tu.exit_code == 0
    assert "return_schema mismatch" not in capsys.readouterr().out


def test_an_error_result_is_still_reported_as_an_error_not_a_schema_mismatch(
    monkeypatch, capsys, disable_network
):
    """Widening must not turn a tool's own failure into a schema complaint."""
    tu = _run(
        monkeypatch,
        {"status": "error", "error": "upstream is down"},
        {"type": "object", "properties": {"n": {"type": "integer"}}},
    )
    out = capsys.readouterr().out
    assert tu.exit_code == 1
    assert "tool returned error" in out
    assert "return_schema mismatch" not in out
