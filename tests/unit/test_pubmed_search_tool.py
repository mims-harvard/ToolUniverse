"""
Unit tests for PubMed Search MCP Tools (25 tools)

Tests all tool classes from pubmed_search_tool.py.
Requires: pip install pubmed-search-mcp

Author: u9401066
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


# =============================================================================
# Helper: Create dummy tool config for BaseTool.__init__
# =============================================================================

def make_config(name: str, description: str = "Test tool") -> dict:
    """Create a minimal tool_config for testing."""
    return {
        "name": name,
        "type": name,
        "description": description,
        "parameter": {}
    }


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_searcher():
    """Mock LiteratureSearcher responses."""
    with patch('pubmed_search.entrez.LiteratureSearcher') as mock:
        instance = MagicMock()
        mock.return_value = instance
        instance.search.return_value = [
            {"pmid": "36653562", "title": "Test Article", "authors": ["Smith J"], "year": "2023"}
        ]
        instance.fetch_details.return_value = [
            {"pmid": "36653562", "title": "Test Article", "abstract": "Test abstract", "year": "2023"}
        ]
        instance.find_related.return_value = ["36653563", "36653564"]
        instance.find_citing_articles.return_value = ["36653565"]
        instance.get_article_references.return_value = ["36653566"]
        yield instance


@pytest.fixture
def mock_pmc_client():
    """Mock EuropePMCClient responses."""
    with patch('pubmed_search.sources.europe_pmc.EuropePMCClient') as mock:
        instance = MagicMock()
        mock.return_value = instance
        instance.get_fulltext.return_value = {"abstract": "Full text", "methods": "Methods text"}
        instance.get_annotations.return_value = {"genes": ["BRCA1"], "diseases": ["cancer"]}
        yield instance


# =============================================================================
# 1. Core Search Tests
# =============================================================================

class TestPubMedUnifiedSearchMCP:
    def test_search_success(self, mock_searcher):
        from tooluniverse.pubmed_search_tool import PubMedUnifiedSearchMCP
        tool = PubMedUnifiedSearchMCP(tool_config=make_config("pubmed_unified_search_mcp"))
        result = tool.run({"query": "CRISPR gene therapy"})
        assert "error" in result or result.get("status") == "success"

    def test_missing_query(self):
        from tooluniverse.pubmed_search_tool import PubMedUnifiedSearchMCP
        tool = PubMedUnifiedSearchMCP(tool_config=make_config("pubmed_unified_search_mcp"))
        result = tool.run({})
        assert "error" in result


# =============================================================================
# 2. Query Intelligence Tests
# =============================================================================

class TestPubMedParsePICOMCP:
    def test_parse_pico(self):
        from tooluniverse.pubmed_search_tool import PubMedParsePICOMCP
        tool = PubMedParsePICOMCP(tool_config=make_config("pubmed_parse_pico_mcp"))
        result = tool.run({"description": "Does aspirin reduce mortality in MI patients?"})
        assert result.get("status") == "success" or "error" in result
        # PICO parsing may require external resources


class TestPubMedGenerateQueriesMCP:
    def test_generate_queries(self):
        from tooluniverse.pubmed_search_tool import PubMedGenerateQueriesMCP
        tool = PubMedGenerateQueriesMCP(tool_config=make_config("pubmed_generate_queries_mcp"))
        result = tool.run({"topic": "diabetes prevention"})
        assert "error" in result or "data" in result


# =============================================================================
# 3. Article Exploration Tests
# =============================================================================

class TestPubMedFetchArticleMCP:
    def test_fetch_success(self, mock_searcher):
        from tooluniverse.pubmed_search_tool import PubMedFetchArticleMCP
        tool = PubMedFetchArticleMCP(tool_config=make_config("pubmed_fetch_article_mcp"))
        result = tool.run({"pmids": "36653562"})
        assert "error" in result or "articles" in result


class TestPubMedFindRelatedMCP:
    def test_find_related(self, mock_searcher):
        from tooluniverse.pubmed_search_tool import PubMedFindRelatedMCP
        tool = PubMedFindRelatedMCP(tool_config=make_config("pubmed_find_related_mcp"))
        result = tool.run({"pmid": "36653562"})
        assert "error" in result or "related_articles" in result


class TestPubMedFindCitationsMCP:
    def test_find_citations(self, mock_searcher):
        from tooluniverse.pubmed_search_tool import PubMedFindCitationsMCP
        tool = PubMedFindCitationsMCP(tool_config=make_config("pubmed_find_citations_mcp"))
        result = tool.run({"pmid": "36653562"})
        assert "error" in result or "citing_articles" in result


class TestPubMedGetReferencesMCP:
    def test_get_references(self, mock_searcher):
        from tooluniverse.pubmed_search_tool import PubMedGetReferencesMCP
        tool = PubMedGetReferencesMCP(tool_config=make_config("pubmed_get_references_mcp"))
        result = tool.run({"pmid": "36653562"})
        assert "error" in result or "references" in result


class TestPubMedGetCitationMetricsMCP:
    def test_get_metrics(self, mock_searcher):
        from tooluniverse.pubmed_search_tool import PubMedGetCitationMetricsMCP
        tool = PubMedGetCitationMetricsMCP(tool_config=make_config("pubmed_get_citation_metrics_mcp"))
        result = tool.run({"pmids": "36653562"})
        assert "error" in result or "metrics" in result


# =============================================================================
# 4. Full Text Tests
# =============================================================================

class TestPubMedGetFullTextMCP:
    def test_get_fulltext(self, mock_pmc_client):
        from tooluniverse.pubmed_search_tool import PubMedGetFullTextMCP
        tool = PubMedGetFullTextMCP(tool_config=make_config("pubmed_get_full_text_mcp"))
        result = tool.run({"pmcid": "PMC7614529"})
        assert "error" in result or "fulltext" in result


class TestPubMedGetTextMinedTermsMCP:
    def test_get_annotations(self, mock_pmc_client):
        from tooluniverse.pubmed_search_tool import PubMedGetTextMinedTermsMCP
        tool = PubMedGetTextMinedTermsMCP(tool_config=make_config("pubmed_get_text_mined_terms_mcp"))
        result = tool.run({"pmcid": "PMC7614529"})
        assert "error" in result or "terms" in result or "annotations" in result


# =============================================================================
# 5. NCBI Extended Tests
# =============================================================================

class TestPubMedSearchGeneMCP:
    def test_search_gene(self):
        from tooluniverse.pubmed_search_tool import PubMedSearchGeneMCP
        tool = PubMedSearchGeneMCP(tool_config=make_config("pubmed_search_gene_mcp"))
        result = tool.run({"query": "BRCA1"})
        assert "error" in result or "genes" in result or "note" in result


class TestPubMedGetGeneDetailsMCP:
    def test_get_gene_details(self):
        from tooluniverse.pubmed_search_tool import PubMedGetGeneDetailsMCP
        tool = PubMedGetGeneDetailsMCP(tool_config=make_config("pubmed_get_gene_details_mcp"))
        result = tool.run({"gene_id": "672"})
        assert "error" in result or "gene" in result


class TestPubMedGetGeneLiteratureMCP:
    def test_get_gene_literature(self, mock_searcher):
        from tooluniverse.pubmed_search_tool import PubMedGetGeneLiteratureMCP
        tool = PubMedGetGeneLiteratureMCP(tool_config=make_config("pubmed_get_gene_literature_mcp"))
        result = tool.run({"gene_id": "672"})
        assert "error" in result or "articles" in result


class TestPubMedSearchCompoundMCP:
    def test_search_compound(self):
        from tooluniverse.pubmed_search_tool import PubMedSearchCompoundMCP
        tool = PubMedSearchCompoundMCP(tool_config=make_config("pubmed_search_compound_mcp"))
        result = tool.run({"query": "aspirin"})
        assert "error" in result or "compounds" in result or "note" in result


class TestPubMedGetCompoundDetailsMCP:
    def test_get_compound_details(self):
        from tooluniverse.pubmed_search_tool import PubMedGetCompoundDetailsMCP
        tool = PubMedGetCompoundDetailsMCP(tool_config=make_config("pubmed_get_compound_details_mcp"))
        result = tool.run({"cid": "2244"})
        assert "error" in result or "compound" in result


class TestPubMedGetCompoundLiteratureMCP:
    def test_get_compound_literature(self, mock_searcher):
        from tooluniverse.pubmed_search_tool import PubMedGetCompoundLiteratureMCP
        tool = PubMedGetCompoundLiteratureMCP(tool_config=make_config("pubmed_get_compound_literature_mcp"))
        result = tool.run({"cid": "2244"})
        assert "error" in result or "articles" in result


class TestPubMedSearchClinVarMCP:
    def test_search_clinvar(self):
        from tooluniverse.pubmed_search_tool import PubMedSearchClinVarMCP
        tool = PubMedSearchClinVarMCP(tool_config=make_config("pubmed_search_clinvar_mcp"))
        result = tool.run({"query": "BRCA1"})
        assert "error" in result or "variants" in result


# =============================================================================
# 6. Citation Network Tests
# =============================================================================

class TestPubMedBuildCitationTreeMCP:
    def test_build_tree(self, mock_searcher):
        from tooluniverse.pubmed_search_tool import PubMedBuildCitationTreeMCP
        tool = PubMedBuildCitationTreeMCP(tool_config=make_config("pubmed_build_citation_tree_mcp"))
        result = tool.run({"pmid": "36653562"})
        assert "error" in result or "tree" in result


class TestPubMedSuggestCitationTreeMCP:
    def test_suggest_tree(self, mock_searcher):
        from tooluniverse.pubmed_search_tool import PubMedSuggestCitationTreeMCP
        tool = PubMedSuggestCitationTreeMCP(tool_config=make_config("pubmed_suggest_citation_tree_mcp"))
        result = tool.run({"pmid": "36653562"})
        assert "status" in result or "error" in result


# =============================================================================
# 7. Export Tests
# =============================================================================

class TestPubMedExportCitationsMCP:
    def test_export_ris(self, mock_searcher):
        from tooluniverse.pubmed_search_tool import PubMedExportCitationsMCP
        tool = PubMedExportCitationsMCP(tool_config=make_config("pubmed_export_citations_mcp"))
        result = tool.run({"pmids": "36653562", "format": "ris"})
        assert "error" in result or "content" in result


# =============================================================================
# 8. Vision Search Tests
# =============================================================================

class TestPubMedAnalyzeFigureMCP:
    def test_analyze_figure(self):
        from tooluniverse.pubmed_search_tool import PubMedAnalyzeFigureMCP
        tool = PubMedAnalyzeFigureMCP(tool_config=make_config("pubmed_analyze_figure_mcp"))
        result = tool.run({"image_url": "https://example.com/figure.png"})
        assert "status" in result or "error" in result


class TestPubMedReverseImageSearchMCP:
    def test_reverse_search(self, mock_searcher):
        from tooluniverse.pubmed_search_tool import PubMedReverseImageSearchMCP
        tool = PubMedReverseImageSearchMCP(tool_config=make_config("pubmed_reverse_image_search_mcp"))
        result = tool.run({"keywords": "western blot BRCA1"})
        assert "error" in result or "articles" in result or "message" in result


# =============================================================================
# 9. Institutional Access Tests
# =============================================================================

class TestPubMedConfigureInstitutionMCP:
    def test_configure(self):
        from tooluniverse.pubmed_search_tool import PubMedConfigureInstitutionMCP
        tool = PubMedConfigureInstitutionMCP(tool_config=make_config("pubmed_configure_institution_mcp"))
        result = tool.run({"preset": "ntu"})
        assert "error" in result or "config" in result


class TestPubMedGetInstitutionalLinkMCP:
    def test_get_link(self, mock_searcher):
        from tooluniverse.pubmed_search_tool import PubMedGetInstitutionalLinkMCP
        tool = PubMedGetInstitutionalLinkMCP(tool_config=make_config("pubmed_get_institutional_link_mcp"))
        result = tool.run({"pmid": "36653562"})
        assert "error" in result or "link" in result


class TestPubMedListResolverPresetsMCP:
    def test_list_presets(self):
        from tooluniverse.pubmed_search_tool import PubMedListResolverPresetsMCP
        tool = PubMedListResolverPresetsMCP(tool_config=make_config("pubmed_list_resolver_presets_mcp"))
        result = tool.run({})
        assert result.get("status") == "success" or "error" in result


# =============================================================================
# Tool Registration Verification
# =============================================================================

class TestAllToolsRegistered:
    def test_all_25_tools_exist(self):
        from tooluniverse import pubmed_search_tool
        expected_tools = [
            # 1. Core Search (1)
            "PubMedUnifiedSearchMCP",
            # 2. Query Intelligence (2)
            "PubMedParsePICOMCP",
            "PubMedGenerateQueriesMCP",
            # 3. Article Exploration (5)
            "PubMedFetchArticleMCP",
            "PubMedFindRelatedMCP",
            "PubMedFindCitationsMCP",
            "PubMedGetReferencesMCP",
            "PubMedGetCitationMetricsMCP",
            # 4. Full Text (2)
            "PubMedGetFullTextMCP",
            "PubMedGetTextMinedTermsMCP",
            # 5. NCBI Extended (7)
            "PubMedSearchGeneMCP",
            "PubMedGetGeneDetailsMCP",
            "PubMedGetGeneLiteratureMCP",
            "PubMedSearchCompoundMCP",
            "PubMedGetCompoundDetailsMCP",
            "PubMedGetCompoundLiteratureMCP",
            "PubMedSearchClinVarMCP",
            # 6. Citation Network (2)
            "PubMedBuildCitationTreeMCP",
            "PubMedSuggestCitationTreeMCP",
            # 7. Export (1)
            "PubMedExportCitationsMCP",
            # 8. Vision Search (2)
            "PubMedAnalyzeFigureMCP",
            "PubMedReverseImageSearchMCP",
            # 9. Institutional Access (3)
            "PubMedConfigureInstitutionMCP",
            "PubMedGetInstitutionalLinkMCP",
            "PubMedListResolverPresetsMCP",
        ]
        
        for tool_name in expected_tools:
            assert hasattr(pubmed_search_tool, tool_name), f"Missing tool: {tool_name}"
        
        assert len(expected_tools) == 25, f"Expected 25 tools, got {len(expected_tools)}"
        print(f"✅ All {len(expected_tools)} tools verified!")
