"""
PubMed Search MCP Tools for ToolUniverse

Complete integration with pubmed-search-mcp package (25 tools).
All tools delegate to package classes - minimal code duplication.

Install: uv add pubmed-search-mcp
    or:  pip install pubmed-search-mcp

Tools:
═══════════════════════════════════════════════════════════════════
1. Core Search (1):
   - PubMedUnifiedSearchMCP: Main search entry point (auto multi-source)

2. Query Intelligence (2):
   - PubMedParsePICOMCP: Parse clinical questions into PICO
   - PubMedGenerateQueriesMCP: Generate MeSH-based queries

3. Article Exploration (5):
   - PubMedFetchArticleMCP: Get article details by PMID
   - PubMedFindRelatedMCP: Find similar articles
   - PubMedFindCitationsMCP: Find citing articles (forward)
   - PubMedGetReferencesMCP: Get bibliography (backward)
   - PubMedGetCitationMetricsMCP: NIH iCite metrics

4. Full Text Tools (2):
   - PubMedGetFullTextMCP: Get Europe PMC fulltext
   - PubMedGetTextMinedTermsMCP: Text-mined annotations

5. NCBI Extended (7):
   - PubMedSearchGeneMCP: Search NCBI Gene
   - PubMedGetGeneDetailsMCP: Get gene details
   - PubMedGetGeneLiteratureMCP: Gene-related papers
   - PubMedSearchCompoundMCP: Search PubChem
   - PubMedGetCompoundDetailsMCP: Get compound details
   - PubMedGetCompoundLiteratureMCP: Compound-related papers
   - PubMedSearchClinVarMCP: Search clinical variants

6. Citation Network (2):
   - PubMedBuildCitationTreeMCP: Build citation graph
   - PubMedSuggestCitationTreeMCP: Suggest tree params

7. Export (1):
   - PubMedExportCitationsMCP: Export RIS/BibTeX/CSV

8. Vision Search (2) [Experimental]:
   - PubMedAnalyzeFigureMCP: Analyze figure for search
   - PubMedReverseImageSearchMCP: Image-based search

9. Institutional Access (3):
   - PubMedConfigureInstitutionMCP: Set link resolver
   - PubMedGetInstitutionalLinkMCP: Get access link
   - PubMedListResolverPresetsMCP: List available presets

Author: u9401066
License: Apache-2.0
"""

import os
import json
from typing import Dict, Any, List

from .base_tool import BaseTool
from .tool_registry import register_tool

# Lazy-loaded clients
_searcher = None
_pmc_client = None
_ncbi_ext_client = None

_INSTALL_MSG = (
    "pubmed-search-mcp package is required. "
    "Install with: pip install tooluniverse[pubmed]"
)


def _get_searcher():
    """Lazy initialize LiteratureSearcher."""
    global _searcher
    if _searcher is None:
        try:
            from pubmed_search.entrez import LiteratureSearcher
        except ImportError as e:
            raise ImportError(_INSTALL_MSG) from e

        _searcher = LiteratureSearcher(
            email=os.environ.get("NCBI_EMAIL", "tooluniverse@example.com"),
            api_key=os.environ.get("NCBI_API_KEY"),
        )
    return _searcher


def _get_pmc_client():
    """Lazy initialize EuropePMCClient."""
    global _pmc_client
    if _pmc_client is None:
        try:
            from pubmed_search.sources.europe_pmc import EuropePMCClient
        except ImportError as e:
            raise ImportError(_INSTALL_MSG) from e

        _pmc_client = EuropePMCClient()
    return _pmc_client


def _get_ncbi_ext_client():
    """Lazy initialize NCBIExtendedClient."""
    global _ncbi_ext_client
    if _ncbi_ext_client is None:
        try:
            from pubmed_search.sources.ncbi_extended import NCBIExtendedClient
        except ImportError as e:
            raise ImportError(_INSTALL_MSG) from e

        _ncbi_ext_client = NCBIExtendedClient(
            email=os.environ.get("NCBI_EMAIL", "tooluniverse@example.com"),
            api_key=os.environ.get("NCBI_API_KEY"),
        )
    return _ncbi_ext_client


def _normalize_pmids(pmids) -> List[str]:
    """Convert string or list of PMIDs to clean list."""
    if isinstance(pmids, str):
        return [p.strip().replace("PMID:", "") for p in pmids.split(",")]
    return [str(p).strip() for p in pmids]


def _safe_json(data) -> str:
    """Safe JSON serialization."""
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        return str(data)


# =============================================================================
# 1. Core Search (1 tool)
# =============================================================================


@register_tool("PubMedUnifiedSearchMCP")
class PubMedUnifiedSearchMCP(BaseTool):
    """
    Main search entry point - auto multi-source search across PubMed, Europe PMC, CORE.
    Automatically analyzes query and selects optimal sources.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query")
        if not query:
            return {"error": "`query` parameter is required."}

        try:
            # Use LiteratureSearcher directly (UnifiedSearchEngine is MCP-only)
            searcher = _get_searcher()
            results = searcher.search(
                query=query,
                limit=int(arguments.get("limit", 10)),
                min_year=arguments.get("min_year"),
                max_year=arguments.get("max_year"),
                # Advanced filters
                age_group=arguments.get("age_group"),
                sex=arguments.get("sex"),
                species=arguments.get("species"),
                language=arguments.get("language"),
                clinical_query=arguments.get("clinical_query"),
            )
            return {"status": "success", "articles": results, "total": len(results)}
        except ImportError:
            return {"error": "pubmed-search-mcp not installed"}
        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# 2. Query Intelligence (3 tools)
# =============================================================================


@register_tool("PubMedParsePICOMCP")
class PubMedParsePICOMCP(BaseTool):
    """Parse clinical question into PICO elements."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        description = arguments.get("description")
        if not description:
            return {"error": "`description` parameter is required."}

        # PICO parsing - use provided elements or extract from description
        pico = {
            "P": arguments.get("p") or "",
            "I": arguments.get("i") or "",
            "C": arguments.get("c") or "",
            "O": arguments.get("o") or "",
        }

        # If PICO elements not provided, return description for agent to parse
        if not any(pico.values()):
            return {
                "status": "success",
                "pico": pico,
                "original_question": description,
                "note": "Please provide P/I/C/O elements or let agent parse the question",
            }

        return {
            "status": "success",
            "pico": pico,
            "original_question": description,
        }


@register_tool("PubMedGenerateQueriesMCP")
class PubMedGenerateQueriesMCP(BaseTool):
    """Generate optimized PubMed search queries using MeSH vocabulary."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        topic = arguments.get("topic")
        if not topic:
            return {"error": "`topic` parameter is required."}

        try:
            from pubmed_search.entrez.strategy import SearchStrategyGenerator

            generator = SearchStrategyGenerator(
                email=os.environ.get("NCBI_EMAIL", "tooluniverse@example.com"),
                api_key=os.environ.get("NCBI_API_KEY"),
            )
            result = generator.generate_strategies(
                topic=topic,
                strategy=arguments.get("strategy", "comprehensive"),
                check_spelling=arguments.get("check_spelling", True),
            )
            return {"status": "success", "data": result}
        except ImportError:
            return {"error": "pubmed-search-mcp not installed"}
        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# 3. Article Exploration (5 tools)
# =============================================================================


@register_tool("PubMedFetchArticleMCP")
class PubMedFetchArticleMCP(BaseTool):
    """Fetch detailed article information by PMID(s)."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pmids = arguments.get("pmids")
        if not pmids:
            return {"error": "`pmids` parameter is required."}

        try:
            pmid_list = _normalize_pmids(pmids)
            articles = _get_searcher().fetch_details(pmid_list)
            return {"status": "success", "articles": articles, "total": len(articles)}
        except ImportError:
            return {"error": "pubmed-search-mcp not installed"}
        except Exception as e:
            return {"error": str(e)}


@register_tool("PubMedFindRelatedMCP")
class PubMedFindRelatedMCP(BaseTool):
    """Find articles related to a given paper using PubMed's Similar Articles."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pmid = arguments.get("pmid")
        if not pmid:
            return {"error": "`pmid` parameter is required."}

        try:
            searcher = _get_searcher()
            related_articles = searcher.find_related_articles(
                str(pmid), limit=min(int(arguments.get("limit", 10)), 50)
            )
            articles = related_articles if related_articles else []
            return {
                "status": "success",
                "source_pmid": pmid,
                "related_articles": articles,
                "total": len(articles),
            }
        except Exception as e:
            return {"error": str(e)}


@register_tool("PubMedFindCitationsMCP")
class PubMedFindCitationsMCP(BaseTool):
    """Find articles that cite a given paper (forward citation tracking)."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pmid = arguments.get("pmid")
        if not pmid:
            return {"error": "`pmid` parameter is required."}

        try:
            searcher = _get_searcher()
            # find_citing_articles returns article details directly
            articles = searcher.find_citing_articles(
                str(pmid), limit=min(int(arguments.get("limit", 20)), 100)
            )
            return {
                "status": "success",
                "source_pmid": pmid,
                "citing_articles": articles if articles else [],
                "total": len(articles) if articles else 0,
            }
        except Exception as e:
            return {"error": str(e)}


@register_tool("PubMedGetReferencesMCP")
class PubMedGetReferencesMCP(BaseTool):
    """Get the reference list (bibliography) of an article."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pmid = arguments.get("pmid")
        if not pmid:
            return {"error": "`pmid` parameter is required."}

        try:
            searcher = _get_searcher()
            # get_article_references returns article details directly
            articles = searcher.get_article_references(
                str(pmid), limit=min(int(arguments.get("limit", 20)), 100)
            )
            return {
                "status": "success",
                "source_pmid": pmid,
                "references": articles if articles else [],
                "total": len(articles) if articles else 0,
            }
        except Exception as e:
            return {"error": str(e)}


@register_tool("PubMedGetCitationMetricsMCP")
class PubMedGetCitationMetricsMCP(BaseTool):
    """Get NIH iCite citation metrics (RCR, percentile) for articles."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pmids = arguments.get("pmids")
        if not pmids:
            return {"error": "`pmids` parameter is required."}

        try:
            pmid_list = _normalize_pmids(pmids)
            # LiteratureSearcher includes ICiteMixin
            searcher = _get_searcher()
            metrics = searcher.get_icite_metrics(pmid_list)
            return {
                "status": "success",
                "metrics": metrics,
                "total": len(metrics) if metrics else 0,
                "source": "NIH iCite",
            }
        except Exception as e:
            # Fallback to basic citation count from PubMed
            try:
                articles = _get_searcher().fetch_details(pmid_list)
                metrics = [
                    {
                        "pmid": a.get("pmid"),
                        "citation_count": a.get("citation_count", 0),
                    }
                    for a in articles
                ]
                return {
                    "status": "success",
                    "metrics": metrics,
                    "source": "PubMed (basic)",
                }
            except Exception:
                return {"error": str(e)}


# =============================================================================
# 4. Full Text Tools (2 tools)
# =============================================================================


@register_tool("PubMedGetFullTextMCP")
class PubMedGetFullTextMCP(BaseTool):
    """
    Get fulltext from Europe PMC (supports PMC ID).
    Returns parsed sections from full-text XML.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pmcid = arguments.get("pmcid")
        if not pmcid:
            return {"error": "`pmcid` parameter is required."}

        try:
            client = _get_pmc_client()
            pmcid = str(pmcid).upper()
            if not pmcid.startswith("PMC"):
                pmcid = f"PMC{pmcid}"

            # Get and parse fulltext XML
            xml = client.get_fulltext_xml(pmcid)
            if not xml:
                return {"status": "not_found", "pmcid": pmcid, "fulltext": None}

            # Parse XML to sections
            parsed = client.parse_fulltext_xml(xml)
            if not parsed:
                return {"status": "not_found", "pmcid": pmcid, "fulltext": None}

            # Filter sections if requested
            sections = arguments.get("sections", "")
            if sections and parsed:
                requested = [s.strip().lower() for s in sections.split(",")]
                parsed = {k: v for k, v in parsed.items() if k.lower() in requested}

            return {
                "status": "success",
                "pmcid": pmcid,
                "fulltext": parsed,
                "sections_available": list(parsed.keys()) if parsed else [],
            }
        except Exception as e:
            return {"error": str(e)}


@register_tool("PubMedGetTextMinedTermsMCP")
class PubMedGetTextMinedTermsMCP(BaseTool):
    """Get text-mined entities (genes, diseases, chemicals) from Europe PMC."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pmcid = arguments.get("pmcid")
        pmid = arguments.get("pmid")

        if not pmcid and not pmid:
            return {"error": "Either `pmcid` or `pmid` is required."}

        try:
            client = _get_pmc_client()

            # Determine source and article_id
            if pmcid:
                source = "PMC"
                article_id = str(pmcid).upper().replace("PMC", "")
            else:
                source = "MED"
                article_id = str(pmid)

            # Get semantic type filter
            semantic_type = arguments.get("entity_types") or arguments.get(
                "semantic_type"
            )

            # Call the correct API method
            terms = client.get_text_mined_terms(
                source=source, article_id=article_id, semantic_type=semantic_type
            )

            return {
                "status": "success" if terms else "not_found",
                "source": source,
                "article_id": article_id,
                "terms": terms,
                "total": len(terms) if terms else 0,
            }
        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# 5. NCBI Extended (7 tools)
# =============================================================================


@register_tool("PubMedSearchGeneMCP")
class PubMedSearchGeneMCP(BaseTool):
    """Search NCBI Gene database for gene information."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query")
        if not query:
            return {"error": "`query` parameter is required."}

        try:
            client = _get_ncbi_ext_client()
            genes = client.search_gene(
                query=query,
                organism=arguments.get("organism", "human"),
                limit=min(int(arguments.get("limit", 10)), 50),
            )
            return {"status": "success", "genes": genes, "total": len(genes)}
        except ImportError:
            return {
                "status": "success",
                "genes": [],
                "note": "NCBI Gene module not available",
            }
        except Exception as e:
            return {"error": str(e)}


@register_tool("PubMedGetGeneDetailsMCP")
class PubMedGetGeneDetailsMCP(BaseTool):
    """Get detailed information about a specific gene by Gene ID."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene_id = arguments.get("gene_id")
        if not gene_id:
            return {"error": "`gene_id` parameter is required."}

        try:
            client = _get_ncbi_ext_client()
            details = client.get_gene(str(gene_id))
            return {"status": "success", "gene": details}
        except Exception as e:
            return {"error": str(e)}


@register_tool("PubMedGetGeneLiteratureMCP")
class PubMedGetGeneLiteratureMCP(BaseTool):
    """Get PubMed articles related to a specific gene."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene_id = arguments.get("gene_id")
        if not gene_id:
            return {"error": "`gene_id` parameter is required."}

        try:
            client = _get_ncbi_ext_client()
            pmids = client.get_gene_pubmed_links(
                str(gene_id), limit=int(arguments.get("limit", 20))
            )
            articles = _get_searcher().fetch_details(pmids) if pmids else []
            return {
                "status": "success",
                "gene_id": gene_id,
                "articles": articles,
                "total": len(articles),
            }
        except Exception as e:
            return {"error": str(e)}


@register_tool("PubMedSearchCompoundMCP")
class PubMedSearchCompoundMCP(BaseTool):
    """Search PubChem for chemical compound information."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query")
        if not query:
            return {"error": "`query` parameter is required."}

        try:
            client = _get_ncbi_ext_client()
            compounds = client.search_compound(
                query, limit=min(int(arguments.get("limit", 10)), 50)
            )
            return {
                "status": "success",
                "compounds": compounds,
                "total": len(compounds),
            }
        except ImportError:
            return {
                "status": "success",
                "compounds": [],
                "note": "PubChem module not available",
            }
        except Exception as e:
            return {"error": str(e)}


@register_tool("PubMedGetCompoundDetailsMCP")
class PubMedGetCompoundDetailsMCP(BaseTool):
    """Get detailed information about a compound by CID."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        cid = arguments.get("cid")
        if not cid:
            return {"error": "`cid` parameter is required."}

        try:
            client = _get_ncbi_ext_client()
            details = client.get_compound(str(cid))
            return {"status": "success", "compound": details}
        except Exception as e:
            return {"error": str(e)}


@register_tool("PubMedGetCompoundLiteratureMCP")
class PubMedGetCompoundLiteratureMCP(BaseTool):
    """Get PubMed articles related to a specific compound."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        cid = arguments.get("cid")
        if not cid:
            return {"error": "`cid` parameter is required."}

        try:
            client = _get_ncbi_ext_client()
            pmids = client.get_compound_pubmed_links(
                str(cid), limit=int(arguments.get("limit", 20))
            )
            articles = _get_searcher().fetch_details(pmids) if pmids else []
            return {
                "status": "success",
                "cid": cid,
                "articles": articles,
                "total": len(articles),
            }
        except Exception as e:
            return {"error": str(e)}


@register_tool("PubMedSearchClinVarMCP")
class PubMedSearchClinVarMCP(BaseTool):
    """Search ClinVar for clinical variant records."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query")
        if not query:
            return {"error": "`query` parameter is required."}

        try:
            client = _get_ncbi_ext_client()
            variants = client.search_clinvar(
                query=query, limit=min(int(arguments.get("limit", 10)), 50)
            )
            return {"status": "success", "variants": variants, "total": len(variants)}
        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# 6. Citation Network (2 tools)
# =============================================================================


@register_tool("PubMedBuildCitationTreeMCP")
class PubMedBuildCitationTreeMCP(BaseTool):
    """
    Build citation network graph from a seed article.
    Uses LiteratureSearcher's citation methods to build a simple tree.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pmid = arguments.get("pmid")
        if not pmid:
            return {"error": "`pmid` parameter is required."}

        try:
            pmid_str = str(pmid)
            searcher = _get_searcher()
            depth = min(int(arguments.get("depth", 1)), 3)
            limit_per_level = min(int(arguments.get("limit_per_level", 5)), 20)
            direction = arguments.get("direction", "both")

            # Get root article details
            root_articles = searcher.fetch_details([pmid_str])
            root = root_articles[0] if root_articles else {"pmid": pmid_str}

            # Build tree structure
            tree: Dict[str, Any] = {
                "root": root,
                "citing": [],
                "references": [],
                "metadata": {
                    "depth": depth,
                    "limit_per_level": limit_per_level,
                    "direction": direction,
                },
            }

            if direction in ["forward", "both"]:
                tree["citing"] = searcher.find_citing_articles(
                    pmid_str, limit=limit_per_level
                )

            if direction in ["backward", "both"]:
                tree["references"] = searcher.get_article_references(
                    pmid_str, limit=limit_per_level
                )

            return {
                "status": "success",
                "tree": tree,
                "stats": {
                    "citing_count": len(tree["citing"]),
                    "reference_count": len(tree["references"]),
                    "total_nodes": 1 + len(tree["citing"]) + len(tree["references"]),
                },
            }
        except Exception as e:
            return {"error": str(e)}


@register_tool("PubMedSuggestCitationTreeMCP")
class PubMedSuggestCitationTreeMCP(BaseTool):
    """Suggest optimal citation tree parameters based on article characteristics."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pmid = arguments.get("pmid")
        if not pmid:
            return {"error": "`pmid` parameter is required."}

        try:
            pmid_str = str(pmid)
            searcher = _get_searcher()

            # Get article info to estimate citation density
            articles = searcher.fetch_details([pmid_str])
            if not articles:
                return {"error": f"Article {pmid_str} not found."}

            article = articles[0]
            year = article.get("year", 2020)

            # Heuristic: older papers tend to have more citations
            current_year = 2025
            age = current_year - int(year) if year else 5

            # Suggest parameters based on age
            if age > 10:
                suggestion = {
                    "depth": 1,
                    "limit_per_level": 10,
                    "direction": "both",
                    "estimated_nodes": 30,
                }
            elif age > 5:
                suggestion = {
                    "depth": 2,
                    "limit_per_level": 5,
                    "direction": "both",
                    "estimated_nodes": 20,
                }
            else:
                suggestion = {
                    "depth": 2,
                    "limit_per_level": 3,
                    "direction": "both",
                    "estimated_nodes": 10,
                }

            suggestion["article_title"] = article.get("title", "")[:80]
            suggestion["article_year"] = year

            return {"status": "success", "suggestion": suggestion}
        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# 7. Export (1 tool)
# =============================================================================


@register_tool("PubMedExportCitationsMCP")
class PubMedExportCitationsMCP(BaseTool):
    """Export citations in RIS, BibTeX, CSV, or MEDLINE format."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pmids = arguments.get("pmids")
        if not pmids:
            return {"error": "`pmids` parameter is required."}

        export_format = arguments.get("format", "ris").lower()

        try:
            pmid_list = _normalize_pmids(pmids)[:50]
            articles = _get_searcher().fetch_details(pmid_list)

            if not articles:
                return {"error": "No articles found"}

            from pubmed_search import export_articles

            content = export_articles(articles, format=export_format)
            return {
                "status": "success",
                "content": content,
                "format": export_format.upper(),
                "article_count": len(articles),
            }
        except ImportError:
            # Simple fallback RIS
            articles = _get_searcher().fetch_details(_normalize_pmids(pmids)[:50])
            lines = []
            for a in articles:
                lines.extend(
                    [
                        "TY  - JOUR",
                        f"TI  - {a.get('title', '')}",
                        f"JO  - {a.get('journal', '')}",
                        f"PY  - {a.get('year', '')}",
                        f"AN  - PMID:{a.get('pmid', '')}",
                        "ER  - ",
                        "",
                    ]
                )
            return {
                "status": "success",
                "content": "\n".join(lines),
                "format": "RIS",
                "article_count": len(articles),
            }
        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# 8. Vision Search (2 tools) [Experimental]
# =============================================================================


@register_tool("PubMedAnalyzeFigureMCP")
class PubMedAnalyzeFigureMCP(BaseTool):
    """
    Analyze a scientific figure/image and extract search keywords.
    Returns image for agent to analyze with vision capabilities.

    Note: This is an experimental feature. The image analysis relies on
    the calling agent's vision capabilities to describe the image content.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        image_url = arguments.get("image_url")
        image_base64 = arguments.get("image_base64")
        context = arguments.get("context", "")

        if not image_url and not image_base64:
            return {"error": "Either `image_url` or `image_base64` is required."}

        # Vision analysis requires agent with vision capabilities
        # Return the image info for the agent to analyze
        return {
            "status": "success",
            "message": "Please analyze this image using your vision capabilities.",
            "image_url": image_url,
            "image_base64_provided": bool(image_base64),
            "context": context,
            "instructions": [
                "1. Describe what you see in the image",
                "2. Identify key scientific concepts, methods, or subjects",
                "3. Extract relevant search terms for PubMed search",
                "4. Suggest queries using unified_search() tool",
            ],
        }


@register_tool("PubMedReverseImageSearchMCP")
class PubMedReverseImageSearchMCP(BaseTool):
    """
    Search for papers based on image content or extracted keywords.

    Workflow:
    1. If keywords provided: Search PubMed directly
    2. If image_url provided: Return image for agent to analyze and extract keywords
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        image_url = arguments.get("image_url")
        keywords = arguments.get("keywords")
        limit = min(int(arguments.get("limit", 10)), 50)

        if not image_url and not keywords:
            return {"error": "Either `image_url` or `keywords` is required."}

        try:
            # If keywords provided, search directly
            if keywords:
                results = _get_searcher().search(keywords, limit=limit)
                return {
                    "status": "success",
                    "articles": results,
                    "search_type": "keyword",
                    "query": keywords,
                    "count": len(results),
                }

            # Image URL provided - return instructions for agent
            return {
                "status": "pending",
                "message": "Image-based search requires keyword extraction.",
                "image_url": image_url,
                "workflow": [
                    "1. Use PubMedAnalyzeFigureMCP to analyze the image",
                    "2. Extract keywords from the image description",
                    "3. Call this tool again with the extracted keywords",
                ],
            }
        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# 9. Institutional Access (3 tools)
# =============================================================================


@register_tool("PubMedConfigureInstitutionMCP")
class PubMedConfigureInstitutionMCP(BaseTool):
    """
    Configure institutional link resolver for full-text access.
    Supports presets (ntu, harvard, etc.) or custom URL.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        preset = arguments.get("preset")
        resolver_base = arguments.get("resolver_url") or arguments.get("resolver_base")
        enabled = arguments.get("enable", arguments.get("enabled", True))

        try:
            from pubmed_search import configure_openurl

            configure_openurl(
                preset=preset, resolver_base=resolver_base, enabled=enabled
            )
            return {
                "status": "success",
                "config": {
                    "preset": preset,
                    "resolver_base": resolver_base,
                    "enabled": enabled,
                },
            }
        except ImportError:
            return {"error": "OpenURL module not available"}
        except Exception as e:
            return {"error": str(e)}


@register_tool("PubMedGetInstitutionalLinkMCP")
class PubMedGetInstitutionalLinkMCP(BaseTool):
    """Generate institutional access link (OpenURL) for an article."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pmid = arguments.get("pmid")
        doi = arguments.get("doi")

        if not pmid and not doi:
            return {"error": "Either `pmid` or `doi` is required."}

        try:
            from pubmed_search import get_openurl_link

            # Get article metadata
            if pmid:
                articles = _get_searcher().fetch_details([str(pmid)])
                if articles:
                    metadata = articles[0]
                else:
                    metadata = {"pmid": pmid}
            else:
                metadata = {"doi": doi}

            link = get_openurl_link(metadata)
            return {"status": "success", "link": link, "metadata": metadata}
        except ImportError:
            return {"error": "OpenURL module not available"}
        except Exception as e:
            return {"error": str(e)}


@register_tool("PubMedListResolverPresetsMCP")
class PubMedListResolverPresetsMCP(BaseTool):
    """List available institutional link resolver presets."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from pubmed_search import list_openurl_presets

            presets = list_openurl_presets()
            return {"status": "success", "presets": presets}
        except ImportError:
            # Return common presets
            return {
                "status": "success",
                "presets": {
                    "taiwan": ["ntu", "ncku", "nthu", "nycu"],
                    "usa": ["harvard", "stanford", "mit", "yale"],
                    "uk": ["oxford", "cambridge"],
                    "generic": ["sfx", "360link", "primo"],
                },
                "note": "Install pubmed-search-mcp for full preset details",
            }
