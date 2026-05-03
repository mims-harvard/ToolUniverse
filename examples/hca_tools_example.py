#!/usr/bin/env python3
"""
Example script for Human Cell Atlas (HCA) Tool.
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
    
    # HCA Tool: Search for heart projects
    print("\nRunning HCA Tool: Searching for 'heart' projects...")
    try:
        # Search for projects
        result = tu.tools.hca_search_projects(
            action="search_projects", 
            organ="heart", 
            limit=2
        )
        print_result("HCA Search", result)
        
        # Get file manifest for the first project if found
        if result and "projects" in result and result["projects"]:
            project_id = result["projects"][0]["entryId"]
            print(f"\nRunning HCA Tool: Getting file manifest for project {project_id}...")
            file_result = tu.tools.hca_get_file_manifest(
                action="get_file_manifest",
                project_id=project_id,
                limit=2
            )
            print_result("HCA File Manifest", file_result)
    except AttributeError as e:
        print(f"Error accessing HCA tool: {e}")
    except Exception as e:
        print(f"Error running HCA tool: {e}")

if __name__ == "__main__":
    main()
