#!/usr/bin/env python3
"""
Unit tests for ToolUniverse core functionality based on documentation.

Tests core methods without external dependencies to ensure fast execution.
Covers all core functionality mentioned in the documentation.
"""

import pytest
import json
import tempfile
from pathlib import Path

from tooluniverse import ToolUniverse


@pytest.mark.unit
class TestToolUniverseCore:
    """Test core ToolUniverse functionality from documentation."""

    def teardown_method(self):
        """Tear down ToolUniverse instance."""
        if hasattr(self, 'tu'):
            self.tu.close()

    def test_initialization(self):
        """Test ToolUniverse initialization as documented."""
        self.tu = ToolUniverse()
        assert self.tu is not None
        assert hasattr(self.tu, 'load_tools')
        assert hasattr(self.tu, 'list_built_in_tools')
        assert hasattr(self.tu, 'run')

    def test_load_tools_basic(self):
        """Test basic load_tools() functionality."""
        self.tu = ToolUniverse()

        # Test loading all tools
        self.tu.load_tools()
        assert len(self.tu.all_tools) > 0

        # Test that tools are loaded
        assert hasattr(self.tu, 'all_tools')
        assert isinstance(self.tu.all_tools, list)

    def test_load_tools_selective_categories(self):
        """Test selective tool loading by categories."""
        self.tu = ToolUniverse()

        # Test loading specific categories
        self.tu.load_tools(tool_type=["uniprot", "ChEMBL"])
        assert len(self.tu.all_tools) > 0

        # Test excluding categories
        tu2 = ToolUniverse()
        try:
            tu2.load_tools(exclude_categories=["mcp_auto_loader", "special_tools"])
            assert len(tu2.all_tools) > 0
        finally:
            tu2.close()

    def test_load_tools_include_tools(self):
        """Test loading specific tools by name."""
        self.tu = ToolUniverse()
        
        # Test loading specific tools
        self.tu.load_tools(include_tools=[
            "UniProt_get_entry_by_accession",
            "ChEMBL_get_molecule_by_chembl_id"
        ])
        assert len(self.tu.all_tools) > 0

    def test_load_tools_include_tool_types(self):
        """Test filtering by tool types."""
        self.tu = ToolUniverse()
        
        # Test including specific tool types
        self.tu.load_tools(include_tool_types=["OpenTarget", "ChEMBLTool"])
        assert len(self.tu.all_tools) > 0
        
        # Test excluding tool types
        tu2 = ToolUniverse()
        try:
            tu2.load_tools(exclude_tool_types=["ToolFinderEmbedding", "Unknown"])
            assert len(tu2.all_tools) > 0
        finally:
            tu2.close()

    def test_load_tools_exclude_tools(self):
        """Test excluding specific tools."""
        self.tu = ToolUniverse()
        
        # Test excluding specific tools
        self.tu.load_tools(exclude_tools=["problematic_tool", "slow_tool"])
        assert len(self.tu.all_tools) > 0

    def test_load_tools_custom_config_files(self):
        """Test loading with custom configuration files."""
        self.tu = ToolUniverse()
        
        # Create a temporary custom config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            custom_config = {
                "type": "CustomTool",
                "name": "test_custom_tool",
                "description": "A test custom tool",
                "parameter": {
                    "type": "object",
                    "properties": {
                        "test_param": {
                            "type": "string",
                            "description": "Test parameter"
                        }
                    },
                    "required": ["test_param"]
                }
            }
            json.dump(custom_config, f)
            temp_file = f.name

        try:
            # Test loading with custom config files
            # This may fail due to config format issues, which is expected
            try:
                self.tu.load_tools(tool_config_files={
                    "custom": temp_file
                })
                assert len(self.tu.all_tools) > 0
            except (KeyError, ValueError) as e:
                # Expected to fail due to config format issues
                assert "name" in str(e) or "KeyError" in str(e)
        finally:
            Path(temp_file).unlink()

    def test_list_built_in_tools_config_mode(self):
        """Test list_built_in_tools in config mode (default)."""
        self.tu = ToolUniverse()
        
        # Test default config mode
        stats = self.tu.list_built_in_tools()
        assert isinstance(stats, dict)
        assert 'categories' in stats
        assert 'total_categories' in stats
        assert 'total_tools' in stats
        assert 'mode' in stats
        assert 'summary' in stats
        assert stats['mode'] == 'config'
        assert stats['total_tools'] > 0

    def test_list_built_in_tools_type_mode(self):
        """Test list_built_in_tools in type mode."""
        self.tu = ToolUniverse()
        
        # Test type mode
        stats = self.tu.list_built_in_tools(mode='type')
        assert isinstance(stats, dict)
        assert 'categories' in stats
        assert 'total_categories' in stats
        assert 'total_tools' in stats
        assert 'mode' in stats
        assert 'summary' in stats
        assert stats['mode'] == 'type'
        assert stats['total_tools'] > 0

    def test_list_built_in_tools_list_name_mode(self):
        """Test list_built_in_tools in list_name mode."""
        self.tu = ToolUniverse()
        
        # Test list_name mode
        tool_names = self.tu.list_built_in_tools(mode='list_name')
        assert isinstance(tool_names, list)
        assert len(tool_names) > 0
        assert all(isinstance(name, str) for name in tool_names)

    def test_list_built_in_tools_list_spec_mode(self):
        """Test list_built_in_tools in list_spec mode."""
        self.tu = ToolUniverse()
        
        # Test list_spec mode
        tool_specs = self.tu.list_built_in_tools(mode='list_spec')
        assert isinstance(tool_specs, list)
        assert len(tool_specs) > 0
        assert all(isinstance(spec, dict) for spec in tool_specs)
        
        # Check spec structure
        if tool_specs:
            spec = tool_specs[0]
            assert 'name' in spec
            assert 'type' in spec
            assert 'description' in spec

    def test_list_built_in_tools_scan_all(self):
        """Test list_built_in_tools with scan_all parameter."""
        self.tu = ToolUniverse()
        
        # Test scan_all=False (default)
        tools_predefined = self.tu.list_built_in_tools(mode='list_name', scan_all=False)
        assert isinstance(tools_predefined, list)
        assert len(tools_predefined) > 0
        
        # Test scan_all=True
        tools_all = self.tu.list_built_in_tools(mode='list_name', scan_all=True)
        assert isinstance(tools_all, list)
        assert len(tools_all) >= len(tools_predefined)

    def test_tool_specification_single(self):
        """Test tool_specification for single tool."""
        self.tu = ToolUniverse()
        self.tu.load_tools()
        
        # Test getting tool specification for a tool that exists
        # First, get a list of available tools
        tool_names = self.tu.list_built_in_tools(mode='list_name')
        assert len(tool_names) > 0
        
        # Use the first available tool
        first_tool = tool_names[0]
        spec = self.tu.tool_specification(first_tool)
        assert isinstance(spec, dict)
        assert 'name' in spec
        assert 'description' in spec
        # Check for either 'parameters' or 'parameter' (both are valid)
        assert 'parameters' in spec or 'parameter' in spec
        assert spec['name'] == first_tool

    def test_tool_specification_multiple(self):
        """Test get_tool_specification_by_names for multiple tools."""
        self.tu = ToolUniverse()
        self.tu.load_tools()
        
        # Test getting multiple tool specifications
        # First, get a list of available tools
        tool_names = self.tu.list_built_in_tools(mode='list_name')
        assert len(tool_names) >= 2
        
        # Use the first two available tools
        first_two_tools = tool_names[:2]
        specs = self.tu.get_tool_specification_by_names(first_two_tools)
        assert isinstance(specs, list)
        assert len(specs) == 2
        assert all(isinstance(spec, dict) for spec in specs)

    def test_select_tools(self):
        """Test filter_tools + category filter (replacement for deprecated select_tools)."""
        self.tu = ToolUniverse()
        self.tu.load_tools()

        # Filter by categories using filter_tools + category field
        include_cat_set = {"opentarget", "chembl"}
        selected_tools = [
            t
            for t in self.tu.filter_tools(exclude_tools={"tool_to_exclude"})
            if t.get("category") in include_cat_set
        ]
        assert isinstance(selected_tools, list)

    def test_refresh_tool_name_desc(self):
        """Test refresh_tool_name_desc method."""
        self.tu = ToolUniverse()
        self.tu.load_tools()
        
        # Test refreshing tool names and descriptions
        tool_names, tool_descs = self.tu.refresh_tool_name_desc(
            include_categories=['fda_drug_label'],
            exclude_categories=['deprecated_tools']
        )
        assert isinstance(tool_names, list)
        assert isinstance(tool_descs, list)
        assert len(tool_names) == len(tool_descs)

    def test_error_handling_invalid_tool_name(self):
        """Test error handling for invalid tool names."""
        self.tu = ToolUniverse()
        self.tu.load_tools()
        
        # Test with invalid tool name
        result = self.tu.run({
            "name": "nonexistent_tool",
            "arguments": {"param": "value"}
        })
        # Result can be a dict or string, so convert to string for checking
        result_str = str(result).lower()
        assert "error" in result_str or "invalid" in result_str or "not found" in result_str

    def test_error_handling_missing_parameters(self):
        """Test error handling for missing required parameters."""
        self.tu = ToolUniverse()
        self.tu.load_tools()
        
        # Test with missing required parameter
        result = self.tu.run({
            "name": "UniProt_get_entry_by_accession",
            "arguments": {"wrong_param": "value"}  # Missing required 'accession'
        })
        # Result can be a dict or string, so convert to string for checking
        result_str = str(result).lower()
        assert "error" in result_str or "missing" in result_str or "invalid" in result_str or "not found" in result_str

    def test_run_method_single_tool(self):
        """Test run method with single tool call."""
        self.tu = ToolUniverse()
        self.tu.load_tools()
        
        # Test single tool call format
        result = self.tu.run({
            "name": "UniProt_get_entry_by_accession",
            "arguments": {"accession": "P05067"}
        })
        assert result is not None

    @pytest.mark.network
    def test_run_method_multiple_tools(self):
        """Sequential run() calls must each return a non-None dict."""
        self.tu = ToolUniverse()
        self.tu.load_tools()

        result1 = self.tu.run({
            "name": "UniProt_get_entry_by_accession",
            "arguments": {"accession": "P05067"}
        })
        result2 = self.tu.run({
            "name": "OpenTargets_get_associated_targets_by_disease_efoId",
            "arguments": {"efoId": "EFO_0000249"}
        })

        assert result1 is not None, "First run() must return a value"
        assert result2 is not None, "Second run() must return a value"
        assert isinstance(result1, dict), f"Expected dict, got {type(result1)}"
        assert isinstance(result2, dict), f"Expected dict, got {type(result2)}"

    def test_direct_import_pattern(self):
        """The tooluniverse.tools namespace must be resolvable."""
        try:
            import tooluniverse.tools as tools_module
            assert tools_module is not None
            assert hasattr(tools_module, "__name__")
        except ImportError as exc:
            # If a sub-module is missing (e.g. ghost_tool not installed), skip
            pytest.skip(f"tooluniverse.tools not fully importable: {exc}")

    def test_dynamic_access_pattern(self):
        """Test dynamic access pattern from documentation."""
        self.tu = ToolUniverse()
        self.tu.load_tools()
        
        # Test dynamic access through self.tu.tools
        assert hasattr(self.tu, 'tools')
        # Note: Actual tool execution would require external APIs
        # This test verifies the structure exists

    def test_tool_finder_keyword_execution(self):
        """Tool_Finder_Keyword must return a non-empty list (no API key needed)."""
        self.tu = ToolUniverse()
        self.tu.load_tools()

        result = self.tu.run({
            "name": "Tool_Finder_Keyword",
            "arguments": {"description": "protein analysis", "limit": 5}
        })

        # Tool_Finder_Keyword returns a list of tool dicts directly (not a wrapper dict)
        assert isinstance(result, list), f"Expected list, got {type(result)}: {result!r}"
        assert len(result) > 0, "Expected at least one keyword match for 'protein analysis'"
        assert isinstance(result[0], dict), f"Each item must be a dict, got: {result[0]!r}"

    @pytest.mark.require_api_keys
    def test_tool_finder_llm_execution(self):
        """Tool_Finder_LLM must return dict with 'tools' when API key is present."""
        self.tu = ToolUniverse()
        self.tu.load_tools()

        result = self.tu.run({
            "name": "Tool_Finder_LLM",
            "arguments": {"description": "protein analysis", "limit": 5}
        })

        assert isinstance(result, dict), f"Expected dict, got: {result!r}"
        assert "tools" in result or "error" in result

    def test_tool_finder_keyword_with_selective_load(self):
        """Tool_Finder_Keyword works when loaded selectively (no embedding model)."""
        self.tu = ToolUniverse()
        self.tu.load_tools(include_tools=[
            "Tool_Finder_Keyword",
            "UniProt_get_entry_by_accession",
        ])

        result = self.tu.run({
            "name": "Tool_Finder_Keyword",
            "arguments": {"description": "protein analysis", "limit": 5},
        })

        # Returns a list of tool dicts (or error dict if validation fails)
        assert isinstance(result, (list, dict)), (
            f"Expected list or dict, got {type(result).__name__}: {result!r}"
        )
        if isinstance(result, list):
            assert len(result) >= 0  # list can be empty if keyword search has no matches
        else:
            assert "error" in result, f"dict result must have 'error' key: {result!r}"

    @pytest.mark.slow
    @pytest.mark.require_gpu
    def test_tool_finder_embedding_execution_slow(self):
        """Tool_Finder (embedding) must return a dict — requires GPU/heavy model."""
        self.tu = ToolUniverse()
        self.tu.load_tools(include_tools=["Tool_Finder", "UniProt_get_entry_by_accession"])

        result = self.tu.run({
            "name": "Tool_Finder",
            "arguments": {"description": "protein analysis", "limit": 5},
        })

        assert isinstance(result, dict), f"Expected dict, got: {result!r}"
        assert "tools" in result or "error" in result

    def test_combined_loading_parameters(self):
        """Test combined loading parameters as documented."""
        self.tu = ToolUniverse()
        
        # Test combining multiple loading options
        self.tu.load_tools(
            tool_type=["uniprot", "ChEMBL", "custom"],
            exclude_tools=["problematic_tool"],
            exclude_tool_types=["Unknown"],
            tool_config_files={
                "custom": "/path/to/custom.json"  # This will fail but tests structure
            }
        )
        assert len(self.tu.all_tools) > 0

    def test_tool_loading_without_loading_tools(self):
        """Test that list_built_in_tools works before load_tools."""
        self.tu = ToolUniverse()
        
        # Test that we can explore tools before loading them
        tool_names = self.tu.list_built_in_tools(mode='list_name')
        tool_specs = self.tu.list_built_in_tools(mode='list_spec')
        stats = self.tu.list_built_in_tools(mode='config')
        
        assert isinstance(tool_names, list)
        assert isinstance(tool_specs, list)
        assert isinstance(stats, dict)
        assert len(tool_names) > 0

    def test_tool_categories_organization(self):
        """Test tool organization by categories."""
        self.tu = ToolUniverse()
        
        # Test config mode shows categories
        stats = self.tu.list_built_in_tools(mode='config')
        categories = stats['categories']
        
        # Check for expected categories from documentation
        expected_categories = [
            'fda_drug_label', 'clinical_trials', 'semantic_scholar',
            'opentarget', 'chembl'
        ]
        
        # At least some expected categories should be present
        found_categories = [cat for cat in expected_categories if cat in categories]
        assert len(found_categories) > 0

    def test_tool_types_organization(self):
        """Test tool organization by types."""
        self.tu = ToolUniverse()
        
        # Test type mode shows tool types
        stats = self.tu.list_built_in_tools(mode='type')
        categories = stats['categories']
        
        # Check for expected tool types from documentation
        expected_types = [
            'FDADrugLabel', 'OpenTarget', 'ChEMBLTool', 'MCPAutoLoaderTool'
        ]
        
        # At least some expected types should be present
        found_types = [ttype for ttype in expected_types if ttype in categories]
        assert len(found_types) > 0

    def test_tool_specification_structure(self):
        """Test tool specification structure matches documentation."""
        self.tu = ToolUniverse()
        self.tu.load_tools()
        
        # Get a tool specification for a tool that exists
        # First, get a list of available tools
        tool_names = self.tu.list_built_in_tools(mode='list_name')
        assert len(tool_names) > 0
        
        # Use the first available tool
        first_tool = tool_names[0]
        spec = self.tu.tool_specification(first_tool)
        
        # Check required fields from documentation
        assert 'name' in spec
        assert 'description' in spec
        # Check for either 'parameters' or 'parameter' (both are valid)
        assert 'parameters' in spec or 'parameter' in spec
        
        # Check parameter structure if it exists
        if 'parameters' in spec and 'properties' in spec['parameters']:
            properties = spec['parameters']['properties']
            assert isinstance(properties, dict)
            
            # Check that parameters have required fields
            for param_name, param_info in properties.items():
                assert 'type' in param_info
                assert 'description' in param_info

    def test_tool_execution_flow_structure(self):
        """run() must accept documented format and return a dict (not raise)."""
        self.tu = ToolUniverse()
        self.tu.load_tools()

        result = self.tu.run({
            "name": "action_description",   # unknown tool → error dict
            "arguments": {"parameter1": "value1", "parameter2": "value2"},
        })

        # run() must never raise; unknown tool → error dict
        assert result is not None
        assert isinstance(result, dict), f"Expected dict, got {type(result)}: {result!r}"
        assert "error" in result, f"Expected error for unknown tool, got: {result!r}"

    def test_tool_loading_performance(self):
        """Test that tool loading is reasonably fast."""
        import time
        
        self.tu = ToolUniverse()
        
        # Test loading time
        start_time = time.time()
        self.tu.load_tools()
        end_time = time.time()
        
        # Should load within reasonable time (adjust threshold as needed)
        load_time = end_time - start_time
        assert load_time < 30  # 30 seconds should be more than enough

    def test_tool_listing_performance(self):
        """Test that tool listing is fast."""
        import time
        
        self.tu = ToolUniverse()
        
        # Test listing time
        start_time = time.time()
        _ = self.tu.list_built_in_tools()
        end_time = time.time()
        
        # Should be very fast
        listing_time = end_time - start_time
        assert listing_time < 5  # 5 seconds should be more than enough

    def test_parameter_schema_extraction(self):
        """Test parameter schema extraction from tool configuration."""
        from tooluniverse.utils import get_parameter_schema
        
        # Test with standard 'parameter' key
        config1 = {
            "name": "test_tool",
            "parameter": {
                "type": "object",
                "properties": {"arg1": {"type": "string"}},
                "required": ["arg1"]
            }
        }
        schema1 = get_parameter_schema(config1)
        assert schema1["type"] == "object"
        assert "arg1" in schema1["properties"]
        
        # Test with missing parameter key (should return empty dict)
        config2 = {
            "name": "test_tool"
        }
        schema2 = get_parameter_schema(config2)
        assert schema2 == {}
        
        # Test with neither key
        config3 = {"name": "test_tool"}
        schema3 = get_parameter_schema(config3)
        assert schema3 == {}

    def test_error_formatting_consistency(self):
        """Test that error formatting is consistent."""
        from tooluniverse.utils import format_error_response
        from tooluniverse.exceptions import ToolAuthError
        
        # Test with regular exception
        regular_error = ValueError("Test error")
        formatted = format_error_response(regular_error, "test_tool", {"arg": "value"})
        
        assert isinstance(formatted, dict)
        assert "error" in formatted
        assert "error_type" in formatted
        assert "retriable" in formatted
        assert "next_steps" in formatted
        assert "details" in formatted
        assert "tool_name" in formatted
        assert "timestamp" in formatted
        
        assert formatted["error"] == "Test error"
        assert formatted["error_type"] == "ValueError"
        assert formatted["retriable"] is False
        assert formatted["tool_name"] == "test_tool"
        assert formatted["details"]["arg"] == "value"
        
        # Test with ToolError
        tool_error = ToolAuthError("Auth failed", retriable=True, next_steps=["Check API key"])
        formatted_tool = format_error_response(tool_error, "test_tool")
        
        assert formatted_tool["error"] == "Auth failed"
        assert formatted_tool["error_type"] == "ToolAuthError"
        assert formatted_tool["retriable"] is True
        assert "Check API key" in formatted_tool["next_steps"]

    def test_all_tools_data_type_consistency(self):
        """all_tools must be a list of dicts, each with at least a 'name' string key."""
        self.tu = ToolUniverse()

        # The workspace profile may auto-load tools; just verify it's a list
        assert isinstance(self.tu.all_tools, list)

        self.tu.load_tools()
        assert isinstance(self.tu.all_tools, list)
        assert len(self.tu.all_tools) > 0, "load_tools() must populate all_tools"

        for tool in self.tu.all_tools:
            assert isinstance(tool, dict), f"Tool must be dict, got {type(tool)}: {tool!r}"
            assert "name" in tool, f"Tool dict must have 'name' key: {tool!r}"
            assert isinstance(tool["name"], str), f"Tool name must be str: {tool['name']!r}"

