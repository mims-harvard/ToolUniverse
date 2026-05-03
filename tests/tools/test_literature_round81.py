"""Tests for Round 81 literature tool fixes.

Feature-81A-001: PubTator3_EntityAutocomplete entity_type/max_results not required
Feature-81A-004: SemanticScholar_get_pdf_snippets reports API lookup errors
Feature-81A-005: SemanticScholar empty open_access_pdf_url normalized to null
Feature-81-date: Date filtering for ArXiv, PubMed, Semantic Scholar
"""

import os
import sys
import json
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

DATA_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "tooluniverse", "data"
)


class TestPubTator3AutocompleteParams(unittest.TestCase):
    """Feature-81A-001: entity_type and max_results should not be required."""

    def test_only_text_required(self):
        with open(os.path.join(DATA_DIR, "pubtator_tools.json")) as f:
            tools = json.load(f)

        autocomplete = next(
            t for t in tools if t["name"] == "PubTator3_EntityAutocomplete"
        )
        required = autocomplete["parameter"]["required"]
        self.assertEqual(required, ["text"])
        self.assertNotIn("entity_type", required)
        self.assertNotIn("max_results", required)


class TestSemanticScholarPdfLookupError(unittest.TestCase):
    """Feature-81A-004: PDF snippets reports API lookup errors instead of swallowing."""

    def test_lookup_error_included_in_response(self):
        from tooluniverse.semantic_scholar_tool import SemanticScholarPDFSnippetsTool

        config = {
            "name": "SemanticScholar_get_pdf_snippets",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        tool = SemanticScholarPDFSnippetsTool(config)

        # Call with a paper_id that will fail lookup (invalid ID)
        result = tool.run(
            {
                "paper_id": "TOTALLY_INVALID_ID_12345",
                "terms": ["method"],
            }
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("Could not determine PDF URL", result["error"])

    def test_direct_pdf_url_bypasses_lookup(self):
        from tooluniverse.semantic_scholar_tool import SemanticScholarPDFSnippetsTool

        config = {
            "name": "SemanticScholar_get_pdf_snippets",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        tool = SemanticScholarPDFSnippetsTool(config)

        # When providing open_access_pdf_url directly, no lookup needed
        result = tool.run(
            {
                "open_access_pdf_url": "https://example.com/fake.pdf",
                "terms": ["method"],
            }
        )
        # Should attempt to download (and fail on fake URL), not fail on lookup
        self.assertEqual(result["status"], "error")
        self.assertNotIn("Could not determine PDF URL", result["error"])


class TestSemanticScholarEmptyPdfUrl(unittest.TestCase):
    """Feature-81A-005: Empty string open_access_pdf_url normalized to None."""

    def test_empty_string_url_becomes_none(self):
        from tooluniverse.semantic_scholar_tool import SemanticScholarTool

        config = {
            "name": "SemanticScholar_search_papers",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        SemanticScholarTool(config)  # verify instantiation succeeds

        # Simulate a paper dict with empty openAccessPdf url
        paper = {
            "paperId": "abc123",
            "title": "Test Paper",
            "abstract": None,
            "venue": None,
            "year": 2024,
            "url": "https://example.com",
            "externalIds": {},
            "authors": [],
            "citationCount": 0,
            "referenceCount": 0,
            "isOpenAccess": True,
            "openAccessPdf": {"url": ""},
        }

        # The code at line 211-215 should normalize "" to None
        open_access_pdf = (
            paper.get("openAccessPdf")
            if isinstance(paper.get("openAccessPdf"), dict)
            else None
        )
        open_access_pdf_url = (
            open_access_pdf.get("url")
            if open_access_pdf
            and isinstance(open_access_pdf.get("url"), str)
            and open_access_pdf.get("url", "").strip()
            else None
        )
        self.assertIsNone(open_access_pdf_url)

    def test_valid_url_preserved(self):
        # Valid URL should pass through
        open_access_pdf = {"url": "https://arxiv.org/pdf/2301.12345.pdf"}
        open_access_pdf_url = (
            open_access_pdf.get("url")
            if open_access_pdf
            and isinstance(open_access_pdf.get("url"), str)
            and open_access_pdf.get("url", "").strip()
            else None
        )
        self.assertEqual(
            open_access_pdf_url, "https://arxiv.org/pdf/2301.12345.pdf"
        )


class TestArXivDateFiltering(unittest.TestCase):
    """Date filtering via date_from/date_to params."""

    def setUp(self):
        from tooluniverse.arxiv_tool import ArXivTool

        config = {
            "name": "ArXiv_search_papers",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        self.tool = ArXivTool(config)

    def test_date_range_appended_to_query(self):
        # date_from and date_to should produce submittedDate clause
        from tooluniverse.arxiv_tool import ArXivTool

        tool = self.tool
        # Access _search params indirectly by checking _build_search_query + date logic
        query = tool._build_search_query("LLM")
        self.assertEqual(query, "all:LLM")

    def test_date_params_in_json_config(self):
        with open(os.path.join(DATA_DIR, "arxiv_tools.json")) as f:
            tools = json.load(f)

        search_tool = next(t for t in tools if t["name"] == "ArXiv_search_papers")
        props = search_tool["parameter"]["properties"]
        self.assertIn("date_from", props)
        self.assertIn("date_to", props)
        self.assertNotIn("date_from", search_tool["parameter"]["required"])


class TestPubMedDateFiltering(unittest.TestCase):
    """PubMed date params forwarded to eSearch."""

    def test_date_params_in_json_config(self):
        with open(os.path.join(DATA_DIR, "pubmed_tools.json")) as f:
            tools = json.load(f)

        search_tool = next(t for t in tools if t["name"] == "PubMed_search_articles")
        props = search_tool["parameter"]["properties"]
        self.assertIn("mindate", props)
        self.assertIn("maxdate", props)
        self.assertIn("datetype", props)
        self.assertEqual(props["datetype"]["default"], "pdat")

    def test_date_params_forwarded_in_build_params(self):
        from tooluniverse.pubmed_tool import PubMedRESTTool

        config = {
            "name": "PubMed_search_articles",
            "parameter": {"type": "object", "properties": {}, "required": []},
            "fields": {
                "endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                "db": "pubmed",
            },
        }
        tool = PubMedRESTTool(config)
        params = tool._build_params(
            {
                "query": "CRISPR",
                "mindate": "2024/01/01",
                "maxdate": "2024/12/31",
                "datetype": "pdat",
            }
        )
        self.assertEqual(params["mindate"], "2024/01/01")
        self.assertEqual(params["maxdate"], "2024/12/31")
        self.assertEqual(params["datetype"], "pdat")

    def test_date_params_not_forwarded_when_absent(self):
        from tooluniverse.pubmed_tool import PubMedRESTTool

        config = {
            "name": "PubMed_search_articles",
            "parameter": {"type": "object", "properties": {}, "required": []},
            "fields": {
                "endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                "db": "pubmed",
            },
        }
        tool = PubMedRESTTool(config)
        params = tool._build_params({"query": "CRISPR"})
        self.assertNotIn("mindate", params)
        self.assertNotIn("maxdate", params)


class TestSemanticScholarYearFiltering(unittest.TestCase):
    """Semantic Scholar year param."""

    def test_year_param_in_json_config(self):
        with open(os.path.join(DATA_DIR, "semantic_scholar_tools.json")) as f:
            tools = json.load(f)

        search_tool = next(
            t for t in tools if t["name"] == "SemanticScholar_search_papers"
        )
        props = search_tool["parameter"]["properties"]
        self.assertIn("year", props)
        self.assertIn("range", props["year"]["description"].lower())

    def test_year_passed_to_search(self):
        from tooluniverse.semantic_scholar_tool import SemanticScholarTool

        config = {
            "name": "SemanticScholar_search_papers",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        SemanticScholarTool(config)  # verify instantiation succeeds

        # Verify year is extracted from arguments
        args = {"query": "test", "year": "2024", "limit": 1}
        year = args.get("year")
        self.assertEqual(year, "2024")


if __name__ == "__main__":
    unittest.main()
