#!/usr/bin/env python3
"""
Performance benchmarks for ToolUniverse direct import functionality

Note: These tests are marked as @pytest.mark.manual because they:
1. Depend on external APIs (unstable)
2. Have loose assertions (15-30 second timeouts)
3. Don't provide regression detection
4. Should be run manually for performance analysis

To run manually: pytest tests/examples/test_performance_benchmarks.py -v
"""

import sys
import unittest
import time
import statistics
from pathlib import Path
import pytest

# `helpers` also comes from pytest.ini's `pythonpath`, but that does not apply
# when this file is run as a bare script via the __main__ block below.
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.threads import join_all
from tooluniverse.tools import (
    OpenTargets_get_disease_id_description_by_name,
    ChEMBL_search_similar_molecules,
    HPA_search_genes_by_query,
    ArXiv_search_papers,
    get_sequence_by_pdb_id,
    search_clinical_trials
)


@pytest.mark.slow
@pytest.mark.manual
class TestPerformanceBenchmarks(unittest.TestCase):
    """Test performance benchmarks for direct import functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.benchmark_results = {}
    
    def benchmark_tool_performance(self, tool_func, params, iterations=3):
        """Benchmark a single tool's performance."""
        execution_times = []
        
        for i in range(iterations):
            start_time = time.time()
            try:
                result = tool_func(**params)
                end_time = time.time()
                execution_time = end_time - start_time
                execution_times.append(execution_time)
            except Exception as e:
                # If tool fails, record a high execution time
                end_time = time.time()
                execution_time = end_time - start_time
                execution_times.append(execution_time)
        
        return {
            'min_time': min(execution_times),
            'max_time': max(execution_times),
            'avg_time': statistics.mean(execution_times),
            'median_time': statistics.median(execution_times),
            'success_rate': sum(1 for t in execution_times if t < 10) / len(execution_times)
        }
    
    def test_open_targets_performance(self):
        """Benchmark OpenTargets tools performance."""
        print("\n=== OpenTargets Performance Benchmark ===")
        
        # Test disease search
        disease_benchmark = self.benchmark_tool_performance(
            OpenTargets_get_disease_id_description_by_name,
            {"disease_name": "diabetes"},
            iterations=3
        )
        
        self.benchmark_results['open_targets_disease'] = disease_benchmark
        
        print(f"Disease search - Avg: {disease_benchmark['avg_time']:.2f}s, "
              f"Min: {disease_benchmark['min_time']:.2f}s, "
              f"Max: {disease_benchmark['max_time']:.2f}s")
        
        # Performance assertions
        self.assertLess(disease_benchmark['avg_time'], 15, "OpenTargets disease search too slow")
        self.assertGreater(disease_benchmark['success_rate'], 0, "OpenTargets disease search failed")
    
    def test_chembl_performance(self):
        """Benchmark ChEMBL tools performance."""
        print("\n=== ChEMBL Performance Benchmark ===")
        
        # Test compound search
        compound_benchmark = self.benchmark_tool_performance(
            ChEMBL_search_similar_molecules,
            {"query": "aspirin", "max_results": 5},
            iterations=3
        )
        
        self.benchmark_results['chembl_compounds'] = compound_benchmark
        
        print(f"Compound search - Avg: {compound_benchmark['avg_time']:.2f}s, "
              f"Min: {compound_benchmark['min_time']:.2f}s, "
              f"Max: {compound_benchmark['max_time']:.2f}s")
        
        # Performance assertions
        self.assertLess(compound_benchmark['avg_time'], 20, "ChEMBL compound search too slow")
        self.assertGreater(compound_benchmark['success_rate'], 0, "ChEMBL compound search failed")
    
    def test_hpa_performance(self):
        """Benchmark HPA tools performance."""
        print("\n=== HPA Performance Benchmark ===")
        
        # Test gene search
        gene_benchmark = self.benchmark_tool_performance(
            HPA_search_genes_by_query,
            {"query": "BRCA1", "limit": 5},
            iterations=3
        )
        
        self.benchmark_results['hpa_genes'] = gene_benchmark
        
        print(f"Gene search - Avg: {gene_benchmark['avg_time']:.2f}s, "
              f"Min: {gene_benchmark['min_time']:.2f}s, "
              f"Max: {gene_benchmark['max_time']:.2f}s")
        
        # Performance assertions
        self.assertLess(gene_benchmark['avg_time'], 15, "HPA gene search too slow")
        self.assertGreater(gene_benchmark['success_rate'], 0, "HPA gene search failed")
    
    def test_literature_performance(self):
        """Benchmark literature search tools performance."""
        print("\n=== Literature Search Performance Benchmark ===")
        
        # Test ArXiv search
        arxiv_benchmark = self.benchmark_tool_performance(
            ArXiv_search_papers,
            {"query": "machine learning", "limit": 5},
            iterations=3
        )
        
        self.benchmark_results['arxiv_search'] = arxiv_benchmark
        
        print(f"ArXiv search - Avg: {arxiv_benchmark['avg_time']:.2f}s, "
              f"Min: {arxiv_benchmark['min_time']:.2f}s, "
              f"Max: {arxiv_benchmark['max_time']:.2f}s")
        
        # Performance assertions
        self.assertLess(arxiv_benchmark['avg_time'], 10, "ArXiv search too slow")
        self.assertGreater(arxiv_benchmark['success_rate'], 0, "ArXiv search failed")
    
    def test_pdb_performance(self):
        """Benchmark PDB tools performance."""
        print("\n=== PDB Performance Benchmark ===")
        
        # Test sequence retrieval
        sequence_benchmark = self.benchmark_tool_performance(
            get_sequence_by_pdb_id,
            {"pdb_id": "1CRN"},
            iterations=3
        )
        
        self.benchmark_results['pdb_sequence'] = sequence_benchmark
        
        print(f"Sequence retrieval - Avg: {sequence_benchmark['avg_time']:.2f}s, "
              f"Min: {sequence_benchmark['min_time']:.2f}s, "
              f"Max: {sequence_benchmark['max_time']:.2f}s")
        
        # Performance assertions
        self.assertLess(sequence_benchmark['avg_time'], 10, "PDB sequence retrieval too slow")
        self.assertGreater(sequence_benchmark['success_rate'], 0, "PDB sequence retrieval failed")
    
    def test_clinical_trial_performance(self):
        """Benchmark clinical trial tools performance."""
        print("\n=== Clinical Trial Performance Benchmark ===")
        
        # Test trial search
        trial_benchmark = self.benchmark_tool_performance(
            search_clinical_trials,
            {"condition": "diabetes", "limit": 5},
            iterations=3
        )
        
        self.benchmark_results['clinical_trials'] = trial_benchmark
        
        print(f"Trial search - Avg: {trial_benchmark['avg_time']:.2f}s, "
              f"Min: {trial_benchmark['min_time']:.2f}s, "
              f"Max: {trial_benchmark['max_time']:.2f}s")
        
        # Performance assertions
        self.assertLess(trial_benchmark['avg_time'], 15, "Clinical trial search too slow")
        self.assertGreater(trial_benchmark['success_rate'], 0, "Clinical trial search failed")
    
    def test_overall_performance_summary(self):
        """Generate overall performance summary."""
        print("\n=== Overall Performance Summary ===")
        
        if not self.benchmark_results:
            self.skipTest("No benchmark results available")
        
        total_avg_time = statistics.mean([
            result['avg_time'] for result in self.benchmark_results.values()
        ])
        
        total_success_rate = statistics.mean([
            result['success_rate'] for result in self.benchmark_results.values()
        ])
        
        print(f"Overall average execution time: {total_avg_time:.2f}s")
        print(f"Overall success rate: {total_success_rate:.2%}")
        
        # Performance assertions
        self.assertLess(total_avg_time, 15, "Overall performance too slow")
        self.assertGreater(total_success_rate, 0.5, "Overall success rate too low")
        
        # Print detailed results
        print("\nDetailed Results:")
        for tool_name, results in self.benchmark_results.items():
            print(f"  {tool_name}: {results['avg_time']:.2f}s avg, "
                  f"{results['success_rate']:.2%} success rate")
    
    def test_concurrent_tool_usage(self):
        """Test concurrent usage of multiple tools."""
        print("\n=== Concurrent Tool Usage Test ===")
        
        import threading
        import queue
        
        results_queue = queue.Queue()
        
        def run_tool(tool_func, params, tool_name):
            """Run a tool in a separate thread."""
            start_time = time.time()
            try:
                result = tool_func(**params)
                end_time = time.time()
                results_queue.put({
                    'tool': tool_name,
                    'success': True,
                    'time': end_time - start_time
                })
            except Exception as e:
                end_time = time.time()
                results_queue.put({
                    'tool': tool_name,
                    'success': False,
                    'time': end_time - start_time,
                    'error': str(e)
                })
        
        # Define tools to run concurrently
        concurrent_tools = [
            (OpenTargets_get_disease_id_description_by_name, {"disease_name": "cancer"}, "OpenTargets"),
            (ChEMBL_search_similar_molecules, {"query": "aspirin", "max_results": 3}, "ChEMBL"),
            (HPA_search_genes_by_query, {"query": "TP53", "limit": 3}, "HPA"),
            (ArXiv_search_papers, {"query": "biology", "limit": 3}, "ArXiv"),
            (get_sequence_by_pdb_id, {"pdb_id": "1A8M"}, "PDB")
        ]
        
        # Start all tools concurrently
        threads = []
        for tool_func, params, tool_name in concurrent_tools:
            thread = threading.Thread(
                target=run_tool, args=(tool_func, params, tool_name), name=tool_name
            )
            threads.append(thread)
            thread.start()

        # A silent timeout would drop that thread's entry from results_queue,
        # so the success count below would blame the tools for the wait.
        join_all(threads)

        # Collect results
        concurrent_results = []
        while not results_queue.empty():
            concurrent_results.append(results_queue.get())
        
        print(f"Concurrent execution completed: {len(concurrent_results)} tools")
        
        # Analyze results
        successful_tools = [r for r in concurrent_results if r['success']]
        total_time = max([r['time'] for r in concurrent_results]) if concurrent_results else 0
        
        print(f"Successful tools: {len(successful_tools)}/{len(concurrent_tools)}")
        print(f"Total execution time: {total_time:.2f}s")
        
        # Performance assertions
        self.assertGreater(len(successful_tools), 0, "No tools succeeded in concurrent execution")
        self.assertLess(total_time, 30, "Concurrent execution took too long")


if __name__ == "__main__":
    unittest.main()
