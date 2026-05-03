"""
Harmonizome_get_gene

Get comprehensive gene information from Harmonizome (Ma'ayan Lab), which integrates data from 100...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Harmonizome_get_gene(
    gene_symbol: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get comprehensive gene information from Harmonizome (Ma'ayan Lab), which integrates data from 100...

    Parameters
    ----------
    gene_symbol : str
        Official gene symbol (case-insensitive). Examples: 'TP53', 'BRCA1', 'EGFR', '...
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
    _args = {k: v for k, v in {"gene_symbol": gene_symbol}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Harmonizome_get_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Harmonizome_get_gene"]
