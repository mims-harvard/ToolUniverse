"""
ZINC_search_compounds

NOT SUPPORTED by ZINC22 (CartBlanche22): free-text / compound-name search. ZINC has always been s...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ZINC_search_compounds(
    operation: Optional[str] = "search_compounds",
    query: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    NOT SUPPORTED by ZINC22 (CartBlanche22): free-text / compound-name search. ZINC has always been s...

    Parameters
    ----------
    operation : str
        Operation type
    query : str
        Drug name or keyword (NOTE: name search is not supported by CartBlanche22; th...
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
        for k, v in {"operation": operation, "query": query}.items()
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
