"""
OpenFoodFacts_search_products

Search for food products in the Open Food Facts database by name or brand. Returns product detail...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenFoodFacts_search_products(
    search_terms: str,
    page_size: Optional[int | Any] = None,
    page: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for food products in the Open Food Facts database by name or brand. Returns product detail...

    Parameters
    ----------
    search_terms : str
        Food product name or brand to search for. Examples: 'nutella', 'coca cola', '...
    page_size : int | Any
        Number of results per page (1-100). Default: 10
    page : int | Any
        Page number for pagination. Default: 1
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
    _args = {k: v for k, v in {
        "search_terms": search_terms,
                "page_size": page_size,
                "page": page
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenFoodFacts_search_products",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["OpenFoodFacts_search_products"]
