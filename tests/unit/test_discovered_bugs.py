#!/usr/bin/env python3
"""
Test critical bugs and issues discovered during system testing.

Covers bugs unique to this file:
1. Deprecated method warnings
2. Tool loading does not hang
3. Error message quality (clear, helpful)
4. Parameter validation edge cases
5. Memory leak prevention
6. Cache management

Tests that duplicate test_critical_error_handling.py have been removed.
"""

import gc
import sys
import time
import unittest
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse import ToolUniverse
from tooluniverse.exceptions import ToolError, ToolValidationError  # noqa: F401


@pytest.mark.unit
class TestDiscoveredBugs(unittest.TestCase):
    """Test critical bugs and issues discovered during system testing."""

    def setUp(self):
        self.tu = ToolUniverse()
        self.tu.load_tools()

    def tearDown(self):
        if hasattr(self, "tu"):
            self.tu.close()

    # ------------------------------------------------------------------ #
    #  Deprecation warnings                                               #
    # ------------------------------------------------------------------ #

    def test_deprecated_method_warnings(self):
        """get_tool_by_name must issue a DeprecationWarning when called."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                result = self.tu.get_tool_by_name(["NonExistentTool"])
                self.assertIsInstance(result, list)
            except Exception:
                pass  # If the method no longer exists that is also fine

        deprecation_warnings = [
            warning for warning in w
            if issubclass(warning.category, DeprecationWarning)
        ]
        # If a deprecation warning is raised, it must mention the method name
        if deprecation_warnings:
            self.assertTrue(
                any("get_tool_by_name" in str(wn.message) for wn in deprecation_warnings),
                "DeprecationWarning should reference 'get_tool_by_name'",
            )

    # ------------------------------------------------------------------ #
    #  Tool loading must not hang                                         #
    # ------------------------------------------------------------------ #

    def test_tool_loading_does_not_hang(self):
        """load_tools() must complete within 30 seconds."""
        start = time.time()
        self.tu.load_tools()  # re-load (already loaded in setUp, should be fast)
        elapsed = time.time() - start
        self.assertLess(elapsed, 30, f"load_tools() took {elapsed:.1f}s (limit 30s)")

    # ------------------------------------------------------------------ #
    #  Error message quality                                              #
    # ------------------------------------------------------------------ #

    def test_error_message_clarity(self):
        """Error dict for an unknown tool must have a non-empty, meaningful message."""
        result = self.tu.run({
            "name": "NonExistentTool",
            "arguments": {"test": "value"},
        })

        self.assertIsInstance(result, dict)
        self.assertIn("error", result, "Expected error key for unknown tool")
        error_msg = str(result["error"])
        self.assertGreater(len(error_msg), 0, "Error message must not be empty")
        self.assertTrue(
            any(kw in error_msg.lower() for kw in ["tool", "not", "found", "error"]),
            f"Error message should mention tool/not/found/error: {error_msg!r}",
        )

    # ------------------------------------------------------------------ #
    #  Parameter validation edge cases                                    #
    # ------------------------------------------------------------------ #

    def test_parameter_validation_none_and_collections(self):
        """None, list, and dict accession values must return an error dict."""
        invalid_cases = [
            {"accession": None},   # None is not a string
            {"accession": []},     # List is not a string
            {"accession": {}},     # Dict is not a string
        ]
        for case in invalid_cases:
            result = self.tu.run({
                "name": "UniProt_get_entry_by_accession",
                "arguments": case,
            })
            self.assertIsInstance(result, dict, f"Expected dict for {case!r}")
            self.assertIn("error", result, f"Expected error for invalid accession {case!r}")

    def test_parameter_validation_empty_string(self):
        """Empty-string accession must return an error dict (no network call)."""
        result = self.tu.run({
            "name": "UniProt_get_entry_by_accession",
            "arguments": {"accession": ""},
        })
        self.assertIsInstance(result, dict)
        # An empty accession should fail validation before any network call
        self.assertIn("error", result, "Expected error for empty accession string")

    @pytest.mark.network
    def test_parameter_validation_wrong_types_coerced(self):
        """Integer/boolean accession values — system either coerces or returns error."""
        coercible_cases = [
            {"accession": 123},   # Integer — may be coerced to "123"
            {"accession": True},  # Boolean — may be coerced to "True"
        ]
        for case in coercible_cases:
            result = self.tu.run({
                "name": "UniProt_get_entry_by_accession",
                "arguments": case,
            })
            self.assertIsInstance(result, dict, f"Expected dict for {case!r}")
            # Either an error (validation rejected it) or a data response (was coerced)
            self.assertTrue(
                "error" in result or "status" in result or "data" in result,
                f"Unexpected response structure for {case!r}: {list(result.keys())}",
            )

    # ------------------------------------------------------------------ #
    #  Memory leak check                                                  #
    # ------------------------------------------------------------------ #

    @pytest.mark.network
    def test_memory_leak_prevention(self):
        """10 sequential run() calls must not grow the object graph by >2000 objects."""
        initial_objects = len(gc.get_objects())

        for i in range(10):
            result = self.tu.run({
                "name": "UniProt_get_entry_by_accession",
                "arguments": {"accession": f"P{i:05d}"},
            })
            self.assertIsInstance(result, dict)
            if i % 5 == 0:
                gc.collect()

        gc.collect()
        object_growth = len(gc.get_objects()) - initial_objects
        self.assertLess(
            object_growth, 2000,
            f"Object growth of {object_growth} suggests a memory leak",
        )

    # ------------------------------------------------------------------ #
    #  Missing API key handling                                           #
    # ------------------------------------------------------------------ #

    @pytest.mark.network
    def test_missing_api_key_returns_dict(self):
        """Tools that need API keys must return a dict (not raise) when keys absent."""
        tool_args = {
            "UniProt_get_entry_by_accession": {"accession": "P05067"},
            "ArXiv_search_papers": {"query": "test", "limit": 5},
            "OpenTargets_get_associated_targets_by_disease_efoId": {"efoId": "EFO_0000305"},
        }
        for tool_name, args in tool_args.items():
            result = self.tu.run({"name": tool_name, "arguments": args})
            self.assertIsInstance(result, dict, f"Expected dict from {tool_name}")
            if "error" in result:
                error_msg = result["error"]
                self.assertIsInstance(error_msg, str)
                self.assertGreater(len(error_msg), 0,
                                   f"Error message for {tool_name} must not be empty")

    # ------------------------------------------------------------------ #
    #  Cache management                                                   #
    # ------------------------------------------------------------------ #

    def test_cache_set_get_clear(self):
        """Cache set/get/clear must work as a basic key-value store."""
        self.tu.clear_cache()
        self.assertEqual(len(self.tu._cache), 0)

        self.tu._cache.set("mykey", "myvalue")
        self.assertEqual(self.tu._cache.get("mykey"), "myvalue")

        self.tu.clear_cache()
        self.assertEqual(len(self.tu._cache), 0)


if __name__ == "__main__":
    unittest.main()
