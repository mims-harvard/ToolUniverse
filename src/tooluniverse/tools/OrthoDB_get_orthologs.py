"""
OrthoDB_get_orthologs

Get orthologous genes from an OrthoDB group, optionally filtered by species. Returns gene IDs, or...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OrthoDB_get_orthologs(
    group_id: str,
    species: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get orthologous genes from an OrthoDB group, optionally filtered by species. Returns gene IDs, or...

    Parameters
    ----------
    group_id : str
        OrthoDB group ID. Format: 'numberATtaxid'. Get IDs from OrthoDB_search_groups.
    species : str | Any
        Comma-separated NCBI taxonomy IDs to filter. Examples: '9606' (human only), '...
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
        {
            "name": "OrthoDB_get_orthologs",
            "arguments": {"group_id": group_id, "species": species},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OrthoDB_get_orthologs"]
