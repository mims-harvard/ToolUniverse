#!/usr/bin/env python3
"""
Tests for ToolUniverse_get_usage_tips (UsageTipsTool).

This tool requires no API keys, no network, and no heavy models —
it is the canonical "always works" offline tool for testing.
"""

import sys
import unittest
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse import ToolUniverse

TOOL_NAME = "ToolUniverse_get_usage_tips"
ALL_TOPICS = ["loading", "running", "searching", "workspace"]


@pytest.mark.unit
class TestUsageTipsTool(unittest.TestCase):
    """Tests for the ToolUniverse_get_usage_tips tool."""

    def setUp(self):
        self.tu = ToolUniverse()
        # Explicitly load tools so all_tool_dict is populated regardless of
        # whether workspace auto-load is available in the test environment.
        if not self.tu.all_tool_dict:
            self.tu.load_tools()

    def tearDown(self):
        if hasattr(self, "tu"):
            self.tu.close()

    # ------------------------------------------------------------------
    # Tool discovery
    # ------------------------------------------------------------------

    def test_tool_is_discoverable(self):
        """Tool must appear in all_tool_dict after load."""
        self.assertIn(
            TOOL_NAME,
            self.tu.all_tool_dict,
            f"'{TOOL_NAME}' not found in all_tool_dict",
        )

    def test_tool_config_has_required_fields(self):
        """Tool config dict must contain name, type, description, parameter."""
        config = self.tu.all_tool_dict[TOOL_NAME]
        for field in ("name", "type", "description", "parameter"):
            self.assertIn(field, config, f"Missing field '{field}' in tool config")
        self.assertEqual(config["name"], TOOL_NAME)

    # ------------------------------------------------------------------
    # Default / 'all' topic
    # ------------------------------------------------------------------

    def test_run_no_arguments_returns_all_tips(self):
        """Calling with no arguments (or topic='all') returns all topics."""
        result = self.tu.run({"name": TOOL_NAME, "arguments": {}})
        self.assertIsInstance(result, dict)
        self.assertNotIn("error", result, f"Unexpected error: {result}")
        self.assertEqual(result.get("topic"), "all")
        self.assertIsInstance(result.get("tips"), dict)
        self.assertIsInstance(result.get("available_topics"), list)
        for topic in ALL_TOPICS:
            self.assertIn(topic, result["tips"], f"Missing topic '{topic}' in tips")

    def test_run_topic_all_explicit(self):
        """Explicit topic='all' must return the same structure as no arguments."""
        result = self.tu.run({"name": TOOL_NAME, "arguments": {"topic": "all"}})
        self.assertIsInstance(result, dict)
        self.assertNotIn("error", result)
        self.assertEqual(result.get("topic"), "all")
        self.assertIsInstance(result.get("tips"), dict)

    # ------------------------------------------------------------------
    # Individual topics
    # ------------------------------------------------------------------

    def _assert_topic_result(self, topic):
        result = self.tu.run({"name": TOOL_NAME, "arguments": {"topic": topic}})
        self.assertIsInstance(result, dict, f"topic={topic}: expected dict")
        self.assertNotIn("error", result, f"topic={topic}: unexpected error: {result}")
        self.assertEqual(result.get("topic"), topic)
        tips = result.get("tips")
        self.assertIsInstance(tips, list, f"topic={topic}: tips must be a list")
        self.assertGreater(len(tips), 0, f"topic={topic}: tips list must not be empty")
        for tip in tips:
            self.assertIsInstance(tip, str, f"topic={topic}: each tip must be a string")
            self.assertGreater(len(tip), 5, f"topic={topic}: tip too short: {tip!r}")

    def test_topic_loading(self):
        self._assert_topic_result("loading")

    def test_topic_running(self):
        self._assert_topic_result("running")

    def test_topic_searching(self):
        self._assert_topic_result("searching")

    def test_topic_workspace(self):
        self._assert_topic_result("workspace")

    # ------------------------------------------------------------------
    # available_topics field
    # ------------------------------------------------------------------

    def test_available_topics_returned_always(self):
        """Every response must include available_topics listing all topics."""
        for topic in ALL_TOPICS + ["all"]:
            result = self.tu.run({"name": TOOL_NAME, "arguments": {"topic": topic}})
            avail = result.get("available_topics")
            self.assertIsInstance(avail, list, f"topic={topic}: available_topics must be list")
            for t in ALL_TOPICS:
                self.assertIn(t, avail, f"topic={topic}: '{t}' missing from available_topics")

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    def test_unknown_topic_returns_error(self):
        """An unrecognised topic must return an error dict, never raise."""
        result = self.tu.run(
            {"name": TOOL_NAME, "arguments": {"topic": "nonexistent_topic_xyz"}}
        )
        self.assertIsInstance(result, dict)
        self.assertIn("error", result, "Expected error for unknown topic")
        self.assertGreater(len(result["error"]), 0)

    def test_run_never_raises(self):
        """run() must never raise an exception regardless of input."""
        bad_inputs = [
            {"topic": None},
            {"topic": 123},
            {"topic": ""},
            {"unexpected_key": "value"},
            None,
        ]
        for args in bad_inputs:
            try:
                result = self.tu.run({"name": TOOL_NAME, "arguments": args})
                self.assertIsInstance(result, dict, f"args={args}: expected dict, got {result!r}")
            except Exception as exc:  # noqa: BLE001
                self.fail(f"run() raised {type(exc).__name__} for args={args!r}: {exc}")

    # ------------------------------------------------------------------
    # Content sanity checks
    # ------------------------------------------------------------------

    def test_running_tips_mention_run_method(self):
        """The 'running' tips must mention 'run()' and 'dict'."""
        result = self.tu.run({"name": TOOL_NAME, "arguments": {"topic": "running"}})
        tips_text = " ".join(result.get("tips", []))
        self.assertIn("run", tips_text.lower())
        self.assertIn("dict", tips_text.lower())

    def test_loading_tips_mention_load_tools(self):
        """The 'loading' tips must mention 'load_tools'."""
        result = self.tu.run({"name": TOOL_NAME, "arguments": {"topic": "loading"}})
        tips_text = " ".join(result.get("tips", []))
        self.assertIn("load_tools", tips_text)

    def test_workspace_tips_mention_tooluniverse_dir(self):
        """The 'workspace' tips must mention '.tooluniverse'."""
        result = self.tu.run({"name": TOOL_NAME, "arguments": {"topic": "workspace"}})
        tips_text = " ".join(result.get("tips", []))
        self.assertIn(".tooluniverse", tips_text)


if __name__ == "__main__":
    unittest.main()
