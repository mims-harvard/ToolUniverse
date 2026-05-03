"""
CLUE_get_gene_expression

Get gene information from L1000 Connectivity Map landmark and inferred gene set. Returns gene met...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CLUE_get_gene_expression(
    operation: str,
    gene_symbol: Optional[str] = None,
    limit: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get gene information from L1000 Connectivity Map landmark and inferred gene set. Returns gene met...

    Parameters
    ----------
    operation : str
        Operation type
    gene_symbol : str
        Gene symbol to search (e.g., 'TP53', 'BRCA1')
    limit : int
        Maximum number of results
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
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "gene_symbol": gene_symbol,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CLUE_get_gene_expression",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CLUE_get_gene_expression"]
