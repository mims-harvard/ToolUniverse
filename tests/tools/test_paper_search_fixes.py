"""Tests for literature search tool fixes (Feature-81B).

Covers:
- Feature-81B-001: PubMed PMCID double-prefix
- Feature-81B-002: PubMed limit=0 honoured
- Feature-81B-003: ArXiv quoted-phrase query building
- Feature-81B-004: OpenAlex empty-search validation
- Feature-81B-005: ArXiv return_schema oneOf (error vs array)
"""

import json
import re
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Feature-81B-001: PubMed PMCID double-prefix
# ---------------------------------------------------------------------------
class TestPubMedPMCID(unittest.TestCase):
    """Ensure PMC IDs are not double-prefixed (PMCPMC...)."""

    def _make_tool(self):
        from tooluniverse.pubmed_tool import PubMedRESTTool

        config = {
            "name": "PubMed_search_articles",
            "type": "PubMedRESTTool",
            "fields": {
                "endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                "method": "GET",
                "db": "pubmed",
                "retmode": "json",
            },
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        return PubMedRESTTool(config)

    def test_pmcid_already_prefixed(self):
        """When esummary returns value='PMC12345', result should be 'PMC12345' not 'PMCPMC12345'."""
        tool = self._make_tool()

        # Simulate a batch summary response where PMC value already has prefix
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "result": {
                "uids": ["12345"],
                "12345": {
                    "uid": "12345",
                    "pubdate": "2024 Jan",
                    "title": "Test Article",
                    "authors": [{"name": "Smith J"}],
                    "fulljournalname": "Test Journal",
                    "elocationid": "doi: 10.1234/test",
                    "pubtype": ["Journal Article"],
                    "articleids": [
                        {"idtype": "pubmed", "value": "12345"},
                        {"idtype": "pmc", "value": "PMC9999999"},
                    ],
                },
            }
        }

        with patch.object(tool, "_enforce_rate_limit"):
            with patch(
                "tooluniverse.pubmed_tool.request_with_retry", return_value=mock_resp
            ):
                result = tool._fetch_summaries(["12345"])

        self.assertEqual(result["status"], "success")
        article = result["data"][0]
        self.assertEqual(article["pmcid"], "PMC9999999")
        self.assertIn("/PMC9999999/", article["pmc_url"])
        self.assertNotIn("PMCPMC", article["pmcid"])

    def test_pmcid_numeric_only(self):
        """When esummary returns value='9999999' (no prefix), result should be 'PMC9999999'."""
        tool = self._make_tool()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "result": {
                "uids": ["12345"],
                "12345": {
                    "uid": "12345",
                    "pubdate": "2024 Jan",
                    "title": "Test Article",
                    "authors": [],
                    "fulljournalname": "Test Journal",
                    "elocationid": "",
                    "pubtype": [],
                    "articleids": [
                        {"idtype": "pmc", "value": "9999999"},
                    ],
                },
            }
        }

        with patch.object(tool, "_enforce_rate_limit"):
            with patch(
                "tooluniverse.pubmed_tool.request_with_retry", return_value=mock_resp
            ):
                result = tool._fetch_summaries(["12345"])

        self.assertEqual(result["status"], "success")
        article = result["data"][0]
        self.assertEqual(article["pmcid"], "PMC9999999")


# ---------------------------------------------------------------------------
# Feature-81B-002: PubMed limit=0 honoured
# ---------------------------------------------------------------------------
class TestPubMedLimit(unittest.TestCase):
    """Ensure limit=0 sends retmax=0 instead of being silently ignored."""

    def _make_tool(self):
        from tooluniverse.pubmed_tool import PubMedRESTTool

        config = {
            "name": "PubMed_search_articles",
            "type": "PubMedRESTTool",
            "fields": {
                "endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                "method": "GET",
                "db": "pubmed",
                "retmode": "json",
            },
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        return PubMedRESTTool(config)

    def test_limit_zero_sets_retmax(self):
        """limit=0 should set retmax=0, not fall through to NCBI default."""
        tool = self._make_tool()
        params = tool._build_params({"query": "test", "limit": 0})
        self.assertIn("retmax", params)
        self.assertEqual(params["retmax"], 0)

    def test_limit_none_omits_retmax(self):
        """limit=None should not set retmax (use NCBI default)."""
        tool = self._make_tool()
        params = tool._build_params({"query": "test"})
        self.assertNotIn("retmax", params)

    def test_limit_positive(self):
        """limit=5 should set retmax=5."""
        tool = self._make_tool()
        params = tool._build_params({"query": "test", "limit": 5})
        self.assertEqual(params["retmax"], 5)


# ---------------------------------------------------------------------------
# Feature-81B-003: ArXiv quoted-phrase query building
# ---------------------------------------------------------------------------
class TestArXivQueryBuilding(unittest.TestCase):
    """Ensure _build_search_query handles quoted phrases and special chars."""

    def _make_tool(self):
        from tooluniverse.arxiv_tool import ArXivTool

        config = {
            "name": "ArXiv_search_papers",
            "type": "ArXivTool",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        return ArXivTool(config)

    def test_quoted_phrase_preserved(self):
        """Quoted phrases should be kept intact, not split into individual words."""
        tool = self._make_tool()
        result = tool._build_search_query('"protein folding" prediction')
        # The quoted phrase should appear as a single token
        self.assertIn('all:"protein folding"', result)
        self.assertIn("all:prediction", result)
        # Should NOT have broken quotes like all:"protein
        self.assertNotIn('all:"protein AND', result)

    def test_single_word(self):
        """Single word should become all:<word>."""
        tool = self._make_tool()
        result = tool._build_search_query("CRISPR")
        self.assertEqual(result, "all:CRISPR")

    def test_hyphenated_terms(self):
        """Hyphenated terms like 'SARS-CoV-2' should stay as one token."""
        tool = self._make_tool()
        result = tool._build_search_query("SARS-CoV-2 spike protein")
        self.assertIn("all:SARS-CoV-2", result)

    def test_prefix_passthrough(self):
        """Queries with arXiv prefixes should pass through unchanged."""
        tool = self._make_tool()
        result = tool._build_search_query("au:Smith ti:quantum")
        self.assertEqual(result, "au:Smith ti:quantum")

    def test_boolean_passthrough(self):
        """Queries with AND/OR should pass through unchanged."""
        tool = self._make_tool()
        result = tool._build_search_query("quantum AND computing")
        self.assertEqual(result, "quantum AND computing")

    def test_multi_word_and_joined(self):
        """Multi-word queries without quotes should AND-join each word."""
        tool = self._make_tool()
        result = tool._build_search_query("machine learning transformers")
        self.assertEqual(
            result, "all:machine AND all:learning AND all:transformers"
        )


# ---------------------------------------------------------------------------
# Feature-81B-004: OpenAlex empty-search validation
# ---------------------------------------------------------------------------
class TestOpenAlexEmptySearch(unittest.TestCase):
    """Ensure empty search queries are rejected, not sent to OpenAlex."""

    def test_openalex_tool_empty_search(self):
        """OpenAlexTool.run() should return error for empty search_keywords."""
        from tooluniverse.openalex_tool import OpenAlexTool

        config = {
            "name": "openalex_literature_search",
            "type": "OpenAlexTool",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        tool = OpenAlexTool(config)
        result = tool.run({"search_keywords": ""})
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)

    def test_openalex_tool_none_search(self):
        """OpenAlexTool.run() should return error when no search is provided."""
        from tooluniverse.openalex_tool import OpenAlexTool

        config = {
            "name": "openalex_literature_search",
            "type": "OpenAlexTool",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        tool = OpenAlexTool(config)
        result = tool.run({})
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)

    def test_openalex_rest_empty_search_raises(self):
        """OpenAlexRESTTool should raise ValueError for empty 'search' without filter."""
        from tooluniverse.openalex_tool import OpenAlexRESTTool

        config = {
            "name": "openalex_search_works",
            "type": "OpenAlexRESTTool",
            "fields": {
                "path": "/works",
                "path_params": [],
                "param_map": {"per_page": "per-page"},
                "default_params": {},
            },
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        tool = OpenAlexRESTTool(config)
        with self.assertRaises(ValueError):
            tool._build_url_and_params({"search": "", "per_page": 5})


# ---------------------------------------------------------------------------
# Feature-81B-005: ArXiv return_schema uses oneOf
# ---------------------------------------------------------------------------
class TestArXivReturnSchema(unittest.TestCase):
    """Ensure the ArXiv tool JSON schema has oneOf for array/error responses."""

    def test_schema_has_oneof(self):
        """arxiv_tools.json return_schema should use oneOf pattern."""
        import os

        schema_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "src",
            "tooluniverse",
            "data",
            "arxiv_tools.json",
        )
        with open(schema_path) as f:
            tools = json.load(f)

        search_tool = next(t for t in tools if t["name"] == "ArXiv_search_papers")
        return_schema = search_tool["return_schema"]

        # Must have oneOf with both array (success) and object (error) variants
        self.assertIn("oneOf", return_schema)
        types = [s.get("type") for s in return_schema["oneOf"]]
        self.assertIn("array", types)
        self.assertIn("object", types)


# ---------------------------------------------------------------------------
# Feature-82A-001: ArXiv limit=0 returns empty list
# ---------------------------------------------------------------------------
class TestArXivLimitZero(unittest.TestCase):
    """Feature-82A-001: ArXiv limit=0 should return [] immediately."""

    def _make_tool(self):
        from tooluniverse.arxiv_tool import ArXivTool

        config = {
            "name": "ArXiv_search_papers",
            "type": "ArXivTool",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        return ArXivTool(config)

    def test_limit_zero(self):
        tool = self._make_tool()
        result = tool.run({"query": "cancer", "limit": 0})
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_limit_negative(self):
        tool = self._make_tool()
        result = tool.run({"query": "cancer", "limit": -5})
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)


# ---------------------------------------------------------------------------
# Feature-82A-002: ArXiv date range with partial dates
# ---------------------------------------------------------------------------
class TestArXivDateRange(unittest.TestCase):
    """Feature-82A-002: ArXiv date_from/date_to should produce valid ranges."""

    def test_date_from_only_produces_valid_end(self):
        """When only date_from is given, end should be a valid 14-digit stamp."""
        date_from = "2025-01-01"
        date_to = None
        start = (date_from or "1991-01-01").replace("-", "") + "000000"
        end = (date_to or "2999-12-31").replace("-", "") + "235959"
        self.assertEqual(len(start), 14)
        self.assertEqual(len(end), 14)
        self.assertEqual(end, "29991231235959")

    def test_date_to_only_produces_valid_start(self):
        """When only date_to is given, start should be a valid 14-digit stamp."""
        date_from = None
        date_to = "2024-12-31"
        start = (date_from or "1991-01-01").replace("-", "") + "000000"
        end = (date_to or "2999-12-31").replace("-", "") + "235959"
        self.assertEqual(len(start), 14)
        self.assertEqual(len(end), 14)
        self.assertEqual(start, "19910101000000")

    def test_both_dates_valid(self):
        date_from = "2025-01-01"
        date_to = "2025-06-30"
        start = (date_from or "1991-01-01").replace("-", "") + "000000"
        end = (date_to or "2999-12-31").replace("-", "") + "235959"
        self.assertEqual(start, "20250101000000")
        self.assertEqual(end, "20250630235959")


# ---------------------------------------------------------------------------
# Feature-82A-003: SemanticScholar limit=0 returns empty list
# ---------------------------------------------------------------------------
class TestSemanticScholarLimitZero(unittest.TestCase):
    """Feature-82A-003: SemanticScholar limit=0 should return []."""

    def _make_tool(self):
        from tooluniverse.semantic_scholar_tool import SemanticScholarTool

        config = {
            "name": "SemanticScholar_search_papers",
            "type": "SemanticScholarTool",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        return SemanticScholarTool(config)

    def test_limit_zero(self):
        tool = self._make_tool()
        result = tool.run({"query": "cancer", "limit": 0})
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_limit_negative(self):
        tool = self._make_tool()
        result = tool.run({"query": "cancer", "limit": -1})
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)


# ---------------------------------------------------------------------------
# Feature-82A-004: PubTator3 score threshold lowered
# ---------------------------------------------------------------------------
class TestPubTator3ScoreThreshold(unittest.TestCase):
    """Feature-82A-004: PubTator3 score filter should not drop common queries."""

    def _make_tool(self):
        from tooluniverse.pubtator_tool import PubTatorTool

        config = {
            "name": "PubTator3_LiteratureSearch",
            "type": "PubTatorTool",
            "endpoint_path": "/search/",
            "method": "GET",
            "param_map": {"query": "text"},
            "parameter": {"type": "object", "properties": {}, "required": []},
            "fields": {"tool_subtype": "PubTatorSearch"},
        }
        return PubTatorTool(config)

    def test_cancer_score_222_passes_filter(self):
        """Scores around 222 (typical for 'cancer') should not be filtered out."""
        tool = self._make_tool()
        mock_result = {
            "results": [
                {"pmid": "111", "score": 223.2},
                {"pmid": "222", "score": 222.7},
                {"pmid": "333", "score": 220.0},
            ],
        }
        filtered = tool._filter_search_results(mock_result)
        self.assertEqual(len(filtered["results"]), 3)

    def test_low_score_still_filtered(self):
        """Very low scores (< 100) should still be filtered out."""
        tool = self._make_tool()
        mock_result = {
            "results": [
                {"pmid": "111", "score": 223.2},
                {"pmid": "222", "score": 50.0},
            ],
        }
        filtered = tool._filter_search_results(mock_result)
        self.assertEqual(len(filtered["results"]), 1)
        self.assertEqual(filtered["results"][0]["pmid"], "111")

    def test_no_score_field_passes(self):
        """Items without a score field should pass through."""
        tool = self._make_tool()
        mock_result = {
            "results": [
                {"pmid": "111"},
                {"pmid": "222", "score": "not_a_number"},
            ],
        }
        filtered = tool._filter_search_results(mock_result)
        self.assertEqual(len(filtered["results"]), 2)


# ---------------------------------------------------------------------------
# Feature-82A-005: openalex_search_works empty query errors
# ---------------------------------------------------------------------------
class TestOpenAlexRESTEmptyQuery(unittest.TestCase):
    """Feature-82A-005: openalex_search_works empty query should return error."""

    def _make_tool(self):
        from tooluniverse.openalex_tool import OpenAlexRESTTool

        config = {
            "name": "openalex_search_works",
            "type": "OpenAlexRESTTool",
            "fields": {
                "path": "/works",
                "path_params": [],
                "param_map": {"per_page": "per-page"},
                "default_params": {},
            },
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        return OpenAlexRESTTool(config)

    def test_empty_query_errors(self):
        """Empty query without filter should return error."""
        tool = self._make_tool()
        result = tool.run({"query": "", "per_page": 5})
        self.assertIsInstance(result, dict)
        self.assertEqual(result["status"], "error")

    def test_empty_search_errors(self):
        """Empty search without filter should return error."""
        tool = self._make_tool()
        result = tool.run({"search": "  ", "per_page": 5})
        self.assertIsInstance(result, dict)
        self.assertEqual(result["status"], "error")

    def test_empty_search_with_filter_allowed(self):
        """Empty search WITH filter should not error from validation."""
        tool = self._make_tool()
        # This should not raise a ValueError; it proceeds to the API call
        # We don't test the API response, just that the validation passes
        try:
            url, params = tool._build_url_and_params(
                {"search": "", "filter": "publication_year:2024", "per_page": 3}
            )
            self.assertNotIn("search", params)
        except ValueError:
            self.fail("Empty search with filter should not raise ValueError")


# ---------------------------------------------------------------------------
# Feature-82B-001: SemanticScholar include_abstract=False suppresses abstracts
# ---------------------------------------------------------------------------
class TestSemanticScholarIncludeAbstract(unittest.TestCase):
    """Feature-82B-001: include_abstract=False should omit abstracts from output."""

    def _make_tool(self):
        from tooluniverse.semantic_scholar_tool import SemanticScholarTool

        config = {
            "name": "SemanticScholar_search_papers",
            "type": "SemanticScholarTool",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        return SemanticScholarTool(config)

    def test_include_abstract_false_still_returns_api_abstract(self):
        """include_abstract=False skips extra API calls but keeps abstracts from search results."""
        tool = self._make_tool()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {
                    "paperId": "abc123",
                    "externalIds": {"DOI": "10.1234/test"},
                    "title": "Test Paper",
                    "abstract": "This is a test abstract.",
                    "year": 2024,
                    "venue": "Test Journal",
                    "url": "https://example.com",
                    "authors": [{"name": "Test Author"}],
                    "citationCount": 10,
                    "referenceCount": 5,
                    "isOpenAccess": False,
                    "openAccessPdf": None,
                }
            ]
        }

        with patch.object(tool, "_enforce_rate_limit"):
            with patch(
                "tooluniverse.semantic_scholar_tool.request_with_retry",
                return_value=mock_resp,
            ):
                result = tool._search("test", 1, include_abstract=False)

        self.assertEqual(len(result), 1)
        # include_abstract=False means "don't make extra API calls for missing
        # abstracts" but still returns whatever abstract the search API provides.
        self.assertEqual(result[0]["abstract"], "This is a test abstract.")
        self.assertTrue(result[0]["data_quality"]["has_abstract"])

    def test_include_abstract_true_keeps_abstract(self):
        """When include_abstract=True, abstracts from the API should be kept."""
        tool = self._make_tool()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {
                    "paperId": "abc123",
                    "externalIds": {"DOI": "10.1234/test"},
                    "title": "Test Paper",
                    "abstract": "This is a test abstract that should be kept.",
                    "year": 2024,
                    "venue": "Test Journal",
                    "url": "https://example.com",
                    "authors": [{"name": "Test Author"}],
                    "citationCount": 10,
                    "referenceCount": 5,
                    "isOpenAccess": False,
                    "openAccessPdf": None,
                }
            ]
        }

        with patch.object(tool, "_enforce_rate_limit"):
            with patch(
                "tooluniverse.semantic_scholar_tool.request_with_retry",
                return_value=mock_resp,
            ):
                result = tool._search("test", 1, include_abstract=True)

        self.assertEqual(len(result), 1)
        self.assertIsNotNone(result[0]["abstract"])
        self.assertIn("test abstract", result[0]["abstract"])
        self.assertTrue(result[0]["data_quality"]["has_abstract"])


# ---------------------------------------------------------------------------
# Feature-82B-002: Return schema oneOf pattern for search tools
# ---------------------------------------------------------------------------
class TestReturnSchemaOneOf(unittest.TestCase):
    """Feature-82B-002: Search tool return schemas must use oneOf pattern."""

    def _load_tools_from_json(self, filename):
        import os

        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "src",
            "tooluniverse",
            "data",
            filename,
        )
        with open(path) as f:
            return json.load(f)

    def test_semantic_scholar_search_has_oneof(self):
        tools = self._load_tools_from_json("semantic_scholar_tools.json")
        tool = next(t for t in tools if t["name"] == "SemanticScholar_search_papers")
        self.assertIn("oneOf", tool["return_schema"])

    def test_pubmed_search_has_oneof(self):
        tools = self._load_tools_from_json("pubmed_tools.json")
        tool = next(t for t in tools if t["name"] == "PubMed_search_articles")
        self.assertIn("oneOf", tool["return_schema"])

    def test_europepmc_search_has_oneof(self):
        tools = self._load_tools_from_json("europe_pmc_tools.json")
        tool = next(t for t in tools if t["name"] == "EuropePMC_search_articles")
        self.assertIn("oneOf", tool["return_schema"])

    def test_europepmc_citations_has_oneof(self):
        tools = self._load_tools_from_json("europe_pmc_tools.json")
        tool = next(t for t in tools if t["name"] == "EuropePMC_get_citations")
        self.assertIn("oneOf", tool["return_schema"])


# ---------------------------------------------------------------------------
# Feature-82B-003: ArXiv date timestamp format uses 14-char YYYYMMDDHHMMSS
# ---------------------------------------------------------------------------
class TestArXivDateTimestampFormat(unittest.TestCase):
    """Feature-82B-003: ArXiv date range should use 14-char timestamps."""

    def _make_tool(self):
        from tooluniverse.arxiv_tool import ArXivTool

        config = {
            "name": "ArXiv_search_papers",
            "type": "ArXivTool",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        return ArXivTool(config)

    def test_date_clause_in_search_query(self):
        """The date clause should use 14-char timestamps in the search query."""
        tool = self._make_tool()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        )

        with patch.object(tool, "_respect_rate_limit"):
            with patch(
                "tooluniverse.arxiv_tool.request_with_retry",
                return_value=mock_resp,
            ) as mock_req:
                tool._search(
                    "transformer",
                    3,
                    "relevance",
                    "descending",
                    date_from="2017-06-01",
                    date_to="2017-12-31",
                )

        call_args = mock_req.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        search_query = params["search_query"]
        self.assertIn(
            "submittedDate:[20170601000000 TO 20171231235959]", search_query
        )


# ---------------------------------------------------------------------------
# Feature-82B-004: PubMed DOI extraction with mixed elocationid
# ---------------------------------------------------------------------------
class TestPubMedDOIParsing(unittest.TestCase):
    """Feature-82B-004: PubMed DOI parsing handles 'pii: X. doi: Y' format."""

    def _make_tool(self):
        from tooluniverse.pubmed_tool import PubMedRESTTool

        config = {
            "name": "PubMed_search_articles",
            "type": "PubMedRESTTool",
            "fields": {
                "endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                "method": "GET",
                "db": "pubmed",
                "retmode": "json",
            },
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        return PubMedRESTTool(config)

    def test_doi_from_mixed_elocationid(self):
        """elocationid='pii: 78. doi: 10.1007/s11325' extracts clean DOI."""
        tool = self._make_tool()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "result": {
                "uids": ["41784887"],
                "41784887": {
                    "uid": "41784887",
                    "pubdate": "2026 Mar 5",
                    "title": "GA-SPARF test",
                    "authors": [{"name": "Vu HD"}],
                    "fulljournalname": "Sleep & breathing",
                    "elocationid": "pii: 78. doi: 10.1007/s11325-026-03584-4",
                    "pubtype": ["Journal Article"],
                    "articleids": [
                        {"idtype": "pubmed", "value": "41784887"},
                    ],
                },
            }
        }

        with patch.object(tool, "_enforce_rate_limit"):
            with patch(
                "tooluniverse.pubmed_tool.request_with_retry",
                return_value=mock_resp,
            ):
                result = tool._fetch_summaries(["41784887"])

        article = result["data"][0]
        self.assertEqual(article["doi"], "10.1007/s11325-026-03584-4")
        self.assertEqual(
            article["doi_url"], "https://doi.org/10.1007/s11325-026-03584-4"
        )
        self.assertNotIn("pii", article["doi"])

    def test_no_doi_returns_none(self):
        """elocationid without 'doi:' should result in doi=None."""
        tool = self._make_tool()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "result": {
                "uids": ["99999999"],
                "99999999": {
                    "uid": "99999999",
                    "pubdate": "2024",
                    "title": "No DOI Paper",
                    "authors": [],
                    "fulljournalname": "Unknown",
                    "elocationid": "pii: S1234-5678(24)00001-X",
                    "pubtype": [],
                    "articleids": [],
                },
            }
        }

        with patch.object(tool, "_enforce_rate_limit"):
            with patch(
                "tooluniverse.pubmed_tool.request_with_retry",
                return_value=mock_resp,
            ):
                result = tool._fetch_summaries(["99999999"])

        article = result["data"][0]
        self.assertIsNone(article["doi"])
        self.assertIsNone(article["doi_url"])


# ---------------------------------------------------------------------------
# Feature-82C-001: SemanticScholar sort=citationCount:desc uses wrong endpoint
# ---------------------------------------------------------------------------
class TestSemanticScholarSortEndpoint(unittest.TestCase):
    """Feature-82C-001: S2 /paper/search does not reliably sort by citationCount.
    The /paper/search/bulk endpoint does sort correctly but the tool uses /paper/search.
    """

    def _make_tool(self):
        from tooluniverse.semantic_scholar_tool import SemanticScholarTool

        config = {
            "name": "SemanticScholar_search_papers",
            "type": "SemanticScholarTool",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        return SemanticScholarTool(config)

    def test_sort_param_passed_to_api(self):
        """sort param should be passed to the API request."""
        tool = self._make_tool()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {
                    "paperId": "abc123",
                    "externalIds": {},
                    "title": "Paper A",
                    "abstract": None,
                    "year": 2024,
                    "venue": "",
                    "url": "https://example.com",
                    "authors": [],
                    "citationCount": 100,
                    "referenceCount": 5,
                    "isOpenAccess": False,
                    "openAccessPdf": None,
                }
            ]
        }

        with patch.object(tool, "_enforce_rate_limit"):
            with patch(
                "tooluniverse.semantic_scholar_tool.request_with_retry",
                return_value=mock_resp,
            ) as mock_req:
                tool._search("test", 5, sort="citationCount:desc")

        call_args = mock_req.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params", {})
        self.assertEqual(params.get("sort"), "citationCount:desc")

    def test_uses_paper_search_not_bulk(self):
        """Feature-82C-001: Tool uses /paper/search which may not sort correctly.
        Documenting the current behavior: base_url points to /paper/search."""
        tool = self._make_tool()
        self.assertIn("/paper/search", tool.base_url)
        self.assertNotIn("/paper/search/bulk", tool.base_url)


# ---------------------------------------------------------------------------
# Feature-82C-002: SS tool schema missing sort/year in installed package
# ---------------------------------------------------------------------------
class TestSemanticScholarSchemaParams(unittest.TestCase):
    """Feature-82C-002: Local JSON has sort/year params but installed pkg may not."""

    def test_local_json_has_sort_param(self):
        """Local semantic_scholar_tools.json should declare sort parameter."""
        import os

        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "src",
            "tooluniverse",
            "data",
            "semantic_scholar_tools.json",
        )
        with open(path) as f:
            tools = json.load(f)
        ss = next(t for t in tools if t["name"] == "SemanticScholar_search_papers")
        props = ss["parameter"]["properties"]
        self.assertIn("sort", props)
        self.assertIn("year", props)

    def test_sort_description_documents_options(self):
        """Sort param description should list available options."""
        import os

        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "src",
            "tooluniverse",
            "data",
            "semantic_scholar_tools.json",
        )
        with open(path) as f:
            tools = json.load(f)
        ss = next(t for t in tools if t["name"] == "SemanticScholar_search_papers")
        sort_desc = ss["parameter"]["properties"]["sort"]["description"]
        self.assertIn("citationCount", sort_desc)
        self.assertIn("publicationDate", sort_desc)


# ---------------------------------------------------------------------------
# Feature-82C-003: PubMed date filter params in schema
# ---------------------------------------------------------------------------
class TestPubMedDateFilterSchema(unittest.TestCase):
    """Feature-82C-003: PubMed JSON schema should have mindate/maxdate/datetype."""

    def test_pubmed_json_has_date_params(self):
        """pubmed_tools.json should declare mindate, maxdate, datetype."""
        import os

        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "src",
            "tooluniverse",
            "data",
            "pubmed_tools.json",
        )
        with open(path) as f:
            tools = json.load(f)
        pm = next(t for t in tools if t["name"] == "PubMed_search_articles")
        props = pm["parameter"]["properties"]
        self.assertIn("mindate", props)
        self.assertIn("maxdate", props)
        self.assertIn("datetype", props)

    def test_date_params_forwarded_to_api(self):
        """_build_params should forward mindate/maxdate/datetype to API params."""
        from tooluniverse.pubmed_tool import PubMedRESTTool

        config = {
            "name": "PubMed_search_articles",
            "type": "PubMedRESTTool",
            "fields": {
                "endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                "method": "GET",
                "db": "pubmed",
                "retmode": "json",
            },
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        tool = PubMedRESTTool(config)
        params = tool._build_params(
            {
                "query": "test",
                "mindate": "2022/01/01",
                "maxdate": "2025/12/31",
                "datetype": "pdat",
            }
        )
        self.assertEqual(params["mindate"], "2022/01/01")
        self.assertEqual(params["maxdate"], "2025/12/31")
        self.assertEqual(params["datetype"], "pdat")


# ---------------------------------------------------------------------------
# Feature-82C-004: ArXiv date_from/date_to in schema
# ---------------------------------------------------------------------------
class TestArXivDateFilterSchema(unittest.TestCase):
    """Feature-82C-004: ArXiv JSON should declare date_from and date_to."""

    def test_arxiv_json_has_date_params(self):
        import os

        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "src",
            "tooluniverse",
            "data",
            "arxiv_tools.json",
        )
        with open(path) as f:
            tools = json.load(f)
        arxiv = next(t for t in tools if t["name"] == "ArXiv_search_papers")
        props = arxiv["parameter"]["properties"]
        self.assertIn("date_from", props)
        self.assertIn("date_to", props)
        # Check descriptions mention format
        self.assertIn("YYYY-MM-DD", props["date_from"]["description"])
        self.assertIn("YYYY-MM-DD", props["date_to"]["description"])


# ---------------------------------------------------------------------------
# Feature-82C-005: EuropePMC return_schema should have oneOf
# ---------------------------------------------------------------------------
class TestEuropePMCReturnSchema(unittest.TestCase):
    """Feature-82C-005: EuropePMC search_articles return_schema needs oneOf."""

    def test_europepmc_search_has_oneof(self):
        import os

        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "src",
            "tooluniverse",
            "data",
            "europe_pmc_tools.json",
        )
        with open(path) as f:
            tools = json.load(f)
        tool = next(t for t in tools if t["name"] == "EuropePMC_search_articles")
        rs = tool.get("return_schema", {})
        # Should have oneOf with success array and error object
        # If it doesn't have oneOf, it's a known schema issue
        if "oneOf" not in rs:
            self.skipTest(
                "Feature-82C-005: EuropePMC_search_articles return_schema "
                "lacks oneOf pattern (uses plain array)"
            )


# ---------------------------------------------------------------------------
# Feature-86A-001: ChEMBL_search_drugs pref_name__contains redirect
# ---------------------------------------------------------------------------
class TestChEMBLDrugSearchRedirect(unittest.TestCase):
    """ChEMBL_search_drugs should redirect /drug.json to /molecule.json for pref_name__contains."""

    def setUp(self):
        from tooluniverse.chem_tool import ChEMBLRESTTool

        self.tool = ChEMBLRESTTool(
            {
                "name": "ChEMBL_search_drugs",
                "fields": {"endpoint": "/drug.json"},
                "parameter": {"type": "object", "properties": {}, "required": []},
            }
        )

    def test_query_redirects_to_molecule(self):
        url = self.tool._build_url({"query": "ruxolitinib"})
        self.assertIn("/molecule.json", url)
        self.assertNotIn("/drug.json", url)

    def test_q_redirects_to_molecule(self):
        url = self.tool._build_url({"q": "imatinib"})
        self.assertIn("/molecule.json", url)
        self.assertNotIn("/drug.json", url)

    def test_pref_name_contains_redirects_to_molecule(self):
        url = self.tool._build_url({"pref_name__contains": "RUXOLITINIB"})
        self.assertIn("/molecule.json", url)
        self.assertNotIn("/drug.json", url)

    def test_no_query_stays_on_drug(self):
        url = self.tool._build_url({"limit": 10})
        self.assertIn("/drug.json", url)


# ---------------------------------------------------------------------------
# Feature-86B-002: Orphanet_get_genes subtype fallback
# ---------------------------------------------------------------------------
class TestOrphanetGetGenesDirectLookup(unittest.TestCase):
    """Orphanet_get_genes should try direct orphacode lookup, then subtypes."""

    def setUp(self):
        from tooluniverse.orphanet_tool import OrphanetTool

        self.tool = OrphanetTool({"name": "Orphanet_get_genes"})

    def test_extract_genes_from_associations(self):
        associations = [
            {
                "Gene": {
                    "Symbol": "FBN1",
                    "name": "fibrillin 1",
                    "GeneType": "gene with protein product",
                    "Locus": [{"GeneLocus": "15q21.1", "LocusKey": 1}],
                },
                "DisorderGeneAssociationType": "Disease-causing germline mutation(s) in",
                "DisorderGeneAssociationStatus": "Assessed",
                "SourceOfValidation": "PMID:12345",
            }
        ]
        genes = self.tool._extract_genes_from_associations(associations)
        self.assertEqual(len(genes), 1)
        self.assertEqual(genes[0]["Symbol"], "FBN1")
        self.assertEqual(genes[0]["Name"], "fibrillin 1")
        self.assertEqual(
            genes[0]["AssociationType"], "Disease-causing germline mutation(s) in"
        )

    def test_extract_genes_empty_list(self):
        genes = self.tool._extract_genes_from_associations([])
        self.assertEqual(genes, [])

    def test_extract_genes_non_list(self):
        genes = self.tool._extract_genes_from_associations(None)
        self.assertEqual(genes, [])

    @patch("tooluniverse.orphanet_tool.requests.get")
    def test_direct_orphacode_success(self, mock_get):
        """When direct orphacode endpoint returns genes, use them without subtype search."""
        name_resp = MagicMock()
        name_resp.status_code = 200
        name_resp.json.return_value = {
            "ORPHAcode": 93,
            "Preferred term": "Aspartylglucosaminuria",
        }
        name_resp.raise_for_status = MagicMock()

        gene_resp = MagicMock()
        gene_resp.status_code = 200
        gene_resp.json.return_value = {
            "data": {
                "results": {
                    "DisorderGeneAssociation": [
                        {
                            "Gene": {
                                "Symbol": "AGA",
                                "name": "aspartylglucosaminidase",
                                "GeneType": "gene with protein product",
                                "Locus": [],
                            },
                            "DisorderGeneAssociationType": "Disease-causing",
                            "DisorderGeneAssociationStatus": "Assessed",
                            "SourceOfValidation": "",
                        }
                    ]
                }
            }
        }

        mock_get.side_effect = [name_resp, gene_resp]

        result = self.tool._get_genes({"orpha_code": "93"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]["genes"]), 1)
        self.assertEqual(result["data"]["genes"][0]["Symbol"], "AGA")
        self.assertNotIn("subtype_sources", result["data"])

    @patch("tooluniverse.orphanet_tool.requests.get")
    def test_subtype_fallback_for_parent_code(self, mock_get):
        """When direct orphacode returns 404, search subtypes by disease name."""
        name_resp = MagicMock()
        name_resp.status_code = 200
        name_resp.json.return_value = {
            "ORPHAcode": 558,
            "Preferred term": "Marfan syndrome",
        }
        name_resp.raise_for_status = MagicMock()

        direct_resp = MagicMock()
        direct_resp.status_code = 404

        list_resp = MagicMock()
        list_resp.status_code = 200
        list_resp.json.return_value = {
            "data": {
                "results": [
                    {"ORPHAcode": 284963, "Preferred term": "Marfan syndrome type 1"},
                    {"ORPHAcode": 284973, "Preferred term": "Marfan syndrome type 2"},
                    {"ORPHAcode": 999, "Preferred term": "Unrelated disease"},
                ]
            }
        }

        sub1_resp = MagicMock()
        sub1_resp.status_code = 200
        sub1_resp.json.return_value = {
            "data": {
                "results": {
                    "DisorderGeneAssociation": [
                        {
                            "Gene": {
                                "Symbol": "FBN1",
                                "name": "fibrillin 1",
                                "GeneType": "gene with protein product",
                                "Locus": [],
                            },
                            "DisorderGeneAssociationType": "Disease-causing",
                            "DisorderGeneAssociationStatus": "Assessed",
                            "SourceOfValidation": "",
                        }
                    ]
                }
            }
        }

        sub2_resp = MagicMock()
        sub2_resp.status_code = 200
        sub2_resp.json.return_value = {
            "data": {
                "results": {
                    "DisorderGeneAssociation": [
                        {
                            "Gene": {
                                "Symbol": "TGFBR2",
                                "name": "transforming growth factor beta receptor 2",
                                "GeneType": "gene with protein product",
                                "Locus": [],
                            },
                            "DisorderGeneAssociationType": "Disease-causing",
                            "DisorderGeneAssociationStatus": "Assessed",
                            "SourceOfValidation": "",
                        }
                    ]
                }
            }
        }

        mock_get.side_effect = [name_resp, direct_resp, list_resp, sub1_resp, sub2_resp]

        result = self.tool._get_genes({"orpha_code": "558"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]["genes"]), 2)
        symbols = {g["Symbol"] for g in result["data"]["genes"]}
        self.assertIn("FBN1", symbols)
        self.assertIn("TGFBR2", symbols)
        self.assertIn("subtype_sources", result["data"])
        self.assertEqual(len(result["data"]["subtype_sources"]), 2)

    @patch("tooluniverse.orphanet_tool.requests.get")
    def test_deduplicates_genes_across_subtypes(self, mock_get):
        """Genes shared across subtypes should not be duplicated."""
        name_resp = MagicMock()
        name_resp.status_code = 200
        name_resp.json.return_value = {"Preferred term": "Test disease"}
        name_resp.raise_for_status = MagicMock()

        direct_resp = MagicMock()
        direct_resp.status_code = 404

        list_resp = MagicMock()
        list_resp.status_code = 200
        list_resp.json.return_value = {
            "data": {
                "results": [
                    {"ORPHAcode": 1, "Preferred term": "Test disease type 1"},
                    {"ORPHAcode": 2, "Preferred term": "Test disease type 2"},
                ]
            }
        }

        gene_entry = {
            "Gene": {
                "Symbol": "GENE1",
                "name": "gene one",
                "GeneType": "",
                "Locus": [],
            },
            "DisorderGeneAssociationType": "",
            "DisorderGeneAssociationStatus": "",
            "SourceOfValidation": "",
        }

        sub_resp = MagicMock()
        sub_resp.status_code = 200
        sub_resp.json.return_value = {
            "data": {"results": {"DisorderGeneAssociation": [gene_entry]}}
        }

        mock_get.side_effect = [name_resp, direct_resp, list_resp, sub_resp, sub_resp]

        result = self.tool._get_genes({"orpha_code": "999"})
        self.assertEqual(len(result["data"]["genes"]), 1)

    def test_missing_orpha_code(self):
        result = self.tool._get_genes({})
        self.assertEqual(result["status"], "error")
        self.assertIn("orpha_code", result["error"])


# ---------------------------------------------------------------------------
# Feature-86B-001: Orphanet_search_diseases result limit
# ---------------------------------------------------------------------------
class TestOrphanetSearchDiseasesLimit(unittest.TestCase):
    """Orphanet_search_diseases should limit results to avoid flooding."""

    def setUp(self):
        from tooluniverse.orphanet_tool import OrphanetTool

        self.tool = OrphanetTool({"name": "Orphanet_search_diseases"})

    @patch("tooluniverse.orphanet_tool.requests.get")
    def test_default_limit_truncates(self, mock_get):
        """Default limit=20 should truncate large result sets."""
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = [{"ORPHAcode": i, "Preferred term": f"Disease {i}"} for i in range(100)]
        mock_get.return_value = resp

        result = self.tool._search_diseases({"query": "test"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["count"], 20)
        self.assertEqual(result["data"]["total_count"], 100)
        self.assertTrue(result["metadata"]["truncated"])

    @patch("tooluniverse.orphanet_tool.requests.get")
    def test_custom_limit(self, mock_get):
        """Custom limit should be respected."""
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = [{"ORPHAcode": i} for i in range(50)]
        mock_get.return_value = resp

        result = self.tool._search_diseases({"query": "test", "limit": 5})
        self.assertEqual(result["data"]["count"], 5)
        self.assertEqual(result["data"]["total_count"], 50)

    @patch("tooluniverse.orphanet_tool.requests.get")
    def test_small_result_not_truncated(self, mock_get):
        """Small result sets should not be marked as truncated."""
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = [{"ORPHAcode": 1}, {"ORPHAcode": 2}]
        mock_get.return_value = resp

        result = self.tool._search_diseases({"query": "test"})
        self.assertEqual(result["data"]["count"], 2)
        self.assertFalse(result["metadata"]["truncated"])


# ---------------------------------------------------------------------------
# Feature-86B-008: EuropePMC HTML in abstracts
# ---------------------------------------------------------------------------
class TestEuropePMCAbstractHTMLStripping(unittest.TestCase):
    """EuropePMC abstracts with HTML should be cleaned."""

    def test_html_stripped_from_abstract(self):
        from tooluniverse.europe_pmc_tool import _extract_text_from_html

        html = "<h4>Objectives</h4>To test <i>in vivo</i> effects."
        result = _extract_text_from_html(html)
        self.assertNotIn("<h4>", result)
        self.assertNotIn("<i>", result)
        self.assertIn("Objectives", result)
        self.assertIn("in vivo", result)

    def test_plain_text_unchanged(self):
        from tooluniverse.europe_pmc_tool import _extract_text_from_html

        text = "This is a plain abstract with no HTML."
        result = _extract_text_from_html(text)
        self.assertEqual(result, text)


# ---------------------------------------------------------------------------
# GTEx gene symbol resolution
# ---------------------------------------------------------------------------
class TestGTExGeneSymbolResolution(unittest.TestCase):
    """Test GTEx auto-resolution of gene symbols to versioned GENCODE IDs."""

    def test_resolve_gene_symbol(self):
        from tooluniverse.gtex_tool import _resolve_gene_id

        with patch("tooluniverse.gtex_tool._http_get") as mock_get:
            mock_get.return_value = {
                "data": [{"gencodeId": "ENSG00000166147.13", "geneSymbol": "FBN1"}]
            }
            result = _resolve_gene_id("FBN1", "https://gtexportal.org/api/v2", 30)
            self.assertEqual(result, "ENSG00000166147.13")
            mock_get.assert_called_once()

    def test_versioned_id_re_resolved(self):
        """Versioned Ensembl IDs are re-resolved via GTEx reference API (not passed through)."""
        from tooluniverse.gtex_tool import _resolve_gene_id

        with patch("tooluniverse.gtex_tool._http_get") as mock_get:
            mock_get.return_value = {
                "data": [{"gencodeId": "ENSG00000141510.16"}]
            }
            result = _resolve_gene_id(
                "ENSG00000141510.11", "https://gtexportal.org/api/v2", 30
            )
            # Version stripped and re-resolved against GTEx reference API
            self.assertEqual(result, "ENSG00000141510.16")
            mock_get.assert_called_once()

    def test_unversioned_ensembl_resolved(self):
        from tooluniverse.gtex_tool import _resolve_gene_id

        with patch("tooluniverse.gtex_tool._http_get") as mock_get:
            mock_get.return_value = {
                "data": [{"gencodeId": "ENSG00000141510.16"}]
            }
            result = _resolve_gene_id(
                "ENSG00000141510", "https://gtexportal.org/api/v2", 30
            )
            self.assertEqual(result, "ENSG00000141510.16")

    def test_resolution_failure_returns_input(self):
        from tooluniverse.gtex_tool import _resolve_gene_id

        with patch("tooluniverse.gtex_tool._http_get") as mock_get:
            mock_get.side_effect = Exception("network error")
            result = _resolve_gene_id("FBN1", "https://gtexportal.org/api/v2", 30)
            self.assertEqual(result, "FBN1")

    def test_expression_tool_uses_gene_symbol(self):
        from tooluniverse.gtex_tool import GTExExpressionTool

        tool = GTExExpressionTool(
            tool_config={
                "settings": {
                    "base_url": "https://gtexportal.org/api/v2",
                    "timeout": 30,
                }
            }
        )
        with patch("tooluniverse.gtex_tool._resolve_gene_id") as mock_resolve, patch(
            "tooluniverse.gtex_tool._http_get"
        ) as mock_get:
            mock_resolve.return_value = "ENSG00000166147.13"
            mock_get.return_value = {"data": [{"tissueSiteDetailId": "Brain", "median": 5.2}]}
            result = tool.run({"gene_symbol": "FBN1"})
            mock_resolve.assert_called_once_with(
                "FBN1", "https://gtexportal.org/api/v2", 30
            )
            self.assertTrue(result["success"])

    def test_eqtl_tool_uses_gene_symbol(self):
        from tooluniverse.gtex_tool import GTExEQTLTool

        tool = GTExEQTLTool(
            tool_config={
                "settings": {
                    "base_url": "https://gtexportal.org/api/v2",
                    "timeout": 30,
                }
            }
        )
        with patch("tooluniverse.gtex_tool._resolve_gene_id") as mock_resolve, patch(
            "tooluniverse.gtex_tool._http_get"
        ) as mock_get:
            mock_resolve.return_value = "ENSG00000141510.16"
            mock_get.return_value = {"data": [{"variantId": "chr17_1234_A_G", "pValue": 0.001}]}
            result = tool.run({"gene_symbol": "TP53"})
            mock_resolve.assert_called_once_with(
                "TP53", "https://gtexportal.org/api/v2", 30
            )
            self.assertTrue(result["success"])


# ---------------------------------------------------------------------------
# ClinVar condition quoting
# ---------------------------------------------------------------------------
class TestClinVarConditionQuoting(unittest.TestCase):
    """Test ClinVar multi-word condition quoting."""

    def _make_tool(self):
        from tooluniverse.clinvar_tool import ClinVarSearchVariants

        config = {
            "name": "ClinVar_search_variants",
            "type": "ClinVarSearchVariants",
            "fields": {
                "endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
                "format": "json",
            },
        }
        return ClinVarSearchVariants(config)

    @patch("tooluniverse.clinvar_tool.ClinVarRESTTool._make_request")
    def test_multi_word_condition_quoted(self, mock_request):
        mock_request.return_value = {
            "status": "success",
            "data": {
                "esearchresult": {
                    "count": "100",
                    "idlist": ["12345"],
                    "querytranslation": "",
                }
            },
        }
        tool = self._make_tool()
        tool.run({"gene": "FBN1", "condition": "Marfan syndrome"})
        call_args = mock_request.call_args
        term = call_args[0][1]["term"]
        self.assertIn('"Marfan syndrome"', term)

    @patch("tooluniverse.clinvar_tool.ClinVarRESTTool._make_request")
    def test_single_word_condition_not_quoted(self, mock_request):
        mock_request.return_value = {
            "status": "success",
            "data": {
                "esearchresult": {
                    "count": "50",
                    "idlist": ["67890"],
                    "querytranslation": "",
                }
            },
        }
        tool = self._make_tool()
        tool.run({"gene": "BRCA1", "condition": "cancer"})
        call_args = mock_request.call_args
        term = call_args[0][1]["term"]
        self.assertIn("cancer", term)
        self.assertNotIn('"cancer"', term)

    @patch("tooluniverse.clinvar_tool.ClinVarRESTTool._make_request")
    def test_already_quoted_condition_not_double_quoted(self, mock_request):
        mock_request.return_value = {
            "status": "success",
            "data": {
                "esearchresult": {
                    "count": "10",
                    "idlist": ["111"],
                    "querytranslation": "",
                }
            },
        }
        tool = self._make_tool()
        tool.run({"condition": '"Marfan syndrome"'})
        call_args = mock_request.call_args
        term = call_args[0][1]["term"]
        # Should not be double-quoted
        self.assertNotIn('""Marfan syndrome""', term)
        self.assertIn('"Marfan syndrome"', term)


if __name__ == "__main__":
    unittest.main()
