#!/usr/bin/env python3
"""Output formatters for DESeq2 results to match BixBench expected formats."""

import pandas as pd
import numpy as np


def format_count(value):
    """Format as integer count (no decimals)."""
    return int(value)


def format_decimal(value, n_decimals=2):
    """Format with specific number of decimal places."""
    return round(value, n_decimals)


def format_scientific(value, n_decimals=2):
    """Format in scientific notation."""
    return f"{value:.{n_decimals}E}"


def format_percentage(value, n_decimals=1, include_sign=True):
    """Format as percentage.

    Args:
        value: Float value (0-1 or 0-100)
        n_decimals: Decimal places
        include_sign: Include % sign in output

    Returns:
        Formatted percentage string or float
    """
    if value < 1:  # Assume 0-1 scale
        value = value * 100

    if include_sign:
        return f"{round(value, n_decimals)}%"
    else:
        return round(value, n_decimals)


def format_ratio(numerator, denominator):
    """Format as ratio X:Y."""
    return f"{numerator}:{denominator}"


def format_fraction(numerator, denominator):
    """Format as fraction X/Y."""
    return f"{numerator}/{denominator}"


def format_confidence_interval(ci_low, ci_high, n_decimals=2):
    """Format confidence interval as (X, Y)."""
    return (round(ci_low, n_decimals), round(ci_high, n_decimals))


def format_range(min_val, max_val, n_decimals=2):
    """Format as range min-max."""
    return f"{round(min_val, n_decimals)}-{round(max_val, n_decimals)}"


def auto_format(value, question_text):
    """Auto-detect format from question text and apply appropriate formatting.

    Args:
        value: Value to format
        question_text: Question text to parse for format hints

    Returns:
        Formatted value
    """
    question_lower = question_text.lower()

    # Count questions
    if "how many" in question_lower:
        return format_count(value)

    # Decimal places
    if "2 decimal" in question_lower:
        return format_decimal(value, 2)
    elif "4 decimal" in question_lower:
        return format_decimal(value, 4)
    elif "1 decimal" in question_lower:
        return format_decimal(value, 1)

    # Scientific notation
    if "scientific notation" in question_lower:
        return format_scientific(value)

    # Percentage
    if "percentage" in question_lower:
        return format_percentage(value)

    # Default: no formatting
    return value


def format_deg_summary(results, padj_threshold=0.05, lfc_threshold=0):
    """Generate formatted summary of DEG counts.

    Args:
        results: DESeq2 results DataFrame
        padj_threshold: Adjusted p-value threshold
        lfc_threshold: Absolute log2 fold change threshold

    Returns:
        Dict with formatted summary statistics
    """
    sig = results[
        (results['padj'] < padj_threshold) &
        (results['log2FoldChange'].abs() > lfc_threshold)
    ]

    summary = {
        'total_genes': format_count(len(results)),
        'significant_genes': format_count(len(sig)),
        'upregulated': format_count(len(sig[sig['log2FoldChange'] > 0])),
        'downregulated': format_count(len(sig[sig['log2FoldChange'] < 0])),
        'percent_significant': format_percentage(len(sig) / len(results), n_decimals=1),
    }

    return summary


def format_gene_result(results, gene_name, column='log2FoldChange', n_decimals=2):
    """Extract and format specific gene result.

    Args:
        results: DESeq2 results DataFrame
        gene_name: Gene to extract
        column: Column to extract
        n_decimals: Decimal places for formatting

    Returns:
        Formatted value or None if gene not found
    """
    if gene_name not in results.index:
        # Try case-insensitive match
        idx_lower = {g.lower(): g for g in results.index}
        if gene_name.lower() in idx_lower:
            gene_name = idx_lower[gene_name.lower()]
        else:
            return None

    value = results.loc[gene_name, column]

    if pd.isna(value):
        return None

    return format_decimal(value, n_decimals)


def format_enrichment_result(enr_results, term_query, metric='Adjusted P-value', n_decimals=4):
    """Extract and format enrichment result.

    Args:
        enr_results: gseapy enrichment results DataFrame
        term_query: Term to search for (case-insensitive)
        metric: Metric to extract
        n_decimals: Decimal places

    Returns:
        Formatted value or None if not found
    """
    mask = enr_results['Term'].str.lower().str.contains(term_query.lower())
    matches = enr_results[mask]

    if len(matches) == 0:
        return None
    elif len(matches) == 1:
        value = matches.iloc[0][metric]
        return format_decimal(value, n_decimals)
    else:
        # Multiple matches - return first
        value = matches.iloc[0][metric]
        return format_decimal(value, n_decimals)


def format_results_table(results, top_n=10, columns=None):
    """Format results as clean table for display.

    Args:
        results: DESeq2 results DataFrame
        top_n: Number of top genes to include
        columns: Columns to include (default: key columns)

    Returns:
        Formatted DataFrame
    """
    if columns is None:
        columns = ['baseMean', 'log2FoldChange', 'lfcSE', 'stat', 'pvalue', 'padj']

    # Get top genes by padj
    top_genes = results.sort_values('padj').head(top_n)

    # Format numeric columns
    formatted = top_genes[columns].copy()
    for col in ['baseMean', 'log2FoldChange', 'lfcSE', 'stat']:
        if col in formatted.columns:
            formatted[col] = formatted[col].apply(lambda x: f"{x:.2f}")
    for col in ['pvalue', 'padj']:
        if col in formatted.columns:
            formatted[col] = formatted[col].apply(lambda x: f"{x:.2E}" if x < 0.01 else f"{x:.4f}")

    return formatted


def export_deg_list(results, output_file, padj_threshold=0.05, lfc_threshold=0,
                    include_stats=True):
    """Export DEG list to file with formatting.

    Args:
        results: DESeq2 results DataFrame
        output_file: Output file path
        padj_threshold: Adjusted p-value threshold
        lfc_threshold: Absolute log2 fold change threshold
        include_stats: Include statistical columns
    """
    sig = results[
        (results['padj'] < padj_threshold) &
        (results['log2FoldChange'].abs() > lfc_threshold)
    ]

    if include_stats:
        columns = ['baseMean', 'log2FoldChange', 'lfcSE', 'pvalue', 'padj']
    else:
        columns = ['log2FoldChange', 'padj']

    sig[columns].to_csv(output_file)
    print(f"Exported {len(sig)} DEGs to {output_file}")


def create_answer_dict(results, question_patterns):
    """Create dictionary of formatted answers for multiple questions.

    Args:
        results: DESeq2 results or dict of results
        question_patterns: Dict of {question_id: (pattern_type, params)}

    Returns:
        Dict of {question_id: formatted_answer}
    """
    answers = {}

    for qid, (pattern, params) in question_patterns.items():
        if pattern == 'deg_count':
            sig = results[
                (results['padj'] < params['padj']) &
                (results['log2FoldChange'].abs() > params.get('lfc', 0))
            ]
            answers[qid] = format_count(len(sig))

        elif pattern == 'gene_value':
            value = format_gene_result(
                results,
                params['gene'],
                params.get('column', 'log2FoldChange'),
                params.get('decimals', 2)
            )
            answers[qid] = value

        elif pattern == 'percentage':
            answers[qid] = format_percentage(
                params['value'],
                params.get('decimals', 1),
                params.get('include_sign', True)
            )

    return answers


# Example usage
if __name__ == "__main__":
    # Example: Format various outputs
    print("=== Formatting Examples ===\n")

    # Count
    print(f"Count: {format_count(842.0)}")

    # Decimals
    print(f"2 decimals: {format_decimal(2.456789, 2)}")
    print(f"4 decimals: {format_decimal(0.0234567, 4)}")

    # Scientific notation
    print(f"Scientific: {format_scientific(0.0000123, 2)}")

    # Percentage
    print(f"Percentage (0-1): {format_percentage(0.153, 1)}")
    print(f"Percentage (0-100): {format_percentage(15.3, 1)}")

    # Ratio and fraction
    print(f"Ratio: {format_ratio(3, 1)}")
    print(f"Fraction: {format_fraction(11, 42)}")

    # Confidence interval
    print(f"CI: {format_confidence_interval(0.15, 0.25, 2)}")

    # Auto-format
    print(f"\nAuto-format examples:")
    print(f"  'How many genes...': {auto_format(842.0, 'How many genes are significant?')}")
    print(f"  '...2 decimal points': {auto_format(2.456, 'Round to 2 decimal points')}")
    print(f"  '...percentage': {auto_format(0.153, 'What percentage of genes?')}")
