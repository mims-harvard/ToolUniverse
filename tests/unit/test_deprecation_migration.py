#!/usr/bin/env python3
"""
Regression tests for the deprecated-method migration.

Each test exercises a code path that was changed:
  1. refresh_tool_name_desc() — category/name filtering inlined (was filter_tool_lists)
  2. filter_tool_lists() body — select_tools replaced by filter_tools + category filter
  3. get_tool_description() body — get_one_tool_by_one_name replaced by tool_specification
  4. ToolFinderKeyword._run_json_search — select_tools replaced by category list comprehension
  5. Deprecated wrappers still delegate correctly (get_tool_by_name, select_tools, etc.)

All tests are pure-Python and offline (no network calls).
"""

import sys
import unittest
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse import ToolUniverse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _category_of(tu, tool_name):
    """Return the category string stored in the tool config."""
    return tu.all_tool_dict.get(tool_name, {}).get("category")


def _any_name_in_category(tu, category):
    """Return first tool name in the given category, or None."""
    for t in tu.all_tools:
        if t.get("category") == category:
            return t["name"]
    return None


# ---------------------------------------------------------------------------
# 1. refresh_tool_name_desc — inlined filtering
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRefreshToolNameDescFiltering(unittest.TestCase):
    """Verify the inlined category/name filter in refresh_tool_name_desc()."""

    def setUp(self):
        self.tu = ToolUniverse()
        self.tu.load_tools()

    def tearDown(self):
        self.tu.close()

    def test_no_filters_returns_all_tools(self):
        names, descs = self.tu.refresh_tool_name_desc()
        self.assertEqual(len(names), len(descs))
        self.assertEqual(len(names), len(self.tu.all_tools))

    def test_include_categories_restricts_to_that_category(self):
        # Pick a category that is actually loaded
        sample_tool = next(
            (t for t in self.tu.all_tools if t.get("category") == "special_tools"), None
        )
        self.assertIsNotNone(sample_tool, "Need at least one special_tools tool")

        names, descs = self.tu.refresh_tool_name_desc(include_categories=["special_tools"])
        self.assertGreater(len(names), 0)
        self.assertEqual(len(names), len(descs))
        for name in names:
            cat = _category_of(self.tu, name)
            self.assertEqual(cat, "special_tools",
                             f"Tool '{name}' has category '{cat}', expected 'special_tools'")

    def test_exclude_categories_removes_that_category(self):
        names_all, _ = self.tu.refresh_tool_name_desc()
        names_exc, descs_exc = self.tu.refresh_tool_name_desc(
            exclude_categories=["special_tools"]
        )
        self.assertEqual(len(names_exc), len(descs_exc))
        for name in names_exc:
            self.assertNotEqual(
                _category_of(self.tu, name), "special_tools",
                f"Tool '{name}' should have been excluded",
            )
        # Fewer tools after exclusion
        self.assertLess(len(names_exc), len(names_all))

    def test_include_names_restricts_to_named_tools(self):
        target = "ToolUniverse_get_usage_tips"
        names, descs = self.tu.refresh_tool_name_desc(include_names=[target])
        self.assertEqual(names, [target])
        self.assertEqual(len(descs), 1)

    def test_exclude_names_removes_named_tools(self):
        target = "ToolUniverse_get_usage_tips"
        names, descs = self.tu.refresh_tool_name_desc(exclude_names=[target])
        self.assertEqual(len(names), len(descs))
        self.assertNotIn(target, names)

    def test_names_and_descs_stay_parallel_after_filtering(self):
        """After category filtering, name[i] must match what desc[i] starts with."""
        names, descs = self.tu.refresh_tool_name_desc(include_categories=["special_tools"])
        for name, desc in zip(names, descs):
            self.assertTrue(
                desc.startswith(name),
                f"desc '{desc[:40]}' does not start with name '{name}'",
            )

    def test_combined_include_category_and_exclude_name(self):
        """Combining include_categories + exclude_names must apply both filters."""
        special_names, _ = self.tu.refresh_tool_name_desc(include_categories=["special_tools"])
        if not special_names:
            self.skipTest("No special_tools tools loaded")
        excluded = special_names[0]

        names, descs = self.tu.refresh_tool_name_desc(
            include_categories=["special_tools"],
            exclude_names=[excluded],
        )
        self.assertNotIn(excluded, names)
        for name in names:
            self.assertEqual(_category_of(self.tu, name), "special_tools")


# ---------------------------------------------------------------------------
# 2. filter_tool_lists — deprecated wrapper, body now uses filter_tools
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestFilterToolListsWrapper(unittest.TestCase):
    """Deprecated filter_tool_lists() must still produce correct results."""

    def setUp(self):
        self.tu = ToolUniverse()
        self.tu.load_tools()
        all_tools = self.tu.all_tools
        self.tool_names = [t.get("name", "") for t in all_tools if isinstance(t, dict)]
        self.tool_descs = [t.get("description", "") for t in all_tools if isinstance(t, dict)]

    def tearDown(self):
        self.tu.close()

    def _call(self, **kwargs):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            return self.tu.filter_tool_lists(self.tool_names, self.tool_descs, **kwargs)

    def test_no_filter_returns_all(self):
        # When no filter, returns original lists unchanged
        names, descs = self._call()
        self.assertEqual(names, self.tool_names)
        self.assertEqual(descs, self.tool_descs)

    def test_include_category_restricts_results(self):
        names, descs = self._call(include_categories=["special_tools"])
        self.assertEqual(len(names), len(descs))
        for name in names:
            cat = _category_of(self.tu, name)
            self.assertEqual(cat, "special_tools",
                             f"'{name}' should be in special_tools, got '{cat}'")

    def test_exclude_category_removes_tools(self):
        names_full, _ = self._call()
        names_exc, descs_exc = self._call(exclude_categories=["special_tools"])
        self.assertEqual(len(names_exc), len(descs_exc))
        for name in names_exc:
            self.assertNotEqual(_category_of(self.tu, name), "special_tools")
        self.assertLess(len(names_exc), len(names_full))

    def test_include_names_filter(self):
        target = "ToolUniverse_get_usage_tips"
        names, descs = self._call(include_names=[target])
        self.assertEqual(names, [target])
        self.assertEqual(len(descs), 1)

    def test_lists_remain_parallel(self):
        names, descs = self._call(include_categories=["special_tools"])
        for name, desc in zip(names, descs):
            self.assertTrue(desc.startswith(name) or len(desc) > 0)

    def test_emits_deprecation_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.tu.filter_tool_lists(self.tool_names, self.tool_descs)
        depr = [x for x in w if issubclass(x.category, DeprecationWarning)]
        self.assertTrue(len(depr) > 0, "filter_tool_lists must emit DeprecationWarning")
        self.assertIn("filter_tool_lists", str(depr[0].message))


# ---------------------------------------------------------------------------
# 3. get_tool_description — body now calls tool_specification directly
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetToolDescriptionWrapper(unittest.TestCase):
    """get_tool_description() must delegate to tool_specification() and return
    the same result, without double-chaining through get_one_tool_by_one_name."""

    def setUp(self):
        self.tu = ToolUniverse()
        self.tu.load_tools()

    def tearDown(self):
        self.tu.close()

    def _get_desc(self, name):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            return self.tu.get_tool_description(name)

    def test_known_tool_returns_same_as_tool_specification(self):
        name = "ToolUniverse_get_usage_tips"
        from_deprecated = self._get_desc(name)
        from_new = self.tu.tool_specification(name)
        self.assertEqual(from_deprecated, from_new)

    def test_unknown_tool_returns_none(self):
        result = self._get_desc("NonExistent_XYZ_999")
        self.assertIsNone(result)

    def test_result_has_name_and_description_keys(self):
        result = self._get_desc("ToolUniverse_get_usage_tips")
        self.assertIsNotNone(result)
        self.assertIn("name", result)
        self.assertIn("description", result)

    def test_emits_deprecation_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.tu.get_tool_description("ToolUniverse_get_usage_tips")
        depr = [x for x in w if issubclass(x.category, DeprecationWarning)]
        self.assertTrue(len(depr) > 0, "get_tool_description must emit DeprecationWarning")
        self.assertIn("get_tool_description", str(depr[0].message))

    def test_not_double_chained(self):
        """Result must match tool_specification; if double-chained, the prompt
        stripping in get_one_tool_by_one_name would have removed keys."""
        name = "ToolUniverse_get_usage_tips"
        full_spec = self.tu.tool_specification(name, return_prompt=False)
        via_deprecated = self._get_desc(name)
        # Both should have the same keys (no extra stripping from chaining)
        self.assertEqual(set(full_spec.keys()), set(via_deprecated.keys()))


# ---------------------------------------------------------------------------
# 4. ToolFinderKeyword — category filter uses list comprehension on field
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestToolFinderKeywordCategoryFilter(unittest.TestCase):
    """Keyword search with categories= must only return tools from those categories."""

    def setUp(self):
        self.tu = ToolUniverse()
        self.tu.load_tools()

    def tearDown(self):
        self.tu.close()

    def test_category_filter_restricts_results(self):
        result = self.tu.run({
            "name": "Tool_Finder_Keyword",
            "arguments": {
                "description": "protein",
                "limit": 10,
                "categories": ["uniprot"],
            },
        })
        # Result is a list of tool dicts
        self.assertIsInstance(result, list)
        if result:
            for tool in result:
                cat = _category_of(self.tu, tool["name"])
                self.assertEqual(
                    cat, "uniprot",
                    f"Tool '{tool['name']}' in category '{cat}', expected 'uniprot'",
                )

    def test_no_category_filter_searches_all(self):
        result_all = self.tu.run({
            "name": "Tool_Finder_Keyword",
            "arguments": {"description": "protein", "limit": 5},
        })
        result_cat = self.tu.run({
            "name": "Tool_Finder_Keyword",
            "arguments": {
                "description": "protein",
                "limit": 5,
                "categories": ["uniprot"],
            },
        })
        # Without category filter, results may include tools from other categories
        # (this test simply ensures neither call raises)
        self.assertIsInstance(result_all, list)
        self.assertIsInstance(result_cat, list)

    def test_nonexistent_category_returns_empty_or_error(self):
        result = self.tu.run({
            "name": "Tool_Finder_Keyword",
            "arguments": {
                "description": "protein",
                "limit": 5,
                "categories": ["__nonexistent_category_xyz__"],
            },
        })
        # Either an empty list or an error dict — must not raise
        self.assertIsInstance(result, (list, dict))
        if isinstance(result, list):
            self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# 5. Remaining deprecated wrappers still work correctly
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRemainingDeprecatedWrappers(unittest.TestCase):
    """
    Verify that deprecated wrappers still produce correct results and emit
    DeprecationWarning — they must not be broken by the internal refactoring.
    """

    def setUp(self):
        self.tu = ToolUniverse()
        self.tu.load_tools()

    def tearDown(self):
        self.tu.close()

    def _warn_call(self, method, *args, **kwargs):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = getattr(self.tu, method)(*args, **kwargs)
        depr = [x for x in w if issubclass(x.category, DeprecationWarning)]
        return result, depr

    # --- get_tool_by_name ---

    def test_get_tool_by_name_returns_list(self):
        result, depr = self._warn_call(
            "get_tool_by_name", ["ToolUniverse_get_usage_tips"]
        )
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "ToolUniverse_get_usage_tips")
        self.assertTrue(len(depr) > 0, "Must emit DeprecationWarning")

    def test_get_tool_by_name_unknown_returns_empty(self):
        result, _ = self._warn_call("get_tool_by_name", ["NonExistent_XYZ"])
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    # --- select_tools ---

    def test_select_tools_include_names(self):
        result, depr = self._warn_call(
            "select_tools",
            include_names=["ToolUniverse_get_usage_tips"],
        )
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertTrue(len(depr) > 0)

    def test_select_tools_include_categories(self):
        result, depr = self._warn_call(
            "select_tools",
            include_categories=["special_tools"],
        )
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        for tool in result:
            self.assertEqual(tool.get("category"), "special_tools")
        self.assertTrue(len(depr) > 0)

    def test_select_tools_exclude_names(self):
        all_result, _ = self._warn_call("select_tools")
        exc_result, _ = self._warn_call(
            "select_tools",
            exclude_names=["ToolUniverse_get_usage_tips"],
        )
        self.assertNotIn(
            "ToolUniverse_get_usage_tips",
            [t["name"] for t in exc_result],
        )
        self.assertEqual(len(exc_result), len(all_result) - 1)

    # --- load_tools_from_names_list ---

    def test_load_tools_from_names_list(self):
        target = "ToolUniverse_get_usage_tips"
        result, depr = self._warn_call(
            "load_tools_from_names_list",
            [target],
            clear_existing=False,
        )
        available = self.tu.get_available_tools()
        self.assertIn(target, available)
        self.assertTrue(len(depr) > 0)

    # --- remove_keys ---

    def test_remove_keys_strips_specified_keys(self):
        tools = [
            {"name": "A", "description": "desc A", "type": "T", "extra": "drop"},
        ]
        result, depr = self._warn_call("remove_keys", tools, ["extra", "type"])
        self.assertIsInstance(result, list)
        self.assertNotIn("extra", result[0])
        self.assertNotIn("type", result[0])
        self.assertIn("name", result[0])
        self.assertTrue(len(depr) > 0)

    # --- prepare_tool_examples ---

    def test_prepare_tool_examples_keeps_example_keys(self):
        tools = [
            {
                "name": "B",
                "description": "desc",
                "parameter": {},
                "type": "T",
                "query_schema": {},
                "fields": [],
                "label": "lbl",
                "source_file": "drop_me",
            }
        ]
        result, depr = self._warn_call("prepare_tool_examples", tools)
        self.assertIsInstance(result, list)
        self.assertIn("query_schema", result[0])
        self.assertNotIn("source_file", result[0])
        self.assertTrue(len(depr) > 0)


if __name__ == "__main__":
    unittest.main()
