#!/usr/bin/env python3
"""
Example script for Immune Epitope Database (IEDB) Tool.
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
    
    # IEDB Tool: Search for epitopes
    print("\nRunning IEDB Tool: Searching for 'KVF' epitopes...")
    try:
        result = tu.tools.iedb_search_epitopes(
            action="search_epitopes",
            query="KVF",
            limit=2
        )
        print_result("IEDB Search", result)
    except AttributeError as e:
         print(f"Error accessing IEDB tool: {e}")
    except Exception as e:
        print(f"Error running IEDB tool: {e}")

if __name__ == "__main__":
    main()
