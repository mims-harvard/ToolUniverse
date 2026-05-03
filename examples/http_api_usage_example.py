#!/usr/bin/env python3
"""
ToolUniverse HTTP API Usage Example

This example demonstrates how to use the ToolUniverse HTTP API server
to remotely call ALL ToolUniverse methods.

Prerequisites:
    1. Start the server:
       tooluniverse-http-api --host 0.0.0.0 --port 8080
    
    2. Install client dependency:
       pip install tooluniverse[client]

Run:
    python examples/http_api_usage_example.py
"""

import sys
import os

# Add src directory to path for local development
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from tooluniverse import ToolUniverseClient


def example_1_list_methods():
    """Example 1: Discover available methods"""
    print("=" * 70)
    print("Example 1: List Available Methods")
    print("=" * 70)
    
    with ToolUniverseClient("http://localhost:8080") as client:
        methods = client.list_available_methods()
        
        print(f"\n✅ Found {len(methods)} methods\n")
        print("First 10 methods:")
        for i, method in enumerate(methods[:10], 1):
            name = method["name"]
            doc = method.get("docstring", "No description")
            doc_first_line = doc.split('\n')[0][:60] + "..." if len(doc) > 60 else doc
            print(f"{i:2}. {name}")
            print(f"    {doc_first_line}")


def example_2_load_tools():
    """Example 2: Load specific tools"""
    print("\n" + "=" * 70)
    print("Example 2: Load Specific Tools")
    print("=" * 70)
    
    with ToolUniverseClient("http://localhost:8080") as client:
        print("\n📦 Loading tools...")
        
        # This calls tu.load_tools() on the server
        result = client.load_tools(
            tool_type=['tool_finder', 'opentarget', 'fda_drug_label',
                      'special_tools', 'monarch', 'ChEMBL',
                      'EuropePMC', 'semantic_scholar', 'pubtator', 'EFO']
        )
        
        print("✅ Tools loaded successfully")
        
        # Get available tools
        tools = client.get_available_tools(name_only=True)
        print(f"\n✅ Total tools available: {len(tools) if isinstance(tools, list) else 'N/A'}")
        
        if isinstance(tools, list) and len(tools) > 0:
            print(f"First 10 tools:")
            for i, tool_name in enumerate(tools[:10], 1):
                print(f"  {i:2}. {tool_name}")


def example_3_get_tool_specification():
    """Example 3: Get tool specification"""
    print("\n" + "=" * 70)
    print("Example 3: Get Tool Specification")
    print("=" * 70)
    
    with ToolUniverseClient("http://localhost:8080") as client:
        # Load tools first
        client.load_tools(tool_type=['uniprot'])
        
        print("\n🔍 Getting specification for UniProt_get_entry_by_accession...")
        
        # This calls tu.tool_specification() on the server
        spec = client.tool_specification(
            "UniProt_get_entry_by_accession",
            return_prompt=False,
            format="default"
        )
        
        print("\n✅ Tool specification:")
        print(f"  Name: {spec.get('name', 'N/A')}")
        print(f"  Description: {spec.get('description', 'N/A')[:100]}...")
        
        if 'parameter' in spec:
            params = spec['parameter'].get('properties', {})
            print(f"  Parameters: {', '.join(params.keys())}")


def example_4_prepare_tool_prompts():
    """Example 4: Prepare tool prompts"""
    print("\n" + "=" * 70)
    print("Example 4: Prepare Tool Prompts")
    print("=" * 70)
    
    with ToolUniverseClient("http://localhost:8080") as client:
        # Load tools
        client.load_tools(tool_type=['uniprot', 'ChEMBL'])
        
        # Get tools
        tools = client.get_available_tools(name_only=False)
        
        if isinstance(tools, list) and len(tools) > 0:
            print(f"\n📝 Preparing prompts for {min(3, len(tools))} tools...")
            
            # This calls tu.prepare_tool_prompts() on the server
            prompts = client.prepare_tool_prompts(
                tool_list=tools[:3],
                mode="prompt"
            )
            
            print(f"\n✅ Prepared {len(prompts) if isinstance(prompts, list) else 0} prompts")
            
            if isinstance(prompts, list) and len(prompts) > 0:
                print("\nFirst prompt:")
                first_prompt = prompts[0]
                print(f"  Name: {first_prompt.get('name', 'N/A')}")
                print(f"  Type: {first_prompt.get('type', 'N/A')}")


def example_5_execute_tool():
    """Example 5: Execute a tool"""
    print("\n" + "=" * 70)
    print("Example 5: Execute a Tool")
    print("=" * 70)
    
    with ToolUniverseClient("http://localhost:8080") as client:
        # Load tools
        client.load_tools(tool_type=['uniprot'])
        
        print("\n🧬 Executing UniProt tool...")
        print("   Query: P05067 (Amyloid-beta precursor protein)")
        
        # This calls tu.run_one_function() on the server
        result = client.run_one_function(
            function_call_json={
                "name": "UniProt_get_entry_by_accession",
                "arguments": {"accession": "P05067"}
            },
            use_cache=False,
            validate=True
        )
        
        print("\n✅ Tool executed successfully!")
        
        if isinstance(result, dict):
            print(f"  Accession: {result.get('primaryAccession', 'N/A')}")
            if 'proteinDescription' in result:
                desc = result['proteinDescription']
                if 'recommendedName' in desc:
                    name = desc['recommendedName'].get('fullName', {}).get('value', 'N/A')
                    print(f"  Protein Name: {name}")
            if 'organism' in result:
                org = result['organism'].get('scientificName', 'N/A')
                print(f"  Organism: {org}")
            if 'sequence' in result:
                length = result['sequence'].get('length', 'N/A')
                print(f"  Sequence Length: {length} amino acids")


def example_6_list_built_in_tools():
    """Example 6: List built-in tools categories"""
    print("\n" + "=" * 70)
    print("Example 6: List Built-in Tool Categories")
    print("=" * 70)
    
    with ToolUniverseClient("http://localhost:8080") as client:
        print("\n📚 Listing built-in tool categories...")
        
        # This calls tu.list_built_in_tools() on the server
        result = client.list_built_in_tools(mode="config", scan_all=False)
        
        print("\n✅ Available categories:")
        
        if isinstance(result, dict) and 'categories' in result:
            categories = result['categories']
            for i, (cat_name, cat_info) in enumerate(sorted(categories.items())[:10], 1):
                count = cat_info.get('count', 0)
                display_name = cat_name.replace('_', ' ').title()
                print(f"  {i:2}. {display_name}: {count} tools")
            
            total_cats = result.get('total_categories', 0)
            total_tools = result.get('total_tools', 0)
            print(f"\n  Total Categories: {total_cats}")
            print(f"  Total Unique Tools: {total_tools}")


def example_7_health_and_help():
    """Example 7: Health check and help"""
    print("\n" + "=" * 70)
    print("Example 7: Health Check and Help")
    print("=" * 70)
    
    with ToolUniverseClient("http://localhost:8080") as client:
        # Health check
        print("\n💊 Health check...")
        health = client.health_check()
        print(f"  Status: {health.get('status', 'unknown')}")
        print(f"  ToolUniverse Initialized: {health.get('tooluniverse_initialized', False)}")
        print(f"  Loaded Tools Count: {health.get('loaded_tools_count', 0)}")
        
        # Get help for a specific method
        print("\n📖 Getting help for 'load_tools'...")
        client.help("load_tools")


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("ToolUniverse HTTP API Usage Examples")
    print("=" * 70)
    print("\n⚙️  Server: http://localhost:8080")
    print("📝 Make sure the server is running!")
    print("   Command: tooluniverse-http-api --host 0.0.0.0 --port 8080\n")
    
    try:
        # Run examples
        example_1_list_methods()
        example_2_load_tools()
        example_3_get_tool_specification()
        example_4_prepare_tool_prompts()
        example_5_execute_tool()
        example_6_list_built_in_tools()
        example_7_health_and_help()
        
        print("\n" + "=" * 70)
        print("✅ All Examples Completed Successfully!")
        print("=" * 70)
        print("\n💡 Key Takeaways:")
        print("   1. Client automatically supports ALL ToolUniverse methods")
        print("   2. No manual updates needed when ToolUniverse changes")
        print("   3. Client only needs 'requests' (no ToolUniverse package)")
        print("   4. Server maintains ToolUniverse instance state")
        print("   5. Use __getattr__ magic for automatic method proxying")
        
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Make sure the server is running:")
        print("      tooluniverse-http-api --host 0.0.0.0 --port 8080")
        print("   2. Check the server is accessible:")
        print("      curl http://localhost:8080/health")
        print("   3. Install client dependency:")
        print("      pip install requests")
        sys.exit(1)


if __name__ == "__main__":
    main()
