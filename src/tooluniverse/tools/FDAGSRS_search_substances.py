"""
FDAGSRS_search_substances

Search FDA GSRS (Global Substance Registration System) for substances by name, UNII, InChIKey, or formula.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDAGSRS_search_substances(
    query: str,
    substance_class: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search FDA GSRS for substances by name, UNII code, InChIKey, or formula.

    Parameters
    ----------
    query : str
        Search query: drug/chemical name, UNII code, InChIKey, or molecular formula.
    substance_class : str, optional
        Filter by substance class (e.g., 'chemical', 'protein', 'mixture').
    limit : int, optional
        Maximum number of results to return (1-50, default 10).
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
    _args = {
        k: v
        for k, v in {
            "query": query,
            "substance_class": substance_class,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FDAGSRS_search_substances",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDAGSRS_search_substances"]
