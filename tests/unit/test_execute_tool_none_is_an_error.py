"""Fix-47-4: execute_tool presented a failed call as an empty answer.

`execute_tool` wrapped any non-dict, non-str inner result in `{"result": ...}`,
so a tool returning `None` came back as `{"result": None}` -- a dict with no
`status` and no `error`. The CLI prints that as `{"result": null}` and exits 0.
There is no tool for which `None` is a valid answer, so every one of those was
a failure presented as a successful empty result: for the openFDA label family
`{"result": null}` in answer to a boxed-warning question reads as "this drug
has no boxed warning".

The openFDA path that produced most of these is fixed at source (Fix-47-1),
but a None from ANY tool reaches the caller through a dispatch wrapper, and
there are two of them. `execute_tool` itself is declared `type: "ExecuteTool"`
in data/compact_mode_tools.json, so it dispatches through
`ExecuteToolTool.run` -- that is the one the CLI and MCP callers reach.
`ComposeTool._call_tool` is the other, reached from composition scripts. Both
are exercised below against the same invariant, because a test written against
only the compose helper passes green while the CLI still prints
`{"result": null}`.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.compose_tool import ComposeTool
from tooluniverse.tool_discovery_tools import ExecuteToolTool

pytestmark = pytest.mark.unit


def _tooluniverse(inner_result):
    tu = MagicMock()
    tu.callable_functions = {"SomeTool": object()}
    tu.all_tool_dict = {"SomeTool": {"name": "SomeTool"}}
    tu.run_one_function.return_value = inner_result
    return tu


def _run(inner_result):
    """Drive `execute_tool` the way the CLI and MCP do."""
    tool = ExecuteToolTool(
        {"name": "execute_tool", "parameter": {}, "fields": {}},
        tooluniverse=_tooluniverse(inner_result),
    )
    return tool.run(
        {"tool_name": "SomeTool", "arguments": {"drug_name": "tramadol"}}
    )


def _run_via_compose(inner_result):
    """Drive the second wrapper, used by composition scripts."""
    tool = ComposeTool(
        {"name": "compose_test", "parameter": {}, "fields": {}},
        tooluniverse=_tooluniverse(inner_result),
    )
    return tool._call_tool("SomeTool", {"drug_name": "tramadol"})


class TestExecuteToolIsTheDispatchedClass:
    def test_execute_tool_config_declares_the_class_under_test(self):
        """If execute_tool stops routing through ExecuteToolTool, the rest of
        this file would be testing a path no caller reaches."""
        import json

        cfg = json.loads(
            (
                Path(__file__).parent.parent.parent
                / "src/tooluniverse/data/compact_mode_tools.json"
            ).read_text()
        )
        tool = next(t for t in cfg if t["name"] == "execute_tool")
        assert tool["type"] == "ExecuteTool"


class TestNoneBecomesAnErrorViaCompose:
    def test_none_reports_error_status(self):
        assert _run_via_compose(None)["status"] == "error"

    def test_error_names_the_tool_that_failed(self):
        assert "SomeTool" in _run_via_compose(None)["error"]


class TestNoneBecomesAnError:
    def test_none_is_not_wrapped_as_a_result(self):
        assert _run(None) != {"result": None}

    def test_none_reports_error_status(self):
        assert _run(None)["status"] == "error"

    def test_error_names_the_tool_that_failed(self):
        assert "SomeTool" in _run(None)["error"]

    def test_error_denies_that_the_query_matched_nothing(self):
        """The whole hazard is reading this as a real, empty answer."""
        assert "does not mean the query matched nothing" in _run(None)["error"]


class TestOtherResultShapesUnchanged:
    def test_dict_result_passes_through(self):
        payload = {"status": "success", "results": [{"boxed_warning": ["x"]}]}
        assert _run(payload) == payload

    def test_json_string_result_still_parsed(self):
        assert _run('{"status": "success", "n": 1}') == {"status": "success", "n": 1}

    def test_plain_string_result_still_wrapped(self):
        assert _run("some text") == {"result": "some text"}

    def test_falsy_but_real_results_are_not_treated_as_failures(self):
        """An empty list is a genuine 'no matches'; only None is a failure."""
        assert _run([]) == {"result": []}
        assert _run(0) == {"result": 0}
