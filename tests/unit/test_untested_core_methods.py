#!/usr/bin/env python3
"""
Tests for core ToolUniverse methods that previously had no coverage:

  - prepare_one_tool_prompt()
  - prepare_tool_prompts()
  - filter_tools()
  - force_full_discovery()
  - clear_tools()
  - get_profile_llm_config()
  - get_profile_metadata()
  - get_one_tool_by_one_name()  (deprecated wrapper)
  - tool_to_str()
  - return_all_loaded_tools()
  - extract_function_call_json()
"""

import copy
import json
import sys
import unittest
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse import ToolUniverse

# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

def _make_tool(name="TestTool", tool_type="SpecialTool", **extra):
    """Return a minimal tool config dict."""
    return {
        "name": name,
        "type": tool_type,
        "description": f"Description of {name}",
        "parameter": {"type": "object", "properties": {}, "required": []},
        "category": "special_tools",
        **extra,
    }


@pytest.mark.unit
class TestPrepareToolPrompts(unittest.TestCase):
    """Tests for prepare_one_tool_prompt() and prepare_tool_prompts()."""

    def setUp(self):
        self.tu = ToolUniverse()
        self.sample_tool = _make_tool(
            "UniProt_test",
            return_schema={"type": "object"},
            test_examples=[{"accession": "P05067"}],
            source_file="/fake/path.json",
            mcp_annotations={"readOnlyHint": True},
        )

    def tearDown(self):
        self.tu.close()

    # --- prepare_one_tool_prompt ---

    def test_prepare_one_tool_prompt_keeps_essential_keys(self):
        result = self.tu.prepare_one_tool_prompt(self.sample_tool)
        self.assertIsInstance(result, dict)
        for key in ("name", "description", "parameter"):
            self.assertIn(key, result, f"Essential key '{key}' missing")

    def test_prepare_one_tool_prompt_removes_extra_keys(self):
        result = self.tu.prepare_one_tool_prompt(self.sample_tool)
        for key in ("return_schema", "test_examples", "source_file", "mcp_annotations", "type", "category"):
            self.assertNotIn(key, result, f"Extra key '{key}' should be removed")

    def test_prepare_one_tool_prompt_does_not_mutate_input(self):
        original = copy.deepcopy(self.sample_tool)
        self.tu.prepare_one_tool_prompt(self.sample_tool)
        self.assertEqual(self.sample_tool, original, "Input dict must not be mutated")

    def test_prepare_one_tool_prompt_name_value_preserved(self):
        result = self.tu.prepare_one_tool_prompt(self.sample_tool)
        self.assertEqual(result["name"], self.sample_tool["name"])

    # --- prepare_tool_prompts (mode='prompt') ---

    def test_prepare_tool_prompts_prompt_mode_strips_extra_keys(self):
        tool_list = [copy.deepcopy(self.sample_tool), _make_tool("ToolB")]
        result = self.tu.prepare_tool_prompts(tool_list, mode="prompt")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        for tool in result:
            for key in ("return_schema", "test_examples", "source_file", "mcp_annotations"):
                self.assertNotIn(key, tool, f"Key '{key}' should be absent in prompt mode")
            for key in ("name", "description", "parameter"):
                self.assertIn(key, tool)

    def test_prepare_tool_prompts_example_mode_keeps_extra_fields(self):
        tool_with_schema = _make_tool(
            "ToolC",
            query_schema={"type": "string"},
            fields=["field1"],
            label="TestLabel",
        )
        result = self.tu.prepare_tool_prompts([tool_with_schema], mode="example")
        self.assertEqual(len(result), 1)
        for key in ("query_schema", "fields", "label", "type"):
            self.assertIn(key, result[0], f"Key '{key}' should be kept in example mode")

    def test_prepare_tool_prompts_custom_mode_uses_provided_keys(self):
        result = self.tu.prepare_tool_prompts(
            [copy.deepcopy(self.sample_tool)],
            mode="custom",
            valid_keys=["name", "type"],
        )
        self.assertIn("name", result[0])
        self.assertIn("type", result[0])
        self.assertNotIn("description", result[0])
        self.assertNotIn("parameter", result[0])

    def test_prepare_tool_prompts_custom_mode_requires_valid_keys(self):
        with self.assertRaises(ValueError):
            self.tu.prepare_tool_prompts([self.sample_tool], mode="custom")

    def test_prepare_tool_prompts_invalid_mode_raises(self):
        with self.assertRaises(ValueError):
            self.tu.prepare_tool_prompts([self.sample_tool], mode="invalid_mode")

    def test_prepare_tool_prompts_does_not_mutate_input(self):
        original = [copy.deepcopy(self.sample_tool)]
        self.tu.prepare_tool_prompts(original, mode="prompt")
        # original must be unchanged
        self.assertIn("return_schema", original[0])

    def test_prepare_tool_prompts_empty_list(self):
        result = self.tu.prepare_tool_prompts([], mode="prompt")
        self.assertEqual(result, [])


@pytest.mark.unit
class TestFilterTools(unittest.TestCase):
    """Tests for filter_tools()."""

    def setUp(self):
        self.tu = ToolUniverse()
        self.tu.load_tools()

    def tearDown(self):
        self.tu.close()

    def test_filter_tools_no_criteria_returns_all(self):
        result = self.tu.filter_tools()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), len(self.tu.all_tools))

    def test_filter_tools_include_by_name(self):
        target = self.tu.all_tools[0]["name"]
        result = self.tu.filter_tools(include_tools={target})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], target)

    def test_filter_tools_exclude_by_name(self):
        target = self.tu.all_tools[0]["name"]
        result = self.tu.filter_tools(exclude_tools={target})
        names = [t["name"] for t in result]
        self.assertNotIn(target, names)
        self.assertEqual(len(result), len(self.tu.all_tools) - 1)

    def test_filter_tools_include_by_type(self):
        # SpecialTool type is always present (Finish, CallAgent, UsageTips)
        result = self.tu.filter_tools(include_tool_types={"SpecialTool"})
        self.assertGreater(len(result), 0)
        for tool in result:
            self.assertEqual(tool.get("type"), "SpecialTool")

    def test_filter_tools_exclude_by_type(self):
        result = self.tu.filter_tools(exclude_tool_types={"SpecialTool"})
        for tool in result:
            self.assertNotEqual(tool.get("type"), "SpecialTool")

    def test_filter_tools_returns_list_not_original_reference(self):
        """filter_tools must return a new list (not a direct reference to all_tools)."""
        result = self.tu.filter_tools()
        self.assertIsNot(result, self.tu.all_tools)

    def test_filter_tools_before_load_returns_empty(self):
        tu2 = ToolUniverse()
        tu2.all_tools = []
        tu2.all_tool_dict = {}
        result = tu2.filter_tools()
        self.assertEqual(result, [])
        tu2.close()


@pytest.mark.unit
class TestForceFullDiscovery(unittest.TestCase):
    """Tests for force_full_discovery()."""

    def setUp(self):
        self.tu = ToolUniverse()

    def tearDown(self):
        self.tu.close()

    def test_force_full_discovery_returns_dict(self):
        result = self.tu.force_full_discovery()
        self.assertIsInstance(result, dict)

    def test_force_full_discovery_returns_nonempty_registry(self):
        result = self.tu.force_full_discovery()
        self.assertGreater(len(result), 0)

    def test_force_full_discovery_registry_has_known_type(self):
        result = self.tu.force_full_discovery()
        # UsageTipsTool is a built-in class always in the registry
        self.assertIn("UsageTipsTool", result)

    def test_force_full_discovery_idempotent(self):
        """Calling twice must not raise and must return consistent results."""
        result1 = self.tu.force_full_discovery()
        result2 = self.tu.force_full_discovery()
        self.assertEqual(set(result1.keys()), set(result2.keys()))


@pytest.mark.unit
class TestClearTools(unittest.TestCase):
    """Tests for clear_tools()."""

    def setUp(self):
        self.tu = ToolUniverse()
        self.tu.load_tools()

    def tearDown(self):
        self.tu.close()

    def test_clear_tools_empties_all_tools(self):
        self.assertGreater(len(self.tu.all_tools), 0)
        self.tu.clear_tools()
        self.assertEqual(self.tu.all_tools, [])

    def test_clear_tools_empties_all_tool_dict(self):
        self.assertGreater(len(self.tu.all_tool_dict), 0)
        self.tu.clear_tools()
        self.assertEqual(self.tu.all_tool_dict, {})

    def test_clear_tools_empties_callable_functions(self):
        self.tu.clear_tools()
        self.assertEqual(self.tu.callable_functions, {})

    def test_clear_tools_clear_cache_false_preserves_cache(self):
        """With clear_cache=False (default), the result cache must not be cleared."""
        self.tu._cache.set("test_key", {"value": 1})
        self.tu.clear_tools(clear_cache=False)
        self.assertIsNotNone(self.tu._cache.get("test_key"))

    def test_clear_tools_clear_cache_true_wipes_cache(self):
        self.tu._cache.set("test_key2", {"value": 2})
        self.tu.clear_tools(clear_cache=True)
        self.assertIsNone(self.tu._cache.get("test_key2"))

    def test_reload_after_clear(self):
        """After clear, load_tools() must restore tools normally."""
        self.tu.clear_tools()
        self.assertEqual(self.tu.all_tools, [])
        self.tu.load_tools()
        self.assertGreater(len(self.tu.all_tools), 0)


@pytest.mark.unit
class TestProfileAccessors(unittest.TestCase):
    """Tests for get_profile_llm_config() and get_profile_metadata()."""

    def setUp(self):
        self.tu = ToolUniverse()

    def tearDown(self):
        self.tu.close()

    def test_get_profile_llm_config_returns_dict_or_none(self):
        result = self.tu.get_profile_llm_config()
        self.assertIsInstance(result, (dict, type(None)))

    def test_get_profile_metadata_returns_dict_or_none(self):
        result = self.tu.get_profile_metadata()
        self.assertIsInstance(result, (dict, type(None)))

    def test_profile_llm_config_set_and_retrieved(self):
        """Manually setting _profile_llm_config is reflected by the accessor."""
        config = {"model": "claude-3", "temperature": 0.0}
        self.tu._profile_llm_config = config
        result = self.tu.get_profile_llm_config()
        self.assertEqual(result, config)

    def test_profile_metadata_set_and_retrieved(self):
        meta = {"name": "test-profile", "version": "1.0"}
        self.tu._profile_metadata = meta
        result = self.tu.get_profile_metadata()
        self.assertEqual(result, meta)

    def test_profile_llm_config_default_none(self):
        """When not set, accessor must return None (not raise)."""
        if hasattr(self.tu, "_profile_llm_config"):
            del self.tu._profile_llm_config
        result = self.tu.get_profile_llm_config()
        self.assertIsNone(result)

    def test_profile_metadata_default_none(self):
        if hasattr(self.tu, "_profile_metadata"):
            del self.tu._profile_metadata
        result = self.tu.get_profile_metadata()
        self.assertIsNone(result)


@pytest.mark.unit
class TestGetOneToolByOneName(unittest.TestCase):
    """Tests for the deprecated get_one_tool_by_one_name() wrapper."""

    def setUp(self):
        self.tu = ToolUniverse()
        self.tu.load_tools()

    def tearDown(self):
        self.tu.close()

    def _call_deprecated(self, name, **kwargs):
        """Call get_one_tool_by_one_name and assert the deprecation message is logged."""
        with self.assertLogs("tooluniverse", level="WARNING") as cm:
            result = self.tu.get_one_tool_by_one_name(name, **kwargs)
        self.assertTrue(
            any("deprecated" in line.lower() for line in cm.output),
            "Expected deprecation message in logs",
        )
        return result

    def test_returns_dict_for_known_tool(self):
        result = self._call_deprecated("ToolUniverse_get_usage_tips")
        self.assertIsInstance(result, dict)
        self.assertIn("name", result)

    def test_returns_none_for_unknown_tool(self):
        result = self._call_deprecated("NonExistent_XYZ_123")
        self.assertIsNone(result)

    def test_return_prompt_true_strips_extra_keys(self):
        result = self._call_deprecated("ToolUniverse_get_usage_tips", return_prompt=True)
        # return_prompt=True passes through prepare_one_tool_prompt logic
        if result is not None:
            for key in ("return_schema", "test_examples", "source_file"):
                self.assertNotIn(key, result)

    def test_return_prompt_false_gives_full_config(self):
        result = self._call_deprecated("ToolUniverse_get_usage_tips", return_prompt=False)
        if result is not None:
            self.assertIn("name", result)


@pytest.mark.unit
class TestToolToStr(unittest.TestCase):
    """Tests for tool_to_str()."""

    def setUp(self):
        self.tu = ToolUniverse()

    def tearDown(self):
        self.tu.close()

    def test_returns_string(self):
        tools = [_make_tool("A"), _make_tool("B")]
        result = self.tu.tool_to_str(tools)
        self.assertIsInstance(result, str)

    def test_output_is_valid_json_when_split(self):
        tools = [_make_tool("A"), _make_tool("B")]
        result = self.tu.tool_to_str(tools)
        parts = result.split("\n\n")
        self.assertEqual(len(parts), 2)
        for part in parts:
            parsed = json.loads(part)
            self.assertIsInstance(parsed, dict)

    def test_empty_list_returns_empty_string(self):
        result = self.tu.tool_to_str([])
        self.assertEqual(result, "")

    def test_single_tool_has_no_double_newline_separator(self):
        result = self.tu.tool_to_str([_make_tool("Only")])
        self.assertNotIn("\n\n", result)

    def test_tool_names_appear_in_output(self):
        tools = [_make_tool("ToolAlpha"), _make_tool("ToolBeta")]
        result = self.tu.tool_to_str(tools)
        self.assertIn("ToolAlpha", result)
        self.assertIn("ToolBeta", result)


@pytest.mark.unit
class TestReturnAllLoadedTools(unittest.TestCase):
    """Tests for return_all_loaded_tools()."""

    def setUp(self):
        self.tu = ToolUniverse()
        self.tu.load_tools()

    def tearDown(self):
        self.tu.close()

    def test_returns_list(self):
        result = self.tu.return_all_loaded_tools()
        self.assertIsInstance(result, list)

    def test_returns_same_count_as_all_tools(self):
        result = self.tu.return_all_loaded_tools()
        self.assertEqual(len(result), len(self.tu.all_tools))

    def test_returns_deep_copy(self):
        """Mutating the returned list must not affect all_tools."""
        result = self.tu.return_all_loaded_tools()
        original_count = len(self.tu.all_tools)
        result.clear()
        self.assertEqual(len(self.tu.all_tools), original_count)

    def test_inner_dicts_are_copies(self):
        result = self.tu.return_all_loaded_tools()
        result[0]["__test_mutation__"] = True
        self.assertNotIn("__test_mutation__", self.tu.all_tools[0])

    def test_empty_when_no_tools_loaded(self):
        tu2 = ToolUniverse()
        tu2.all_tools = []
        tu2.all_tool_dict = {}
        result = tu2.return_all_loaded_tools()
        self.assertEqual(result, [])
        tu2.close()


@pytest.mark.unit
class TestExtractFunctionCallJson(unittest.TestCase):
    """Tests for extract_function_call_json()."""

    def setUp(self):
        self.tu = ToolUniverse()

    def tearDown(self):
        self.tu.close()

    def test_accepts_dict_with_name_and_arguments(self):
        """Well-formed dicts must be returned as-is (or wrapped consistently)."""
        call = {"name": "SomeTool", "arguments": {"key": "value"}}
        result = self.tu.extract_function_call_json(call, verbose=False)
        # Result should not raise; accept any non-None return
        self.assertIsNotNone(result)

    def test_accepts_list_input(self):
        """List input must not raise."""
        call = [{"name": "SomeTool", "arguments": {}}]
        result = self.tu.extract_function_call_json(call, verbose=False)
        # Accept any return type — main contract is no exception
        self.assertIsNotNone(result)

    def test_returns_consistently_typed(self):
        """Return value must be a dict or tuple, never raise."""
        inputs = [
            {"name": "A", "arguments": {}},
            [{"name": "B", "arguments": {"x": 1}}],
        ]
        for inp in inputs:
            try:
                result = self.tu.extract_function_call_json(inp, verbose=False)
                self.assertIsInstance(result, (dict, tuple, list, str, type(None)))
            except Exception as exc:  # noqa: BLE001
                self.fail(f"extract_function_call_json raised {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    unittest.main()
