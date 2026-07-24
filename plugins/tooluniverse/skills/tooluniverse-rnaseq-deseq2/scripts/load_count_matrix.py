#!/usr/bin/env python3
"""Data loading utilities for RNA-seq count matrices."""

import pandas as pd
import numpy as np
import os


def load_count_matrix(file_path, **kwargs):
    """Load count matrix from various formats.

    Expects: genes as rows/columns, samples as rows/columns.
    PyDESeq2 requires: samples as rows, genes as columns.

    Args:
        file_path: Path to count matrix file
        **kwargs: Additional arguments for pd.read_csv

    Returns:
        DataFrame with counts, or (DataFrame, metadata) for h5ad files
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext in ['.csv']:
        df = pd.read_csv(file_path, index_col=0, **kwargs)
    elif ext in ['.tsv', '.txt']:
        df = pd.read_csv(file_path, sep='\t', index_col=0, **kwargs)
    elif ext in ['.h5ad']:
        import anndata
        adata = anndata.read_h5ad(file_path)
        df = pd.DataFrame(
            adata.X.toarray() if hasattr(adata.X, 'toarray') else adata.X,
            index=adata.obs_names,
            columns=adata.var_names
        )
        return df, adata.obs  # Return metadata too if available
    else:
        # Try tab-separated as default
        df = pd.read_csv(file_path, sep='\t', index_col=0, **kwargs)

    return df


def load_metadata(file_path, **kwargs):
    """Load sample metadata (colData in R).

    Args:
        file_path: Path to metadata file
        **kwargs: Additional arguments for pd.read_csv

    Returns:
        DataFrame with metadata
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext in ['.csv']:
        meta = pd.read_csv(file_path, index_col=0, **kwargs)
    elif ext in ['.tsv', '.txt']:
        meta = pd.read_csv(file_path, sep='\t', index_col=0, **kwargs)
    else:
        meta = pd.read_csv(file_path, sep='\t', index_col=0, **kwargs)

    return meta


def orient_count_matrix(df, metadata_samples=None):
    """Ensure samples are rows and genes are columns.

    Heuristic: if column count >> row count, genes are likely columns (correct).
    If row count >> column count, genes are likely rows (need transpose).
    If metadata_samples provided, match against index and columns.

    Args:
        df: Count matrix DataFrame
        metadata_samples: List/Index of sample names from metadata

    Returns:
        Oriented DataFrame (samples as rows, genes as columns)
    """
    if metadata_samples is not None:
        # Check if samples match rows or columns
        row_match = len(set(df.index) & set(metadata_samples))
        col_match = len(set(df.columns) & set(metadata_samples))
        if col_match > row_match:
            df = df.T
        return df

    # Heuristic: typical RNA-seq has 10-1000 samples and 10000-60000 genes
    if df.shape[0] > df.shape[1] * 5:  # Many more rows than columns
        df = df.T  # Transpose: genes were rows

    return df


def validate_inputs(counts, metadata):
    """Validate count matrix and metadata alignment.

    Args:
        counts: Count matrix DataFrame
        metadata: Metadata DataFrame

    Returns:
        Tuple of (counts, metadata, issues)
        - counts: Validated and aligned count matrix
        - metadata: Validated and aligned metadata
        - issues: List of validation messages
    """
    issues = []

    # Check sample alignment
    count_samples = set(counts.index)
    meta_samples = set(metadata.index)

    if count_samples != meta_samples:
        common = count_samples & meta_samples
        if len(common) == 0:
            # Try matching columns
            if set(counts.columns) & meta_samples:
                counts = counts.T
                count_samples = set(counts.index)
                common = count_samples & meta_samples

        if len(common) > 0:
            counts = counts.loc[sorted(common)]
            metadata = metadata.loc[sorted(common)]
            issues.append(f"Aligned to {len(common)} common samples")
        else:
            issues.append("ERROR: No matching samples between counts and metadata")
            return None, None, issues

    # Ensure integer counts
    if counts.dtypes.apply(lambda x: x == float).any():
        if (counts % 1 == 0).all().all():
            counts = counts.astype(int)
        else:
            # Might be normalized data - round to integers for DESeq2
            issues.append("WARNING: Non-integer counts detected. Rounding to integers.")
            counts = counts.round().astype(int)

    # Remove genes with zero counts across all samples
    nonzero_mask = counts.sum(axis=0) > 0
    n_removed = (~nonzero_mask).sum()
    if n_removed > 0:
        counts = counts.loc[:, nonzero_mask]
        issues.append(f"Removed {n_removed} genes with zero counts across all samples")

    # Remove negative values
    if (counts < 0).any().any():
        issues.append("WARNING: Negative counts detected. Setting to 0.")
        counts = counts.clip(lower=0)

    return counts, metadata, issues


def subset_samples(counts, metadata, condition_col, values=None, exclude=None):
    """Subset samples based on metadata conditions.

    Args:
        counts: Count matrix DataFrame
        metadata: Metadata DataFrame
        condition_col: Column name in metadata to filter on
        values: List of values to keep (if provided)
        exclude: List of values to exclude (if provided)

    Returns:
        Tuple of (counts, metadata) with subsetted samples
    """
    if values is not None:
        mask = metadata[condition_col].isin(values)
    elif exclude is not None:
        mask = ~metadata[condition_col].isin(exclude)
    else:
        return counts, metadata

    metadata = metadata[mask]
    counts = counts.loc[metadata.index]
    return counts, metadata


def set_reference_level(metadata, factor_col, ref_value):
    """Set reference level for a factor by reordering Categorical.

    The FIRST category becomes the reference level in PyDESeq2.

    Args:
        metadata: Metadata DataFrame
        factor_col: Column name to set reference for
        ref_value: Value to use as reference

    Returns:
        Metadata with updated categorical column
    """
    current_cats = metadata[factor_col].unique().tolist()
    if ref_value not in current_cats:
        raise ValueError(f"Reference '{ref_value}' not in categories: {current_cats}")

    # Put reference first
    ordered_cats = [ref_value] + [c for c in current_cats if c != ref_value]
    metadata[factor_col] = pd.Categorical(
        metadata[factor_col],
        categories=ordered_cats
    )
    return metadata


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python load_count_matrix.py <counts_file> <metadata_file>")
        sys.exit(1)

    counts_file = sys.argv[1]
    metadata_file = sys.argv[2]

    print(f"Loading counts from {counts_file}")
    counts = load_count_matrix(counts_file)
    print(f"  Shape: {counts.shape}")

    print(f"\nLoading metadata from {metadata_file}")
    metadata = load_metadata(metadata_file)
    print(f"  Shape: {metadata.shape}")

    print("\nOrienting matrix...")
    counts = orient_count_matrix(counts, metadata.index)
    print(f"  Shape after orientation: {counts.shape}")

    print("\nValidating...")
    counts, metadata, issues = validate_inputs(counts, metadata)
    if counts is not None:
        print(f"  Final shape: {counts.shape[0]} samples × {counts.shape[1]} genes")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  Validation failed!")
        for issue in issues:
            print(f"  {issue}")
