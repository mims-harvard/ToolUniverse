#!/usr/bin/env python3
"""
ArrayExpress and BioStudies Tools Demo

This script demonstrates how to use both ArrayExpress and BioStudies tools.
Both tools now use the BioStudies API backend, with markitdown support for
HTML responses.

Features:
- ArrayExpress tools: Specialized for genomics experiments
- BioStudies tools: General-purpose for all study types
- Automatic HTML to Markdown conversion via markitdown
- Access to multiple collections (arrayexpress, bioimages, biomodels, etc.)
"""

import sys
from pathlib import Path

# Add src to path for development
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

from tooluniverse import ToolUniverse


def demo_arrayexpress_tools():
    """Demonstrate ArrayExpress tools (genomics-focused)"""
    print("=" * 70)
    print("ArrayExpress Tools (Genomics Experiments)")
    print("=" * 70)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # 1. Search for cancer experiments
    print("\n1. Searching for cancer experiments...")
    result = tu.run_one_function({
        'name': 'arrayexpress_search_experiments',
        'arguments': {
            'keywords': 'cancer',
            'species': 'Homo sapiens',
            'limit': 3
        }
    })
    
    if result.get('status') == 'success':
        data = result.get('data', {})
        experiments = data.get('experiments', [])
        print(f"   Found {data.get('totalHits', 0)} total experiments")
        print(f"   Showing {len(experiments)} experiments:")
        for exp in experiments[:3]:
            print(f"   - {exp.get('accession')}: {exp.get('title', '')[:60]}...")
    
    # 2. Get specific experiment details
    print("\n2. Getting details for experiment E-GEOD-26319...")
    result = tu.run_one_function({
        'name': 'arrayexpress_get_experiment',
        'arguments': {'experiment_id': 'E-GEOD-26319'}
    })
    
    if result.get('status') == 'success':
        data = result.get('data', {})
        print(f"   Accession: {data.get('accno')}")
        attrs = data.get('attributes', [])
        for attr in attrs[:3]:
            print(f"   {attr.get('name')}: {attr.get('value', '')[:60]}")
    
    # 3. Get experiment files
    print("\n3. Getting files for experiment E-GEOD-26319...")
    result = tu.run_one_function({
        'name': 'arrayexpress_get_experiment_files',
        'arguments': {'experiment_id': 'E-GEOD-26319'}
    })
    
    if result.get('status') == 'success':
        files = result.get('data', [])
        print(f"   Found {len(files)} files")
        for f in files[:5]:
            print(f"   - {f.get('name')} ({f.get('size', 0)} bytes)")


def demo_biostudies_tools():
    """Demonstrate BioStudies tools (all study types)"""
    print("\n" + "=" * 70)
    print("BioStudies Tools (All Study Types)")
    print("=" * 70)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # 1. General search across all collections
    print("\n1. Searching all BioStudies for 'CRISPR'...")
    result = tu.run_one_function({
        'name': 'biostudies_search',
        'arguments': {
            'query': 'CRISPR',
            'pageSize': 3,
            'sortBy': 'relevance'
        }
    })
    
    if result.get('status') == 'success':
        data = result.get('data', {})
        hits = data.get('hits', [])
        print(f"   Found {data.get('totalHits', 0)} total studies")
        print(f"   Showing {len(hits)} studies:")
        for hit in hits:
            print(f"   - {hit.get('accession')}: {hit.get('title', '')[:60]}...")
            print(f"     Type: {hit.get('type')}, Collection: {hit.get('accession')[:2]}")
    
    # 2. Search within specific collection
    print("\n2. Searching ArrayExpress collection for 'stem cells'...")
    result = tu.run_one_function({
        'name': 'biostudies_search_by_collection',
        'arguments': {
            'query': 'stem cells',
            'collection': 'arrayexpress',
            'pageSize': 3
        }
    })
    
    if result.get('status') == 'success':
        data = result.get('data', {})
        hits = data.get('hits', [])
        print(f"   Found {data.get('totalHits', 0)} ArrayExpress studies")
        print(f"   Showing {len(hits)} studies:")
        for hit in hits:
            print(f"   - {hit.get('accession')}: {hit.get('title', '')[:60]}...")
    
    # 3. Get specific study
    print("\n3. Getting study S-BSST1254...")
    result = tu.run_one_function({
        'name': 'biostudies_get_study',
        'arguments': {'accession': 'S-BSST1254'}
    })
    
    if result.get('status') == 'success':
        data = result.get('data', {})
        print(f"   Accession: {data.get('accno')}")
        print(f"   Type: {data.get('type')}")
        attrs = data.get('attributes', [])
        for attr in attrs[:3]:
            print(f"   {attr.get('name')}: {attr.get('value', '')[:60]}")
    
    # 4. Get study files
    print("\n4. Getting files for study S-BSST1254...")
    result = tu.run_one_function({
        'name': 'biostudies_get_study_files',
        'arguments': {'accession': 'S-BSST1254'}
    })
    
    if result.get('status') == 'success':
        files = result.get('data', [])
        print(f"   Found {len(files)} files")
        for f in files[:5]:
            print(f"   - {f.get('path')} ({f.get('size', 0)} bytes)")


def demo_markitdown_support():
    """Demonstrate HTML to Markdown conversion"""
    print("\n" + "=" * 70)
    print("MarkItDown Support (HTML to Markdown Conversion)")
    print("=" * 70)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    print("\n📝 When BioStudies API returns HTML instead of JSON,")
    print("   the tools automatically convert it to Markdown using markitdown.")
    print("   This ensures consistent, readable output regardless of response format.")
    
    print("\n✅ Both ArrayExpress and BioStudies tools include:")
    print("   - Automatic content-type detection")
    print("   - HTML to Markdown conversion via markitdown")
    print("   - Graceful fallback if markitdown is unavailable")
    print("   - Clear status messages in responses")


def main():
    """Run all demos"""
    try:
        demo_arrayexpress_tools()
        demo_biostudies_tools()
        demo_markitdown_support()
        
        print("\n" + "=" * 70)
        print("Summary")
        print("=" * 70)
        print("✅ ArrayExpress tools: Specialized for genomics experiments")
        print("✅ BioStudies tools: General-purpose for all study types")
        print("✅ Both use BioStudies API backend")
        print("✅ Automatic HTML to Markdown conversion with markitdown")
        print("✅ Support for multiple collections (arrayexpress, bioimages, etc.)")
        
        print("\n📚 Available Collections:")
        print("   - arrayexpress: Functional genomics experiments")
        print("   - bioimages: Biological imaging data")
        print("   - biomodels: Systems biology models")
        print("   - europepmc: Europe PubMed Central literature")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
