"""
MedGen_search_conditions

Search NCBI MedGen for genetic conditions, diseases, or syndromes by keyword. Use the zero-based ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MedGen_search_conditions(
    query: str,
    max_results: Optional[int] = 10,
    start: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search NCBI MedGen for genetic conditions, diseases, or syndromes by keyword. Use the zero-based ...

    Parameters
    ----------
    query : str
        Search term (e.g., 'cystic fibrosis', 'BRCA1', 'Marfan syndrome', 'autosomal ...
    max_results : int
        Maximum number of results (default 10, max 50).
    start : int
        Zero-based result offset. Continue with next_start while has_more is true.
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
        for k, v in {"query": query, "max_results": max_results, "start": start}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MedGen_search_conditions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MedGen_search_conditions"]
