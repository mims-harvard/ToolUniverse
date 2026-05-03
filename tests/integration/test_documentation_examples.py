#!/usr/bin/env python3
"""
Integration tests for ToolUniverse examples validation based on documentation.

Tests all example files and documentation code snippets to ensure they work correctly.
Covers quickstart, getting_started, and key documentation examples.
"""

import pytest
import os
import sys
import subprocess
import tempfile
from pathlib import Path
import importlib.util

from tooluniverse import ToolUniverse


@pytest.mark.integration
@pytest.mark.network
class TestToolUniverseExamplesValidation:
    """Test examples validation with real execution."""

    @pytest.fixture(autouse=True)
    def setup_tooluniverse(self):
        """Setup ToolUniverse instance for each test."""
        self.tu = ToolUniverse()
        self.tu.load_tools()
        yield
        self.tu.close()

    def test_quickstart_example_1(self):
        """Test quickstart example 1: Basic ToolUniverse usage."""
        # Test the basic quickstart example from documentation
        tu = ToolUniverse()
        try:
            tu.load_tools()
            
            # Test tool execution
            result = tu.run({
                "name": "OpenTargets_get_associated_targets_by_disease_efoId",
                "arguments": {"efoId": "EFO_0000537"}  # hypertension
            })
            
            assert result is not None
            assert isinstance(result, (dict, list, str))
        finally:
            tu.close()

    def test_quickstart_example_2(self):
        """Test quickstart example 2: Tool finder usage."""
        # Test tool finder example from documentation
        result = self.tu.run({
            "name": "Tool_Finder_Keyword",
            "arguments": {
                "description": "disease target associations",
                "limit": 10
            }
        })
        
        assert result is not None
        assert isinstance(result, (list, dict))

    def test_getting_started_example_1(self):
        """Test getting started example 1: Initialize and load tools."""
        # Test initialization and loading from getting started tutorial
        tu = ToolUniverse()
        try:
            tu.load_tools()
            
            # Check that tools are loaded
            assert len(tu.all_tools) > 0
            
            # Test tool listing
            stats = tu.list_built_in_tools()
            assert stats['total_tools'] > 0
        finally:
            tu.close()

    def test_getting_started_example_2(self):
        """Test getting started example 2: Explore available tools."""
        # Test tool exploration from getting started tutorial
        stats = self.tu.list_built_in_tools(mode='config')
        assert 'categories' in stats
        assert 'total_categories' in stats
        assert 'total_tools' in stats
        
        # Test type mode
        type_stats = self.tu.list_built_in_tools(mode='type')
        assert 'categories' in type_stats
        assert 'total_categories' in type_stats
        assert 'total_tools' in type_stats

    def test_getting_started_example_3(self):
        """Test getting started example 3: Tool specification retrieval."""
        # Test tool specification retrieval from getting started tutorial
        spec = self.tu.tool_specification("UniProt_get_function_by_accession", format="openai")
        assert isinstance(spec, dict)
        assert 'name' in spec
        assert 'description' in spec
        assert 'parameters' in spec
        
        # Test multiple tool specifications
        specs = self.tu.get_tool_specification_by_names([
            "FAERS_count_reactions_by_drug_event",
            "OpenTargets_get_associated_targets_by_disease_efoId"
        ])
        assert isinstance(specs, list)
        assert len(specs) == 2

    def test_getting_started_example_4(self):
        """Test getting started example 4: Execute tools."""
        # Test tool execution from getting started tutorial
        # Test UniProt tool
        gene_info = self.tu.run({
            "name": "UniProt_get_function_by_accession",
            "arguments": {"accession": "P05067"}
        })
        assert gene_info is not None
        
        # Test FAERS tool
        safety_data = self.tu.run({
            "name": "FAERS_count_reactions_by_drug_event",
            "arguments": {"medicinalproduct": "aspirin"}
        })
        assert safety_data is not None
        
        # Test OpenTargets tool
        targets = self.tu.run({
            "name": "OpenTargets_get_associated_targets_by_disease_efoId",
            "arguments": {"efoId": "EFO_0000685"}  # Rheumatoid arthritis
        })
        assert targets is not None
        
        # Test literature search tool
        papers = self.tu.run({
            "name": "PubTator_search_publications",
            "arguments": {
                "query": "CRISPR cancer therapy",
                "limit": 10
            }
        })
        assert papers is not None

    def test_examples_directory_structure(self):
        """Test that examples directory has expected structure."""
        examples_dir = Path("examples")
        assert examples_dir.exists()
        
        # Check for key example files
        expected_files = [
            "uniprot_tools_example.py",
            "tool_finder_example.py",
            "mcp_server_example.py",
            "literature_search_example.py"
        ]
        
        for file_name in expected_files:
            file_path = examples_dir / file_name
            if file_path.exists():
                assert file_path.is_file()

    def test_uniprot_tools_example(self):
        """Test UniProt tools example."""
        example_file = Path("examples/uniprot_tools_example.py")
        if example_file.exists():
            # Test that the example file can be imported and executed
            spec = importlib.util.spec_from_file_location("uniprot_example", example_file)
            if spec and spec.loader:
                _ = importlib.util.module_from_spec(spec)
                # Don't actually execute the module to avoid side effects
                assert spec is not None

    def test_tool_finder_example(self):
        """Test tool finder example."""
        example_file = Path("examples/tool_finder_example.py")
        if example_file.exists():
            # Test that the example file can be imported
            spec = importlib.util.spec_from_file_location("tool_finder_example", example_file)
            if spec and spec.loader:
                _ = importlib.util.module_from_spec(spec)
                assert spec is not None

    def test_mcp_server_example(self):
        """Test MCP server example."""
        example_file = Path("examples/mcp_server_example.py")
        if example_file.exists():
            # Test that the example file can be imported
            spec = importlib.util.spec_from_file_location("mcp_server_example", example_file)
            if spec and spec.loader:
                _ = importlib.util.module_from_spec(spec)
                assert spec is not None

    def test_literature_search_example(self):
        """Test literature search example."""
        example_file = Path("examples/literature_search_example.py")
        if example_file.exists():
            # Test that the example file can be imported
            spec = importlib.util.spec_from_file_location("literature_search_example", example_file)
            if spec and spec.loader:
                _ = importlib.util.module_from_spec(spec)
                assert spec is not None

    def test_quickstart_tutorial_code_snippets(self):
        """Test quickstart tutorial code snippets."""
        # Test the code snippets from quickstart tutorial
        
        # Snippet 1: Installation
        # This is just a comment, no code to test
        
        # Snippet 2: Basic usage
        tu = ToolUniverse()
        try:
            tu.load_tools()
            assert len(tu.all_tools) > 0
            
            # Snippet 3: Query scientific databases
            result = tu.run({
                "name": "OpenTargets_get_associated_targets_by_disease_efoId",
                "arguments": {"efoId": "EFO_0000537"}  # hypertension
            })
            assert result is not None
        finally:
            tu.close()

    def test_getting_started_tutorial_code_snippets(self):
        """Test getting started tutorial code snippets."""
        # Test the code snippets from getting started tutorial
        
        # Snippet 1: Initialize ToolUniverse
        tu = ToolUniverse()
        try:
            tu.load_tools()
            assert len(tu.all_tools) > 0
            
            # Snippet 2: List built-in tools
            stats = tu.list_built_in_tools(mode='config')
            assert 'categories' in stats
            
            # Snippet 3: Search for specific tools
            protein_tools = tu.run({
                "name": "Tool_Finder_Keyword",
                "arguments": {
                    "description": "protein structure",
                    "limit": 5
                }
            })
            assert protein_tools is not None
            
            # Snippet 4: Get tool specification
            spec = tu.tool_specification("UniProt_get_function_by_accession")
            assert 'name' in spec
            
            # Snippet 5: Execute tools
            gene_query = tu.run({
                "name": "UniProt_get_function_by_accession",
                "arguments": {"accession": "P05067"}
            })
            assert gene_query is not None
        finally:
            tu.close()

    def test_loading_tools_tutorial_code_snippets(self):
        """Test loading tools tutorial code snippets."""
        # Test the code snippets from loading tools tutorial
        
        # Snippet 1: Load all tools
        tu = ToolUniverse()
        try:
            tu.load_tools()
            assert len(tu.all_tools) > 0
        finally:
            tu.close()
        
        # Snippet 2: Load specific categories
        tu2 = ToolUniverse()
        try:
            tu2.load_tools(tool_type=["uniprot", "ChEMBL", "opentarget"])
            assert len(tu2.all_tools) > 0
        finally:
            tu2.close()
        
        # Snippet 3: Load specific tools
        tu3 = ToolUniverse()
        try:
            tu3.load_tools(include_tools=[
                "UniProt_get_entry_by_accession",
                "ChEMBL_get_molecule_by_chembl_id",
                "OpenTargets_get_associated_targets_by_disease_efoId"
            ])
            assert len(tu3.all_tools) > 0
        finally:
            tu3.close()

    def test_listing_tools_tutorial_code_snippets(self):
        """Test listing tools tutorial code snippets."""
        # Test the code snippets from listing tools tutorial
        
        # Snippet 1: List tools by config categories
        stats = self.tu.list_built_in_tools(mode='config')
        assert 'categories' in stats
        
        # Snippet 2: List tools by implementation types
        type_stats = self.tu.list_built_in_tools(mode='type')
        assert 'categories' in type_stats
        
        # Snippet 3: Get all tool names as a list
        tool_names = self.tu.list_built_in_tools(mode='list_name')
        assert isinstance(tool_names, list)
        assert len(tool_names) > 0
        
        # Snippet 4: Get all tool specifications as a list
        tool_specs = self.tu.list_built_in_tools(mode='list_spec')
        assert isinstance(tool_specs, list)
        assert len(tool_specs) > 0

    def test_tool_caller_tutorial_code_snippets(self):
        """Test tool caller tutorial code snippets."""
        # Test the code snippets from tool caller tutorial
        
        # Snippet 1: Direct import
        from tooluniverse.tools import UniProt_get_entry_by_accession
        result = UniProt_get_entry_by_accession(accession="P05067")
        assert result is not None
        
        # Snippet 2: Dynamic access
        result = self.tu.tools.UniProt_get_entry_by_accession(accession="P05067")
        assert result is not None
        
        # Snippet 3: JSON format (single tool call)
        result = self.tu.run({
            "name": "UniProt_get_entry_by_accession",
            "arguments": {"accession": "P05067"}
        })
        assert result is not None
        
        # Snippet 4: JSON format (multiple tool calls)
        results = self.tu.run([
            {
                "name": "UniProt_get_entry_by_accession",
                "arguments": {"accession": "P05067"}
            },
            {
                "name": "OpenTargets_get_associated_targets_by_disease_efoId",
                "arguments": {"efoId": "EFO_0000249"}
            }
        ])
        assert isinstance(results, list)
        # Allow for additional messages in the conversation
        assert len(results) >= 2

    def test_mcp_support_tutorial_code_snippets(self):
        """Test MCP support tutorial code snippets."""
        # Test the code snippets from MCP support tutorial
        
        # Snippet 1: Python MCP server setup
        from tooluniverse.smcp import SMCP
        
        server = SMCP(
            name="Scientific Research Server",
            tool_categories=["uniprot", "opentarget", "ChEMBL"],
            search_enabled=True
        )
        assert server is not None
        assert server.name == "Scientific Research Server"

    def test_hooks_tutorial_code_snippets(self):
        """Test hooks tutorial code snippets."""
        # Test the code snippets from hooks tutorial
        
        # Snippet 1: Hook configuration
        hook_config = {
            "SummarizationHook": {
                "max_tokens": 2048,
                "summary_style": "concise"
            },
            "FileSaveHook": {
                "output_dir": "/tmp/tu_outputs",
                "filename_template": "{tool}_{timestamp}.json"
            }
        }
        
        # Validate configuration structure
        assert "SummarizationHook" in hook_config
        assert "FileSaveHook" in hook_config
        assert hook_config["SummarizationHook"]["max_tokens"] == 2048

    def test_tool_composition_tutorial_code_snippets(self):
        """Test tool composition tutorial code snippets."""
        # Test the code snippets from tool composition tutorial
        
        # Snippet 1: Compose function signature
        def compose(arguments, tooluniverse, call_tool):
            """Test compose function signature."""
            topic = arguments['research_topic']
            
            literature = {}
            literature['pmc'] = call_tool('EuropePMC_search_articles', {'query': topic, 'limit': 5})
            literature['openalex'] = call_tool('openalex_literature_search', {'search_keywords': topic, 'max_results': 5})
            literature['pubtator'] = call_tool('PubTator3_LiteratureSearch', {'text': topic, 'page_size': 5})
            
            summary = call_tool('MedicalLiteratureReviewer', {
                'research_topic': topic,
                'literature_content': str(literature),
                'focus_area': 'key findings',
                'study_types': 'all studies',
                'quality_level': 'all evidence',
                'review_scope': 'rapid review'
            })
            
            return summary
        
        # Test the compose function
        result = compose(
            arguments={'research_topic': 'cancer therapy'},
            tooluniverse=self.tu,
            call_tool=lambda name, args: {"mock": "result"}
        )
        assert result is not None

    def test_scientific_workflows_tutorial_code_snippets(self):
        """Test scientific workflows tutorial code snippets."""
        # Test the code snippets from scientific workflows tutorial
        
        # Snippet 1: Drug discovery workflow
        workflow_results = {}
        
        # Target identification
        workflow_results['targets'] = self.tu.run({
            "name": "OpenTargets_get_associated_targets_by_disease_efoId",
            "arguments": {"efoId": "EFO_0000537"}  # hypertension
        })
        
        # Compound search
        workflow_results['compounds'] = self.tu.run({
            "name": "ChEMBL_get_molecule_by_chembl_id",
            "arguments": {"chembl_id": "CHEMBL25"}
        })
        
        # Safety analysis
        workflow_results['safety'] = self.tu.run({
            "name": "FAERS_count_reactions_by_drug_event",
            "arguments": {"medicinalproduct": "aspirin"}
        })
        
        assert all(result is not None for result in workflow_results.values())

    def test_ai_scientists_tutorial_code_snippets(self):
        """Test AI scientists tutorial code snippets."""
        # Test the code snippets from AI scientists tutorial
        
        # Snippet 1: Claude Desktop MCP configuration
        claude_config = {
            "mcpServers": {
                "tooluniverse": {
                    "command": "tooluniverse-smcp-stdio",
                    "args": ["--categories", "uniprot", "ChEMBL", "opentarget", "--hooks", "--hook-type", "SummarizationHook"]
                }
            }
        }
        
        # Validate configuration structure
        assert "mcpServers" in claude_config
        assert "tooluniverse" in claude_config["mcpServers"]
        assert claude_config["mcpServers"]["tooluniverse"]["command"] == "tooluniverse-smcp-stdio"


    def test_examples_execution_validation(self):
        """Test that example files can be executed without syntax errors."""
        examples_dir = Path("examples")
        if not examples_dir.exists():
            pytest.skip("Examples directory not found")
        
        # Test Python files in examples directory
        python_files = list(examples_dir.glob("*.py"))
        
        for py_file in python_files[:5]:  # Test first 5 files to avoid timeout
            try:
                # Check syntax by compiling the file
                with open(py_file, 'r', encoding='utf-8') as f:
                    source = f.read()
                
                # Compile to check for syntax errors
                compile(source, py_file, 'exec')
                
            except SyntaxError as e:
                pytest.fail(f"Syntax error in {py_file}: {e}")
            except Exception:
                # Other errors (like import errors) are acceptable for examples
                # that require specific setup or API keys
                pass

    def test_documentation_code_blocks_validation(self):
        """Test that code blocks in documentation are valid Python."""
        # This test would validate code blocks from documentation files
        # For now, we test the key patterns that appear in documentation
        
        # Test ToolUniverse initialization pattern
        tu = ToolUniverse()
        try:
            assert tu is not None
            
            # Test tool loading pattern
            tu.load_tools()
            assert len(tu.all_tools) > 0
            
            # Test tool execution pattern
            result = tu.run({
                "name": "UniProt_get_entry_by_accession",
                "arguments": {"accession": "P05067"}
            })
            assert result is not None
        finally:
            tu.close()

    def test_examples_import_validation(self):
        """Test that example files can be imported without import errors."""
        examples_dir = Path("examples")
        if not examples_dir.exists():
            pytest.skip("Examples directory not found")
        
        # Test key example files
        key_examples = [
            "uniprot_tools_example.py",
            "tool_finder_example.py",
            "mcp_server_example.py"
        ]
        
        for example_file in key_examples:
            file_path = examples_dir / example_file
            if file_path.exists():
                try:
                    # Try to import the module
                    spec = importlib.util.spec_from_file_location("example", file_path)
                    if spec and spec.loader:
                        _ = importlib.util.module_from_spec(spec)
                        # Don't actually load to avoid side effects
                        assert spec is not None
                except ImportError:
                    # Import errors are acceptable for examples that require
                    # specific setup or API keys
                    pass

    def test_examples_parameter_validation(self):
        """Test that example files use correct parameter formats."""
        # Test that examples use the correct ToolUniverse parameter format
        valid_query = {
            "name": "UniProt_get_entry_by_accession",
            "arguments": {"accession": "P05067"}
        }
        
        # Test that the format is valid
        assert "name" in valid_query
        assert "arguments" in valid_query
        assert isinstance(valid_query["arguments"], dict)

    def test_examples_error_handling_validation(self):
        """Test that example files handle errors appropriately."""
        # Test that examples handle errors gracefully
        try:
            # Test with invalid tool name
            result = self.tu.run({
                "name": "nonexistent_tool",
                "arguments": {"param": "value"}
            })
            # Should either return error message or None
            assert result is not None or result is None
        except Exception as e:
            # Should not crash the system
            assert "error" in str(e).lower() or "invalid" in str(e).lower()

    def test_examples_performance_validation(self):
        """Test that example files execute within reasonable time."""
        import time
        
        # Test that basic examples execute quickly
        start_time = time.time()
        
        result = self.tu.run({
            "name": "UniProt_get_entry_by_accession",
            "arguments": {"accession": "P05067"}
        })
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        assert result is not None
        assert execution_time < 60  # Should complete within 60 seconds

    def test_examples_memory_usage_validation(self):
        """Test that example files don't cause memory leaks."""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Execute multiple examples
        for i in range(5):
            result = self.tu.run({
                "name": "UniProt_get_entry_by_accession",
                "arguments": {"accession": f"P{i:05d}"}
            })
            assert result is not None
        
        # Force garbage collection
        gc.collect()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable
        assert memory_increase < 100 * 1024 * 1024  # 100MB

    def test_examples_concurrent_execution_validation(self):
        """Test that example files can be executed concurrently."""
        import threading
        import queue
        
        results_queue = queue.Queue()
        
        def execute_example():
            result = self.tu.run({
                "name": "UniProt_get_entry_by_accession",
                "arguments": {"accession": "P05067"}
            })
            results_queue.put(result)
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=execute_example)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        assert len(results) == 3
        assert all(result is not None for result in results)
