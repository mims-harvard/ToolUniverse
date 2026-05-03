"""
ARCHS4_get_gene_correlations

Get genes most co-expressed with a query gene from ARCHS4, based on Pearson correlation computed ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ARCHS4_get_gene_correlations(
    gene: str,
    count: Optional[int | Any] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get genes most co-expressed with a query gene from ARCHS4, based on Pearson correlation computed ...

    Parameters
    ----------
    gene : str
        Gene symbol (e.g., TP53, BRCA1, EGFR, MYC)
    count : int | Any
        Number of top correlated genes to return (default: 20, max: 200)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"gene": gene, "count": count}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ARCHS4_get_gene_correlations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ARCHS4_get_gene_correlations"]
