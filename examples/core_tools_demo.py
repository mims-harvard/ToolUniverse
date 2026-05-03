"""
Demonstration of fixed core tools handling nullable metadata fields.

This script shows how the core tools now gracefully handle missing metadata
(doi, license, author, home_page) that may be None in API responses.
"""

from tooluniverse import ToolUniverse
import json


def demo_core_search_papers():
    """Demo CORE paper search with nullable DOI field."""
    print("\n" + "="*80)
    print("DEMO 1: CORE Paper Search (nullable DOI)")
    print("="*80)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run_one_function({
        'name': 'CORE_search_papers',
        'arguments': {
            'query': 'machine learning',
            'limit': 3
        }
    })
    
    print(f"\nStatus: {result['status']}")
    print(f"Found {len(result['data'])} papers\n")
    
    for i, paper in enumerate(result['data'], 1):
        print(f"Paper {i}:")
        print(f"  Title: {paper.get('title', 'N/A')[:80]}...")
        print(f"  Year: {paper.get('year', 'N/A')}")
        
        # DOI may be None - this is now valid!
        doi = paper.get('doi')
        if doi:
            print(f"  DOI: {doi}")
        else:
            print(f"  DOI: Not available ✓ (nullable field)")
        
        print(f"  URL: {paper.get('url', 'N/A')[:60]}...")
        print()


def demo_package_info():
    """Demo bioinformatics package info with nullable metadata."""
    print("\n" + "="*80)
    print("DEMO 2: Package Info (nullable license, author, home_page)")
    print("="*80)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Test a few packages that might have missing metadata
    packages = [
        'get_biopython_info',
        'get_numba_info',
        'get_networkx_info'
    ]
    
    for pkg_tool in packages:
        result = tu.run_one_function({
            'name': pkg_tool,
            'arguments': {'include_examples': True}
        })
        
        if result['status'] == 'success':
            data = result['data']
            print(f"\nPackage: {data.get('package_name', 'N/A')}")
            print(f"Description: {data.get('description', 'N/A')[:70]}...")
            print(f"Version: {data.get('version', 'N/A')}")
            
            # These fields may be None - now valid!
            author = data.get('author')
            license_info = data.get('license')
            homepage = data.get('home_page')
            
            print(f"Author: {author if author else 'Not specified ✓ (nullable)'}")
            print(f"License: {license_info if license_info else 'Not specified ✓ (nullable)'}")
            print(f"Homepage: {homepage if homepage else 'Not specified ✓ (nullable)'}")
            
            # These should always be present
            if data.get('repository'):
                print(f"Repository: {data['repository']}")
            if data.get('documentation'):
                print(f"Documentation: {data['documentation']}")
        else:
            print(f"\nPackage: {pkg_tool} - {result.get('message', 'Error')}")


def demo_schema_validation():
    """Demo that None values pass schema validation."""
    print("\n" + "="*80)
    print("DEMO 3: Schema Validation with Null Values")
    print("="*80)
    
    from jsonschema import validate, ValidationError
    
    # Simulate the old schema (would fail)
    old_schema = {
        "type": "object",
        "properties": {
            "doi": {"type": "string"}  # Doesn't allow null
        }
    }
    
    # Simulate the new schema (passes)
    new_schema = {
        "type": "object", 
        "properties": {
            "doi": {"type": ["string", "null"]}  # Allows null
        }
    }
    
    # Test data with None value
    test_data = {"doi": None}
    
    print("\nTest data:", test_data)
    print("\n1. Old schema (type: 'string'):")
    try:
        validate(instance=test_data, schema=old_schema)
        print("   ✓ Validation passed")
    except ValidationError as e:
        print(f"   ✗ Validation failed: {e.message}")
    
    print("\n2. New schema (type: ['string', 'null']):")
    try:
        validate(instance=test_data, schema=new_schema)
        print("   ✓ Validation passed!")
    except ValidationError as e:
        print(f"   ✗ Validation failed: {e.message}")
    
    # Test with actual string value
    test_data2 = {"doi": "10.1234/example"}
    print(f"\nTest data: {test_data2}")
    print("New schema still accepts string values:")
    try:
        validate(instance=test_data2, schema=new_schema)
        print("   ✓ Validation passed!")
    except ValidationError as e:
        print(f"   ✗ Validation failed: {e.message}")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("CORE TOOLS FIX DEMONSTRATION")
    print("="*80)
    print("\nThis demo shows that the core tools now handle nullable metadata fields")
    print("correctly. Fields like doi, license, author, and home_page can be None")
    print("without causing schema validation failures.")
    
    try:
        # Demo 1: CORE paper search with nullable DOI
        demo_core_search_papers()
        
        # Demo 2: Package info with nullable metadata
        demo_package_info()
        
        # Demo 3: Schema validation explanation
        demo_schema_validation()
        
        print("\n" + "="*80)
        print("✅ ALL DEMOS COMPLETED SUCCESSFULLY")
        print("="*80)
        print("\nKey takeaway: Nullable fields allow APIs to return None for optional")
        print("metadata without breaking schema validation. This matches real-world API")
        print("behavior where not all data is always available.")
        print()
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
