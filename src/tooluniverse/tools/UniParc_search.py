"""
UniParc_search

Search UniParc with official result cursor pagination plus independently reachable organism and g...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniParc_search(
    query: str,
    size: Optional[int] = None,
    cursor: Optional[str] = None,
    organism_offset: Optional[int] = 0,
    organism_limit: Optional[int] = 100,
    gene_name_offset: Optional[int] = 0,
    gene_name_limit: Optional[int] = 100,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search UniParc with official result cursor pagination plus independently reachable organism and g...

    Parameters
    ----------
    query : str
        Search query in Lucene syntax. Examples: 'gene:TP53 AND organism_id:9606', 'd...
    size : int
        Results per official cursor page (default 5, maximum 500). Invalid values ret...
    cursor : str
        Opaque cursor from metadata.next_cursor. Omit for the first page.
    organism_offset : int
        Zero-based offset into each result's organism list.
    organism_limit : int
        Maximum organisms returned per UniParc result.
    gene_name_offset : int
        Zero-based offset into each result's gene-name list.
    gene_name_limit : int
        Maximum gene names returned per UniParc result.
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
            "query": query,
            "size": size,
            "cursor": cursor,
            "organism_offset": organism_offset,
            "organism_limit": organism_limit,
            "gene_name_offset": gene_name_offset,
            "gene_name_limit": gene_name_limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UniParc_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniParc_search"]
