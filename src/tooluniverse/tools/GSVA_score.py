"""
GSVA_score

Gene Set Variation Analysis (Hänzelmann 2013): turn an expression matrix (genes x samples) into a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GSVA_score(
    expression: dict[str, Any],
    samples: Optional[list[str]] = None,
    gene_sets: Optional[dict[str, Any]] = None,
    gene_set: Optional[list[str]] = None,
    tau: Optional[float] = None,
    mx_diff: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Gene Set Variation Analysis (Hänzelmann 2013): turn an expression matrix (genes x samples) into a...

    Parameters
    ----------
    expression : dict[str, Any]
        {gene: [value_per_sample, ...]} — a genes x samples expression matrix on a co...
    samples : list[str]
        Sample names (same order as the per-gene value lists); defaults to sample_1..
    gene_sets : dict[str, Any]
        {set_name: [gene, ...]} collection to score. Alternative to gene_set.
    gene_set : list[str]
        A single gene set (list of gene symbols).
    tau : float
        Rank-weighting exponent in the random walk (default 1.0, the GSVA standard).
    mx_diff : bool
        True (default) = ES_pos+ES_neg difference score (signed, bimodal, GSVA defaul...
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
            "tau": tau,
            "mx_diff": mx_diff,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GSVA_score",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GSVA_score"]
