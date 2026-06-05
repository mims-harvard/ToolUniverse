"""_classify_exception must not assume every tool has handle_error.

Regression: some registered tools are plain classes (not BaseTool subclasses)
and lack ``handle_error``. When such a tool raised, the framework called
``tool_instance.handle_error(exception)`` unconditionally, producing a cryptic
``AttributeError: ... has no attribute 'handle_error'`` that masked the tool's
real error. The framework should fall back to a generic ToolError instead.
"""

import unittest

import pytest

pytestmark = pytest.mark.unit


class _PlainTool:
    """A tool that is not a BaseTool subclass (no handle_error)."""

    def run(self, arguments):  # pragma: no cover - not called here
        raise RuntimeError("boom")


class TestClassifyExceptionGuard(unittest.TestCase):
    def test_plain_tool_without_handle_error_falls_back(self):
        from tooluniverse.execute_function import ToolUniverse

        tu = ToolUniverse()
        # avoid the cost of loading the whole registry
        tu._get_tool_instance = lambda *a, **k: _PlainTool()

        err = tu._classify_exception(
            RuntimeError("boom"), "Some_plain_tool", {"x": 1}
        )
        # must return a ToolError describing the failure, not raise AttributeError
        self.assertIn("Some_plain_tool", str(err))
        self.assertIn("boom", str(err))

    def test_handle_error_is_used_when_present(self):
        from tooluniverse.execute_function import ToolUniverse

        sentinel = object()

        class _WithHandler:
            def handle_error(self, exc):
                return sentinel

        tu = ToolUniverse()
        tu._get_tool_instance = lambda *a, **k: _WithHandler()
        result = tu._classify_exception(RuntimeError("x"), "t", {})
        self.assertIs(result, sentinel)


if __name__ == "__main__":
    unittest.main()
