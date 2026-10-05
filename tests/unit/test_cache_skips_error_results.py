"""A tool result that reports an error must not be written to the result cache.

Tools report a timeout or an HTTP 429 by returning an error payload, not by
raising. Caching that payload replays the failure for the same arguments on
every later call, and with persistence on it survives a restart.
"""

import asyncio
import copy

import pytest

from tooluniverse import ToolUniverse
from tooluniverse.base_tool import BaseTool

pytestmark = pytest.mark.unit


class FlakyTool(BaseTool):
    """Fails on the first call, succeeds afterwards."""

    calls = 0
    failure = {"status": "error", "error": "Request to upstream API timed out"}

    def run(self, arguments, **kwargs):
        FlakyTool.calls += 1
        if FlakyTool.calls == 1:
            return copy.deepcopy(FlakyTool.failure)
        return {"status": "success", "data": {"value": arguments["value"]}}


_CONFIG = {
    "name": "FlakyToolTest",
    "type": "FlakyTool",
    "description": "Tool that fails once",
    "parameter": {
        "type": "object",
        "properties": {"value": {"type": "integer"}},
        "required": ["value"],
    },
}


def _make_tu():
    tu = ToolUniverse(tool_files={}, keep_default_tools=False)
    tu.register_custom_tool(FlakyTool, tool_config=_CONFIG)
    return tu


def _call(tu):
    return tu.run_one_function(
        {"name": "FlakyToolTest", "arguments": {"value": 7}}, use_cache=True
    )


def _call_async(tu):
    return asyncio.run(
        tu.run_one_function_async(
            {"name": "FlakyToolTest", "arguments": {"value": 7}}, use_cache=True
        )
    )


@pytest.mark.parametrize(
    "failure",
    [
        {"status": "error", "error": "Request to upstream API timed out"},
        {"error": "HTTP 429 Too Many Requests"},
        [{"error": "API request failed: 429 Client Error"}],
    ],
)
def test_error_result_is_not_cached(cache_env, failure):
    """The call after a failed one reaches the tool again."""
    FlakyTool.calls = 0
    FlakyTool.failure = failure
    tu = _make_tu()

    assert _call(tu) == failure
    assert _call(tu) == {"status": "success", "data": {"value": 7}}
    assert FlakyTool.calls == 2
    tu.close()


def test_error_result_is_not_cached_async(cache_env):
    """The async entry point skips error results as well."""
    FlakyTool.calls = 0
    FlakyTool.failure = {
        "status": "error",
        "error": "Request to upstream API timed out",
    }
    tu = _make_tu()

    assert _call_async(tu)["status"] == "error"
    assert _call_async(tu) == {"status": "success", "data": {"value": 7}}
    assert FlakyTool.calls == 2
    tu.close()


def test_error_result_is_not_persisted(cache_env):
    """A new instance on the same cache file does not see the failure."""
    FlakyTool.calls = 0
    FlakyTool.failure = {
        "status": "error",
        "error": "Request to upstream API timed out",
    }
    tu = _make_tu()
    assert _call(tu)["status"] == "error"
    tu.close()

    tu = _make_tu()
    assert _call(tu) == {"status": "success", "data": {"value": 7}}
    tu.close()


def test_success_result_is_still_cached(cache_env):
    """Only error results are skipped."""
    FlakyTool.calls = 1  # skip the failing first call
    tu = _make_tu()

    first = _call(tu)
    assert first["status"] == "success"
    assert _call(tu) == first
    assert FlakyTool.calls == 2
    tu.close()
