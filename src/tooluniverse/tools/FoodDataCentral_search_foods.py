"""
FoodDataCentral_search_foods

Search USDA FoodData Central for foods by keyword. Returns matching foods with nutrient data, bra...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FoodDataCentral_search_foods(
    query: str,
    page_size: Optional[int] = 25,
    page_number: Optional[int] = 1,
    data_type: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search USDA FoodData Central for foods by keyword. Returns matching foods with nutrient data, bra...

    Parameters
    ----------
    query : str
        Search keywords (e.g., 'cheddar cheese', 'banana', 'chicken breast'). Support...
    page_size : int
        Number of results per page (default 25, max 200).
    page_number : int
        Page number for pagination (starts at 1).
    data_type : str
        Filter by data type. Options: 'Foundation' (reference foods), 'Branded' (comm...
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
            "query": query,
            "page_size": page_size,
            "page_number": page_number,
            "data_type": data_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FoodDataCentral_search_foods",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FoodDataCentral_search_foods"]
