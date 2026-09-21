"""
EWASCatalog_search_by_gene

Look up all published epigenome-wide association study (EWAS) results annotated to one gene from ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EWASCatalog_search_by_gene(
    gene_symbol: str,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Look up all published epigenome-wide association study (EWAS) results annotated to one gene from ...

    Parameters
    ----------
    gene_symbol : str
        HGNC gene symbol, e.g. 'AHRR', 'TP53'.
    limit : int
        Max associations to return, 1-200. Default 50.
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
        for k, v in {"gene_symbol": gene_symbol, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EWASCatalog_search_by_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EWASCatalog_search_by_gene"]
