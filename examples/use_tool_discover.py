#!/usr/bin/env python3
"""
Simple example of using the ToolDiscover tool like any other tool
"""

import sys
import os

# Add the project root to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.tooluniverse import ToolUniverse

def main():
    """Simple example using ToolDiscover as a regular tool"""
    print("🚀 Using ToolDiscover Tool")
    print("=" * 30)
    
    # Step 1: Initialize ToolUniverse
    print("🔧 Loading ToolUniverse...")
    tooluniverse = ToolUniverse()
    tooluniverse.load_tools()
    
    print("✅ ToolUniverse loaded!")
    
    # Step 2: Use ToolDiscover like any other tool
    tool_description = "A tool for accessing KEGG (Kyoto Encyclopedia of Genes and Genomes) database to search pathways, genes, compounds, and other biological data"
    
    print(f"📝 I want: {tool_description}")
    print("\n🔧 Calling ToolDiscover...")
    
    # Call ToolDiscover with arguments using tu.run()
    result = tooluniverse.run({
        "name": "ToolDiscover",
        "arguments": {
            "tool_description": tool_description,
            "max_iterations": 5,  # Just 1 iteration for simplicity
            "save_to_file": True,
            "output_file": "generated_kegg_tool"  # Required parameter
        }
    })
    
    print("\n✅ Done!")
    print(f"📋 Result type: {type(result)}")
    
    if isinstance(result, dict):
        print(f"📋 Result keys: {list(result.keys())}")
        
        if 'error' in result:
            print(f"❌ Error: {result.get('error')}")
            if 'error_details' in result:
                print(f"📝 Details: {result.get('error_details')}")
        elif 'tool_config' in result:
            tool_config = result['tool_config']
            print(f"🔧 Generated Tool: {tool_config.get('name', 'Unknown')}")
            print(f"📝 Description: {tool_config.get('description', 'No description')}")
        
        if 'saved_files' in result:
            print(f"💾 Saved files:")
            for file_path in result['saved_files']:
                if os.path.exists(file_path):
                    print(f"   ✅ {file_path}")
                else:
                    print(f"   ❌ {file_path}")

if __name__ == "__main__":
    main()
