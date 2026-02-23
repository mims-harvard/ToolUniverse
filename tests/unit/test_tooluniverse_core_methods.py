#!/usr/bin/env python3
"""
ToolUniverse 核心方法测试补充

为缺失的核心方法添加测试覆盖，确保功能稳定性。
"""

import sys
import unittest
from pathlib import Path
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tooluniverse import ToolUniverse
from tooluniverse.exceptions import ToolError, ToolValidationError


@pytest.mark.unit
class TestToolUniverseCoreMethods(unittest.TestCase):
    """Test core ToolUniverse methods that are currently missing test coverage."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tu = ToolUniverse()
        # Load a minimal set of tools for testing
        self.tu.load_tools()
    
    def test_get_tool_by_name(self):
        """Test get_tool_by_name method."""
        # Test getting existing tools
        tool_info = self.tu.get_tool_by_name(["UniProt_get_entry_by_accession"])
        self.assertIsInstance(tool_info, list)
        self.assertGreater(len(tool_info), 0)
        self.assertIn("name", tool_info[0])
        self.assertEqual(tool_info[0]["name"], "UniProt_get_entry_by_accession")
        
        # Test getting multiple tools
        tool_info_multi = self.tu.get_tool_by_name(["UniProt_get_entry_by_accession", "ArXiv_search_papers"])
        self.assertIsInstance(tool_info_multi, list)
        self.assertGreaterEqual(len(tool_info_multi), 1)
        
        # Test getting non-existent tools
        tool_info_empty = self.tu.get_tool_by_name(["NonExistentTool"])
        self.assertIsInstance(tool_info_empty, list)
        self.assertEqual(len(tool_info_empty), 0)
    
    def test_get_tool_description(self):
        """Test get_tool_description method."""
        # Test getting description for existing tool
        description = self.tu.get_tool_description("UniProt_get_entry_by_accession")
        self.assertIsInstance(description, dict)
        self.assertIn("description", description)
        self.assertIsInstance(description["description"], str)
        self.assertGreater(len(description["description"]), 0)
        
        # Test getting description for non-existent tool
        description_none = self.tu.get_tool_description("NonExistentTool")
        self.assertIsNone(description_none)
    
    def test_get_tool_type_by_name(self):
        """Test get_tool_type_by_name method."""
        # Test getting type for existing tool
        tool_type = self.tu.get_tool_type_by_name("UniProt_get_entry_by_accession")
        self.assertIsInstance(tool_type, str)
        self.assertGreater(len(tool_type), 0)
        
        # Test getting type for non-existent tool
        with self.assertRaises(Exception):
            self.tu.get_tool_type_by_name("NonExistentTool")
    
    def test_tool_specification(self):
        """Test tool_specification method."""
        # Test getting specification for existing tool
        spec = self.tu.tool_specification("UniProt_get_entry_by_accession")
        self.assertIsInstance(spec, dict)
        self.assertIn("name", spec)
        
        # Test with return_prompt=True
        spec_with_prompt = self.tu.tool_specification("UniProt_get_entry_by_accession", return_prompt=True)
        self.assertIsInstance(spec_with_prompt, dict)
        self.assertIn("name", spec_with_prompt)
        self.assertIn("description", spec_with_prompt)

    def test_tool_specification_openai_format(self):
        """Test tool_specification with format='openai' produces valid OpenAI schemas.

        Regression test for the bug where legacy required:True/False boolean flags
        embedded on individual property schemas (old JSON format) were not cleaned up
        recursively, causing OpenAI to reject the schema with:
          "True is not of type 'array'"
        """
        # Every tool should return a dict with name/description/parameters keys
        spec = self.tu.tool_specification("UniProt_get_entry_by_accession", format="openai")
        self.assertIsInstance(spec, dict)
        self.assertIn("name", spec)
        self.assertIn("description", spec)
        self.assertIn("parameters", spec)

        params = spec["parameters"]
        self.assertIsInstance(params, dict)
        # top-level 'required' must be a list (not a boolean)
        if "required" in params:
            self.assertIsInstance(params["required"], list)

    def _find_openai_violations(self, obj, path=""):
        """Recursively find required:bool or additionalProperties:True in a schema."""
        issues = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "required" and isinstance(v, bool):
                    issues.append(f"required={v} at {path}.{k}")
                if k == "additionalProperties" and v is True:
                    issues.append(f"additionalProperties=True at {path}.{k}")
                issues.extend(self._find_openai_violations(v, f"{path}.{k}"))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                issues.extend(self._find_openai_violations(v, f"{path}[{i}]"))
        return issues

    def test_sanitize_schema_for_openai_legacy_required(self):
        """_sanitize_schema_for_openai converts legacy required:bool flags to required arrays."""
        legacy_schema = {
            "type": "object",
            "properties": {
                "chemblId": {"type": "string", "description": "ID", "required": True},
                "page": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer", "required": True},
                        "size": {"type": "integer", "required": True},
                    },
                    "required": False,
                },
            },
        }
        result = self.tu._sanitize_schema_for_openai(legacy_schema)

        # No boolean required flags anywhere
        violations = self._find_openai_violations(result)
        self.assertEqual(violations, [], f"Violations found: {violations}")

        # Top-level required array is correctly reconstructed
        self.assertEqual(result.get("required"), ["chemblId"])

        # chemblId has no property-level required
        self.assertNotIn("required", result["properties"]["chemblId"])

        # page (optional) is not in the top-level required array
        self.assertNotIn("page", result.get("required", []))

        # nested index and size are required within page
        page_required = result["properties"]["page"].get("required", [])
        self.assertIn("index", page_required)
        self.assertIn("size", page_required)

    def test_sanitize_schema_for_openai_additional_properties(self):
        """_sanitize_schema_for_openai removes additionalProperties:True recursively."""
        schema = {
            "type": "object",
            "properties": {
                "arguments": {
                    "oneOf": [
                        {"type": "object", "additionalProperties": True},
                        {"type": "string"},
                    ]
                }
            },
        }
        result = self.tu._sanitize_schema_for_openai(schema)
        violations = self._find_openai_violations(result)
        self.assertEqual(violations, [], f"Violations found: {violations}")
        # additionalProperties:True removed from the oneOf branch
        self.assertNotIn("additionalProperties", result["properties"]["arguments"]["oneOf"][0])

    def test_sanitize_schema_for_openai_items(self):
        """_sanitize_schema_for_openai handles required:True inside array items schemas."""
        schema = {"type": "array", "items": {"type": "string", "required": True}}
        result = self.tu._sanitize_schema_for_openai(schema)
        violations = self._find_openai_violations(result)
        self.assertEqual(violations, [], f"Violations found: {violations}")
        self.assertNotIn("required", result["items"])

    def test_sanitize_schema_for_openai_new_format_unchanged(self):
        """_sanitize_schema_for_openai leaves already-correct schemas unchanged."""
        new_format = {
            "type": "object",
            "properties": {
                "accession": {"type": "string", "description": "UniProt ID"},
            },
            "required": ["accession"],
        }
        result = self.tu._sanitize_schema_for_openai(new_format)
        self.assertEqual(result["required"], ["accession"])
        self.assertNotIn("required", result["properties"]["accession"])

    def test_tool_specification_openai_no_required_bool_any_tool(self):
        """All loaded tools produce OpenAI-compatible schemas with no required:bool."""
        tool_names = list(self.tu.all_tool_dict.keys())
        violations_found = []
        for name in tool_names:
            spec = self.tu.tool_specification(name, format="openai")
            if spec and "parameters" in spec:
                issues = self._find_openai_violations(spec["parameters"], name)
                violations_found.extend(issues)
        self.assertEqual(
            violations_found,
            [],
            f"OpenAI schema violations found in {len(violations_found)} tools: "
            f"{violations_found[:5]}",
        )
    
    def test_list_built_in_tools(self):
        """Test list_built_in_tools method."""
        # Test default mode (config) - returns dictionary
        tools_dict = self.tu.list_built_in_tools()
        self.assertIsInstance(tools_dict, dict)
        self.assertIn("categories", tools_dict)
        self.assertIn("total_tools", tools_dict)
        self.assertGreater(tools_dict["total_tools"], 0)
        
        # Test name_only mode - returns list
        tools_list = self.tu.list_built_in_tools(mode="list_name")
        self.assertIsInstance(tools_list, list)
        self.assertGreater(len(tools_list), 0)
        self.assertIsInstance(tools_list[0], str)
        
        # Test with scan_all=True
        tools_all = self.tu.list_built_in_tools(scan_all=True)
        self.assertIsInstance(tools_all, dict)
        self.assertIn("categories", tools_all)
    
    def test_get_available_tools(self):
        """Test get_available_tools method."""
        # Test default parameters
        tools = self.tu.get_available_tools()
        self.assertIsInstance(tools, list)
        self.assertGreater(len(tools), 0)
        
        # Test with name_only=False
        tools_detailed = self.tu.get_available_tools(name_only=False)
        self.assertIsInstance(tools_detailed, list)
        if tools_detailed:
            self.assertIsInstance(tools_detailed[0], dict)
        
        # Test with category filter
        tools_filtered = self.tu.get_available_tools(category_filter="literature")
        self.assertIsInstance(tools_filtered, list)
    
    def test_select_tools(self):
        """Test select_tools method."""
        # Test selecting tools by names
        tool_names = ["UniProt_get_entry_by_accession", "ArXiv_search_papers"]
        selected = self.tu.select_tools(tool_names)
        self.assertIsInstance(selected, list)
        self.assertLessEqual(len(selected), len(tool_names))
        
        # Test with empty list
        empty_selected = self.tu.select_tools([])
        self.assertIsInstance(empty_selected, list)
        self.assertEqual(len(empty_selected), 0)
    
    def test_filter_tool_lists(self):
        """Test filter_tool_lists method."""
        # Test filtering by category
        all_tools = self.tu.get_available_tools(name_only=False)
        if all_tools:
            # Get tool names and descriptions
            tool_names = [tool.get('name', '') for tool in all_tools if isinstance(tool, dict)]
            tool_descriptions = [tool.get('description', '') for tool in all_tools if isinstance(tool, dict)]
            
            filtered_names, filtered_descriptions = self.tu.filter_tool_lists(
                tool_names, tool_descriptions, include_categories=["literature"]
            )
            self.assertIsInstance(filtered_names, list)
            self.assertIsInstance(filtered_descriptions, list)
            self.assertEqual(len(filtered_names), len(filtered_descriptions))
    
    def test_find_tools_by_pattern(self):
        """Test find_tools_by_pattern method."""
        # Test searching by name pattern
        results = self.tu.find_tools_by_pattern("UniProt", search_in="name")
        self.assertIsInstance(results, list)
        
        # Test searching by description pattern
        results_desc = self.tu.find_tools_by_pattern("protein", search_in="description")
        self.assertIsInstance(results_desc, list)
        
        # Test case insensitive search
        results_case = self.tu.find_tools_by_pattern("uniprot", case_sensitive=False)
        self.assertIsInstance(results_case, list)
    
    def test_clear_cache(self):
        """Test clear_cache method."""
        # Test that clear_cache works without errors
        self.tu.clear_cache()
        
        # Verify cache is empty
        self.assertEqual(len(self.tu._cache), 0)
    
    def test_get_lazy_loading_status(self):
        """Test get_lazy_loading_status method."""
        status = self.tu.get_lazy_loading_status()
        self.assertIsInstance(status, dict)
        self.assertIn('lazy_loading_enabled', status)
        self.assertIn('full_discovery_completed', status)
        self.assertIn('immediately_available_tools', status)
        self.assertIn('lazy_mappings_available', status)
        self.assertIn('loaded_tools_count', status)
    
    def test_get_tool_types(self):
        """Test get_tool_types method."""
        tool_types = self.tu.get_tool_types()
        self.assertIsInstance(tool_types, list)
        self.assertGreater(len(tool_types), 0)
        # Check that it contains expected tool types
        self.assertTrue(any("uniprot" in tool_type.lower() for tool_type in tool_types))
    
    def test_call_id_gen(self):
        """Test call_id_gen method."""
        # Test generating multiple IDs
        id1 = self.tu.call_id_gen()
        id2 = self.tu.call_id_gen()
        
        self.assertIsInstance(id1, str)
        self.assertIsInstance(id2, str)
        self.assertNotEqual(id1, id2)
        self.assertGreater(len(id1), 0)
    
    def test_toggle_hooks(self):
        """Test toggle_hooks method."""
        # Test enabling hooks
        self.tu.toggle_hooks(True)
        
        # Test disabling hooks
        self.tu.toggle_hooks(False)
    
    def test_export_tool_names(self):
        """Test export_tool_names method."""
        import tempfile
        import os
        
        # Test exporting to file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_file = f.name
        
        try:
            self.tu.export_tool_names(temp_file)
            
            # Verify file was created and has content
            self.assertTrue(os.path.exists(temp_file))
            with open(temp_file, 'r') as f:
                content = f.read()
                self.assertGreater(len(content), 0)
                
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_generate_env_template(self):
        """Test generate_env_template method."""
        import tempfile
        import os
        
        # Test with empty list
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as f:
            temp_file = f.name
        
        try:
            self.tu.generate_env_template([], output_file=temp_file)
            
            # Verify file was created and has content
            self.assertTrue(os.path.exists(temp_file))
            with open(temp_file, 'r') as f:
                content = f.read()
                self.assertGreater(len(content), 0)
                self.assertIn("API Keys for ToolUniverse", content)
                
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        
        # Test with some missing keys
        missing_keys = ["API_KEY_1", "API_KEY_2"]
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as f:
            temp_file = f.name
        
        try:
            self.tu.generate_env_template(missing_keys, output_file=temp_file)
            
            # Verify file was created and has content
            self.assertTrue(os.path.exists(temp_file))
            with open(temp_file, 'r') as f:
                content = f.read()
                self.assertIn("API_KEY_1", content)
                self.assertIn("API_KEY_2", content)
                
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_load_tools_from_names_list(self):
        """Test load_tools_from_names_list method."""
        # Test loading specific tools
        tool_names = ["UniProt_get_entry_by_accession"]
        self.tu.load_tools_from_names_list(tool_names, clear_existing=False)
        
        # Verify tools are loaded
        available_tools = self.tu.get_available_tools()
        self.assertIn("UniProt_get_entry_by_accession", available_tools)
    
    def test_check_function_call(self):
        """Test check_function_call method."""
        # Test valid function call
        valid_call = '{"name": "UniProt_get_entry_by_accession", "arguments": {"accession": "P05067"}}'
        is_valid, message = self.tu.check_function_call(valid_call)
        self.assertTrue(is_valid)
        self.assertIsInstance(message, str)
        
        # Test invalid function call
        invalid_call = '{"name": "NonExistentTool", "arguments": {}}'
        is_valid, message = self.tu.check_function_call(invalid_call)
        self.assertFalse(is_valid)
        self.assertIsInstance(message, str)


if __name__ == "__main__":
    unittest.main()
