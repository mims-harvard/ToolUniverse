"""
nhanes_search_datasets

Search for NHANES datasets by keyword. Returns information about matching datasets including down...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def nhanes_search_datasets(
    search_term: Optional[str] = None,
    year: Optional[str] = None,
    limit: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for NHANES datasets by keyword. Returns information about matching datasets including down...

    Parameters
    ----------
    search_term : str
        Search term to find datasets (e.g., 'glucose', 'blood pressure', 'diabetes')
    year : str
        Optional NHANES cycle to filter (e.g., '2017-2018')
    limit : int
        Maximum number of results (default: 20)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"search_term": search_term, "year": year, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "nhanes_search_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["nhanes_search_datasets"]
