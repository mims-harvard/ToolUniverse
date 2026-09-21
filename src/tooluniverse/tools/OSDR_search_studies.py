"""
OSDR_search_studies

Full-text search NASA's Open Science Data Repository (OSDR, formerly GeneLab): ~1,000 space biolo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OSDR_search_studies(
    query: str,
    organism: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Full-text search NASA's Open Science Data Repository (OSDR, formerly GeneLab): ~1,000 space biolo...

    Parameters
    ----------
    query : str
        Free-text search, e.g. 'microgravity bone loss', 'radiation Drosophila'.
    organism : str
        Optional organism filter, e.g. 'Mus musculus', 'Homo sapiens', 'Arabidopsis t...
    limit : int
        Max studies to return, 1-100. Default 25.
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
        for k, v in {"query": query, "organism": organism, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OSDR_search_studies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OSDR_search_studies"]
