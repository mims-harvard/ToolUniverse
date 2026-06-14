#!/usr/bin/env python3
"""
Diabetes Metabolomics Study Analysis
Tests the Metabolomics Research skill with a comprehensive diabetes research workflow
"""

from python_implementation import metabolomics_analysis_pipeline

if __name__ == "__main__":
    print("="*80)
    print("DIABETES METABOLOMICS RESEARCH ANALYSIS")
    print("="*80)
    print()
    print("This analysis will:")
    print("1. Identify and annotate diabetes-related metabolites")
    print("2. Retrieve details for study MTBLS1 (diabetes-related)")
    print("3. Search for additional diabetes studies")
    print("4. Generate a comprehensive research report")
    print()
    print("="*80)

    # Define metabolites involved in diabetes
    diabetes_metabolites = [
        "glucose",
        "lactate",
        "pyruvate",
        "citrate",
        "succinate"
    ]

    print(f"\nAnalyzing {len(diabetes_metabolites)} diabetes-related metabolites...")
    print(f"Metabolites: {', '.join(diabetes_metabolites)}")
    print(f"Study ID: MTBLS1")
    print(f"Search query: diabetes")
    print()

    # Run comprehensive analysis
    metabolomics_analysis_pipeline(
        metabolite_list=diabetes_metabolites,
        study_id="MTBLS1",
        search_query="diabetes",
        organism="Homo sapiens",
        output_file="diabetes_metabolomics_report.md"
    )

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE!")
    print("="*80)
    print("\nReport saved to: diabetes_metabolomics_report.md")
    print("\nYou can now review:")
    print("  - HMDB annotations for all 5 metabolites")
    print("  - MTBLS1 study details")
    print("  - Related diabetes studies from MetaboLights")
    print("  - Database integration overview")
    print()
