"""
SynBioHub_get_collections

List all public collections available on SynBioHub. Collections are curated sets of genetic parts...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SynBioHub_get_collections(
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all public collections available on SynBioHub. Collections are curated sets of genetic parts...

    Parameters
    ----------
    No parameters
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
        {"name": "SynBioHub_get_collections", "arguments": {}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SynBioHub_get_collections"]
