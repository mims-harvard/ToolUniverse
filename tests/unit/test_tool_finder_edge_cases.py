#!/usr/bin/env python3
"""
Test edge cases and error handling for Tool Finder functionality.

Tests Tool_Finder_Keyword (no API key required — pure keyword search).
Each test makes direct assertions; no try/except that hides failures.
"""

import sys
import threading
import unittest
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse import ToolUniverse


def _assert_finder_result(result, test_label=""):
    """Assert that a Tool_Finder_Keyword result is valid.

    Tool_Finder_Keyword returns either:
    - a list of tool dicts (success)
    - an error dict with 'error' key (validation failure or empty results)
    """
    assert isinstance(result, (list, dict)), (
        f"{test_label}: expected list or dict, got {type(result).__name__}: {result!r}"
    )
    if isinstance(result, dict):
        assert "error" in result, (
            f"{test_label}: dict result must have 'error' key, got keys: {list(result.keys())}"
        )
    else:
        # It's a list — each element should be a dict
        for i, item in enumerate(result):
            assert isinstance(item, dict), (
                f"{test_label}: tools[{i}] must be dict, got {type(item).__name__}"
            )


class TestToolFinderEdgeCases(unittest.TestCase):
    """Test edge cases and error handling for Tool_Finder_Keyword."""

    def setUp(self):
        self.tu = ToolUniverse()
        self.tu.load_tools()

    def tearDown(self):
        if hasattr(self, "tu"):
            self.tu.close()

    # ------------------------------------------------------------------ #
    #  run() must never raise — all results are dicts                     #
    # ------------------------------------------------------------------ #

    def test_empty_query(self):
        """Empty query string should return a meaningful result dict."""
        result = self.tu.run({
            "name": "Tool_Finder_Keyword",
            "arguments": {"description": "", "limit": 5},
        })
        _assert_finder_result(result, "empty query")

    def test_negative_limit(self):
        """Negative limit should be handled gracefully (error or tools)."""
        result = self.tu.run({
            "name": "Tool_Finder_Keyword",
            "arguments": {"description": "test", "limit": -1},
        })
        _assert_finder_result(result, "negative limit")

    def test_very_large_limit(self):
        """Very large limit should not crash; result is capped or returned fully."""
        result = self.tu.run({
            "name": "Tool_Finder_Keyword",
            "arguments": {"description": "protein", "limit": 10000},
        })
        _assert_finder_result(result, "large limit")
        if "tools" in result:
            # Result must not contain more tools than exist
            assert len(result["tools"]) <= 10000

    def test_special_characters_in_query(self):
        """Special-character queries should return a meaningful result, not crash."""
        special_queries = [
            "test@#$%^&*()",
            "test with spaces and symbols!@#",
            'test with quotes: "double" and \'single\'',
        ]
        for query in special_queries:
            result = self.tu.run({
                "name": "Tool_Finder_Keyword",
                "arguments": {"description": query, "limit": 5},
            })
            _assert_finder_result(result, f"special chars: {query[:20]!r}")

    def test_missing_required_description(self):
        """Omitting the required 'description' param must return an error dict."""
        result = self.tu.run({
            "name": "Tool_Finder_Keyword",
            "arguments": {"limit": 5},
        })
        assert isinstance(result, dict)
        assert "error" in result, (
            "Expected error for missing 'description', got: " + repr(result)
        )

    def test_extra_parameters_ignored(self):
        """Extra unknown parameters should be ignored and not prevent a result."""
        result = self.tu.run({
            "name": "Tool_Finder_Keyword",
            "arguments": {
                "description": "test",
                "limit": 5,
                "extra_param": "should_be_ignored",
            },
        })
        _assert_finder_result(result, "extra params")

    def test_wrong_limit_type_string(self):
        """A non-integer limit should return an error (schema validation) or be coerced."""
        result = self.tu.run({
            "name": "Tool_Finder_Keyword",
            "arguments": {"description": "test", "limit": "not_a_number"},
        })
        assert isinstance(result, dict), f"Expected dict, got: {result!r}"
        # Either schema validation error or a result with tools is acceptable
        assert "error" in result or "tools" in result

    def test_none_description(self):
        """None description must return an error dict, not crash."""
        result = self.tu.run({
            "name": "Tool_Finder_Keyword",
            "arguments": {"description": None, "limit": 5},
        })
        # None is not a valid string — expect validation error dict (not a list)
        assert isinstance(result, dict), (
            f"Expected error dict for None description, got {type(result).__name__}: {result!r}"
        )
        assert "error" in result, (
            "Expected error for None description, got: " + repr(result)
        )

    def test_very_long_query(self):
        """A 5 000-word query should return a dict without crashing."""
        long_query = "test " * 1000
        result = self.tu.run({
            "name": "Tool_Finder_Keyword",
            "arguments": {"description": long_query, "limit": 5},
        })
        _assert_finder_result(result, "long query")

    def test_unicode_query(self):
        """Unicode characters in queries must not crash the finder."""
        unicode_queries = [
            "test with emoji: 🧬🔬🧪",
            "test with accented chars: café naïve résumé",
            "test with symbols: ∑∏∫√∞",
            "test with currency: €£¥$",
        ]
        for query in unicode_queries:
            result = self.tu.run({
                "name": "Tool_Finder_Keyword",
                "arguments": {"description": query, "limit": 5},
            })
            _assert_finder_result(result, f"unicode: {query[:20]!r}")

    def test_concurrent_calls(self):
        """Concurrent Tool_Finder_Keyword calls must all complete and return dicts."""
        results = []
        lock = threading.Lock()

        def make_call(query_id):
            result = self.tu.run({
                "name": "Tool_Finder_Keyword",
                "arguments": {"description": f"protein query {query_id}", "limit": 5},
            })
            with lock:
                results.append(result)

        threads = [threading.Thread(target=make_call, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        self.assertEqual(len(results), 3, f"Expected 3 results, got {len(results)}")
        for i, r in enumerate(results):
            _assert_finder_result(r, f"concurrent call {i}")

    def test_actual_functionality_returns_tools(self):
        """A meaningful query must return a non-empty list of tool dicts."""
        result = self.tu.run({
            "name": "Tool_Finder_Keyword",
            "arguments": {"description": "protein sequence search", "limit": 5},
        })
        # Keyword finder returns a list of matching tool dicts directly
        self.assertIsInstance(result, list, f"Expected list, got {type(result).__name__}: {result!r}")
        self.assertGreater(len(result), 0, "Expected at least one keyword match for 'protein'")
        for tool in result:
            self.assertIsInstance(tool, dict, f"Each tool must be a dict, got: {tool!r}")
            self.assertIn("name", tool, f"Each tool must have a 'name' key: {tool!r}")
            self.assertIsInstance(tool["name"], str)

    def test_result_respects_limit(self):
        """Result list must contain at most `limit` tools."""
        limit = 3
        result = self.tu.run({
            "name": "Tool_Finder_Keyword",
            "arguments": {"description": "protein", "limit": limit},
        })
        _assert_finder_result(result, "limit respected")
        if isinstance(result, list):
            self.assertLessEqual(
                len(result), limit,
                f"Expected <= {limit} tools, got {len(result)}"
            )

    @pytest.mark.require_api_keys
    def test_llm_finder_edge_cases(self):
        """Tool_Finder_LLM must return a list or error dict — requires LLM API key."""
        edge_cases = [
            {"description": "a", "limit": 1},
            {"description": "protein", "limit": 5},
        ]
        for case in edge_cases:
            result = self.tu.run({"name": "Tool_Finder_LLM", "arguments": case})
            assert isinstance(result, (list, dict)), (
                f"Expected list or dict for {case}, got: {type(result).__name__}: {result!r}"
            )

    @pytest.mark.require_gpu
    @pytest.mark.skip(reason="Causes SIGABRT in full test suite due to resource exhaustion")
    def test_embedding_finder_edge_cases(self):
        """Tool_Finder (embedding) edge cases — requires GPU/heavy model."""
        edge_cases = [
            {"description": "", "limit": 0, "return_call_result": False},
            {"description": "a", "limit": 1, "return_call_result": True},
        ]
        for case in edge_cases:
            result = self.tu.run({"name": "Tool_Finder", "arguments": case})
            assert isinstance(result, dict)


if __name__ == "__main__":
    unittest.main()
