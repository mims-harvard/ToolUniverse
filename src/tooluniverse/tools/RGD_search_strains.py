"""
RGD_search_strains

Search the Rat Genome Database (RGD) rat strain catalog by keyword and/or strain type. Results ar...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RGD_search_strains(
    query: Optional[str] = None,
    strain_type: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Rat Genome Database (RGD) rat strain catalog by keyword and/or strain type. Results ar...

    Parameters
    ----------
    query : str
        Keyword to match against strain symbol, name, genetics, and description (case...
    strain_type : str
        Filter by strain type, e.g. 'inbred', 'congenic', 'transgenic', 'recombinant_...
    limit : int
        Maximum number of strains to return (default 25, max 200).
    offset : int
        Zero-based matching-strain offset. Continue with metadata.next_offset while m...
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
            "strain_type": strain_type,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RGD_search_strains",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RGD_search_strains"]
