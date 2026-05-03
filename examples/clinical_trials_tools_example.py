#!/usr/bin/env python3
"""
Example script for ClinicalTrials.gov Tool.
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
    
    # ClinicalTrials.gov Tool: Search for breast cancer trials
    print("\nRunning ClinicalTrials Tool: Searching for 'breast cancer' trials...")
    try:
        result = tu.tools.clinical_trials_search(
            action="search_studies",
            condition="breast cancer",
            limit=2
        )
        print_result("ClinicalTrials Search", result)
        
        # Get details for the first study
        if result and "studies" in result and result["studies"]:
            nct_id = result["studies"][0]["nctId"]
            print(f"\nRunning ClinicalTrials Tool: Getting details for study {nct_id}...")
            details_result = tu.tools.clinical_trials_get_details(
                action="get_study_details",
                nct_id=nct_id
            )
            print_result("ClinicalTrials Details", details_result)
    except AttributeError as e:
         print(f"Error accessing ClinicalTrials tool: {e}")
    except Exception as e:
        print(f"Error running ClinicalTrials tool: {e}")

if __name__ == "__main__":
    main()
