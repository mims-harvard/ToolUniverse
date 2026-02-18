"""
CxGDisc_list_collections

List curated single-cell RNA-seq collections from CZI CellxGene Discovery. Each collection is a p...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CxGDisc_list_collections(
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List curated single-cell RNA-seq collections from CZI CellxGene Discovery. Each collection is a p...

    Parameters
    ----------
    limit : int
        Maximum number of collections to return (1-100). Default: 20.
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

    return get_shared_client().run_one_function(
        {"name": "CxGDisc_list_collections", "arguments": {"limit": limit}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CxGDisc_list_collections"]
