"""
ZINC_search_compounds

Search the ZINC database for commercially available compounds by name or keyword. Returns ZINC ID...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ZINC_search_compounds(
    operation: str,
    query: str,
    count: Optional[int] = 10,
    purchasability: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search the ZINC database for commercially available compounds by name or keyword. Returns ZINC ID...

    Parameters
    ----------
    operation : str
        Operation type
    query : str
        Search query: drug name (aspirin, ibuprofen, metformin), keyword, or partial ...
    count : int
        Maximum number of results to return (default: 10, max: 100)
    purchasability : str | Any
        Filter by purchasability tier. in-stock = ready to ship, for-sale = from vend...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "query": query,
            "count": count,
            "purchasability": purchasability,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ZINC_search_compounds",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ZINC_search_compounds"]
