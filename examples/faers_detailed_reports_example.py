#!/usr/bin/env python3
"""
Usage examples for FAERS Detailed Adverse Event Report tools in ToolUniverse

This script demonstrates how to use the FAERS detailed report tools to retrieve
individual case reports with patient information, adverse event details, drug
information, and report metadata.

These tools return detailed reports (not just counts), making them useful for:
- Case-by-case analysis of adverse events
- Understanding patient demographics and outcomes
- Investigating specific drug-reaction combinations
- Analyzing drug interactions

Field Extraction:
The tools automatically extract essential fields and remove verbose metadata
(like openfda) to keep output concise. This is configured via
extract_essential: true in the tool configuration. The extraction reduces
output size by ~95% while retaining all essential information needed for
analysis.
"""

import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.tooluniverse import ToolUniverse  # noqa: E402

# Configuration for output control
MAX_REPORTS_TO_SHOW = 2  # Limit number of reports to display
MAX_JSON_LENGTH = 5000  # Max characters per report in JSON output
# Note: Field extraction is now handled in the tool class itself via
# extract_essential config in tool_config['fields']


def example_search_basic_reports():
    """Example: Search for basic adverse event reports for a drug"""
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.run({
        "name": "FAERS_search_adverse_event_reports",
        "arguments": {
            "medicinalproduct": "Donanemab",
            "limit": 3
        }
    }, use_cache=False)

    print(f"\n{'='*80}")
    print("Example 1: Basic Adverse Event Reports Search")
    print(f"{'='*80}")
    print(f"Found {len(result) if isinstance(result, list) else 0} reports")

    if isinstance(result, list) and len(result) > 0:
        # Show limited number of reports
        reports_to_show = result[:MAX_REPORTS_TO_SHOW]
        for i, report in enumerate(reports_to_show):
            report_json = json.dumps(report, indent=2, ensure_ascii=False)
            if len(report_json) > MAX_JSON_LENGTH:
                report_json = (report_json[:MAX_JSON_LENGTH] +
                               "\n... (truncated)")
            print(f"\n--- Report {i+1} of {len(reports_to_show)} ---")
            print(report_json)
        if len(result) > MAX_REPORTS_TO_SHOW:
            remaining = len(result) - MAX_REPORTS_TO_SHOW
            print(f"\n... and {remaining} more reports "
                  f"(showing first {MAX_REPORTS_TO_SHOW} only)")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def example_search_by_reaction():
    """Example: Search for reports with a specific drug and reaction"""
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.run({
        "name": "FAERS_search_reports_by_drug_and_reaction",
        "arguments": {
            "medicinalproduct": "Donanemab",
            "reactionmeddrapt": "INFUSION RELATED REACTION",
            "limit": 2
        }
    }, use_cache=False)

    print(f"\n{'='*80}")
    print("Example 2: Search by Drug and Specific Reaction")
    print(f"{'='*80}")
    print(f"Found {len(result) if isinstance(result, list) else 0} reports")

    if isinstance(result, list) and len(result) > 0:
        reports_to_show = result[:MAX_REPORTS_TO_SHOW]
        for i, report in enumerate(reports_to_show):
            report_json = json.dumps(report, indent=2, ensure_ascii=False)
            if len(report_json) > MAX_JSON_LENGTH:
                report_json = (report_json[:MAX_JSON_LENGTH] +
                               "\n... (truncated)")
            print(f"\n--- Report {i+1} of {len(reports_to_show)} ---")
            print(report_json)
        if len(result) > MAX_REPORTS_TO_SHOW:
            remaining = len(result) - MAX_REPORTS_TO_SHOW
            print(f"\n... and {remaining} more reports "
                  f"(showing first {MAX_REPORTS_TO_SHOW} only)")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def example_search_serious_reports():
    """Example: Search for serious adverse events (fatal cases)"""
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.run({
        "name": "FAERS_search_serious_reports_by_drug",
        "arguments": {
            "medicinalproduct": "Donanemab",
            "seriousnessdeath": "Yes",
            "limit": 2
        }
    }, use_cache=False)

    print(f"\n{'='*80}")
    print("Example 3: Search for Serious Adverse Events (Fatal Cases)")
    print(f"{'='*80}")
    print(f"Found {len(result) if isinstance(result, list) else 0} reports")

    if isinstance(result, list) and len(result) > 0:
        reports_to_show = result[:MAX_REPORTS_TO_SHOW]
        for i, report in enumerate(reports_to_show):
            report_json = json.dumps(report, indent=2, ensure_ascii=False)
            if len(report_json) > MAX_JSON_LENGTH:
                report_json = (report_json[:MAX_JSON_LENGTH] +
                               "\n... (truncated)")
            print(f"\n--- Report {i+1} of {len(reports_to_show)} ---")
            print(report_json)
        if len(result) > MAX_REPORTS_TO_SHOW:
            remaining = len(result) - MAX_REPORTS_TO_SHOW
            print(f"\n... and {remaining} more reports "
                  f"(showing first {MAX_REPORTS_TO_SHOW} only)")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def example_search_by_indication():
    """Example: Search for reports by drug and indication"""
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.run({
        "name": "FAERS_search_reports_by_drug_and_indication",
        "arguments": {
            "medicinalproduct": "Donanemab",
            "drugindication": "Dementia",
            "limit": 2
        }
    }, use_cache=False)

    print(f"\n{'='*80}")
    print("Example 4: Search by Drug and Indication")
    print(f"{'='*80}")
    print(f"Found {len(result) if isinstance(result, list) else 0} reports")

    if isinstance(result, list) and len(result) > 0:
        reports_to_show = result[:MAX_REPORTS_TO_SHOW]
        for i, report in enumerate(reports_to_show):
            report_json = json.dumps(report, indent=2, ensure_ascii=False)
            if len(report_json) > MAX_JSON_LENGTH:
                report_json = (report_json[:MAX_JSON_LENGTH] +
                               "\n... (truncated)")
            print(f"\n--- Report {i+1} of {len(reports_to_show)} ---")
            print(report_json)
        if len(result) > MAX_REPORTS_TO_SHOW:
            remaining = len(result) - MAX_REPORTS_TO_SHOW
            print(f"\n... and {remaining} more reports "
                  f"(showing first {MAX_REPORTS_TO_SHOW} only)")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def example_search_by_outcome():
    """Example: Search for reports by reaction outcome"""
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.run({
        "name": "FAERS_search_reports_by_drug_and_outcome",
        "arguments": {
            "medicinalproduct": "Donanemab",
            "reactionoutcome": "Fatal",
            "limit": 2
        }
    }, use_cache=False)

    print(f"\n{'='*80}")
    print("Example 5: Search by Reaction Outcome")
    print(f"{'='*80}")
    print(f"Found {len(result) if isinstance(result, list) else 0} reports")

    if isinstance(result, list) and len(result) > 0:
        reports_to_show = result[:MAX_REPORTS_TO_SHOW]
        for i, report in enumerate(reports_to_show):
            report_json = json.dumps(report, indent=2, ensure_ascii=False)
            if len(report_json) > MAX_JSON_LENGTH:
                report_json = (report_json[:MAX_JSON_LENGTH] +
                               "\n... (truncated)")
            print(f"\n--- Report {i+1} of {len(reports_to_show)} ---")
            print(report_json)
        if len(result) > MAX_REPORTS_TO_SHOW:
            remaining = len(result) - MAX_REPORTS_TO_SHOW
            print(f"\n... and {remaining} more reports "
                  f"(showing first {MAX_REPORTS_TO_SHOW} only)")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def example_search_drug_interactions():
    """Example: Search for drug interaction reports"""
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.run({
        "name": "FAERS_search_reports_by_drug_combination",
        "arguments": {
            "medicinalproducts": ["Donanemab", "Aspirin"],
            "limit": 2
        }
    }, use_cache=False)

    print(f"\n{'='*80}")
    print("Example 6: Search for Drug Interaction Reports")
    print(f"{'='*80}")
    print(f"Found {len(result) if isinstance(result, list) else 0} reports")

    if isinstance(result, list) and len(result) > 0:
        reports_to_show = result[:MAX_REPORTS_TO_SHOW]
        for i, report in enumerate(reports_to_show):
            report_json = json.dumps(report, indent=2, ensure_ascii=False)
            if len(report_json) > MAX_JSON_LENGTH:
                report_json = (report_json[:MAX_JSON_LENGTH] +
                               "\n... (truncated)")
            print(f"\n--- Report {i+1} of {len(reports_to_show)} ---")
            print(report_json)
        if len(result) > MAX_REPORTS_TO_SHOW:
            remaining = len(result) - MAX_REPORTS_TO_SHOW
            print(f"\n... and {remaining} more reports "
                  f"(showing first {MAX_REPORTS_TO_SHOW} only)")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("FAERS Detailed Adverse Event Report Tools - Usage Examples")
    print("="*80)
    print("\nThese examples demonstrate how to retrieve detailed case reports")
    print("from the FDA Adverse Event Reporting System (FAERS).")
    print("\nNote: Results may vary based on available data in FAERS.")

    examples = [
        ("Basic Reports", example_search_basic_reports),
        ("Drug + Reaction", example_search_by_reaction),
        ("Serious Events", example_search_serious_reports),
        ("Drug + Indication", example_search_by_indication),
        ("Reaction Outcome", example_search_by_outcome),
        ("Drug Interactions", example_search_drug_interactions),
    ]

    results = {}
    for name, func in examples:
        try:
            results[name] = func()
        except Exception as e:
            print(f"\n❌ Error in {name} example: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*80)
    print("Summary")
    print("="*80)
    print("\nAll examples completed!")
    print("\nKey Points:")
    print("  • These tools return detailed case reports (not just counts)")
    print("  • Each report contains patient info, drugs, reactions, "
          "and outcomes")
    print("  • Use 'limit' parameter to control number of results (1-100)")
    print("  • Use 'skip' parameter for pagination")
    print("  • All tools require at least one drug name (medicinalproduct)")
    print("  • Additional filters are optional and can be combined")
    print("\nOutput Control:")
    print(f"  • Limited to {MAX_REPORTS_TO_SHOW} reports per example")
    print(f"  • Each report truncated at {MAX_JSON_LENGTH} characters")
    print("  • Modify MAX_REPORTS_TO_SHOW and MAX_JSON_LENGTH to see more")
    print("\nField Extraction (Automatic):")
    print("  • Tools automatically extract essential fields and remove")
    print("    verbose metadata (like openfda) to keep output concise for")
    print("    agent consumption")
    print("  • Configured via extract_essential: true in tool config")
    print("  • Extracted fields include:")
    print("    - Report ID and version")
    print("    - Seriousness indicators (death, hospitalization, etc.)")
    print("    - Patient demographics (sex, age, weight)")
    print("    - Drugs (medicinalproduct, indication, route, dosage)")
    print("    - Reactions (MedDRA terms, outcomes)")
    print("    - Location and date information")
    print("  • Reduces output size by ~95% while retaining all essential")
    print("    information needed for analysis")
    print("\nFor more information, see:")
    print("  • Tool documentation: docs/tools/")
    print("  • FDA API: https://open.fda.gov/apis/drug/event/")


if __name__ == "__main__":
    main()
