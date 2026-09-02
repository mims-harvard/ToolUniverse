#!/usr/bin/env python3
"""
Paper Search Tools Example

This example demonstrates how to use the optimized paper search tools
in ToolUniverse to search for academic papers across multiple databases.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tooluniverse import ToolUniverse

def main():
    """Main example function"""
    
    # Initialize ToolUniverse
    tu = ToolUniverse()
    
    # Load paper search tools
    print("Loading paper search tools...")
    tu.load_tools(tool_type=[
        "semantic_scholar", "EuropePMC", "OpenAlex", "arxiv", "pubmed", "crossref",
        "biorxiv", "medrxiv", "hal", "doaj", "dblp", "pmc"
    ])
    
    print(f"Loaded {len(tu.all_tools)} tools")
    
    # Search query
    query = "machine learning"
    print(f"\nSearching for: '{query}'")
    print("=" * 60)
    
    # Define tools to test
    tools_to_test = [
        ("ArXiv_search_papers", {"query": query, "limit": 2}, "ArXiv"),
        ("EuropePMC_search_articles", {"query": query, "limit": 2}, "Europe PMC"),
        ("openalex_literature_search", {"search_keywords": query, "max_results": 2}, "OpenAlex"),
        ("Crossref_search_works", {"query": query, "limit": 2}, "Crossref"),
        # bioRxiv/medRxiv have no keyword-search endpoint -- their APIs are
        # DOI/date retrieval only. Europe PMC (above) indexes both; fetch full
        # preprint metadata by DOI with BioRxiv_get_preprint / MedRxiv_get_preprint.
    ]
    
    # Test each tool
    for tool_name, args, display_name in tools_to_test:
        print(f"\n--- {display_name} ---")
        
        try:
            function_call = {"name": tool_name, "arguments": args}
            result = tu.run_one_function(function_call)
            
            if isinstance(result, list) and len(result) > 0:
                paper = result[0]
                print(f"Found {len(result)} papers")
                print(f"Title: {paper.get('title', 'N/A')[:60]}...")
                
                # Show data quality
                if 'data_quality' in paper:
                    quality = paper['data_quality']
                    available_fields = [k for k, v in quality.items() if v]
                    print(f"Available fields: {', '.join(available_fields)}")
                
                # Show key information
                if paper.get('authors'):
                    print(f"Authors: {paper['authors'][:2]}..." if len(paper['authors']) > 2 else f"Authors: {paper['authors']}")
                if paper.get('year'):
                    print(f"Year: {paper['year']}")
                if paper.get('journal') or paper.get('venue'):
                    print(f"Journal: {paper.get('journal') or paper.get('venue')}")
                if paper.get('citations') or paper.get('citation_count'):
                    citations = paper.get('citations') or paper.get('citation_count')
                    print(f"Citations: {citations}")
                    
            elif isinstance(result, dict) and 'error' in result:
                print(f"Error: {result['error']}")
            else:
                print("No results found")
                
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n" + "=" * 60)
    print("Example completed!")

if __name__ == "__main__":
    main()
