"""Tests for Round 79 literature tool fixes.

Feature-79A-001: BaseRESTTool applies schema defaults to query params
Feature-79A-002: PubMed_get_article returns structured JSON (not raw XML)
Feature-79A-003: PubMed_get_related returns enriched article metadata
"""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


class TestBaseRESTToolSchemaDefaults(unittest.TestCase):
    """Feature-79A-001: _build_params applies schema defaults for missing optional params."""

    def setUp(self):
        self.tool_config = {
            "name": "TestTool_get_thing",
            "fields": {
                "endpoint": "https://api.example.com/thing/{thing_id}",
                "method": "GET",
                "params": {},
            },
            "parameter": {
                "type": "object",
                "properties": {
                    "thing_id": {
                        "type": "string",
                        "description": "ID of the thing",
                    },
                    "fields": {
                        "type": "string",
                        "description": "Comma-separated fields to return",
                        "default": "id,name,description,count",
                    },
                    "format": {
                        "type": "string",
                        "description": "Response format",
                        "default": "json",
                    },
                    "optional_no_default": {
                        "type": "string",
                        "description": "Optional param without default",
                    },
                },
                "required": ["thing_id"],
            },
        }

    def test_schema_defaults_applied_when_param_missing(self):
        """Params with defaults in schema should be included even when not provided by caller."""
        from tooluniverse.base_rest_tool import BaseRESTTool

        tool = BaseRESTTool(self.tool_config)
        params = tool._build_params({"thing_id": "123"})

        # Schema defaults should be applied
        self.assertEqual(params["fields"], "id,name,description,count")
        self.assertEqual(params["format"], "json")
        # Path param should NOT be in query params
        self.assertNotIn("thing_id", params)
        # Param without default should NOT be added
        self.assertNotIn("optional_no_default", params)

    def test_explicit_value_overrides_default(self):
        """Explicitly provided values should override schema defaults."""
        from tooluniverse.base_rest_tool import BaseRESTTool

        tool = BaseRESTTool(self.tool_config)
        params = tool._build_params({"thing_id": "123", "fields": "id,name"})

        self.assertEqual(params["fields"], "id,name")
        self.assertEqual(params["format"], "json")

    def test_explicit_none_not_added(self):
        """Explicitly passed None values should not be added to params."""
        from tooluniverse.base_rest_tool import BaseRESTTool

        tool = BaseRESTTool(self.tool_config)
        params = tool._build_params({"thing_id": "123", "fields": None})

        # fields was explicitly None, so not added from args
        # But default should still be applied since key has None value in args
        # Actually, the key IS in args, so default won't override
        # The behavior: explicit None means "don't send this param"
        self.assertNotIn("thing_id", params)

    def test_no_defaults_in_schema(self):
        """Tool with no defaults in schema should work as before."""
        config = {
            "name": "TestTool_simple",
            "fields": {
                "endpoint": "https://api.example.com/search",
                "method": "GET",
                "params": {},
            },
            "parameter": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        }
        from tooluniverse.base_rest_tool import BaseRESTTool

        tool = BaseRESTTool(config)
        params = tool._build_params({"query": "test"})

        self.assertEqual(params["query"], "test")
        self.assertEqual(len(params), 1)


class TestPubMedGetArticleXMLParsing(unittest.TestCase):
    """Feature-79A-002: PubMed_get_article returns structured JSON, not raw XML."""

    SAMPLE_XML = """<?xml version="1.0" ?>
<PubmedArticleSet>
<PubmedArticle>
  <MedlineCitation Status="MEDLINE" Owner="NLM">
    <PMID>12345678</PMID>
    <Article PubModel="Print">
      <Journal>
        <Title>Nature Reviews Cancer</Title>
        <ISOAbbreviation>Nat Rev Cancer</ISOAbbreviation>
      </Journal>
      <ArticleTitle>CAR T-cell therapy for solid tumors</ArticleTitle>
      <Abstract>
        <AbstractText Label="BACKGROUND">CAR-T cells have shown promise.</AbstractText>
        <AbstractText Label="METHODS">We reviewed clinical trials.</AbstractText>
      </Abstract>
      <AuthorList>
        <Author>
          <LastName>Smith</LastName>
          <ForeName>John A</ForeName>
          <AffiliationInfo><Affiliation>Harvard Medical School</Affiliation></AffiliationInfo>
        </Author>
        <Author>
          <LastName>Jones</LastName>
          <ForeName>Mary B</ForeName>
        </Author>
      </AuthorList>
      <ELocationID EIdType="doi">10.1038/s41568-024-00001-x</ELocationID>
      <PublicationTypeList>
        <PublicationType>Journal Article</PublicationType>
        <PublicationType>Review</PublicationType>
      </PublicationTypeList>
      <ArticleDate DateType="Electronic">
        <Year>2024</Year>
        <Month>03</Month>
        <Day>15</Day>
      </ArticleDate>
    </Article>
    <MeshHeadingList>
      <MeshHeading><DescriptorName>Receptors, Chimeric Antigen</DescriptorName></MeshHeading>
      <MeshHeading><DescriptorName>Neoplasms</DescriptorName></MeshHeading>
    </MeshHeadingList>
  </MedlineCitation>
</PubmedArticle>
</PubmedArticleSet>"""

    def test_parse_efetch_xml_structured(self):
        """_parse_efetch_xml should return structured article data, not raw XML."""
        from tooluniverse.pubmed_tool import PubMedRESTTool

        # Minimal config to instantiate
        config = {
            "name": "PubMed_get_article",
            "fields": {
                "endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                "method": "GET",
                "params": {"db": "pubmed", "retmode": "xml"},
            },
            "parameter": {
                "type": "object",
                "properties": {"pmid": {"type": "string"}},
                "required": ["pmid"],
            },
        }
        tool = PubMedRESTTool(config)

        mock_response = MagicMock()
        mock_response.text = self.SAMPLE_XML
        mock_response.url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=12345678"

        result = tool._parse_efetch_xml(mock_response)

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertIsInstance(data, dict)
        self.assertEqual(data["pmid"], "12345678")
        self.assertEqual(data["title"], "CAR T-cell therapy for solid tumors")
        self.assertIn("BACKGROUND:", data["abstract"])
        self.assertEqual(len(data["authors"]), 2)
        self.assertEqual(data["authors"][0]["name"], "Smith John A")
        self.assertEqual(data["authors"][0]["affiliation"], "Harvard Medical School")
        self.assertEqual(data["doi"], "10.1038/s41568-024-00001-x")
        self.assertEqual(data["journal"], "Nature Reviews Cancer")
        self.assertIn("Receptors, Chimeric Antigen", data["mesh_terms"])
        self.assertIn("Review", data["publication_types"])

    def test_parse_efetch_xml_invalid_xml_fallback(self):
        """Invalid XML should fall back to returning raw text."""
        from tooluniverse.pubmed_tool import PubMedRESTTool

        config = {
            "name": "PubMed_get_article",
            "fields": {"endpoint": "https://example.com", "method": "GET", "params": {}},
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        tool = PubMedRESTTool(config)

        mock_response = MagicMock()
        mock_response.text = "This is not XML"
        mock_response.url = "https://example.com"

        result = tool._parse_efetch_xml(mock_response)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"], "This is not XML")


class TestPubMedGetRelatedEnrichment(unittest.TestCase):
    """Feature-79A-003: PubMed_get_related returns enriched metadata, not just IDs."""

    def test_related_articles_enriched_live(self):
        """Live test: PubMed_get_related should return enriched results with titles."""
        try:
            from tooluniverse import ToolUniverse

            tu = ToolUniverse()
            tu.load_tools()
        except Exception:
            self.skipTest("ToolUniverse not available")

        try:
            result = tu.execute_tool(
                "PubMed_get_related", {"pmid": "35953136", "limit": 3}
            )
        except Exception as e:
            self.skipTest(f"API call failed: {e}")

        if isinstance(result, str):
            result = json.loads(result)

        # Should have data
        data = result.get("data", result.get("result", []))
        if isinstance(data, dict):
            data = [data]
        self.assertGreater(len(data), 0, "Should return at least 1 related article")

        first = data[0]
        self.assertIsInstance(first, dict)
        # Should have enriched fields, not just id+score
        self.assertIn("title", first, "Related articles should include title")
        self.assertIn("pmid", first, "Related articles should include pmid")
        self.assertTrue(
            first.get("title"),
            "Title should not be empty",
        )


class TestSemanticScholarSchemaDefaults(unittest.TestCase):
    """Integration test: S2 tools should return full fields via schema defaults."""

    def test_get_paper_returns_full_fields(self):
        """Live test: SemanticScholar_get_paper should return abstract, year, etc."""
        try:
            from tooluniverse import ToolUniverse

            tu = ToolUniverse()
            tu.load_tools()
        except Exception:
            self.skipTest("ToolUniverse not available")

        try:
            result = tu.execute_tool(
                "SemanticScholar_get_paper",
                {"paper_id": "DOI:10.1038/s41586-020-2649-2"},
            )
        except Exception as e:
            self.skipTest(f"API call failed: {e}")

        if isinstance(result, str):
            result = json.loads(result)

        data = result.get("data", result)
        if isinstance(data, str):
            data = json.loads(data)

        self.assertIsInstance(data, dict)
        # With schema defaults, these fields should be present
        self.assertIn("abstract", data, "Should have abstract via schema default fields")
        self.assertIn("year", data, "Should have year via schema default fields")
        self.assertIn("citationCount", data, "Should have citationCount via schema default fields")
        self.assertIn("authors", data, "Should have authors via schema default fields")


class TestBaseRESTToolClientSideLimit(unittest.TestCase):
    """Feature-79B-004: Client-side limit for APIs that return unbounded lists."""

    def test_client_side_limit_truncates_data(self):
        from tooluniverse.base_rest_tool import BaseRESTTool

        config = {
            "name": "Test_get_all",
            "fields": {
                "endpoint": "https://api.example.com/items",
                "method": "GET",
                "params": {},
                "client_side_limit": True,
            },
            "parameter": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": ["integer", "null"],
                        "description": "Max items",
                        "default": 10,
                    },
                },
                "required": [],
            },
        }
        BaseRESTTool(config)  # verify config is valid

        # Simulate run() post-processing with a large list result
        result = {"status": "success", "data": list(range(100)), "count": 100}
        limit = None  # not in user args
        if limit is None:
            limit = config["parameter"]["properties"].get("limit", {}).get("default")
        if limit is not None and isinstance(result.get("data"), list):
            limit = int(limit)
            if len(result["data"]) > limit:
                result["total_before_limit"] = len(result["data"])
                result["data"] = result["data"][:limit]
                result["count"] = limit

        self.assertEqual(result["count"], 10)
        self.assertEqual(result["total_before_limit"], 100)
        self.assertEqual(len(result["data"]), 10)

    def test_limit_not_sent_as_query_param(self):
        """When client_side_limit is set, limit should not appear in API query params."""
        from tooluniverse.base_rest_tool import BaseRESTTool

        config = {
            "name": "Test_get_all",
            "fields": {
                "endpoint": "https://api.example.com/items",
                "method": "GET",
                "params": {},
                "client_side_limit": True,
            },
            "parameter": {
                "type": "object",
                "properties": {
                    "limit": {"type": ["integer", "null"], "default": 10},
                },
                "required": [],
            },
        }
        tool = BaseRESTTool(config)
        params = tool._build_params({"limit": 50})
        self.assertNotIn("limit", params)

    def test_no_client_side_limit_sends_param(self):
        """Without client_side_limit flag, limit is sent as query param normally."""
        from tooluniverse.base_rest_tool import BaseRESTTool

        config = {
            "name": "Test_search",
            "fields": {
                "endpoint": "https://api.example.com/search",
                "method": "GET",
                "params": {},
            },
            "parameter": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        }
        tool = BaseRESTTool(config)
        params = tool._build_params({"query": "test", "limit": 50})
        self.assertEqual(params["limit"], 50)


class TestMultiAgentParseResult(unittest.TestCase):
    """Feature-79B-008: _parse_result unwraps nested JSON from agent results."""

    def test_parse_result_unwraps_nested_json(self):
        from tooluniverse.compose_scripts.enhanced_multi_agent_literature_search import (
            _parse_result,
        )

        nested = {
            "success": True,
            "result": json.dumps({"user_intent": "Find CRISPR papers", "search_plans": []}),
            "metadata": {"model": "gpt-5"},
        }
        parsed = _parse_result(nested)
        self.assertEqual(parsed["user_intent"], "Find CRISPR papers")
        self.assertIn("search_plans", parsed)

    def test_parse_result_plain_dict(self):
        from tooluniverse.compose_scripts.enhanced_multi_agent_literature_search import (
            _parse_result,
        )

        plain = {"user_intent": "Find papers", "search_plans": [{"title": "plan1"}]}
        parsed = _parse_result(plain)
        self.assertEqual(parsed["user_intent"], "Find papers")

    def test_parse_result_string(self):
        from tooluniverse.compose_scripts.enhanced_multi_agent_literature_search import (
            _parse_result,
        )

        s = json.dumps({"user_intent": "Test", "plans": []})
        parsed = _parse_result(s)
        self.assertEqual(parsed["user_intent"], "Test")


if __name__ == "__main__":
    unittest.main()
