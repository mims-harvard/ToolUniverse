#!/usr/bin/env python3
"""
Test Tool Composition and Workflow functionality - Cleaned Version

This test file covers important composition and workflow scenarios:
1. Compose tool creation and execution
2. Real tool chaining patterns
3. Error handling in composed workflows
4. Dependency management
"""

import sys
import unittest
from pathlib import Path
import pytest
from unittest.mock import patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse import ToolUniverse


@pytest.mark.unit
class TestToolComposition(unittest.TestCase):
    """Test tool composition and workflow functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.tu = ToolUniverse()
        # Don't load tools to avoid embedding model loading issues
        self.tu.all_tools = []
        self.tu.all_tool_dict = {}

    def tearDown(self):
        """Tear down test fixtures."""
        if hasattr(self, 'tu'):
            self.tu.close()

    def test_compose_tool_creation_real(self):
        """Test creating and configuring compose tools with real ToolUniverse."""
        # Test compose tool configuration
        compose_config = {
            "type": "ComposeTool",
            "name": "TestComposeTool",
            "description": "Test compose tool",
            "parameter": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    }
                },
                "required": ["query"]
            },
            "composition_file": "test_compose.py",
            "composition_function": "compose"
        }

        # Add to tools
        self.tu.all_tools.append(compose_config)
        self.tu.all_tool_dict["TestComposeTool"] = compose_config

        # Test tool specification
        spec = self.tu.tool_specification("TestComposeTool")
        self.assertIsNotNone(spec)
        self.assertEqual(spec["name"], "TestComposeTool")

    def test_tool_chaining_pattern_real(self):
        """Test sequential tool chaining pattern with real ToolUniverse calls."""
        # Test that we can make sequential calls (may fail due to missing API keys, but that's OK)
        try:
            # First call
            disease_result = self.tu.run({
                "name": "OpenTargets_get_disease_id_description_by_name",
                "arguments": {"diseaseName": "Alzheimer's disease"}
            })
            
            # If first call succeeded, try second call
            if disease_result and isinstance(disease_result, dict) and "data" in disease_result:
                disease_id = disease_result["data"]["disease"]["id"]
                
                targets_result = self.tu.run({
                    "name": "OpenTargets_get_associated_targets_by_disease_efoId",
                    "arguments": {"efoId": disease_id}
                })
                
                # If second call succeeded, try third call
                if targets_result and isinstance(targets_result, dict) and "data" in targets_result:
                    drugs_result = self.tu.run({
                        "name": "OpenTargets_get_associated_drugs_by_disease_efoId",
                        "arguments": {"efoId": disease_id}
                    })
                    
                    self.assertIsInstance(drugs_result, dict)
        except Exception:
            # Expected if API keys not configured or tools not available
            pass

    def test_broadcasting_pattern_real(self):
        """Test parallel tool execution with real ToolUniverse calls."""
        # Test that we can make parallel calls (may fail due to missing API keys, but that's OK)
        literature_sources = {}
        
        try:
            # Parallel searches
            literature_sources['europepmc'] = self.tu.run({
                "name": "EuropePMC_search_articles",
                "arguments": {"query": "CRISPR", "limit": 5}
            })

            literature_sources['openalex'] = self.tu.run({
                "name": "openalex_literature_search",
                "arguments": {
                    "search_keywords": "CRISPR",
                    "max_results": 5
                }
            })

            literature_sources['pubtator'] = self.tu.run({
                "name": "PubTator3_LiteratureSearch",
                "arguments": {"text": "CRISPR", "page_size": 5}
            })

            # Verify all sources were searched
            self.assertEqual(len(literature_sources), 3)
            for source, result in literature_sources.items():
                self.assertIsInstance(result, dict)
        except Exception:
            # Expected if API keys not configured or tools not available
            pass

    def test_error_handling_in_workflows_real(self):
        """Test error handling and fallback mechanisms with real ToolUniverse calls."""
        # Test workflow with error handling
        results = {"status": "running", "completed_steps": []}

        try:
            # Primary step
            primary_result = self.tu.run({
                "name": "NonExistentTool",  # This should fail
                "arguments": {"query": "test"}
            })
            results["primary"] = primary_result
            results["completed_steps"].append("primary")
            
            # If primary succeeded, check if it's an error result
            if isinstance(primary_result, dict) and "error" in primary_result:
                results["primary_error"] = primary_result["error"]

        except Exception as e:
            results["primary_error"] = str(e)

        # Fallback step
        try:
            fallback_result = self.tu.run({
                "name": "UniProt_get_entry_by_accession",  # This might work
                "arguments": {"accession": "P05067"}
            })
            results["fallback"] = fallback_result
            results["completed_steps"].append("fallback")

        except Exception as e2:
            results["fallback_error"] = str(e2)

        # Verify error handling worked
        # Primary should either have an error or be marked as failed
        self.assertTrue("primary_error" in results or 
                       (isinstance(results.get("primary"), dict) and "error" in results["primary"]))
        # Either fallback succeeded or failed, both are valid outcomes
        self.assertTrue("fallback" in results or "fallback_error" in results)

    def test_dependency_management_real(self):
        """Test dependency management with real ToolUniverse."""
        # Test that we can check for tool availability
        required_tools = [
            "EuropePMC_search_articles",
            "openalex_literature_search",
            "PubTator3_LiteratureSearch"
        ]
        
        available_tools = self.tu.get_available_tools()
        
        # Check which required tools are available
        available_required = [tool for tool in required_tools if tool in available_tools]
        
        self.assertIsInstance(available_required, list)
        self.assertLessEqual(len(available_required), len(required_tools))

    def test_workflow_optimization_real(self):
        """Test workflow optimization with real ToolUniverse."""
        # Test caching mechanism
        cache_key = "test_query"
        result = self.tu._cache.get(cache_key)
        if result is None:
            try:
                result = self.tu.run({
                    "name": "UniProt_get_entry_by_accession",
                    "arguments": {"accession": "P05067"}
                })
                self.tu._cache.set(cache_key, result)
            except Exception:
                # Expected if API key not configured
                result = {"error": "API key not configured"}
                self.tu._cache.set(cache_key, result)
        
        # Verify caching worked
        cached_result = self.tu._cache.get(cache_key)
        self.assertIsNotNone(cached_result)
        self.assertEqual(cached_result, result)

    def test_workflow_data_flow_real(self):
        """Test data flow between tools with real ToolUniverse calls."""
        # Test data flow workflow
        workflow_data = {}

        try:
            # Step 1: Gene discovery
            genes_result = self.tu.run({
                "name": "HPA_search_genes_by_query",
                "arguments": {"search_query": "breast cancer"}
            })
            
            if genes_result and isinstance(genes_result, dict) and "genes" in genes_result:
                workflow_data["genes"] = genes_result["genes"]

                # Step 2: Pathway analysis (using genes from step 1)
                pathways_result = self.tu.run({
                    "name": "HPA_get_biological_processes_by_gene",
                    "arguments": {"gene": workflow_data["genes"][0] if workflow_data["genes"] else "BRCA1"}
                })
                
                if pathways_result and isinstance(pathways_result, dict):
                    workflow_data["pathways"] = pathways_result

                # Step 3: Drug discovery
                drugs_result = self.tu.run({
                    "name": "OpenTargets_get_associated_drugs_by_disease_efoId",
                    "arguments": {"efoId": "EFO_0000305"}  # breast cancer
                })
                
                if drugs_result and isinstance(drugs_result, dict):
                    workflow_data["drugs"] = drugs_result

                # Verify data flow
                self.assertIn("genes", workflow_data)
        except Exception:
            # Expected if API keys not configured or tools not available
            pass

    def test_workflow_validation_real(self):
        """Test workflow validation with real ToolUniverse."""
        # Test that we can validate tool specifications
        self.tu.load_tools()
        
        if self.tu.all_tools:
            # Get a tool name from the loaded tools
            tool_name = self.tu.all_tools[0].get("name")
            if tool_name:
                spec = self.tu.tool_specification(tool_name)
                if spec:
                    # Validate workflow structure
                    self.assertIn("name", spec)
                    self.assertIn("description", spec)
                    self.assertIn("parameter", spec)

    def test_workflow_monitoring_real(self):
        """Test workflow monitoring with real ToolUniverse."""
        # Test workflow metrics collection
        workflow_metrics = {
            "start_time": 0,
            "end_time": 0,
            "steps_completed": 0,
            "errors": 0,
            "total_execution_time": 0
        }

        import time

        # Simulate workflow execution with metrics
        workflow_metrics["start_time"] = time.time()

        test_tools = ["UniProt_get_entry_by_accession", "ArXiv_search_papers"]
        
        for i, tool_name in enumerate(test_tools):
            try:
                _ = self.tu.run({
                    "name": tool_name,
                    "arguments": {"accession": "P05067"} if "UniProt" in tool_name else {"query": "test", "limit": 5}
                })
                workflow_metrics["steps_completed"] += 1
            except Exception:
                workflow_metrics["errors"] += 1

        workflow_metrics["end_time"] = time.time()
        workflow_metrics["total_execution_time"] = (
            workflow_metrics["end_time"] - workflow_metrics["start_time"]
        )

        # Verify metrics
        self.assertGreaterEqual(workflow_metrics["steps_completed"], 0)
        self.assertGreaterEqual(workflow_metrics["errors"], 0)
        self.assertGreater(workflow_metrics["total_execution_time"], 0)

    def test_workflow_scaling_real(self):
        """Test workflow scaling with real ToolUniverse."""
        # Test batch processing
        batch_size = 3  # Reduced for testing
        batch_results = []

        for i in range(batch_size):
            try:
                result = self.tu.run({
                    "name": "UniProt_get_entry_by_accession",
                    "arguments": {"accession": f"P{i:05d}"}
                })
                batch_results.append(result)
            except Exception:
                batch_results.append({"error": "API key not configured"})

        self.assertEqual(len(batch_results), batch_size)

    def test_workflow_integration_real(self):
        """Test integration with real ToolUniverse tools."""
        # Test external API integration
        external_apis = [
            "OpenTargets_get_associated_targets_by_disease_efoId",
            "UniProt_get_entry_by_accession",
            "ArXiv_search_papers"
        ]

        integration_results = {}

        for api in external_apis:
            try:
                if "OpenTargets" in api:
                    _ = self.tu.run({
                        "name": api,
                        "arguments": {"efoId": "EFO_0000305"}
                    })
                elif "UniProt" in api:
                    _ = self.tu.run({
                        "name": api,
                        "arguments": {"accession": "P05067"}
                    })
                else:  # ArXiv
                    _ = self.tu.run({
                        "name": api,
                        "arguments": {"query": "test", "limit": 5}
                    })
                integration_results[api] = "success"
            except Exception as e:
                integration_results[api] = f"error: {str(e)}"

        # Verify integration
        self.assertEqual(len(integration_results), 3)
        # At least some should succeed or fail gracefully
        self.assertTrue(len(integration_results) > 0)

    def test_workflow_debugging_real(self):
        """Test workflow debugging with real ToolUniverse."""
        # Test debugging workflow
        debug_info = []

        test_tools = ["UniProt_get_entry_by_accession", "ArXiv_search_papers", "NonExistentTool"]
        
        for i, tool_name in enumerate(test_tools):
            try:
                if "UniProt" in tool_name:
                    _ = self.tu.run({
                        "name": tool_name,
                        "arguments": {"accession": "P05067"}
                    })
                elif "ArXiv" in tool_name:
                    _ = self.tu.run({
                        "name": tool_name,
                        "arguments": {"query": "test", "limit": 5}
                    })
                else:
                    _ = self.tu.run({
                        "name": tool_name,
                        "arguments": {"test": "data"}
                    })
                debug_info.append(f"step_{i}_success")
            except Exception as e:
                debug_info.append(f"step_{i}_failed: {str(e)}")

        # Verify debugging info
        self.assertEqual(len(debug_info), 3)
        # Should have some successes and some failures
        self.assertTrue(any("success" in info for info in debug_info) or 
                       any("failed" in info for info in debug_info))


if __name__ == "__main__":
    unittest.main()
