"""
BVBRC_search_genomes

Search for pathogen genomes in BV-BRC by organism name or keyword. Returns a list of matching gen...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BVBRC_search_genomes(
    keyword: str,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for pathogen genomes in BV-BRC by organism name or keyword. Returns a list of matching gen...

    Parameters
    ----------
    keyword : str
        Search keyword - organism name, strain, or pathogen. Examples: 'Staphylococcu...
    limit : int | Any
        Maximum number of results to return. Default: 10. Max: 100.
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
        k: v for k, v in {"keyword": keyword, "limit": limit}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BVBRC_search_genomes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BVBRC_search_genomes"]
