"""
proteins_api_search

Search proteins in Proteins API by gene name, protein name, or accession. Defaults to human prote...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def proteins_api_search(
    query: Optional[str] = None,
    size: Optional[int] = 25,
    offset: Optional[int] = 0,
    format: Optional[str] = "json",
    gene_symbol: Optional[str] = None,
    gene: Optional[str] = None,
    reviewed: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search proteins in Proteins API by gene name, protein name, or accession. Defaults to human prote...

    Parameters
    ----------
    query : str
        Search query. Can be: gene name (e.g., 'BRCA1', 'TP53'), protein name (e.g., ...
    size : int
        Maximum number of results to return (default: 25, max: 100)
    offset : int
        Offset for pagination (default: 0)
    format : str
        Response format. JSON is recommended for most use cases.
    gene_symbol : str
        Alias for query. Gene symbol to search (e.g., TP53, BRCA1).
    gene : str
        Alias for query. Gene name to search.
    reviewed : bool
        If true, return only reviewed Swiss-Prot entries. If false or omitted, includ...
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
            "query": query,
            "size": size,
            "offset": offset,
            "format": format,
            "gene_symbol": gene_symbol,
            "gene": gene,
            "reviewed": reviewed,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "proteins_api_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["proteins_api_search"]
