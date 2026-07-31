"""
expression_anova_per_gene

Per-gene ANOVA or log2 fold-change on a gene x sample expression matrix. Each gene contributes on...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def expression_anova_per_gene(
    counts_file: str,
    meta_file: str,
    group_col: str,
    mode: str,
    exclude_groups: Optional[list[str]] = None,
    group_a: Optional[str] = None,
    group_b: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Per-gene ANOVA or log2 fold-change on a gene x sample expression matrix. Each gene contributes on...

    Parameters
    ----------
    counts_file : str
        Path to CSV count matrix (genes x samples, first column = gene IDs).
    meta_file : str
        Path to CSV metadata (rows=samples, contains group_col).
    group_col : str
        Metadata column identifying groups (e.g. 'Strain', 'cell_type').
    mode : str
        'anova': one-way ANOVA across groups. 'fold_change': median per-gene log2FC b...
    exclude_groups : list[str]
        Groups in group_col to exclude before analysis.
    group_a : str
        Numerator group for fold_change mode.
    group_b : str
        Denominator group for fold_change mode.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "counts_file": counts_file,
            "meta_file": meta_file,
            "group_col": group_col,
            "mode": mode,
            "exclude_groups": exclude_groups,
            "group_a": group_a,
            "group_b": group_b,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "expression_anova_per_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["expression_anova_per_gene"]
