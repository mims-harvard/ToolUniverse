#!/usr/bin/env python3
"""
Alignment format conversion and manipulation utilities.

This script provides utilities for converting between alignment formats,
filtering alignments, and performing common preprocessing tasks.
"""

from Bio import AlignIO, SeqIO
import glob
import os
import argparse


# ============================================================================
# FILE DISCOVERY
# ============================================================================

def discover_gene_files(data_dir, group_name=None):
    """Discover paired alignment and tree files for a group.

    Args:
        data_dir: root directory to search
        group_name: optional subdirectory (e.g., "fungi", "animals")

    Returns: list of dicts with 'gene_id', 'aln_file', 'tree_file'
    """
    search_dir = os.path.join(data_dir, group_name) if group_name else data_dir

    # Find alignments
    aln_files = {}
    aln_extensions = ['*.fa', '*.fasta', '*.faa', '*.fna', '*.phy', '*.phylip', '*.nex']
    for ext in aln_extensions:
        for f in glob.glob(os.path.join(search_dir, '**', ext), recursive=True):
            gene_id = os.path.splitext(os.path.basename(f))[0]
            # Remove common suffixes
            for suffix in ['.aligned', '.aln', '.msa', '_aligned', '_alignment']:
                gene_id = gene_id.replace(suffix, '')
            aln_files[gene_id] = f

    # Find trees
    tree_files = {}
    tree_extensions = ['*.nwk', '*.newick', '*.tre', '*.tree', '*.treefile']
    for ext in tree_extensions:
        for f in glob.glob(os.path.join(search_dir, '**', ext), recursive=True):
            gene_id = os.path.splitext(os.path.basename(f))[0]
            for suffix in ['.treefile', '_tree', '.rooted', '_rooted']:
                gene_id = gene_id.replace(suffix, '')
            tree_files[gene_id] = f

    # Match pairs
    results = []
    all_gene_ids = set(aln_files.keys()) | set(tree_files.keys())
    for gene_id in sorted(all_gene_ids):
        entry = {'gene_id': gene_id}
        if gene_id in aln_files:
            entry['aln_file'] = aln_files[gene_id]
        if gene_id in tree_files:
            entry['tree_file'] = tree_files[gene_id]
        results.append(entry)

    return results


# ============================================================================
# FORMAT CONVERSION
# ============================================================================

def load_alignment(filepath):
    """Load alignment with auto-format detection."""
    formats_to_try = ['fasta', 'phylip-relaxed', 'phylip', 'nexus', 'clustal', 'stockholm']

    for fmt in formats_to_try:
        try:
            alignment = AlignIO.read(filepath, fmt)
            return alignment, fmt
        except Exception:
            continue

    raise ValueError(f"Cannot parse alignment: {filepath}")


def convert_alignment_format(input_file, output_file, output_format='fasta'):
    """Convert alignment to different format.

    Supported formats: fasta, phylip, phylip-relaxed, nexus, clustal
    """
    alignment, input_format = load_alignment(input_file)
    AlignIO.write(alignment, output_file, output_format)
    print(f"Converted {input_file} ({input_format}) -> {output_file} ({output_format})")
    return output_format


def batch_convert_format(input_dir, output_dir, output_format='fasta'):
    """Convert all alignments in a directory to a specific format.

    Args:
        input_dir: directory containing alignments
        output_dir: directory to write converted alignments
        output_format: target format (fasta, phylip, phylip-relaxed, nexus)
    """
    os.makedirs(output_dir, exist_ok=True)

    gene_files = discover_gene_files(input_dir)
    converted = 0

    for entry in gene_files:
        if 'aln_file' not in entry:
            continue

        input_file = entry['aln_file']
        gene_id = entry['gene_id']

        # Determine output extension
        ext_map = {
            'fasta': '.fa',
            'phylip': '.phy',
            'phylip-relaxed': '.phy',
            'nexus': '.nex',
            'clustal': '.aln'
        }
        ext = ext_map.get(output_format, '.txt')
        output_file = os.path.join(output_dir, f"{gene_id}{ext}")

        try:
            convert_alignment_format(input_file, output_file, output_format)
            converted += 1
        except Exception as e:
            print(f"ERROR converting {input_file}: {e}")

    print(f"\nConverted {converted}/{len([e for e in gene_files if 'aln_file' in e])} alignments")


# ============================================================================
# FILTERING
# ============================================================================

def filter_by_gap_threshold(gene_files, max_gap_pct=5.0):
    """Filter alignments by maximum gap percentage.

    Returns: list of gene entries passing threshold
    """
    import numpy as np

    valid_genes = []
    for entry in gene_files:
        if 'aln_file' not in entry:
            continue

        try:
            alignment, _ = load_alignment(entry['aln_file'])
            n_seqs = len(alignment)
            aln_len = alignment.get_alignment_length()
            total_chars = n_seqs * aln_len

            arr = np.array([[c for c in str(rec.seq)] for rec in alignment])
            gap_count = np.sum(np.isin(arr, ['-', '.', '?']))
            gap_pct = (gap_count / total_chars) * 100

            if gap_pct <= max_gap_pct:
                valid_genes.append(entry)
        except Exception:
            pass

    return valid_genes


def filter_by_min_sequences(gene_files, min_seqs=4):
    """Filter alignments by minimum number of sequences."""
    valid_genes = []
    for entry in gene_files:
        if 'aln_file' not in entry:
            continue

        try:
            alignment, _ = load_alignment(entry['aln_file'])
            if len(alignment) >= min_seqs:
                valid_genes.append(entry)
        except Exception:
            pass

    return valid_genes


def filter_by_min_length(gene_files, min_length=100):
    """Filter alignments by minimum alignment length."""
    valid_genes = []
    for entry in gene_files:
        if 'aln_file' not in entry:
            continue

        try:
            alignment, _ = load_alignment(entry['aln_file'])
            if alignment.get_alignment_length() >= min_length:
                valid_genes.append(entry)
        except Exception:
            pass

    return valid_genes


# ============================================================================
# ALIGNMENT MANIPULATION
# ============================================================================

def trim_alignment(input_file, output_file, start=None, end=None):
    """Trim alignment to specific column range.

    Args:
        input_file: input alignment file
        output_file: output alignment file
        start: start column (0-indexed), None = beginning
        end: end column (exclusive), None = end
    """
    alignment, fmt = load_alignment(input_file)
    aln_len = alignment.get_alignment_length()

    start = start or 0
    end = end or aln_len

    trimmed = alignment[:, start:end]
    AlignIO.write(trimmed, output_file, 'fasta')

    print(f"Trimmed {input_file} from {aln_len} to {end-start} columns")


def remove_gappy_sequences(input_file, output_file, max_gap_pct=50.0):
    """Remove sequences with excessive gaps.

    Args:
        input_file: input alignment file
        output_file: output alignment file
        max_gap_pct: maximum allowed gap percentage per sequence
    """
    alignment, fmt = load_alignment(input_file)
    aln_len = alignment.get_alignment_length()

    kept_seqs = []
    for record in alignment:
        seq_str = str(record.seq)
        gap_count = seq_str.count('-') + seq_str.count('.') + seq_str.count('?')
        gap_pct = (gap_count / len(seq_str)) * 100

        if gap_pct <= max_gap_pct:
            kept_seqs.append(record)

    from Bio.Align import MultipleSeqAlignment
    filtered = MultipleSeqAlignment(kept_seqs)
    AlignIO.write(filtered, output_file, 'fasta')

    print(f"Kept {len(kept_seqs)}/{len(alignment)} sequences (removed {len(alignment)-len(kept_seqs)} gappy sequences)")


def remove_gappy_columns(input_file, output_file, max_gap_pct=50.0):
    """Remove columns with excessive gaps.

    Args:
        input_file: input alignment file
        output_file: output alignment file
        max_gap_pct: maximum allowed gap percentage per column
    """
    import numpy as np

    alignment, fmt = load_alignment(input_file)
    n_seqs = len(alignment)
    aln_len = alignment.get_alignment_length()

    arr = np.array([[c for c in str(rec.seq)] for rec in alignment])

    # Find columns to keep
    keep_cols = []
    for i in range(aln_len):
        col = arr[:, i]
        gap_count = np.sum(np.isin(col, ['-', '.', '?']))
        gap_pct = (gap_count / n_seqs) * 100

        if gap_pct <= max_gap_pct:
            keep_cols.append(i)

    # Create filtered alignment
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.Align import MultipleSeqAlignment

    filtered_records = []
    for j, record in enumerate(alignment):
        filtered_seq = ''.join([arr[j, i] for i in keep_cols])
        filtered_records.append(
            SeqRecord(Seq(filtered_seq), id=record.id, description=record.description)
        )

    filtered = MultipleSeqAlignment(filtered_records)
    AlignIO.write(filtered, output_file, 'fasta')

    print(f"Kept {len(keep_cols)}/{aln_len} columns (removed {aln_len-len(keep_cols)} gappy columns)")


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Alignment format conversion and manipulation")
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert alignment format')
    convert_parser.add_argument('input', help='Input alignment file')
    convert_parser.add_argument('output', help='Output alignment file')
    convert_parser.add_argument('--format', default='fasta',
                               choices=['fasta', 'phylip', 'phylip-relaxed', 'nexus', 'clustal'],
                               help='Output format')

    # Batch convert command
    batch_parser = subparsers.add_parser('batch-convert', help='Batch convert alignments')
    batch_parser.add_argument('input_dir', help='Input directory')
    batch_parser.add_argument('output_dir', help='Output directory')
    batch_parser.add_argument('--format', default='fasta',
                             choices=['fasta', 'phylip', 'phylip-relaxed', 'nexus', 'clustal'],
                             help='Output format')

    # Discover command
    discover_parser = subparsers.add_parser('discover', help='Discover gene files')
    discover_parser.add_argument('data_dir', help='Data directory')
    discover_parser.add_argument('--group', help='Group name (optional subdirectory)')

    # Filter command
    filter_parser = subparsers.add_parser('filter', help='Filter alignments')
    filter_parser.add_argument('data_dir', help='Data directory')
    filter_parser.add_argument('--max-gap', type=float, default=5.0,
                              help='Maximum gap percentage')
    filter_parser.add_argument('--min-seqs', type=int, default=4,
                              help='Minimum number of sequences')
    filter_parser.add_argument('--min-length', type=int, default=100,
                              help='Minimum alignment length')

    # Trim command
    trim_parser = subparsers.add_parser('trim', help='Trim alignment columns')
    trim_parser.add_argument('input', help='Input alignment file')
    trim_parser.add_argument('output', help='Output alignment file')
    trim_parser.add_argument('--start', type=int, help='Start column (0-indexed)')
    trim_parser.add_argument('--end', type=int, help='End column (exclusive)')

    # Remove gappy sequences
    remove_seq_parser = subparsers.add_parser('remove-gappy-seqs', help='Remove gappy sequences')
    remove_seq_parser.add_argument('input', help='Input alignment file')
    remove_seq_parser.add_argument('output', help='Output alignment file')
    remove_seq_parser.add_argument('--max-gap', type=float, default=50.0,
                                   help='Maximum gap percentage per sequence')

    # Remove gappy columns
    remove_col_parser = subparsers.add_parser('remove-gappy-cols', help='Remove gappy columns')
    remove_col_parser.add_argument('input', help='Input alignment file')
    remove_col_parser.add_argument('output', help='Output alignment file')
    remove_col_parser.add_argument('--max-gap', type=float, default=50.0,
                                   help='Maximum gap percentage per column')

    args = parser.parse_args()

    if args.command == 'convert':
        convert_alignment_format(args.input, args.output, args.format)

    elif args.command == 'batch-convert':
        batch_convert_format(args.input_dir, args.output_dir, args.format)

    elif args.command == 'discover':
        gene_files = discover_gene_files(args.data_dir, args.group)
        print(f"Found {len(gene_files)} genes")
        print(f"With alignments: {sum(1 for g in gene_files if 'aln_file' in g)}")
        print(f"With trees: {sum(1 for g in gene_files if 'tree_file' in g)}")
        print(f"With both: {sum(1 for g in gene_files if 'aln_file' in g and 'tree_file' in g)}")

    elif args.command == 'filter':
        gene_files = discover_gene_files(args.data_dir)
        print(f"Total genes: {len(gene_files)}")

        valid = gene_files
        valid = filter_by_gap_threshold(valid, args.max_gap)
        print(f"After gap filter (<{args.max_gap}%): {len(valid)}")

        valid = filter_by_min_sequences(valid, args.min_seqs)
        print(f"After sequence count filter (>={args.min_seqs}): {len(valid)}")

        valid = filter_by_min_length(valid, args.min_length)
        print(f"After length filter (>={args.min_length}): {len(valid)}")

    elif args.command == 'trim':
        trim_alignment(args.input, args.output, args.start, args.end)

    elif args.command == 'remove-gappy-seqs':
        remove_gappy_sequences(args.input, args.output, args.max_gap)

    elif args.command == 'remove-gappy-cols':
        remove_gappy_columns(args.input, args.output, args.max_gap)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
