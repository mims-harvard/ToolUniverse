#!/usr/bin/env python3
"""
Regression tests for the stream_callback UnboundLocalError bug (GitHub issue #28).

Problem: `dynamic_tool_function` inside `_create_mcp_tool_from_tooluniverse` used
`stream_callback` as both a local variable (cell variable, captured by the
`_run_with_stdout_capture` closure) and assigned it inside the outer `try:` block.
If any exception occurred before the `stream_callback = None` assignment was reached,
Python raised:

    UnboundLocalError: cannot access local variable 'stream_callback'
    where it is not associated with a value

which was then surfaced as:

    {"error": "Error executing <tool>: cannot access local variable 'stream_callback'..."}

Fix: move `stream_callback = None` to before the `try:` block so the cell variable is
always initialised regardless of execution path.

Reference: https://github.com/mims-harvard/ToolUniverse/issues/28
"""

import asyncio
import inspect
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.smcp import SMCP

# ---------------------------------------------------------------------------
# Minimal tool config used across tests
# ---------------------------------------------------------------------------
_MINIMAL_TOOL_CONFIG = {
    "name": "test_tool_stream_cb",
    "description": "Minimal test tool for stream_callback regression tests",
    "parameter": {
        "properties": {
            "query": {"type": "string", "description": "A search query"},
        },
        "required": ["query"],
    },
}


def _get_tool_fn(server: SMCP, tool_name: str):
    """Return the underlying async callable registered for *tool_name* in *server*.

    Works with fastmcp 2 (_tool_manager._tools) and fastmcp 3 (async get_tool).
    """
    # fastmcp 2: synchronous tool manager dict
    if hasattr(server, "_tool_manager"):
        tool_obj = server._tool_manager._tools.get(tool_name)
        return tool_obj.fn if tool_obj is not None else None
    # fastmcp 3: get_tool() is async
    async def _fetch():
        try:
            tool = await server.get_tool(tool_name)
            return tool.fn
        except Exception:
            return None
    return asyncio.run(_fetch())


@pytest.mark.unit
class TestStreamCallbackFix(unittest.TestCase):
    """Regression tests for GitHub issue #28 – stream_callback UnboundLocalError."""

    # ------------------------------------------------------------------
    # Source-code structural test (catches regressions at the code level)
    # ------------------------------------------------------------------

    def test_stream_callback_initialized_before_try_block(self):
        """stream_callback = None must appear before the outer try: in dynamic_tool_function.

        This is the core structural assertion for the fix.  If someone moves the
        initialisation back inside the try block, this test will fail immediately.
        """
        src = inspect.getsource(SMCP._create_mcp_tool_from_tooluniverse)
        lines = src.splitlines()

        stream_callback_line = None
        try_block_line = None
        in_dynamic_func = False

        for i, line in enumerate(lines):
            stripped = line.strip()
            if "async def dynamic_tool_function" in stripped:
                in_dynamic_func = True

            if not in_dynamic_func:
                continue

            if stripped == "stream_callback = None" and stream_callback_line is None:
                stream_callback_line = i
            # The very first 'try:' inside dynamic_tool_function is the outer try block.
            if stripped == "try:" and try_block_line is None:
                try_block_line = i

            if stream_callback_line is not None and try_block_line is not None:
                break

        self.assertIsNotNone(
            stream_callback_line,
            "Could not find 'stream_callback = None' inside dynamic_tool_function. "
            "Check that the fix is still in place.",
        )
        self.assertIsNotNone(
            try_block_line,
            "Could not find the outer 'try:' block inside dynamic_tool_function.",
        )
        self.assertLess(
            stream_callback_line,
            try_block_line,
            "REGRESSION (issue #28): 'stream_callback = None' must come BEFORE the "
            "outer 'try:' block in dynamic_tool_function.  Moving it inside the try "
            "block causes an UnboundLocalError when an early exception is raised.",
        )

    # ------------------------------------------------------------------
    # Functional async tests
    # ------------------------------------------------------------------

    def _make_server(self):
        """Create a bare SMCP instance with no real tools loaded."""
        server = SMCP(name="TestServer", tool_categories=[], search_enabled=False)
        return server

    def test_tool_fn_is_callable(self):
        """dynamic_tool_function must be exposed as a callable on a registered tool."""
        server = self._make_server()
        server._create_mcp_tool_from_tooluniverse(_MINIMAL_TOOL_CONFIG)

        fn = _get_tool_fn(server, "test_tool_stream_cb")
        self.assertIsNotNone(fn, "Tool function not found in _tool_manager after registration")
        self.assertTrue(callable(fn), "Registered tool entry should be callable")

    def test_normal_execution_does_not_raise_stream_callback_error(self):
        """A normal successful tool call must not produce a stream_callback error."""
        server = self._make_server()
        server._create_mcp_tool_from_tooluniverse(_MINIMAL_TOOL_CONFIG)

        fn = _get_tool_fn(server, "test_tool_stream_cb")
        if fn is None:
            self.skipTest("Could not retrieve dynamic_tool_function from SMCP")

        # Patch run_one_function to return a simple JSON result
        mock_result = json.dumps({"papers": [], "total": 0})
        server.tooluniverse.run_one_function = MagicMock(return_value=mock_result)

        result_json = asyncio.run(fn(query="CRISPR"))

        self.assertIsInstance(result_json, str)
        result = json.loads(result_json)
        self.assertNotIn(
            "stream_callback",
            result_json,
            "Successful tool call should not mention 'stream_callback' at all",
        )
        self.assertNotIn("error", result, "Successful tool call should return no error key")

    def test_early_exception_returns_clean_error_not_stream_callback(self):
        """If the tool executor raises an exception, the error must not reference stream_callback.

        This is the key regression scenario from issue #28: any unhandled exception
        inside dynamic_tool_function was reported as a stream_callback UnboundLocalError
        instead of the real underlying error.  After the fix the real error message is
        surfaced correctly.
        """
        server = self._make_server()
        server._create_mcp_tool_from_tooluniverse(_MINIMAL_TOOL_CONFIG)

        fn = _get_tool_fn(server, "test_tool_stream_cb")
        if fn is None:
            self.skipTest("Could not retrieve dynamic_tool_function from SMCP")

        # Make run_one_function raise a connection-style error (common in practice)
        server.tooluniverse.run_one_function = MagicMock(
            side_effect=RuntimeError("simulated network failure")
        )

        result_json = asyncio.run(fn(query="test"))

        self.assertIsInstance(result_json, str)
        result = json.loads(result_json)

        # Before the fix this would have contained "stream_callback"; after it must not
        self.assertNotIn(
            "stream_callback",
            result_json,
            "Error response must not reference 'stream_callback'. "
            "This indicates the UnboundLocalError regression from issue #28.",
        )
        # The real error cause should be present
        self.assertIn("error", result)
        self.assertIn("simulated network failure", result["error"])

    def test_asyncio_loop_exception_does_not_expose_stream_callback(self):
        """An unexpected exception from asyncio.get_running_loop must not leak stream_callback.

        In the original (unfixed) code, stream_callback = None was placed after the
        asyncio loop-acquisition block.  If that block raised an exception that was
        not RuntimeError, stream_callback could be left unbound.  This test ensures
        the fixed initialisation order prevents any such leak.
        """
        server = self._make_server()
        server._create_mcp_tool_from_tooluniverse(_MINIMAL_TOOL_CONFIG)

        fn = _get_tool_fn(server, "test_tool_stream_cb")
        if fn is None:
            self.skipTest("Could not retrieve dynamic_tool_function from SMCP")

        async def _call():
            # Raise a non-RuntimeError from get_running_loop so the inner
            # except RuntimeError branch cannot catch it and it must propagate
            # to the outer except.  With the fix stream_callback is already None
            # before this point so no UnboundLocalError is possible.
            with patch(
                "tooluniverse.smcp.asyncio.get_running_loop",
                side_effect=ValueError("mocked loop failure"),
            ):
                return await fn(query="test_query")

        result_json = asyncio.run(_call())

        self.assertIsInstance(result_json, str)
        self.assertNotIn(
            "stream_callback",
            result_json,
            "stream_callback must not appear in error when asyncio.get_running_loop raises. "
            "This is the exact regression scenario from issue #28.",
        )
        result = json.loads(result_json)
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
