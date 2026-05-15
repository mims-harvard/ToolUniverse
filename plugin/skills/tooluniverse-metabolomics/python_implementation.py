#!/usr/bin/env python3
"""
Metabolomics Research - Python SDK Implementation
Tested implementation following TDD principles
"""

from tooluniverse import ToolUniverse
from datetime import datetime
import json

def metabolomics_analysis_pipeline(
    metabolite_list=None,
    study_id=None,
    search_query=None,
    organism="Homo sapiens",
    output_file=None
):
    """
    Metabolomics research analysis pipeline.

    Args:
        metabolite_list: List of metabolite names (e.g., ["glucose", "lactate"])
        study_id: MetaboLights or Metabolomics Workbench study ID
        search_query: Keyword to search metabolomics studies
        organism: Organism name (default: "Homo sapiens")
        output_file: Output markdown file path (default: auto-generated)

    Returns:
        Path to generated report file
    """

    tu = ToolUniverse()
    tu.load_tools()

    # Generate output filename
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if metabolite_list:
            output_file = f"metabolomics_metabolites_{timestamp}.md"
        elif study_id:
            output_file = f"metabolomics_{study_id}_{timestamp}.md"
        elif search_query:
            output_file = f"metabolomics_search_{search_query}_{timestamp}.md"
        else:
            output_file = f"metabolomics_analysis_{timestamp}.md"

    # Initialize report
    report = []
    report.append("# Metabolomics Research Analysis Report\n")
    report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    if metabolite_list:
        report.append(f"**Metabolites**: {', '.join(metabolite_list[:10])}{'...' if len(metabolite_list) > 10 else ''}\n")
    if study_id:
        report.append(f"**Study ID**: {study_id}\n")
    if search_query:
        report.append(f"**Search Query**: {search_query}\n")
    report.append(f"**Organism**: {organism}\n")

    report.append("\n---\n")

    # Phase 1: Metabolite Identification
    if metabolite_list and len(metabolite_list) > 0:
        report.append("\n## 1. Metabolite Identification & Annotation\n")

        for metabolite in metabolite_list[:10]:  # Limit to 10 for report length
            report.append(f"\n### Metabolite: {metabolite}\n")

            # HMDB Search
            try:
                result = tu.tools.HMDB_search(
                    operation="search",  # SOAP tool - CRITICAL
                    query=metabolite
                )

                if isinstance(result, dict) and result.get('status') == 'success':
                    data = result.get('data', {})  # FIX: data is dict, not list
                    results = data.get('results', [])  # FIX: results are nested

                    if results and len(results) > 0:
                        hmdb_entry = results[0]  # FIX: Access results array

                        # Use correct field names from actual API
                        report.append(f"**PubChem CID**: {hmdb_entry.get('cid', 'N/A')}\n")
                        report.append(f"**Name**: {hmdb_entry.get('name', 'N/A')}\n")
                        report.append(f"**Formula**: {hmdb_entry.get('formula', 'N/A')}\n")
                        report.append(f"**Molecular Weight**: {hmdb_entry.get('mw', 'N/A')}\n")

                        # Add HMDB search URL if available
                        hmdb_url = data.get('hmdb_search_url', '')
                        if hmdb_url:
                            report.append(f"**HMDB Search URL**: {hmdb_url}\n")
                    else:
                        report.append(f"*No results found for {metabolite}*\n")
                else:
                    report.append("*HMDB search unavailable.*\n")

            except Exception as e:
                report.append(f"*Error querying HMDB: {str(e)[:100]}*\n")

            # PubChem search (fallback)
            try:
                result = tu.tools.PubChem_get_CID_by_compound_name(name=metabolite)  # FIX: parameter is 'name', not 'compound_name'
                if isinstance(result, dict) and result.get('status') == 'success':
                    data = result.get('data', {})
                    cid = data.get('cid', 'N/A')
                    if cid != 'N/A':
                        report.append(f"**PubChem CID**: {cid}\n")

                        # Get properties
                        props = tu.tools.PubChem_get_compound_properties_by_CID(cid=cid)
                        if isinstance(props, dict) and props.get('status') == 'success':
                            prop_data = props.get('data', {})
                            report.append(f"**SMILES**: {prop_data.get('CanonicalSMILES', 'N/A')}\n")
            except Exception as e:
                pass  # PubChem fallback, don't report errors

    # Phase 2: Study Retrieval
    if study_id:
        report.append(f"\n## 2. Study Details: {study_id}\n")

        # Try MetaboLights first
        if study_id.startswith('MTBLS'):
            try:
                result = tu.tools.metabolights_get_study(study_id=study_id)
                if isinstance(result, dict) and result.get('status') == 'success':
                    data = result.get('data', {})
                    study = data.get('mtblsStudy', {})  # FIX: Extract nested study object

                    report.append(f"**Database**: MetaboLights\n")
                    # Use actual field names from API
                    report.append(f"**Study Status**: {study.get('studyStatus', 'N/A')}\n")
                    report.append(f"**Study ID**: {study.get('accession', 'N/A')}\n")
                    report.append(f"**Release Date**: {study.get('releaseDate', 'N/A')}\n")
                    report.append(f"**Modified Time**: {study.get('modifiedTime', 'N/A')}\n")
                    report.append(f"**HTTP URL**: {study.get('studyHttpUrl', 'N/A')}\n")
                else:
                    report.append("*Study details unavailable from MetaboLights.*\n")
            except Exception as e:
                report.append(f"*Error retrieving MetaboLights study: {str(e)[:100]}*\n")

        # Try Metabolomics Workbench
        elif study_id.startswith('ST'):
            try:
                result = tu.tools.MetabolomicsWorkbench_get_study(
                    study_id=study_id,
                    output_item="summary"
                )
                if isinstance(result, dict) and result.get('status') == 'success':
                    data = result.get('data', {})
                    # Parse the text response
                    if isinstance(data, str):
                        lines = data.strip().split('\n')
                        report.append(f"**Database**: Metabolomics Workbench\n")
                        for line in lines:
                            if '\t' in line:
                                key, value = line.split('\t', 1)
                                report.append(f"**{key}**: {value}\n")
                    else:
                        report.append(f"**Database**: Metabolomics Workbench\n")
                        report.append(f"**Data**: {data}\n")
                else:
                    report.append("*Study details unavailable from Metabolomics Workbench.*\n")
            except Exception as e:
                report.append(f"*Error retrieving Workbench study: {str(e)[:100]}*\n")

    # Phase 3: Study Search
    if search_query:
        report.append(f"\n## 3. Study Search: '{search_query}'\n")

        # MetaboLights search
        try:
            result = tu.tools.metabolights_search_studies(query=search_query)
            if isinstance(result, dict) and result.get('status') == 'success':
                data = result.get('data', [])
                if data:
                    report.append(f"\n### MetaboLights Studies ({len(data)} results)\n")
                    report.append("\n| Study ID | Preview |\n")
                    report.append("|----------|----------|\n")
                    for study in data[:15]:  # Limit to 15
                        if isinstance(study, str):
                            report.append(f"| {study} | - |\n")
                        elif isinstance(study, dict):
                            sid = study.get('accession', study.get('id', 'N/A'))
                            title = study.get('title', '')[:50]
                            report.append(f"| {sid} | {title} |\n")
                else:
                    report.append("\n*No MetaboLights studies found.*\n")
        except Exception as e:
            report.append(f"\n*Error searching MetaboLights: {str(e)[:100]}*\n")

    # Phase 4: Database Statistics (always included)
    report.append("\n## 4. Metabolomics Database Overview\n")

    try:
        result = tu.tools.metabolights_list_studies(size=10)
        if isinstance(result, dict) and result.get('status') == 'success':
            data = result.get('data', [])
            report.append(f"\n**MetaboLights**: {len(data)} studies available (sample)\n")
            report.append(f"**Recent studies**: {', '.join([s if isinstance(s, str) else s.get('accession', '') for s in data[:5]])}\n")
    except Exception:
        report.append("\n**MetaboLights**: Database available\n")

    report.append("\n**Databases integrated**:\n")
    report.append("- HMDB (Human Metabolome Database): 220,000+ metabolites\n")
    report.append("- MetaboLights: Public metabolomics repository\n")
    report.append("- Metabolomics Workbench: NIH metabolomics data\n")
    report.append("- PubChem: Chemical properties and bioactivity\n")

    # Write report to file
    report_content = ''.join(report)
    with open(output_file, 'w') as f:
        f.write(report_content)

    print(f"\n✅ Report generated: {output_file}")
    return output_file


if __name__ == "__main__":
    # Example usage
    print("Metabolomics Research Analysis - Python SDK Implementation")
    print("="*80)

    # Example 1: Metabolite list analysis
    print("\n[Example 1] Metabolite identification...")
    metabolomics_analysis_pipeline(
        metabolite_list=["glucose", "lactate", "pyruvate"],
        output_file="example1_metabolites.md"
    )

    # Example 2: Study retrieval
    print("\n[Example 2] Study analysis...")
    metabolomics_analysis_pipeline(
        study_id="MTBLS1",
        output_file="example2_study.md"
    )

    # Example 3: Study search
    print("\n[Example 3] Study search...")
    metabolomics_analysis_pipeline(
        search_query="diabetes",
        organism="Homo sapiens",
        output_file="example3_search.md"
    )

    print("\n✅ All examples completed!")
