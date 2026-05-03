"""
ArtIC_search_artworks

Search the Art Institute of Chicago's collection of over 100,000 artworks using its public API. R...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ArtIC_search_artworks(
    q: str,
    limit: Optional[int | Any] = None,
    fields: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Art Institute of Chicago's collection of over 100,000 artworks using its public API. R...

    Parameters
    ----------
    q : str
        Search query. Examples: 'monet water lilies', 'picasso cubism', 'ancient egyp...
    limit : int | Any
        Number of results (1-100). Default: 10
    fields : str | Any
        Comma-separated fields to return. Default: 'id,title,artist_display,date_disp...
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
        for k, v in {"q": q, "limit": limit, "fields": fields}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ArtIC_search_artworks",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ArtIC_search_artworks"]
