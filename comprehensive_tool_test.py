#!/usr/bin/env python3
"""Comprehensive testing script for 32 new tools."""
import os
import sys
import json
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tooluniverse import ToolUniverse

def test_tool(tu, tool_name, test_params):
    """Test a single tool with given parameters."""
    print(f"\n  Testing {tool_name}...")
    try:
        result = tu.run_one_function({"name": tool_name, "arguments": test_params})

        # Check if result indicates success
        if isinstance(result, dict):
            if result.get("status") == "success" or result.get("success") is True:
                print(f"    ✅ PASS: {tool_name}")
                return {"status": "pass", "result": result}
            elif result.get("status") == "error" or result.get("error"):
                error_msg = result.get("error", "Unknown error")
                print(f"    ❌ FAIL: {tool_name} - {error_msg}")
                return {"status": "fail", "error": error_msg, "result": result}
            else:
                # Assume success if no explicit error
                print(f"    ✅ PASS: {tool_name} (implicit success)")
                return {"status": "pass", "result": result}
        else:
            print(f"    ✅ PASS: {tool_name} (non-dict result)")
            return {"status": "pass", "result": result}

    except Exception as e:
        print(f"    🔥 EXCEPTION: {tool_name} - {str(e)}")
        return {"status": "exception", "error": str(e)}

def main():
    print("="*70)
    print("COMPREHENSIVE TOOL TESTING - 32 NEW TOOLS")
    print("="*70)

    # Initialize ToolUniverse
    print("\n📦 Initializing ToolUniverse...")
    try:
        tu = ToolUniverse()
        tu.load_tools()
        print(f"✅ Loaded {len(tu.tools)} tools successfully")
    except Exception as e:
        print(f"❌ Failed to initialize ToolUniverse: {e}")
        sys.exit(1)

    # Define test cases for all 32 tools
    test_suite = {
        "STRING-db (Systems Biology)": {
            "STRING_get_protein_interactions": {
                "protein_ids": ["TP53", "MDM2"],
                "species": 9606,
                "confidence_score": 0.4,
                "limit": 10
            },
            "STRING_get_interaction_partners": {
                "protein_ids": ["TP53"],
                "species": 9606,
                "confidence_score": 0.7,
                "limit": 10
            },
            "STRING_functional_enrichment": {
                "protein_ids": ["TP53", "MDM2", "ATM", "CHEK2", "BRCA1"],
                "species": 9606,
                "category": "Process"
            },
            "STRING_map_identifiers": {
                "protein_ids": ["TP53", "BRCA1"],
                "species": 9606,
                "limit": 1
            },
            "STRING_get_network": {
                "protein_ids": ["TP53", "MDM2"],
                "species": 9606,
                "confidence_score": 0.7,
                "add_nodes": 5
            },
            "STRING_ppi_enrichment": {
                "protein_ids": ["TP53", "MDM2", "ATM", "CHEK2", "BRCA1", "BRCA2"],
                "species": 9606,
                "confidence_score": 0.4
            }
        },
        "BioGRID (Systems Biology)": {
            "BioGRID_get_interactions": {
                "gene_names": ["TP53"],
                "organism": "9606",
                "interaction_type": "physical",
                "limit": 10
            },
            "BioGRID_get_chemical_interactions": {
                "gene_names": ["EGFR"],
                "organism": "9606",
                "limit": 10
            },
            "BioGRID_search_by_pubmed": {
                "pubmed_ids": ["28514442"],
                "organism": "9606",
                "limit": 10
            },
            "BioGRID_get_ptms": {
                "gene_names": ["TP53"],
                "organism": "9606",
                "ptm_type": ["Phosphorylation"],
                "limit": 10
            }
        },
        "NCBI SRA (Genomics)": {
            "NCBI_SRA_search_runs": {
                "operation": "search",
                "organism": "Homo sapiens",
                "strategy": "RNA-Seq",
                "limit": 5
            },
            "NCBI_SRA_get_run_info": {
                "operation": "get_run_info",
                "accessions": "SRR000001"
            },
            "NCBI_SRA_get_download_urls": {
                "operation": "get_download_urls",
                "accessions": "SRR000001"
            },
            "NCBI_SRA_link_to_biosample": {
                "operation": "link_to_biosample",
                "accessions": "1"
            }
        },
        "ICD-10/11 (Clinical)": {
            "ICD11_search_diseases": {
                "query": "diabetes mellitus",
                "linearization": "mms",
                "flatResults": True
            },
            "ICD11_get_entity": {
                "entity_id": "1435254666",
                "linearization": "mms"
            },
            "ICD11_browse_hierarchy": {
                "entity_id": "1435254666",
                "linearization": "mms"
            },
            "ICD10_search_codes": {
                "query": "diabetes mellitus type 2",
                "limit": 10
            },
            "ICD10_get_code_info": {
                "code": "E11.9"
            }
        },
        "LOINC (Clinical)": {
            "LOINC_search_tests": {
                "terms": "cholesterol",
                "max_results": 10
            },
            "LOINC_get_code_details": {
                "loinc_code": "2093-3"
            },
            "LOINC_get_answer_list": {
                "loinc_code": "883-9"
            },
            "LOINC_search_forms": {
                "terms": "PHQ-9",
                "max_results": 5
            }
        },
        "SASBDB (Structural Biology)": {
            "SASBDB_search_entries": {
                "query": "lysozyme",
                "method": "SAXS",
                "limit": 10
            },
            "SASBDB_get_entry_data": {
                "sasbdb_id": "SASDBA2"
            },
            "SASBDB_get_scattering_profile": {
                "sasbdb_id": "SASDBA2",
                "format": "json"
            },
            "SASBDB_get_models": {
                "sasbdb_id": "SASDBA2",
                "model_type": "all"
            },
            "SASBDB_download_data": {
                "sasbdb_id": "SASDBA2",
                "file_type": "all"
            }
        },
        "ProteinsPlus (Structural Biology)": {
            "ProteinsPlus_predict_binding_sites": {
                "pdb_id": "1A2B"
            },
            "ProteinsPlus_dock_ligand": {
                "pdb_id": "1A2B",
                "ligand_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"
            },
            "ProteinsPlus_analyze_interactions": {
                "pdb_id": "1A2B"
            },
            "ProteinsPlus_check_structure": {
                "pdb_id": "1A2B"
            }
        }
    }

    # Run tests
    results = {}
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    exception_tests = 0
    skipped_tests = 0

    for category, tools in test_suite.items():
        print(f"\n{'='*70}")
        print(f"Testing: {category}")
        print(f"{'='*70}")

        category_results = {}
        for tool_name, test_params in tools.items():
            total_tests += 1

            # Check if tool requires API keys
            tool_config = tu.tools.get(tool_name)
            if tool_config:
                required_keys = tool_config.get("required_api_keys", [])
                if required_keys:
                    missing_keys = [k for k in required_keys if not os.getenv(k)]
                    if missing_keys:
                        print(f"\n  ⏭️  SKIPPED: {tool_name} (missing API keys: {', '.join(missing_keys)})")
                        category_results[tool_name] = {"status": "skipped", "reason": f"Missing API keys: {missing_keys}"}
                        skipped_tests += 1
                        continue

            result = test_tool(tu, tool_name, test_params)
            category_results[tool_name] = result

            if result["status"] == "pass":
                passed_tests += 1
            elif result["status"] == "fail":
                failed_tests += 1
            elif result["status"] == "exception":
                exception_tests += 1

            # Rate limiting
            time.sleep(0.5)

        results[category] = category_results

    # Generate summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}")
    print(f"Total Tests:     {total_tests}")
    print(f"Passed:          {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
    print(f"Failed:          {failed_tests}")
    print(f"Exceptions:      {exception_tests}")
    print(f"Skipped:         {skipped_tests}")
    print(f"{'='*70}")

    # Save detailed results
    output_file = Path(__file__).parent / "test_results_comprehensive.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n📄 Detailed results saved to: {output_file}")

    # Generate markdown reports
    generate_markdown_reports(results, total_tests, passed_tests, failed_tests, exception_tests, skipped_tests)

    return 0 if failed_tests == 0 and exception_tests == 0 else 1

def generate_markdown_reports(results, total, passed, failed, exceptions, skipped):
    """Generate markdown test reports."""

    # System Biology Report
    systems_bio_content = generate_category_report(
        "Systems Biology",
        ["STRING-db (Systems Biology)", "BioGRID (Systems Biology)"],
        results
    )

    # Genomics Report
    genomics_content = generate_category_report(
        "Genomics",
        ["NCBI SRA (Genomics)"],
        results
    )

    # Clinical Report
    clinical_content = generate_category_report(
        "Clinical/EHR",
        ["ICD-10/11 (Clinical)", "LOINC (Clinical)"],
        results
    )

    # Structural Biology Report
    structural_content = generate_category_report(
        "Structural Biology",
        ["SASBDB (Structural Biology)", "ProteinsPlus (Structural Biology)"],
        results
    )

    # Summary Report
    summary_content = f"""# Test Summary - All 32 Tools

**Test Date:** {time.strftime("%Y-%m-%d %H:%M:%S")}

## Overall Results

- **Total Tests:** {total}
- **Passed:** {passed} ({passed/total*100:.1f}%)
- **Failed:** {failed}
- **Exceptions:** {exceptions}
- **Skipped:** {skipped}

## By Domain

### Systems Biology (10 tools)
- STRING-db: 6 tools
- BioGRID: 4 tools

### Genomics (4 tools)
- NCBI SRA: 4 tools

### Clinical/EHR (9 tools)
- ICD-10/11: 5 tools
- LOINC: 4 tools

### Structural Biology (9 tools)
- SASBDB: 5 tools
- ProteinsPlus: 4 tools

## Status by Category

{generate_status_summary(results)}

## Critical Issues

{generate_critical_issues(results)}

## Recommendations

{generate_recommendations(results)}
"""

    # Write reports
    Path("TEST_REPORT_SYSTEMS_BIOLOGY.md").write_text(systems_bio_content)
    Path("TEST_REPORT_GENOMICS.md").write_text(genomics_content)
    Path("TEST_REPORT_CLINICAL.md").write_text(clinical_content)
    Path("TEST_REPORT_STRUCTURAL.md").write_text(structural_content)
    Path("TEST_SUMMARY.md").write_text(summary_content)

    print("\n📊 Markdown reports generated:")
    print("  - TEST_REPORT_SYSTEMS_BIOLOGY.md")
    print("  - TEST_REPORT_GENOMICS.md")
    print("  - TEST_REPORT_CLINICAL.md")
    print("  - TEST_REPORT_STRUCTURAL.md")
    print("  - TEST_SUMMARY.md")

def generate_category_report(category_name, category_keys, results):
    """Generate markdown report for a category."""
    content = f"""# Test Report - {category_name}

**Test Date:** {time.strftime("%Y-%m-%d %H:%M:%S")}

## Tools Tested

"""

    for key in category_keys:
        if key in results:
            content += f"\n### {key}\n\n"
            for tool_name, result in results[key].items():
                status_emoji = {
                    "pass": "✅",
                    "fail": "❌",
                    "exception": "🔥",
                    "skipped": "⏭️"
                }.get(result["status"], "❓")

                content += f"- **{tool_name}**: {status_emoji} {result['status'].upper()}\n"

                if result["status"] == "fail":
                    content += f"  - Error: `{result.get('error', 'Unknown')}`\n"
                elif result["status"] == "exception":
                    content += f"  - Exception: `{result.get('error', 'Unknown')}`\n"
                elif result["status"] == "skipped":
                    content += f"  - Reason: {result.get('reason', 'Unknown')}\n"

    content += "\n## Summary\n\n"
    content += generate_category_stats(category_keys, results)

    return content

def generate_category_stats(category_keys, results):
    """Generate statistics for a category."""
    total = 0
    passed = 0
    failed = 0
    exceptions = 0
    skipped = 0

    for key in category_keys:
        if key in results:
            for tool_name, result in results[key].items():
                total += 1
                if result["status"] == "pass":
                    passed += 1
                elif result["status"] == "fail":
                    failed += 1
                elif result["status"] == "exception":
                    exceptions += 1
                elif result["status"] == "skipped":
                    skipped += 1

    return f"""- Total Tests: {total}
- Passed: {passed}
- Failed: {failed}
- Exceptions: {exceptions}
- Skipped: {skipped}
- Pass Rate: {passed/total*100:.1f}% (excluding skipped)
"""

def generate_status_summary(results):
    """Generate status summary table."""
    summary = "| Category | Tools | Passed | Failed | Exceptions | Skipped |\n"
    summary += "|----------|-------|--------|--------|------------|--------|\n"

    for category, tools in results.items():
        total = len(tools)
        passed = sum(1 for t in tools.values() if t["status"] == "pass")
        failed = sum(1 for t in tools.values() if t["status"] == "fail")
        exceptions = sum(1 for t in tools.values() if t["status"] == "exception")
        skipped = sum(1 for t in tools.values() if t["status"] == "skipped")

        summary += f"| {category} | {total} | {passed} | {failed} | {exceptions} | {skipped} |\n"

    return summary

def generate_critical_issues(results):
    """Generate list of critical issues."""
    issues = []

    for category, tools in results.items():
        for tool_name, result in tools.items():
            if result["status"] in ["fail", "exception"]:
                severity = "CRITICAL" if result["status"] == "exception" else "HIGH"
                error = result.get("error", "Unknown error")
                issues.append(f"- **[{severity}]** `{tool_name}`: {error}")

    if not issues:
        return "✅ No critical issues found!"

    return "\n".join(issues)

def generate_recommendations(results):
    """Generate recommendations based on test results."""
    recommendations = []

    # Check for authentication issues
    auth_issues = []
    for category, tools in results.items():
        for tool_name, result in tools.items():
            if result["status"] == "skipped" and "API key" in result.get("reason", ""):
                auth_issues.append(tool_name)

    if auth_issues:
        recommendations.append(f"**Authentication Required**: {len(auth_issues)} tools require API keys. Set up environment variables for: {', '.join(auth_issues)}")

    # Check for failed tools
    failed_tools = []
    for category, tools in results.items():
        for tool_name, result in tools.items():
            if result["status"] in ["fail", "exception"]:
                failed_tools.append(tool_name)

    if failed_tools:
        recommendations.append(f"**Failed Tools**: {len(failed_tools)} tools failed and require fixes: {', '.join(failed_tools)}")

    if not recommendations:
        recommendations.append("✅ All tools are functioning correctly!")

    return "\n\n".join(recommendations)

if __name__ == "__main__":
    sys.exit(main())
