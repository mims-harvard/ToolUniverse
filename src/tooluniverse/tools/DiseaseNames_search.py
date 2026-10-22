"""
DiseaseNames_search

Search NLM disease names with official count+offset pagination. Returns canonical disease names w...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DiseaseNames_search(
    terms: str,
    max_results: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search NLM disease names with official count+offset pagination. Returns canonical disease names w...

    Parameters
    ----------
    terms : str
        Disease name or prefix to search, e.g. 'cystic fibrosis', 'lupus', 'sickle ce...
    max_results : int
        Page size (default 20, range 1-500).
    offset : int
        Zero-based first match. Continue with metadata.next_offset; offset + max_resu...
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
            "terms": terms,
            "max_results": max_results,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DiseaseNames_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DiseaseNames_search"]
