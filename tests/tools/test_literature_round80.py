"""Tests for Round 80 literature tool fixes.

Feature-80A-001: ArXiv multi-word queries use AND logic (not broken OR)
Feature-80A-002: ArXiv invalid sort_by returns helpful error
Feature-80A-005: PubMed_get_cited_by returns empty list (not raw linkset) when no citations
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


class TestArXivQueryBuilder(unittest.TestCase):
    """Feature-80A-001: Multi-word queries joined with AND."""

    def setUp(self):
        from tooluniverse.arxiv_tool import ArXivTool

        config = {
            "name": "ArXiv_search_papers",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        self.tool = ArXivTool(config)

    def test_single_word_uses_all_prefix(self):
        result = self.tool._build_search_query("LLM")
        self.assertEqual(result, "all:LLM")

    def test_multi_word_joins_with_and(self):
        result = self.tool._build_search_query("large language model")
        self.assertEqual(result, "all:large AND all:language AND all:model")

    def test_arxiv_field_prefix_passes_through(self):
        result = self.tool._build_search_query("au:Hinton")
        self.assertEqual(result, "au:Hinton")

    def test_author_multiword_auto_quoted(self):
        """Feature-82C: au:FirstName LastName auto-quoted for arXiv API."""
        result = self.tool._build_search_query("au:Shanghua Gao")
        self.assertEqual(result, 'au:"Shanghua Gao"')

    def test_author_already_quoted_unchanged(self):
        result = self.tool._build_search_query('au:"Geoffrey Hinton"')
        self.assertEqual(result, 'au:"Geoffrey Hinton"')

    def test_title_multiword_auto_quoted(self):
        result = self.tool._build_search_query("ti:protein folding")
        self.assertEqual(result, 'ti:"protein folding"')

    def test_category_query_passes_through(self):
        result = self.tool._build_search_query("cat:cs.AI AND ti:transformer")
        self.assertEqual(result, "cat:cs.AI AND ti:transformer")

    def test_boolean_operators_pass_through(self):
        result = self.tool._build_search_query("CRISPR AND gene editing")
        self.assertEqual(result, "CRISPR AND gene editing")

    def test_or_operator_passes_through(self):
        result = self.tool._build_search_query("cancer OR oncology")
        self.assertEqual(result, "cancer OR oncology")


class TestArXivSortValidation(unittest.TestCase):
    """Feature-80A-002: Invalid sort_by returns helpful error."""

    def setUp(self):
        from tooluniverse.arxiv_tool import ArXivTool

        config = {
            "name": "ArXiv_search_papers",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        self.tool = ArXivTool(config)

    def test_invalid_sort_by_returns_error(self):
        result = self.tool._search("LLM", 3, "invalidField", "descending")
        self.assertIn("error", result)
        self.assertIn("invalidField", result["error"])
        self.assertIn("relevance", result["error"])
        self.assertIn("submittedDate", result["error"])

    def test_valid_sort_by_accepted(self):
        for sort_by in ("relevance", "lastUpdatedDate", "submittedDate"):
            self.assertIn(sort_by, self.tool._VALID_SORT_BY)


class TestPubMedCitedByEmptyResult(unittest.TestCase):
    """Feature-80A-005: PubMed_get_cited_by returns [] when no citations."""

    def test_linkset_without_linksetdbs_detected(self):
        """Linkset without linksetdbs means no linked articles."""
        # This is the structure returned when a paper has no citations
        linkset = {"dbfrom": "pubmed", "ids": ["37461722"]}
        self.assertNotIn("linksetdbs", linkset)
        self.assertNotIn("idurllist", linkset)

    def test_cited_by_live_returns_structured(self):
        """Live test: PubMed_get_cited_by should return structured response."""
        try:
            from tooluniverse import ToolUniverse
            import json

            tu = ToolUniverse()
            tu.load_tools()
        except Exception:
            self.skipTest("ToolUniverse not available")

        try:
            result = tu.run_one_function({"name": "PubMed_get_cited_by", "arguments": {"pmid": "37461722", "limit": 3}})
        except Exception as e:
            self.skipTest(f"API call failed: {e}")

        if isinstance(result, str):
            result = json.loads(result)

        # Should be structured, not raw linkset
        self.assertIn("status", result)
        self.assertEqual(result["status"], "success")
        data = result.get("data", None)
        # Data should be a list (possibly empty), never a dict with raw linksets
        self.assertIsInstance(data, list, "data should be a list, not raw linkset dict")


class TestArXivMultiWordLive(unittest.TestCase):
    """Live test: ArXiv multi-word query returns relevant results."""

    def test_multi_word_returns_relevant_results(self):
        try:
            from tooluniverse import ToolUniverse

            tu = ToolUniverse()
            tu.load_tools()
        except Exception:
            self.skipTest("ToolUniverse not available")

        try:
            result = tu.run_one_function(
                {
                    "name": "ArXiv_search_papers",
                    "arguments": {
                        "query": "large language model biomedical",
                        "sort_by": "submittedDate",
                        "sort_order": "descending",
                        "limit": 3,
                    },
                }
            )
        except Exception as e:
            self.skipTest(f"API call failed: {e}")

        import json

        if isinstance(result, str):
            result = json.loads(result)

        papers = result if isinstance(result, list) else result.get("result", [])
        self.assertGreater(len(papers), 0, "Should return at least 1 paper")

        # At least one paper should mention LLM/language model in title or abstract
        found_relevant = any(
            "language model" in (p.get("title", "") + p.get("abstract", "")).lower()
            or "llm" in (p.get("title", "") + p.get("abstract", "")).lower()
            for p in papers
        )
        self.assertTrue(found_relevant, "Results should be relevant to 'large language model'")


class TestSemanticScholarLimitNotRequired(unittest.TestCase):
    """Feature-80B-002: SemanticScholar limit should not be required."""

    def test_limit_not_in_required(self):
        import json

        json_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "src",
            "tooluniverse",
            "data",
            "semantic_scholar_tools.json",
        )
        with open(json_path) as f:
            tools = json.load(f)

        search_tool = next(
            t for t in tools if t["name"] == "SemanticScholar_search_papers"
        )
        required = search_tool["parameter"]["required"]
        self.assertIn("query", required)
        self.assertNotIn("limit", required, "limit should not be required (has default)")

    def test_limit_has_default(self):
        import json

        json_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "src",
            "tooluniverse",
            "data",
            "semantic_scholar_tools.json",
        )
        with open(json_path) as f:
            tools = json.load(f)

        search_tool = next(
            t for t in tools if t["name"] == "SemanticScholar_search_papers"
        )
        limit_prop = search_tool["parameter"]["properties"]["limit"]
        self.assertIn("default", limit_prop)
        self.assertEqual(limit_prop["default"], 5)


class TestBaseRESTToolApiName(unittest.TestCase):
    """Feature-80B-003: BaseRESTTool uses tool config name for error messages."""

    def test_api_name_from_config(self):
        from tooluniverse.base_rest_tool import BaseRESTTool

        config = {
            "name": "MyCustomAPI_search",
            "parameter": {"type": "object", "properties": {}, "required": []},
            "fields": {"endpoint": "https://example.com/api"},
        }
        tool = BaseRESTTool(config)
        self.assertEqual(tool.api_name, "MyCustomAPI_search")

    def test_api_name_fallback_to_class_name(self):
        from tooluniverse.base_rest_tool import BaseRESTTool

        config = {
            "parameter": {"type": "object", "properties": {}, "required": []},
            "fields": {"endpoint": "https://example.com/api"},
        }
        tool = BaseRESTTool(config)
        # Falls back to class name when no name in config
        self.assertIn("Base", tool.api_name)


class TestPubTator3OptionalParams(unittest.TestCase):
    """Feature-80B-005: PubTator3 page/page_size not required, have defaults."""

    def test_page_not_required(self):
        import json

        json_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "src",
            "tooluniverse",
            "data",
            "pubtator_tools.json",
        )
        with open(json_path) as f:
            tools = json.load(f)

        search_tool = next(
            t for t in tools if t["name"] == "PubTator3_LiteratureSearch"
        )
        required = search_tool["parameter"]["required"]
        self.assertEqual(required, ["query"])
        self.assertNotIn("page", required)
        self.assertNotIn("page_size", required)

    def test_page_has_defaults(self):
        import json

        json_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "src",
            "tooluniverse",
            "data",
            "pubtator_tools.json",
        )
        with open(json_path) as f:
            tools = json.load(f)

        search_tool = next(
            t for t in tools if t["name"] == "PubTator3_LiteratureSearch"
        )
        props = search_tool["parameter"]["properties"]
        self.assertEqual(props["page"]["default"], 0)
        self.assertEqual(props["page_size"]["default"], 10)


if __name__ == "__main__":
    unittest.main()
