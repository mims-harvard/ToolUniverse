#!/usr/bin/env python3
"""
Systems Biology & Pathway Analysis - Python SDK Implementation
Tested implementation following TDD principles
"""

from tooluniverse import ToolUniverse
from datetime import datetime
import json

def systems_biology_pipeline(
    gene_list=None,
    protein_id=None,
    pathway_keyword=None,
    organism="Homo sapiens",
    output_file=None
):
    """
    Comprehensive systems biology and pathway analysis pipeline.

    Args:
        gene_list: List of gene symbols for pathway enrichment
        protein_id: UniProt ID to find protein-specific pathways
        pathway_keyword: Keyword to search pathways across databases
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
        if gene_list:
            output_file = f"systems_biology_genelist_{timestamp}.md"
        elif protein_id:
            output_file = f"systems_biology_{protein_id}_{timestamp}.md"
        elif pathway_keyword:
            output_file = f"systems_biology_{pathway_keyword}_{timestamp}.md"
        else:
            output_file = f"systems_biology_report_{timestamp}.md"

    # Initialize report
    report = []
    report.append("# Systems Biology & Pathway Analysis Report\n")
    report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    if gene_list:
        report.append(f"**Gene List**: {', '.join(gene_list[:10])}{'...' if len(gene_list) > 10 else ''}\n")
    if protein_id:
        report.append(f"**Protein ID**: {protein_id}\n")
    if pathway_keyword:
        report.append(f"**Keyword**: {pathway_keyword}\n")
    report.append(f"**Organism**: {organism}\n")

    report.append("\n---\n")

    # Phase 1: Pathway Enrichment (if gene list provided)
    if gene_list and len(gene_list) > 0:
        report.append("\n## 1. Pathway Enrichment Analysis\n")

        # Enrichr analysis
        try:
            result = tu.tools.enrichr_gene_enrichment_analysis(
                gene_list=gene_list,
                library="KEGG_2021_Human"
            )
            if isinstance(result, dict) and result.get('status') == 'success':
                enrichment_data = result.get('data', [])
                if enrichment_data:
                    report.append(f"\n### KEGG Pathway Enrichment ({len(enrichment_data)} pathways)\n")
                    report.append("\n| Pathway | P-value | Adjusted P-value | Genes |\n")
                    report.append("|---------|---------|------------------|-------|\n")
                    for item in enrichment_data[:10]:
                        term = item.get('term', 'N/A')
                        pval = item.get('pvalue', 'N/A')
                        adj_pval = item.get('adjusted_pvalue', 'N/A')
                        genes = ', '.join(item.get('genes', [])[:3]) + ('...' if len(item.get('genes', [])) > 3 else '')

                        # Format p-values
                        pval_str = f"{pval:.2e}" if isinstance(pval, float) else str(pval)
                        adj_pval_str = f"{adj_pval:.2e}" if isinstance(adj_pval, float) else str(adj_pval)

                        report.append(f"| {term} | {pval_str} | {adj_pval_str} | {genes} |\n")
                else:
                    report.append("\n*No significant KEGG pathway enrichment found.*\n")
            else:
                report.append("\n*KEGG enrichment analysis unavailable.*\n")
        except Exception as e:
            report.append(f"\n*Error in enrichment analysis: {str(e)}*\n")

    # Phase 2: Protein-specific pathways (if protein ID provided)
    if protein_id:
        report.append(f"\n## 2. Pathways for Protein {protein_id}\n")

        # Reactome pathways
        try:
            result = tu.tools.Reactome_map_uniprot_to_pathways(id=protein_id)
            if isinstance(result, list) and len(result) > 0:
                report.append(f"\n### Reactome Pathways ({len(result)} pathways)\n")
                report.append("\n| Pathway Name | Pathway ID | Species |\n")
                report.append("|--------------|------------|----------|\n")
                for pathway in result[:15]:
                    name = pathway.get('displayName', 'N/A')
                    stId = pathway.get('stId', 'N/A')
                    species = pathway.get('speciesName', 'N/A')
                    report.append(f"| {name} | {stId} | {species} |\n")

                # Get details for top pathway
                if len(result) > 0:
                    top_pathway_id = result[0].get('stId')
                    if top_pathway_id:
                        report.append(f"\n### Top Pathway Details: {result[0].get('displayName')}\n")
                        try:
                            reactions = tu.tools.Reactome_get_pathway_reactions(stId=top_pathway_id)
                            if isinstance(reactions, list):
                                report.append(f"\n**Reactions/Subpathways**: {len(reactions)}\n")
                                if len(reactions) > 0:
                                    report.append("\n| Event Name | Type |\n")
                                    report.append("|------------|------|\n")
                                    for event in reactions[:10]:
                                        if isinstance(event, dict):
                                            ev_name = event.get('displayName', 'N/A')
                                            ev_type = event.get('schemaClass', 'N/A')
                                            report.append(f"| {ev_name} | {ev_type} |\n")
                        except Exception:
                            pass
            else:
                report.append(f"\n*No Reactome pathways found for {protein_id}.*\n")
        except Exception as e:
            report.append(f"\n*Error retrieving Reactome pathways: {str(e)}*\n")

    # Phase 3: Keyword-based pathway search (if keyword provided)
    if pathway_keyword:
        report.append(f"\n## 3. Pathway Search: '{pathway_keyword}'\n")

        # KEGG pathways
        try:
            result = tu.tools.kegg_search_pathway(keyword=pathway_keyword)
            if result.get('status') == 'success':
                kegg_pathways = result.get('data', [])
                if kegg_pathways:
                    report.append(f"\n### KEGG Pathways ({len(kegg_pathways)} results)\n")
                    report.append("\n| Pathway ID | Description |\n")
                    report.append("|------------|-------------|\n")
                    for pw in kegg_pathways:
                        pid = pw.get('pathway_id', 'N/A')
                        desc = pw.get('description', 'N/A')
                        report.append(f"| {pid} | {desc} |\n")
                else:
                    report.append("\n*No KEGG pathways found.*\n")
        except Exception as e:
            report.append(f"\n*Error searching KEGG: {str(e)}*\n")

        # WikiPathways
        try:
            result = tu.tools.WikiPathways_search(query=pathway_keyword, organism=organism)
            if result.get('status') == 'success':
                wp_data = result.get('data', {})
                wp_pathways = wp_data.get('result', [])
                if wp_pathways:
                    report.append(f"\n### WikiPathways ({len(wp_pathways)} results)\n")
                    report.append("\n| Pathway ID | Name | Species |\n")
                    report.append("|------------|------|----------|\n")
                    for pw in wp_pathways[:15]:
                        wpid = pw.get('id', 'N/A')
                        name = pw.get('name', 'N/A')
                        species = pw.get('species', 'N/A')
                        report.append(f"| {wpid} | {name} | {species} |\n")
                else:
                    report.append("\n*No WikiPathways found.*\n")
        except Exception as e:
            report.append(f"\n*Error searching WikiPathways: {str(e)}*\n")

        # Pathway Commons
        try:
            result = tu.tools.pc_search_pathways(
                action="search_pathways",
                keyword=pathway_keyword,
                limit=15
            )
            if isinstance(result, dict) and 'total_hits' in result:
                total = result.get('total_hits', 0)
                pc_pathways = result.get('pathways', [])
                if pc_pathways:
                    report.append(f"\n### Pathway Commons ({total} total hits, showing {len(pc_pathways)})\n")
                    report.append("\n| Pathway Name | Data Source |\n")
                    report.append("|--------------|-------------|\n")
                    for pw in pc_pathways:
                        name = pw.get('name', 'N/A')
                        source = ', '.join(pw.get('source', []))
                        report.append(f"| {name} | {source} |\n")
                else:
                    report.append("\n*No Pathway Commons results found.*\n")
        except Exception as e:
            report.append(f"\n*Error searching Pathway Commons: {str(e)}*\n")

        # BioModels
        try:
            result = tu.tools.biomodels_search(query=pathway_keyword, limit=10)
            if result.get('status') == 'success':
                biomodels_data = result.get('data', {})
                total = biomodels_data.get('matches', 0)
                models = biomodels_data.get('models', [])
                if models:
                    report.append(f"\n### BioModels ({total} total matches, showing {len(models)})\n")
                    report.append("\n| Model ID | Name |\n")
                    report.append("|----------|------|\n")
                    for model in models:
                        mid = model.get('id', 'N/A')
                        name = model.get('name', 'N/A')
                        report.append(f"| {mid} | {name} |\n")
                else:
                    report.append("\n*No BioModels found.*\n")
        except Exception as e:
            report.append(f"\n*Error searching BioModels: {str(e)}*\n")

    # Phase 4: Top-level human pathways (always included)
    report.append("\n## 4. Top-Level Human Pathways (Reactome)\n")
    try:
        result = tu.tools.Reactome_list_top_pathways(species=organism)
        if isinstance(result, list) and len(result) > 0:
            report.append(f"\n**Total**: {len(result)} top-level pathways\n")
            report.append("\n| Pathway Name | Pathway ID |\n")
            report.append("|--------------|------------|\n")
            for pw in result[:20]:
                name = pw.get('displayName', 'N/A')
                stId = pw.get('stId', 'N/A')
                report.append(f"| {name} | {stId} |\n")
        else:
            report.append("\n*No top-level pathways retrieved.*\n")
    except Exception as e:
        report.append(f"\n*Error retrieving top pathways: {str(e)}*\n")

    # Write report to file
    report_content = ''.join(report)
    with open(output_file, 'w') as f:
        f.write(report_content)

    print(f"\n✅ Report generated: {output_file}")
    return output_file


if __name__ == "__main__":
    # Example usage
    print("Systems Biology & Pathway Analysis - Python SDK Implementation")
    print("="*80)

    # Example 1: Gene list enrichment
    print("\n[Example 1] Gene list enrichment analysis...")
    genes = ["TP53", "BRCA1", "EGFR", "MYC", "KRAS", "AKT1", "PTEN", "RB1"]
    systems_biology_pipeline(
        gene_list=genes,
        output_file="example1_genelist.md"
    )

    # Example 2: Protein-specific pathways
    print("\n[Example 2] Protein-specific pathway analysis...")
    systems_biology_pipeline(
        protein_id="P53350",  # TP53 tumor suppressor
        output_file="example2_protein.md"
    )

    # Example 3: Keyword search
    print("\n[Example 3] Pathway keyword search...")
    systems_biology_pipeline(
        pathway_keyword="apoptosis",
        organism="Homo sapiens",
        output_file="example3_keyword.md"
    )

    print("\n✅ All examples completed!")
