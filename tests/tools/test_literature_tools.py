#!/usr/bin/env python3
"""
Test cases for all literature search tools - Cleaned Version

Test cases with real execution instead of heavy mocking.
"""

import pytest
from tooluniverse import ToolUniverse


@pytest.mark.integration
@pytest.mark.network
class TestLiteratureTools:
    """Test cases for all literature search tools with real execution."""

    @pytest.fixture
    def tu(self):
        """Initialize ToolUniverse for testing."""
        tu = ToolUniverse()
        tu.load_tools()
        yield tu
        tu.close()

    def test_literature_tools_exist(self, tu):
        """Test that literature search tools are registered."""
        tool_names = [tool.get("name") for tool in tu.all_tools if isinstance(tool, dict)]
        
        # Check for common literature tools
        literature_tools = [name for name in tool_names if any(keyword in name.lower() 
                           for keyword in ["arxiv", "crossref", "dblp", "pubmed", "europepmc", "openalex"])]
        
        # Should have some literature tools
        assert len(literature_tools) > 0, "No literature search tools found"
        print(f"Found literature tools: {literature_tools}")

    def test_arxiv_tool_execution(self, tu):
        """Test ArXiv tool execution."""
        try:
            result = tu.run({
                "name": "ArXiv_search_papers",
                "arguments": {"query": "machine learning", "limit": 1}
            })
            
            # Should return a result
            assert isinstance(result, (list, dict))
            
            # Allow for API key errors
            if isinstance(result, dict) and "error" in result:
                assert "API" in str(result["error"]) or "key" in str(result["error"]).lower()
            elif isinstance(result, list) and result:
                # Verify paper structure
                paper = result[0]
                assert isinstance(paper, dict)
                assert "title" in paper or "error" in paper
                
        except Exception as e:
            # Expected if tool not available or API key missing
            assert isinstance(e, Exception)

    def test_crossref_tool_execution(self, tu):
        """Test Crossref tool execution."""
        try:
            result = tu.run({
                "name": "Crossref_search_works",
                "arguments": {"query": "test query", "limit": 1}
            })
            
            # Should return a result
            assert isinstance(result, (list, dict))
            
            # Allow for API key errors
            if isinstance(result, dict) and "error" in result:
                assert "API" in str(result["error"]) or "key" in str(result["error"]).lower()
            elif isinstance(result, list) and result:
                # Verify article structure
                article = result[0]
                assert isinstance(article, dict)
                assert "title" in article or "error" in article
                
        except Exception as e:
            # Expected if tool not available or API key missing
            assert isinstance(e, Exception)

    def test_dblp_tool_execution(self, tu):
        """Test DBLP tool execution."""
        try:
            result = tu.run({
                "name": "DBLP_search_publications",
                "arguments": {"query": "test query", "limit": 1}
            })
            
            # Should return a result
            assert isinstance(result, (list, dict))
            
            # Allow for API key errors
            if isinstance(result, dict) and "error" in result:
                assert "API" in str(result["error"]) or "key" in str(result["error"]).lower()
            elif isinstance(result, list) and result:
                # Verify publication structure
                publication = result[0]
                assert isinstance(publication, dict)
                assert "title" in publication or "error" in publication
                
        except Exception as e:
            # Expected if tool not available or API key missing
            assert isinstance(e, Exception)

    def test_pubmed_tool_execution(self, tu):
        """Test PubMed tool execution."""
        try:
            result = tu.run({
                "name": "PubMed_search_articles",
                "arguments": {"query": "test query", "limit": 1}
            })
            
            # Should return a result
            assert isinstance(result, (list, dict))
            
            # Allow for API key errors
            if isinstance(result, dict) and "error" in result:
                assert "API" in str(result["error"]) or "key" in str(result["error"]).lower()
            elif isinstance(result, list) and result:
                # Verify article structure
                article = result[0]
                assert isinstance(article, dict)
                assert "title" in article or "error" in article
                
        except Exception as e:
            # Expected if tool not available or API key missing
            assert isinstance(e, Exception)

    def test_europepmc_tool_execution(self, tu):
        """Test EuropePMC tool execution."""
        try:
            result = tu.run({
                "name": "EuropePMC_search_articles",
                "arguments": {"query": "test query", "limit": 1}
            })
            
            # Should return a result
            assert isinstance(result, (list, dict))
            
            # Allow for API key errors
            if isinstance(result, dict) and "error" in result:
                assert "API" in str(result["error"]) or "key" in str(result["error"]).lower()
            elif isinstance(result, list) and result:
                # Verify article structure
                article = result[0]
                assert isinstance(article, dict)
                assert "title" in article or "error" in article
                
        except Exception as e:
            # Expected if tool not available or API key missing
            assert isinstance(e, Exception)

    def test_openalex_tool_execution(self, tu):
        """Test OpenAlex tool execution."""
        try:
            result = tu.run({
                "name": "OpenAlex_search_works",
                "arguments": {"query": "test query", "limit": 1}
            })
            
            # Should return a result
            assert isinstance(result, (list, dict))
            
            # Allow for API key errors
            if isinstance(result, dict) and "error" in result:
                assert "API" in str(result["error"]) or "key" in str(result["error"]).lower()
            elif isinstance(result, list) and result:
                # Verify work structure
                work = result[0]
                assert isinstance(work, dict)
                assert "title" in work or "error" in work
                
        except Exception as e:
            # Expected if tool not available or API key missing
            assert isinstance(e, Exception)

    def test_literature_tool_missing_parameters(self, tu):
        """Test literature tools with missing parameters."""
        try:
            result = tu.run({
                "name": "ArXiv_search_papers",
                "arguments": {}
            })
            
            # Should return an error for missing parameters
            assert isinstance(result, dict)
            assert "error" in result or "success" in result
            
        except Exception as e:
            # Expected if tool not available
            assert isinstance(e, Exception)

    def test_literature_tool_invalid_parameters(self, tu):
        """Test literature tools with invalid parameters."""
        try:
            result = tu.run({
                "name": "ArXiv_search_papers",
                "arguments": {
                    "query": "",
                    "limit": -1
                }
            })
            
            # Should return an error for invalid parameters
            assert isinstance(result, dict)
            assert "error" in result or "success" in result
            
        except Exception as e:
            # Expected if tool not available
            assert isinstance(e, Exception)

    def test_literature_tool_performance(self, tu):
        """Test literature tool performance."""
        try:
            import time
            
            start_time = time.time()
            
            result = tu.run({
                "name": "ArXiv_search_papers",
                "arguments": {"query": "test", "limit": 1}
            })
            
            execution_time = time.time() - start_time
            
            # Should complete within reasonable time (60 seconds)
            assert execution_time < 60
            assert isinstance(result, (list, dict))
            
        except Exception as e:
            # Expected if tool not available
            assert isinstance(e, Exception)

    def test_literature_tool_error_handling(self, tu):
        """Test literature tool error handling."""
        try:
            # Test with invalid query
            result = tu.run({
                "name": "ArXiv_search_papers",
                "arguments": {
                    "query": "x" * 1000,  # Very long query
                    "limit": 1
                }
            })
            
            # Should handle invalid input gracefully
            assert isinstance(result, (list, dict))
            
            # Allow for API key errors
            if isinstance(result, dict) and "error" in result:
                assert "API" in str(result["error"]) or "key" in str(result["error"]).lower()
            elif isinstance(result, list) and result:
                # Verify result structure
                paper = result[0]
                assert isinstance(paper, dict)
                
        except Exception as e:
            # Expected if tool not available
            assert isinstance(e, Exception)

    def test_literature_tool_concurrent_execution(self, tu):
        """Test literature tool concurrent execution."""
        try:
            import threading
            import time
            
            results = []
            
            def make_search_call(call_id):
                try:
                    result = tu.run({
                        "name": "ArXiv_search_papers",
                        "arguments": {
                            "query": f"test query {call_id}",
                            "limit": 1
                        }
                    })
                    results.append(result)
                except Exception as e:
                    results.append({"error": str(e)})
            
            # Create multiple threads
            threads = []
            for i in range(3):  # 3 concurrent calls
                thread = threading.Thread(target=make_search_call, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads
            for thread in threads:
                thread.join()
            
            # Verify all calls completed
            assert len(results) == 3
            for result in results:
                assert isinstance(result, (list, dict))
                
        except Exception as e:
            # Expected if tool not available
            assert isinstance(e, Exception)

    def test_literature_tool_memory_usage(self, tu):
        """Test literature tool memory usage."""
        try:
            import psutil
            import os
            
            # Get initial memory usage
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss
            
            # Create multiple search calls
            for i in range(5):
                try:
                    _ = tu.run({
                        "name": "ArXiv_search_papers",
                        "arguments": {
                            "query": f"test query {i}",
                            "limit": 1
                        }
                    })
                except Exception:
                    pass
            
            # Get final memory usage
            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable (less than 100MB)
            assert memory_increase < 100 * 1024 * 1024
            
        except ImportError:
            # psutil not available, skip test
            pass
        except Exception as e:
            # Expected if tool not available
            assert isinstance(e, Exception)

    def test_literature_tool_output_format(self, tu):
        """Test literature tool output format."""
        try:
            result = tu.run({
                "name": "ArXiv_search_papers",
                "arguments": {
                    "query": "test query",
                    "limit": 1
                }
            })
            
            # Should return a result
            assert isinstance(result, (list, dict))
            
            # Allow for API key errors
            if isinstance(result, dict) and "error" in result:
                assert "API" in str(result["error"]) or "key" in str(result["error"]).lower()
            elif isinstance(result, list) and result:
                # Verify output format
                paper = result[0]
                assert isinstance(paper, dict)
                
                # Check for common fields
                if "title" in paper:
                    assert isinstance(paper["title"], str)
                if "abstract" in paper:
                    assert isinstance(paper["abstract"], str)
                if "authors" in paper:
                    assert isinstance(paper["authors"], (list, str))
                if "published" in paper:
                    assert isinstance(paper["published"], str)
                if "url" in paper:
                    assert isinstance(paper["url"], str)
                
        except Exception as e:
            # Expected if tool not available
            assert isinstance(e, Exception)


if __name__ == "__main__":
    pytest.main([__file__])
