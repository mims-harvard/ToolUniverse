#!/usr/bin/env python3
"""
Example script for BioModels Tool.
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
    
    # BioModels Tool: Search for models
    print("\nRunning BioModels Tool: Searching for 'glycolysis' models...")
    try:
        result = tu.tools.biomodels_search(
            action="search_models",
            query="glycolysis",
            limit=2
        )
        print_result("BioModels Search", result)

        if result and "models" in result and result["models"]:
            model_id = result["models"][0]["id"]
            print(f"\nRunning BioModels Tool: Getting file links for {model_id}...")
            files_result = tu.tools.biomodels_get_files(
                action="get_model_files",
                model_id=model_id
            )
            print_result("BioModels Files", files_result)
    except AttributeError as e:
         print(f"Error accessing BioModels tool: {e}")
    except Exception as e:
        print(f"Error running BioModels tool: {e}")

if __name__ == "__main__":
    main()
