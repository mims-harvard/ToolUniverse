#!/usr/bin/env python3
"""
Format enrichment analysis results for reports.

Converts gseapy, PANTHER, STRING, and Reactome results into
standardized markdown tables for inclusion in analysis reports.

Usage:
    from format_enrichment_output import format_ora_results, format_gsea_results

    # Format ORA results
    markdown = format_ora_results(go_bp_result, top_n=10, title="GO Biological Process")

    # Format GSEA results
    markdown = format_gsea_results(gsea_result, top_n=10, title="GSEA - GO BP")
"""

import pandas as pd
import re
from typing import Optional, Union, List, Dict


def format_ora_results(
    enrichr_result,
    top_n: int = 10,
    title: str = "Enrichment Results",
    fdr_cutoff: float = 0.05,
    include_genes: bool = True
) -> str:
    """
    Format gseapy.enrichr() results as markdown table.

    Args:
        enrichr_result: Result from gseapy.enrichr()
        top_n: Number of top terms to include
        title: Table title
        fdr_cutoff: FDR cutoff for filtering
        include_genes: Whether to include gene list in table

    Returns:
        Markdown formatted table string
    """
    df = enrichr_result.results
    sig = df[df['Adjusted P-value'] < fdr_cutoff].copy()

    if len(sig) == 0:
        return f"## {title}\n\nNo significant terms found at FDR < {fdr_cutoff}\n"

    sig = sig.head(top_n)

    # Build markdown
    lines = [f"## {title}\n"]
    lines.append(f"**Total significant terms**: {len(df[df['Adjusted P-value'] < fdr_cutoff])}")
    lines.append(f"**Showing top**: {len(sig)}\n")

    # Table header
    if include_genes:
        lines.append("| Rank | Term | P-value | Adj. P-value | Overlap | Odds Ratio | Genes |")
        lines.append("|------|------|---------|--------------|---------|------------|-------|")
    else:
        lines.append("| Rank | Term | P-value | Adj. P-value | Overlap | Odds Ratio |")
        lines.append("|------|------|---------|--------------|---------|------------|")

    # Table rows
    for idx, (_, row) in enumerate(sig.iterrows(), 1):
        term = row['Term']
        pval = f"{row['P-value']:.2e}"
        adj_pval = f"{row['Adjusted P-value']:.2e}"
        overlap = row['Overlap']
        odds_ratio = f"{row['Odds Ratio']:.2f}"

        if include_genes:
            genes = row['Genes']
            # Truncate if too long
            if len(genes) > 100:
                genes = genes[:97] + "..."
            lines.append(f"| {idx} | {term} | {pval} | {adj_pval} | {overlap} | {odds_ratio} | {genes} |")
        else:
            lines.append(f"| {idx} | {term} | {pval} | {adj_pval} | {overlap} | {odds_ratio} |")

    return "\n".join(lines) + "\n"


def format_gsea_results(
    gsea_result,
    top_n: int = 10,
    title: str = "GSEA Results",
    fdr_cutoff: float = 0.25,
    direction: str = 'both'
) -> str:
    """
    Format gseapy.prerank() results as markdown table.

    Args:
        gsea_result: Result from gseapy.prerank()
        top_n: Number of top terms to include
        title: Table title
        fdr_cutoff: FDR cutoff for filtering
        direction: 'both', 'positive', or 'negative' (NES direction)

    Returns:
        Markdown formatted table string
    """
    df = gsea_result.res2d
    sig = df[df['FDR q-val'].astype(float) < fdr_cutoff].copy()

    if len(sig) == 0:
        return f"## {title}\n\nNo significant terms found at FDR < {fdr_cutoff}\n"

    # Filter by direction
    if direction == 'positive':
        sig = sig[sig['NES'] > 0]
        subtitle = "(Up-regulated pathways)"
    elif direction == 'negative':
        sig = sig[sig['NES'] < 0]
        subtitle = "(Down-regulated pathways)"
    else:
        subtitle = ""

    # Sort by |NES|
    sig['abs_NES'] = sig['NES'].abs()
    sig = sig.sort_values('abs_NES', ascending=False).head(top_n)

    # Build markdown
    lines = [f"## {title} {subtitle}\n"]
    lines.append(f"**Total significant terms**: {len(df[df['FDR q-val'].astype(float) < fdr_cutoff])}")
    lines.append(f"**Showing top**: {len(sig)}\n")

    # Table header
    lines.append("| Rank | Term | NES | FDR q-val | Lead Genes |")
    lines.append("|------|------|-----|-----------|------------|")

    # Table rows
    for idx, (_, row) in enumerate(sig.iterrows(), 1):
        term = row['Term']
        nes = f"{row['NES']:.2f}"
        fdr = f"{row['FDR q-val']:.3e}"
        lead_genes = row['Lead_genes']

        # Truncate if too long
        if len(lead_genes) > 100:
            lead_genes = lead_genes[:97] + "..."

        lines.append(f"| {idx} | {term} | {nes} | {fdr} | {lead_genes} |")

    return "\n".join(lines) + "\n"


def format_panther_results(
    panther_result: Dict,
    top_n: int = 10,
    title: str = "PANTHER Enrichment",
    fdr_cutoff: float = 0.05
) -> str:
    """
    Format PANTHER_enrichment results as markdown table.

    Args:
        panther_result: Result from tu.tools.PANTHER_enrichment()
        top_n: Number of top terms to include
        title: Table title
        fdr_cutoff: FDR cutoff for filtering

    Returns:
        Markdown formatted table string
    """
    terms = panther_result.get('data', {}).get('enriched_terms', [])
    sig = [t for t in terms if t.get('fdr', 1) < fdr_cutoff]

    if len(sig) == 0:
        return f"## {title}\n\nNo significant terms found at FDR < {fdr_cutoff}\n"

    # Sort by FDR
    sig = sorted(sig, key=lambda x: x.get('fdr', 1))[:top_n]

    # Build markdown
    lines = [f"## {title}\n"]
    lines.append(f"**Total significant terms**: {len([t for t in terms if t.get('fdr', 1) < fdr_cutoff])}")
    lines.append(f"**Showing top**: {len(sig)}\n")

    # Table header
    lines.append("| Rank | Term ID | Term | P-value | FDR | Fold Enrichment | Count |")
    lines.append("|------|---------|------|---------|-----|-----------------|-------|")

    # Table rows
    for idx, term in enumerate(sig, 1):
        term_id = term.get('term_id', 'N/A')
        term_label = term.get('term_label', 'N/A')
        pval = f"{term.get('pvalue', 1):.2e}"
        fdr = f"{term.get('fdr', 1):.2e}"
        fold = f"{term.get('fold_enrichment', 0):.2f}"
        count = f"{term.get('number_in_list', 0)}/{term.get('number_in_reference', 0)}"

        lines.append(f"| {idx} | {term_id} | {term_label} | {pval} | {fdr} | {fold} | {count} |")

    return "\n".join(lines) + "\n"


def format_string_results(
    string_result: Dict,
    category: str = 'Process',
    top_n: int = 10,
    title: Optional[str] = None,
    fdr_cutoff: float = 0.05
) -> str:
    """
    Format STRING_functional_enrichment results as markdown table.

    Args:
        string_result: Result from tu.tools.STRING_functional_enrichment()
        category: Category to filter ('Process', 'Function', 'Component', 'KEGG', 'Reactome')
        top_n: Number of top terms to include
        title: Table title (auto-generated if None)
        fdr_cutoff: FDR cutoff for filtering

    Returns:
        Markdown formatted table string
    """
    if title is None:
        title = f"STRING {category} Enrichment"

    data = string_result.get('data', [])
    if not isinstance(data, list):
        return f"## {title}\n\nNo results returned\n"

    # Filter by category
    filtered = [d for d in data if d.get('category') == category]
    sig = [d for d in filtered if d.get('fdr', 1) < fdr_cutoff]

    if len(sig) == 0:
        return f"## {title}\n\nNo significant terms found at FDR < {fdr_cutoff}\n"

    # Sort by FDR
    sig = sorted(sig, key=lambda x: x.get('fdr', 1))[:top_n]

    # Build markdown
    lines = [f"## {title}\n"]
    lines.append(f"**Total significant terms**: {len([d for d in filtered if d.get('fdr', 1) < fdr_cutoff])}")
    lines.append(f"**Showing top**: {len(sig)}\n")

    # Table header
    lines.append("| Rank | Term | Description | P-value | FDR | Count |")
    lines.append("|------|------|-------------|---------|-----|-------|")

    # Table rows
    for idx, item in enumerate(sig, 1):
        term = item.get('term', 'N/A')
        desc = item.get('description', 'N/A')
        # Truncate description
        if len(desc) > 50:
            desc = desc[:47] + "..."
        pval = f"{item.get('p_value', 1):.2e}"
        fdr = f"{item.get('fdr', 1):.2e}"
        count = f"{item.get('number_of_genes', 0)}/{item.get('number_of_genes_in_background', 0)}"

        lines.append(f"| {idx} | {term} | {desc} | {pval} | {fdr} | {count} |")

    return "\n".join(lines) + "\n"


def format_reactome_results(
    reactome_result: Dict,
    top_n: int = 10,
    title: str = "Reactome Pathway Enrichment",
    fdr_cutoff: float = 0.05
) -> str:
    """
    Format ReactomeAnalysis_pathway_enrichment results as markdown table.

    Args:
        reactome_result: Result from tu.tools.ReactomeAnalysis_pathway_enrichment()
        top_n: Number of top terms to include
        title: Table title
        fdr_cutoff: FDR cutoff for filtering

    Returns:
        Markdown formatted table string
    """
    pathways = reactome_result.get('data', {}).get('pathways', [])
    sig = [p for p in pathways if p.get('fdr', 1) < fdr_cutoff]

    if len(sig) == 0:
        return f"## {title}\n\nNo significant pathways found at FDR < {fdr_cutoff}\n"

    # Sort by FDR
    sig = sorted(sig, key=lambda x: x.get('fdr', 1))[:top_n]

    # Build markdown
    lines = [f"## {title}\n"]
    lines.append(f"**Total significant pathways**: {len([p for p in pathways if p.get('fdr', 1) < fdr_cutoff])}")
    lines.append(f"**Showing top**: {len(sig)}\n")

    # Table header
    lines.append("| Rank | Pathway ID | Name | P-value | FDR | Entities Found/Total |")
    lines.append("|------|-----------|------|---------|-----|---------------------|")

    # Table rows
    for idx, pathway in enumerate(sig, 1):
        pathway_id = pathway.get('pathway_id', 'N/A')
        name = pathway.get('name', 'N/A')
        # Truncate name
        if len(name) > 50:
            name = name[:47] + "..."
        pval = f"{pathway.get('p_value', 1):.2e}"
        fdr = f"{pathway.get('fdr', 1):.2e}"
        entities = f"{pathway.get('entities_found', 0)}/{pathway.get('entities_total', 0)}"

        lines.append(f"| {idx} | {pathway_id} | {name} | {pval} | {fdr} | {entities} |")

    return "\n".join(lines) + "\n"


def format_cross_validation_table(
    gseapy_result,
    panther_result: Optional[Dict] = None,
    string_result: Optional[Dict] = None,
    top_n: int = 20,
    fdr_cutoff: float = 0.05
) -> str:
    """
    Create cross-validation table comparing results from multiple tools.

    Args:
        gseapy_result: Result from gseapy.enrichr()
        panther_result: Result from PANTHER_enrichment (optional)
        string_result: Result from STRING_functional_enrichment (optional)
        top_n: Number of terms to include
        fdr_cutoff: FDR cutoff for filtering

    Returns:
        Markdown formatted comparison table
    """
    # Extract GO IDs and FDRs from gseapy
    gseapy_dict = {}
    for _, row in gseapy_result.results.iterrows():
        if row['Adjusted P-value'] < fdr_cutoff:
            match = re.search(r'(GO:\d+)', row['Term'])
            if match:
                go_id = match.group(1)
                gseapy_dict[go_id] = {
                    'term': row['Term'].split('(GO:')[0].strip(),
                    'fdr': row['Adjusted P-value']
                }

    # Extract from PANTHER
    panther_dict = {}
    if panther_result:
        terms = panther_result.get('data', {}).get('enriched_terms', [])
        for term in terms:
            if term.get('fdr', 1) < fdr_cutoff:
                go_id = term.get('term_id', '')
                if go_id.startswith('GO:'):
                    panther_dict[go_id] = {
                        'term': term.get('term_label', ''),
                        'fdr': term.get('fdr', 1)
                    }

    # Extract from STRING
    string_dict = {}
    if string_result:
        data = string_result.get('data', [])
        if isinstance(data, list):
            for item in data:
                if item.get('category') == 'Process' and item.get('fdr', 1) < fdr_cutoff:
                    go_id = item.get('term', '')
                    if go_id.startswith('GO:'):
                        string_dict[go_id] = {
                            'term': item.get('description', ''),
                            'fdr': item.get('fdr', 1)
                        }

    # Combine all GO IDs
    all_go_ids = set(gseapy_dict.keys()) | set(panther_dict.keys()) | set(string_dict.keys())

    # Build comparison rows
    rows = []
    for go_id in all_go_ids:
        sources = []
        if go_id in gseapy_dict: sources.append('gseapy')
        if go_id in panther_dict: sources.append('PANTHER')
        if go_id in string_dict: sources.append('STRING')

        # Only include if in 2+ sources (consensus)
        if len(sources) >= 2:
            term = (gseapy_dict.get(go_id, {}).get('term') or
                   panther_dict.get(go_id, {}).get('term') or
                   string_dict.get(go_id, {}).get('term', 'Unknown'))

            gseapy_fdr = f"{gseapy_dict[go_id]['fdr']:.2e}" if go_id in gseapy_dict else "-"
            panther_fdr = f"{panther_dict[go_id]['fdr']:.2e}" if go_id in panther_dict else "-"
            string_fdr = f"{string_dict[go_id]['fdr']:.2e}" if go_id in string_dict else "-"
            consensus = f"{len(sources)}/3 ✓" if len(sources) == 3 else f"{len(sources)}/3"

            rows.append({
                'go_id': go_id,
                'term': term,
                'gseapy_fdr': gseapy_fdr,
                'panther_fdr': panther_fdr,
                'string_fdr': string_fdr,
                'consensus': consensus,
                'n_sources': len(sources)
            })

    # Sort by number of sources (descending), then by gseapy FDR
    rows = sorted(rows, key=lambda x: (-x['n_sources'], x['gseapy_fdr']))[:top_n]

    if len(rows) == 0:
        return "## Cross-Validation\n\nNo consensus terms found (present in 2+ sources)\n"

    # Build markdown
    lines = ["## Cross-Validation Results\n"]
    lines.append(f"**Consensus terms** (present in 2+ sources): {len(rows)}\n")

    # Table header
    lines.append("| GO ID | Term | gseapy FDR | PANTHER FDR | STRING FDR | Consensus |")
    lines.append("|-------|------|-----------|-------------|-----------|-----------|")

    # Table rows
    for row in rows:
        term = row['term']
        if len(term) > 40:
            term = term[:37] + "..."
        lines.append(f"| {row['go_id']} | {term} | {row['gseapy_fdr']} | "
                    f"{row['panther_fdr']} | {row['string_fdr']} | {row['consensus']} |")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print("Enrichment output formatting functions loaded.")
    print("Import and use in your analysis scripts:")
    print("  from format_enrichment_output import format_ora_results, format_gsea_results")
