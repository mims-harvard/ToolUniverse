#!/usr/bin/env python3
"""
Example script for Pathway Commons Tool.
"""

import os
import sys
import json

# Ensure src is in path to import tooluniverse
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from tooluniverse import ToolUniverse

def print_result(tool_name, result):
    print(f"\n--- Results for {tool_name} ---")
    if result:
        print(json.dumps(result, indent=2))
    else:
        print("No result found or error occurred.")
    print("-" * 40)

def main():
    print("Initializing ToolUniverse...")
    tu = ToolUniverse()
    
    # Pathway Commons Tool: Search for pathways
    print("\nRunning Pathway Commons Tool: Searching for 'p53' pathways...")
    try:
        result = tu.tools.pc_search_pathways(
            action="search_pathways",
            keyword="p53",
            limit=2
        )
        print_result("Pathway Commons Search", result)
        
        # Get interaction graph
        print("\nRunning Pathway Commons Tool: Getting interactions for TP53 and MDM2...")
        result = tu.tools.pc_get_interactions(
            action="get_interaction_graph",
            gene_list=["TP53", "MDM2"]
        )
        print_result("Pathway Commons Interactions", result)
    except AttributeError as e:
         print(f"Error accessing Pathway Commons tool: {e}")
    except Exception as e:
        print(f"Error running Pathway Commons tool: {e}")

if __name__ == "__main__":
    main()
