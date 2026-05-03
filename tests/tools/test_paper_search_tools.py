#!/usr/bin/env python3
"""
Test Paper Search Tools

This test script validates the functionality of all paper search tools
in ToolUniverse, ensuring they return properly formatted results.
"""

import sys
import os
import unittest
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tooluniverse import ToolUniverse


@pytest.mark.integration
class TestPaperSearchTools(unittest.TestCase):
    """Test cases for paper search tools"""

    @classmethod
    def setUpClass(cls):
        """Set up test class"""
        cls.tu = ToolUniverse()
        cls.tu.load_tools(
            tool_type=[
                "semantic_scholar",
                "EuropePMC",
                "OpenAlex",
                "arxiv",
                "pubmed",
                "crossref",
                "biorxiv",
                "medrxiv",
                "hal",
                "doaj",
                "dblp",
                "pmc",
            ]
        )
        cls.test_query = "machine learning"

    @classmethod
    def tearDownClass(cls):
        """Clean up test class"""
        if hasattr(cls, "tu") and cls.tu:
            cls.tu.close()

    def test_arxiv_tool(self):
        """Test ArXiv tool"""
        function_call = {
            "name": "ArXiv_search_papers",
            "arguments": {
                "query": self.test_query,
                "limit": 1,
                "sort_by": "relevance",
                "sort_order": "descending",
            },
        }
        result = self.tu.run_one_function(function_call)

        self.assertIsInstance(result, list)
        if result:
            paper = result[0]
            self.assertIn("title", paper)
            self.assertIn("abstract", paper)
            self.assertIn("authors", paper)
            self.assertIn("url", paper)

    def test_europe_pmc_tool(self):
        """Test Europe PMC tool"""
        function_call = {
            "name": "EuropePMC_search_articles",
            "arguments": {
                "query": self.test_query,
                "limit": 1,
                "enrich_missing_abstract": True,
            },
        }
        result = self.tu.run_one_function(function_call)

        self.assertIsInstance(result, list)
        if result:
            paper = result[0]
            if isinstance(paper, dict) and paper.get("error"):
                print(f"Europe PMC API error (skipping): {paper.get('error')}")
                return
            self.assertIn("title", paper)
            self.assertIn("abstract", paper)
            self.assertIn("authors", paper)
            self.assertIn("journal", paper)
            self.assertIn("data_quality", paper)
            self.assertIn("doi_url", paper)
            self.assertIn("fulltext_xml_url", paper)

    def test_openalex_tool(self):
        """Test OpenAlex tool"""
        function_call = {
            "name": "openalex_literature_search",
            "arguments": {
                "search_keywords": self.test_query,
                "max_results": 1,
                "year_from": 2020,
                "year_to": 2024,
                "open_access": True,
            },
        }
        result = self.tu.run_one_function(function_call)

        self.assertIsInstance(result, list)
        if result:
            paper = result[0]
            self.assertIn("title", paper)
            self.assertIn("abstract", paper)
            self.assertIn("authors", paper)
            self.assertIn("venue", paper)
            self.assertIn("data_quality", paper)

    def test_crossref_tool(self):
        """Test Crossref tool"""
        function_call = {
            "name": "Crossref_search_works",
            "arguments": {
                "query": self.test_query,
                "limit": 1,
                "filter": "type:journal-article",
            },
        }
        result = self.tu.run_one_function(function_call)

        # CrossrefRESTTool wraps its response in {"status": "success", "data": [...]}
        if isinstance(result, dict) and "data" in result:
            result = result["data"]

        self.assertIsInstance(result, list)

    def test_pubmed_tool(self):
        """Test PubMed tool"""
        function_call = {
            "name": "PubMed_search_articles",
            "arguments": {
                "query": self.test_query,
                "limit": 1,
                "include_abstract": True,
            },
        }
        result = self.tu.run_one_function(function_call)

        # Handle API errors gracefully in test environment
        if isinstance(result, dict) and "error" in result:
            print(f"PubMed API error (skipping): {result['error']}")
            return  # Skip test if API is not available

        self.assertIsInstance(result, list)
        if result:
            paper = result[0]
            if isinstance(paper, dict) and paper.get("error"):
                print(f"PubMed API error (skipping): {paper.get('error')}")
                return
            self.assertIsInstance(paper, dict)
            self.assertIn("pmid", paper)
            self.assertIn("title", paper)
            self.assertIn("authors", paper)
            self.assertIn("journal", paper)
            self.assertIn("url", paper)
            self.assertIn("doi_url", paper)
            self.assertIn("pmc_url", paper)
            self.assertIn("abstract", paper)

    def test_biorxiv_tool(self):
        """Test BioRxiv tool - now tests direct DOI retrieval"""
        # Note: BioRxiv_search_preprints has been removed (API doesn't support search)
        # Use EuropePMC_search_articles with 'SRC:PPR' for searching preprints
        # This test now validates BioRxiv_get_preprint for direct DOI retrieval
        function_call = {
            "name": "BioRxiv_get_preprint",
            "arguments": {"doi": "2023.12.01.569554"},  # Known valid DOI
        }
        result = self.tu.run_one_function(function_call)

        # Result should be a dict with status and data
        self.assertIsInstance(result, dict)
        if result.get("status") == "success":
            data = result.get("data", {})
            self.assertIn("title", data)
            self.assertIn("abstract", data)
            self.assertIn("authors", data)
            self.assertIn("doi", data)
            self.assertIn("url", data)
            self.assertIn("pdf_url", data)

    def test_medrxiv_tool(self):
        """Test MedRxiv tool - uses same BioRxiv API with different server"""
        # Note: MedRxiv uses the same tool as BioRxiv with server='medrxiv'
        # For searching, use EuropePMC_search_articles with 'SRC:PPR' filter
        function_call = {
            "name": "BioRxiv_get_preprint",
            "arguments": {
                "doi": "2021.04.29.21256344",  # Known valid medRxiv DOI
                "server": "medrxiv",
            },
        }
        result = self.tu.run_one_function(function_call)

        self.assertIsInstance(result, dict)
        if result.get("status") == "success":
            data = result.get("data", {})
            self.assertIn("title", data)
            self.assertIn("abstract", data)
            self.assertIn("authors", data)
            self.assertIn("server", data)
            self.assertEqual(data["server"], "medrxiv")

    def test_doaj_tool(self):
        """Test DOAJ tool"""
        function_call = {
            "name": "DOAJ_search_articles",
            "arguments": {
                "query": self.test_query,
                "max_results": 1,
                "type": "articles",
            },
        }
        result = self.tu.run_one_function(function_call)

        self.assertIsInstance(result, list)
        if result:
            paper = result[0]
            self.assertIn("title", paper)
            self.assertIn("authors", paper)
            self.assertIn("data_quality", paper)

    def test_dblp_tool(self):
        """Test DBLP tool"""
        function_call = {
            "name": "DBLP_search_publications",
            "arguments": {"query": self.test_query, "limit": 1},
        }
        result = self.tu.run_one_function(function_call)

        if isinstance(result, dict) and "error" in result:
            pytest.skip(f"DBLP API unavailable: {result['error']}")
        self.assertIsInstance(result, list)
        if result:
            paper = result[0]
            self.assertIn("title", paper)
            self.assertIn("authors", paper)
            self.assertIn("data_quality", paper)

    def test_data_quality_fields(self):
        """Test that data_quality fields are properly structured"""
        function_call = {
            "name": "ArXiv_search_papers",
            "arguments": {
                "query": self.test_query,
                "limit": 1,
                "sort_by": "relevance",
                "sort_order": "descending",
            },
        }
        result = self.tu.run_one_function(function_call)

        if result:
            paper = result[0]
            if "data_quality" in paper:
                quality = paper["data_quality"]
                expected_fields = [
                    "has_abstract",
                    "has_authors",
                    "has_journal",
                    "has_year",
                    "has_doi",
                    "has_citations",
                    "has_keywords",
                    "has_url",
                ]
                for field in expected_fields:
                    self.assertIn(field, quality)
                    self.assertIsInstance(quality[field], bool)


if __name__ == "__main__":
    unittest.main()
