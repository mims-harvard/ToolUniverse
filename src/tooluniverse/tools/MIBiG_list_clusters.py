"""
MIBiG_list_clusters

List biosynthetic gene clusters (BGCs) from the MIBiG repository. MIBiG (Minimum Information abou...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MIBiG_list_clusters(
    search_term: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List biosynthetic gene clusters (BGCs) from the MIBiG repository. MIBiG (Minimum Information abou...

    Parameters
    ----------
    search_term : str
        Optional text to filter results by product name or organism. The API returns ...
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
        {"name": "MIBiG_list_clusters", "arguments": {"search_term": search_term}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MIBiG_list_clusters"]
