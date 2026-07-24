#!/usr/bin/env python3
"""
Core PhyKIT metric implementations for phylogenetic analysis.

This script provides all the core functions for computing phylogenetic metrics
using PhyKIT, Biopython, and DendroPy.
"""

import numpy as np
from types import SimpleNamespace
from Bio import AlignIO, Phylo
import io


# ============================================================================
# FILE LOADING
# ============================================================================

def load_alignment(filepath):
    """Load alignment with auto-format detection.

    Supports: FASTA, PHYLIP, PHYLIP-relaxed, Nexus, Clustal, Stockholm

    Returns: (alignment, format)
    """
    formats_to_try = ['fasta', 'phylip-relaxed', 'phylip', 'nexus', 'clustal', 'stockholm']

    for fmt in formats_to_try:
        try:
            alignment = AlignIO.read(filepath, fmt)
            return alignment, fmt
        except Exception:
            continue

    raise ValueError(f"Cannot parse alignment: {filepath}")


def load_tree(filepath):
    """Load tree with auto-format detection.

    Supports: Newick, Nexus

    Returns: (tree, format)
    """
    with open(filepath, 'r') as f:
        content = f.read().strip()

    # Try Newick first (most common)
    try:
        tree = Phylo.read(io.StringIO(content), 'newick')
        return tree, 'newick'
    except Exception:
        pass

    # Try Nexus
    try:
        tree = Phylo.read(io.StringIO(content), 'nexus')
        return tree, 'nexus'
    except Exception:
        pass

    raise ValueError(f"Cannot parse tree: {filepath}")


# ============================================================================
# PHYKIT TREE METRICS
# ============================================================================

def phykit_treeness(tree_file):
    """Calculate treeness (internal branch length / total branch length).

    Returns: float (0-1)
    """
    from phykit.services.tree.treeness import Treeness
    t = Treeness(SimpleNamespace(tree=tree_file))
    tree = t.read_tree_file()
    return t.calculate_treeness(tree)


def phykit_tree_length(tree_file):
    """Calculate total tree length (sum of all branch lengths).

    Returns: float
    """
    from phykit.services.tree.total_tree_length import TotalTreeLength
    tl = TotalTreeLength(SimpleNamespace(tree=tree_file))
    tree = tl.read_tree_file()
    return tl.calculate_total_tree_length(tree)


def phykit_evolutionary_rate(tree_file):
    """Calculate evolutionary rate (total branch length / number of terminals).

    Returns: float
    """
    from phykit.services.tree.evolutionary_rate import EvolutionaryRate
    er = EvolutionaryRate(SimpleNamespace(tree=tree_file))
    tree = er.read_tree_file()
    total_bl = tree.total_branch_length()
    num_terminals = tree.count_terminals()
    return total_bl / num_terminals


def phykit_dvmc(tree_file):
    """Calculate Degree of Violation of Molecular Clock.

    Returns: float
    """
    from phykit.services.tree.dvmc import DVMC
    d = DVMC(SimpleNamespace(tree=tree_file))
    tree = d.read_tree_file()
    return d.determine_dvmc(tree)


# ============================================================================
# PHYKIT ALIGNMENT METRICS
# ============================================================================

def phykit_parsimony_informative(aln_file):
    """Calculate parsimony informative sites.

    Returns: (pi_sites_count, alignment_length, pi_percentage)
    """
    from phykit.services.alignment.parsimony_informative_sites import ParsimonyInformative
    pi = ParsimonyInformative(SimpleNamespace(alignment=aln_file))
    alignment, _, _ = pi.get_alignment_and_format()
    return pi.calculate_parsimony_informative_sites(alignment)


def phykit_rcv(aln_file):
    """Calculate Relative Composition Variability.

    Returns: float
    """
    from phykit.services.alignment.rcv import RelativeCompositionVariability
    rcv = RelativeCompositionVariability(SimpleNamespace(alignment=aln_file))
    return rcv.calculate_rcv()


# ============================================================================
# COMBINED METRICS
# ============================================================================

def phykit_treeness_over_rcv(tree_file, aln_file):
    """Calculate treeness/RCV ratio.

    Returns: (treeness_over_rcv, treeness, rcv)
    """
    treeness = phykit_treeness(tree_file)
    rcv = phykit_rcv(aln_file)

    if rcv == 0:
        return float('inf'), treeness, rcv

    return treeness / rcv, treeness, rcv


# ============================================================================
# ALIGNMENT STATISTICS
# ============================================================================

def alignment_gap_percentage(aln_file):
    """Calculate overall gap percentage in alignment.

    Gap characters: '-', '.', '?'

    Returns: percentage (0-100)
    """
    alignment, fmt = load_alignment(aln_file)
    n_seqs = len(alignment)
    aln_len = alignment.get_alignment_length()
    total_chars = n_seqs * aln_len

    arr = np.array([[c for c in str(rec.seq)] for rec in alignment])
    gap_count = np.sum(np.isin(arr, ['-', '.', '?']))

    return (gap_count / total_chars) * 100


def alignment_statistics(aln_file):
    """Comprehensive alignment statistics.

    Returns: dict with n_seqs, aln_len, gap_pct, gc_pct, pi_sites, pi_pct,
                       variable_sites, variable_pct
    """
    alignment, fmt = load_alignment(aln_file)
    n_seqs = len(alignment)
    aln_len = alignment.get_alignment_length()

    arr = np.array([[c.upper() for c in str(rec.seq)] for rec in alignment])

    # Gap percentage
    gap_count = np.sum(np.isin(arr, ['-', '.', '?']))
    gap_pct = (gap_count / (n_seqs * aln_len)) * 100

    # GC content (excluding gaps)
    non_gap = arr[~np.isin(arr, ['-', '.', '?', 'N'])]
    gc_count = np.sum(np.isin(non_gap, ['G', 'C']))
    gc_pct = (gc_count / len(non_gap)) * 100 if len(non_gap) > 0 else 0

    # Parsimony informative sites
    pi_sites, _, pi_pct = phykit_parsimony_informative(aln_file)

    # Variable sites
    variable_count = 0
    for i in range(aln_len):
        col = arr[:, i]
        non_gap_col = col[~np.isin(col, ['-', '.', '?'])]
        if len(np.unique(non_gap_col)) > 1:
            variable_count += 1

    return {
        'n_seqs': n_seqs,
        'aln_len': aln_len,
        'gap_pct': round(gap_pct, 4),
        'gc_pct': round(gc_pct, 4),
        'pi_sites': pi_sites,
        'pi_pct': round(pi_pct, 4),
        'variable_sites': variable_count,
        'variable_pct': round((variable_count / aln_len) * 100, 4)
    }


# ============================================================================
# TREE STATISTICS
# ============================================================================

def tree_branch_stats(tree_file):
    """Compute branch length statistics from a tree.

    Returns: dict with branch statistics
    """
    tree, _ = load_tree(tree_file)

    internal_lengths = []
    terminal_lengths = []

    for clade in tree.find_clades():
        if clade.branch_length is not None:
            if clade.is_terminal():
                terminal_lengths.append(clade.branch_length)
            else:
                internal_lengths.append(clade.branch_length)

    all_lengths = internal_lengths + terminal_lengths

    return {
        'total_length': sum(all_lengths),
        'n_internal': len(internal_lengths),
        'n_terminal': len(terminal_lengths),
        'internal_sum': sum(internal_lengths),
        'terminal_sum': sum(terminal_lengths),
        'mean_branch': np.mean(all_lengths) if all_lengths else 0,
        'max_branch': max(all_lengths) if all_lengths else 0,
        'min_branch': min(all_lengths) if all_lengths else 0,
    }


def extract_bootstrap_support(tree_file):
    """Extract bootstrap support values from internal nodes.

    Returns: dict with support statistics
    """
    tree, _ = load_tree(tree_file)

    supports = []
    for clade in tree.get_nonterminals():
        if clade.confidence is not None:
            supports.append(clade.confidence)

    if not supports:
        return {'supports': [], 'mean': None, 'median': None}

    return {
        'supports': supports,
        'mean': float(np.mean(supports)),
        'median': float(np.median(supports)),
        'min': float(np.min(supports)),
        'max': float(np.max(supports)),
        'n_nodes': len(supports),
        'above_70': sum(1 for s in supports if s >= 70),
        'above_90': sum(1 for s in supports if s >= 90),
    }


# ============================================================================
# BATCH PROCESSING
# ============================================================================

def batch_compute_metric(gene_files, metric_func, requires='tree'):
    """Compute a metric across all genes in a group.

    Args:
        gene_files: list from discover_gene_files()
        metric_func: function that takes file path(s) and returns a number
        requires: 'tree', 'alignment', or 'both'

    Returns: dict mapping gene_id -> metric_value (skipping failures)
    """
    results = {}
    for entry in gene_files:
        gene_id = entry['gene_id']
        try:
            if requires == 'tree' and 'tree_file' in entry:
                results[gene_id] = metric_func(entry['tree_file'])
            elif requires == 'alignment' and 'aln_file' in entry:
                results[gene_id] = metric_func(entry['aln_file'])
            elif requires == 'both' and 'tree_file' in entry and 'aln_file' in entry:
                results[gene_id] = metric_func(entry['tree_file'], entry['aln_file'])
        except Exception:
            pass
    return results


def batch_treeness(gene_files):
    return batch_compute_metric(gene_files, phykit_treeness, requires='tree')


def batch_tree_length(gene_files):
    return batch_compute_metric(gene_files, phykit_tree_length, requires='tree')


def batch_evolutionary_rate(gene_files):
    return batch_compute_metric(gene_files, phykit_evolutionary_rate, requires='tree')


def batch_dvmc(gene_files):
    return batch_compute_metric(gene_files, phykit_dvmc, requires='tree')


def batch_rcv(gene_files):
    return batch_compute_metric(gene_files, phykit_rcv, requires='alignment')


def batch_parsimony_informative(gene_files):
    """Returns dict of gene_id -> (count, aln_len, percentage)"""
    results = {}
    for entry in gene_files:
        if 'aln_file' in entry:
            try:
                results[entry['gene_id']] = phykit_parsimony_informative(entry['aln_file'])
            except Exception:
                pass
    return results


def batch_treeness_over_rcv(gene_files):
    """Returns dict of gene_id -> (treeness_over_rcv, treeness, rcv)"""
    results = {}
    for entry in gene_files:
        if 'tree_file' in entry and 'aln_file' in entry:
            try:
                results[entry['gene_id']] = phykit_treeness_over_rcv(
                    entry['tree_file'], entry['aln_file']
                )
            except Exception:
                pass
    return results


def batch_gap_percentage(gene_files):
    return batch_compute_metric(gene_files, alignment_gap_percentage, requires='alignment')


# ============================================================================
# SUMMARY STATISTICS
# ============================================================================

def summary_stats(values):
    """Compute standard summary statistics for a list of values."""
    arr = np.array(values)
    return {
        'count': len(arr),
        'mean': float(np.mean(arr)),
        'median': float(np.median(arr)),
        'std': float(np.std(arr, ddof=1)),
        'var': float(np.var(arr, ddof=1)),
        'min': float(np.min(arr)),
        'max': float(np.max(arr)),
        'q25': float(np.percentile(arr, 25)),
        'q75': float(np.percentile(arr, 75)),
    }


# ============================================================================
# GROUP COMPARISON
# ============================================================================

def compare_groups(group1_values, group2_values, group1_name="Group1", group2_name="Group2"):
    """Compare two groups using Mann-Whitney U test.

    Returns: dict with U statistic, p-value, and summary stats for each group
    """
    from scipy import stats

    arr1 = np.array(group1_values)
    arr2 = np.array(group2_values)

    # Mann-Whitney U test (two-sided, default)
    u_stat, p_value = stats.mannwhitneyu(arr1, arr2, alternative='two-sided')

    return {
        'u_statistic': float(u_stat),
        'p_value': float(p_value),
        group1_name: summary_stats(arr1.tolist()),
        group2_name: summary_stats(arr2.tolist()),
        'median_difference': float(np.median(arr1) - np.median(arr2)),
    }


def paired_comparison(group1_dict, group2_dict):
    """Compare matched pairs (same gene IDs in both groups).

    Returns: dict with paired differences and statistics
    """
    common_genes = set(group1_dict.keys()) & set(group2_dict.keys())

    diffs = []
    ratios = []
    for gene in sorted(common_genes):
        v1 = group1_dict[gene]
        v2 = group2_dict[gene]
        diffs.append(v1 - v2)
        if v2 != 0:
            ratios.append(v1 / v2)

    result = {
        'n_pairs': len(common_genes),
        'differences': summary_stats(diffs),
        'median_difference': float(np.median(diffs)),
    }

    if ratios:
        result['ratios'] = summary_stats(ratios)
        result['median_ratio'] = float(np.median(ratios))

    return result


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python tree_statistics.py <tree_file> [alignment_file]")
        sys.exit(1)

    tree_file = sys.argv[1]
    aln_file = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Analyzing: {tree_file}")

    # Tree metrics
    if tree_file:
        print("\n=== Tree Metrics ===")
        print(f"Treeness: {phykit_treeness(tree_file):.4f}")
        print(f"Tree length: {phykit_tree_length(tree_file):.4f}")
        print(f"Evolutionary rate: {phykit_evolutionary_rate(tree_file):.4f}")
        print(f"DVMC: {phykit_dvmc(tree_file):.4f}")

        stats = tree_branch_stats(tree_file)
        print(f"\nBranch statistics:")
        print(f"  Total length: {stats['total_length']:.4f}")
        print(f"  Internal branches: {stats['n_internal']}")
        print(f"  Terminal branches: {stats['n_terminal']}")
        print(f"  Mean branch length: {stats['mean_branch']:.4f}")

    # Alignment metrics
    if aln_file:
        print("\n=== Alignment Metrics ===")
        pi_count, aln_len, pi_pct = phykit_parsimony_informative(aln_file)
        print(f"Parsimony informative sites: {pi_count} / {aln_len} ({pi_pct:.2f}%)")
        print(f"RCV: {phykit_rcv(aln_file):.4f}")
        print(f"Gap percentage: {alignment_gap_percentage(aln_file):.2f}%")

        stats = alignment_statistics(aln_file)
        print(f"\nAlignment statistics:")
        print(f"  Sequences: {stats['n_seqs']}")
        print(f"  Length: {stats['aln_len']}")
        print(f"  GC content: {stats['gc_pct']:.2f}%")
        print(f"  Variable sites: {stats['variable_sites']} ({stats['variable_pct']:.2f}%)")

    # Combined metrics
    if tree_file and aln_file:
        print("\n=== Combined Metrics ===")
        ratio, treeness, rcv = phykit_treeness_over_rcv(tree_file, aln_file)
        print(f"Treeness/RCV: {ratio:.4f} (treeness={treeness:.4f}, rcv={rcv:.4f})")
