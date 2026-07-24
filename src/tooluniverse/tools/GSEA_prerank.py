"""
GSEA_prerank

Pre-ranked Gene Set Enrichment Analysis (Subramanian 2005) on a ranked gene list (e.g. genes rank...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GSEA_prerank(
    ranked_genes: Optional[dict[str, Any]] = None,
    genes: Optional[list[str]] = None,
    scores: Optional[list[Any]] = None,
    gene_sets: Optional[dict[str, Any]] = None,
    gene_set: Optional[list[str]] = None,
    weight: Optional[float] = None,
    n_permutations: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Pre-ranked Gene Set Enrichment Analysis (Subramanian 2005) on a ranked gene list (e.g. genes rank...

    Parameters
    ----------
    ranked_genes : dict[str, Any]
        {gene: score} mapping (score = DE statistic / fold change). Genes are ranked ...
    genes : list[str]
        Gene identifiers (use with `scores`, same order).
    scores : list[Any]
        Per-gene ranking metric (same order as `genes`).
    gene_sets : dict[str, Any]
        {set_name: [gene, ...]} collection to test. Alternative to gene_set.
    gene_set : list[str]
        A single gene set (list of gene symbols).
    weight : float
        Score weighting exponent for the running sum (default 1.0; classic GSEA).
    n_permutations : int
        Gene-label permutations for the p-value (default 1000).
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
            "ranked_genes": ranked_genes,
            "genes": genes,
            "scores": scores,
            "gene_sets": gene_sets,
            "gene_set": gene_set,
            "weight": weight,
            "n_permutations": n_permutations,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GSEA_prerank",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GSEA_prerank"]
