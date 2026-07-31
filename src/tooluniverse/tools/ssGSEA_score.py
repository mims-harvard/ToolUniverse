"""
ssGSEA_score

Single-sample GSEA (Barbie 2009): score each sample for each gene set from an expression matrix (...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ssGSEA_score(
    expression: dict[str, Any],
    samples: Optional[list[str]] = None,
    gene_sets: Optional[dict[str, Any]] = None,
    gene_set: Optional[list[str]] = None,
    alpha: Optional[float] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Single-sample GSEA (Barbie 2009): score each sample for each gene set from an expression matrix (...

    Parameters
    ----------
    expression : dict[str, Any]
        {gene: [value_per_sample, ...]} — a genes x samples expression matrix (e.g. l...
    samples : list[str]
        Sample names (same order as the per-gene value lists); defaults to sample_1..
    gene_sets : dict[str, Any]
        {set_name: [gene, ...]} collection to score. Alternative to gene_set.
    gene_set : list[str]
        A single gene set (list of gene symbols).
    alpha : float
        Rank-weighting exponent (default 0.25, the ssGSEA standard).
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "expression": expression,
            "samples": samples,
            "gene_sets": gene_sets,
            "gene_set": gene_set,
            "alpha": alpha,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ssGSEA_score",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ssGSEA_score"]
