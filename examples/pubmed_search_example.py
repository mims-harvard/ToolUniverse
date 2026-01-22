"""
Example usage of PubMed Search Tools in ToolUniverse

This demonstrates how to use the 25 PubMed search tools after integration.

Prerequisites:
    uv add pubmed-search-mcp
    # or
    pip install pubmed-search-mcp

Usage:
    python examples/pubmed_search_example.py
"""

import os
import sys

# Add parent directory to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    from tooluniverse import ToolUniverse
except ImportError:
    print("Error: ToolUniverse not installed.")
    print("Run: uv add tooluniverse")
    sys.exit(1)

# Initialize ToolUniverse
print("Initializing ToolUniverse...")
tu = ToolUniverse()

# List all PubMed tools
print("\n" + "=" * 70)
print("Available PubMed Search Tools (25 total)")
print("=" * 70)
all_tools = tu.list_tools()
pubmed_tools = [t for t in all_tools if "pubmed" in t.lower()]
for tool_name in sorted(pubmed_tools):
    print(f"  - {tool_name}")

# ============================================================================
# Example 1: Basic Literature Search
# ============================================================================
print("\n" + "=" * 70)
print("Example 1: Multi-Source Literature Search")
print("=" * 70)

result = tu.run_tool(
    "pubmed_unified_search_mcp",
    {"query": "CRISPR gene therapy cancer", "limit": 5, "min_year": 2020},
)

if result.get("status") == "success":
    articles = result.get("articles", [])
    print(f"\nFound {len(articles)} articles")
    for i, article in enumerate(articles[:3], 1):
        print(f"\n{i}. {article.get('title', 'N/A')[:70]}...")
        print(
            f"   PMID: {article.get('pmid', 'N/A')} | Year: {article.get('year', 'N/A')}"
        )
else:
    print(f"Error: {result.get('error', 'Unknown error')}")

# ============================================================================
# Example 2: Fetch Article Details
# ============================================================================
print("\n" + "=" * 70)
print("Example 2: Fetch Article Details")
print("=" * 70)

result = tu.run_tool("pubmed_fetch_article_mcp", {"pmids": "38353755,38353756"})

if result.get("status") == "success":
    articles = result.get("articles", [])
    print(f"\nFetched {len(articles)} articles")
    for article in articles:
        print(f"\n  {article.get('title', 'N/A')[:60]}...")
        authors = article.get("authors", [])[:3]
        print(f"  Authors: {', '.join(authors) if authors else 'N/A'}")

# ============================================================================
# Example 3: Generate Optimized Queries with MeSH
# ============================================================================
print("\n" + "=" * 70)
print("Example 3: MeSH Query Expansion")
print("=" * 70)

result = tu.run_tool(
    "pubmed_generate_queries_mcp",
    {"topic": "diabetes treatment", "strategy": "comprehensive"},
)

if result.get("status") == "success":
    data = result.get("data", {})
    print(f"\nQuery expansion complete")
    print(f"  Original: diabetes treatment")
    if data:
        print(f"  MeSH terms: {len(data.get('mesh_terms', []))}")

# ============================================================================
# Example 4: Find Related Articles
# ============================================================================
print("\n" + "=" * 70)
print("Example 4: Find Similar Articles")
print("=" * 70)

result = tu.run_tool("pubmed_find_related_mcp", {"pmid": "38353755", "limit": 5})

if result.get("status") == "success":
    related = result.get("related_articles", [])
    print(f"\nFound {len(related)} related articles")
    for i, article in enumerate(related[:3], 1):
        print(f"  {i}. {article.get('title', 'N/A')[:60]}...")

# ============================================================================
# Example 5: Citation Tracking
# ============================================================================
print("\n" + "=" * 70)
print("Example 5: Forward and Backward Citation Tracking")
print("=" * 70)

# Forward citations (who cites this paper)
result = tu.run_tool("pubmed_find_citations_mcp", {"pmid": "38353755", "limit": 5})
if result.get("status") == "success":
    citing = result.get("citing_articles", [])
    print(f"\nForward: {len(citing)} articles cite this paper")

# Backward citations (references)
result = tu.run_tool("pubmed_get_references_mcp", {"pmid": "38353755", "limit": 5})
if result.get("status") == "success":
    refs = result.get("references", [])
    print(f"Backward: {len(refs)} references in this paper")

# ============================================================================
# Example 6: NIH iCite Citation Metrics
# ============================================================================
print("\n" + "=" * 70)
print("Example 6: NIH iCite Citation Metrics")
print("=" * 70)

result = tu.run_tool("pubmed_get_citation_metrics_mcp", {"pmids": "38353755"})

if result.get("status") == "success":
    metrics = result.get("metrics", [])
    print(f"\nCitation metrics from {result.get('source', 'iCite')}")
    for m in metrics:
        print(f"  PMID: {m.get('pmid')}")
        print(f"  Citation count: {m.get('citation_count', 'N/A')}")
        if m.get("rcr"):
            print(f"  RCR: {m.get('rcr', 'N/A')}")

# ============================================================================
# Example 7: Get Full Text from Europe PMC
# ============================================================================
print("\n" + "=" * 70)
print("Example 7: Retrieve Full Text")
print("=" * 70)

result = tu.run_tool(
    "pubmed_get_fulltext_mcp", {"pmcid": "PMC7096777", "sections": "introduction"}
)

if result.get("status") == "success":
    sections = result.get("sections_available", [])
    print(f"\nFull text retrieved for {result.get('pmcid')}")
    print(f"  Sections available: {', '.join(sections)}")

# ============================================================================
# Example 8: NCBI Extended - Gene Search
# ============================================================================
print("\n" + "=" * 70)
print("Example 8: NCBI Gene Search")
print("=" * 70)

result = tu.run_tool(
    "pubmed_search_gene_mcp", {"query": "BRCA1", "organism": "human", "limit": 3}
)

if result.get("status") == "success":
    genes = result.get("genes", [])
    print(f"\nFound {len(genes)} genes")

# ============================================================================
# Example 9: PubChem Compound Search
# ============================================================================
print("\n" + "=" * 70)
print("Example 9: PubChem Compound Search")
print("=" * 70)

result = tu.run_tool("pubmed_search_compound_mcp", {"query": "aspirin", "limit": 3})

if result.get("status") == "success":
    compounds = result.get("compounds", [])
    print(f"\nFound {len(compounds)} compounds")

# ============================================================================
# Example 10: ClinVar Variant Search
# ============================================================================
print("\n" + "=" * 70)
print("Example 10: ClinVar Variant Search")
print("=" * 70)

result = tu.run_tool("pubmed_search_clinvar_mcp", {"query": "BRCA1", "limit": 3})

if result.get("status") == "success":
    variants = result.get("variants", [])
    print(f"\nFound {len(variants)} clinical variants")

# ============================================================================
# Example 11: Build Citation Tree
# ============================================================================
print("\n" + "=" * 70)
print("Example 11: Build Citation Tree")
print("=" * 70)

result = tu.run_tool(
    "pubmed_build_citation_tree_mcp",
    {"pmid": "38353755", "depth": 1, "limit_per_level": 3, "direction": "both"},
)

if result.get("status") == "success":
    stats = result.get("stats", {})
    print(f"\nCitation tree built:")
    print(f"  Citing articles: {stats.get('citing_count', 0)}")
    print(f"  References: {stats.get('reference_count', 0)}")
    print(f"  Total nodes: {stats.get('total_nodes', 0)}")

# ============================================================================
# Example 12: Export Citations
# ============================================================================
print("\n" + "=" * 70)
print("Example 12: Export Citations")
print("=" * 70)

result = tu.run_tool(
    "pubmed_export_citations_mcp", {"pmids": "38353755,38353756", "format": "ris"}
)

if result.get("status") == "success":
    print(
        f"\nExported {result.get('article_count')} citations in {result.get('format')} format"
    )
    content = result.get("content", "")
    lines = content.split("\n")[:5]
    print("\n  Preview:")
    for line in lines:
        print(f"  {line}")

# ============================================================================
# Example 13: Institutional Access
# ============================================================================
print("\n" + "=" * 70)
print("Example 13: Institutional Access (OpenURL)")
print("=" * 70)

# List available presets
result = tu.run_tool("pubmed_list_resolver_presets_mcp", {})

if result.get("status") == "success":
    presets = result.get("presets", {})
    print("\nAvailable resolver presets:")
    for region, names in presets.items():
        print(f"  {region}: {', '.join(names) if isinstance(names, list) else names}")

# ============================================================================
# Summary
# ============================================================================
print("\n" + "=" * 70)
print("All 25 PubMed Search tool examples completed!")
print("=" * 70)
print(
    """
Tool Categories (25 total):
  1. Core Search (1):
     - pubmed_unified_search_mcp

  2. Query Intelligence (2):
     - pubmed_parse_pico_mcp
     - pubmed_generate_queries_mcp

  3. Article Exploration (5):
     - pubmed_fetch_article_mcp
     - pubmed_find_related_mcp
     - pubmed_find_citations_mcp
     - pubmed_get_references_mcp
     - pubmed_get_citation_metrics_mcp

  4. Full Text Tools (2):
     - pubmed_get_fulltext_mcp
     - pubmed_get_text_mined_terms_mcp

  5. NCBI Extended (7):
     - pubmed_search_gene_mcp
     - pubmed_get_gene_details_mcp
     - pubmed_get_gene_literature_mcp
     - pubmed_search_compound_mcp
     - pubmed_get_compound_details_mcp
     - pubmed_get_compound_literature_mcp
     - pubmed_search_clinvar_mcp

  6. Citation Network (2):
     - pubmed_build_citation_tree_mcp
     - pubmed_suggest_citation_tree_mcp

  7. Export (1):
     - pubmed_export_citations_mcp

  8. Vision Search (2) [Experimental]:
     - pubmed_analyze_figure_mcp
     - pubmed_reverse_image_search_mcp

  9. Institutional Access (3):
     - pubmed_configure_institution_mcp
     - pubmed_get_institutional_link_mcp
     - pubmed_list_resolver_presets_mcp

For more information, see the pubmed-search-mcp package documentation.
"""
)
