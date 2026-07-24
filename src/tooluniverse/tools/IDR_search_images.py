"""
IDR_search_images

Search the Image Data Resource (IDR) for individual images across ALL published studies at once b...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IDR_search_images(
    value: str,
    key: Optional[str] = None,
    operator: Optional[str] = None,
    case_sensitive: Optional[bool] = None,
    study: Optional[str] = None,
    resource: Optional[str] = None,
    max_results: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Image Data Resource (IDR) for individual images across ALL published studies at once b...

    Parameters
    ----------
    value : str
        The metadata value to search for, e.g. 'TP53', 'homo sapiens', 'HeLa', 'pacli...
    key : str
        The metadata attribute to match the value against, e.g. 'Gene Symbol', 'Organ...
    operator : str
        Match operator: 'equals' (default) or 'contains' for substring matching.
    case_sensitive : bool
        Whether the value match is case sensitive. Default false.
    study : str
        Optional study-name filter, e.g. 'idr0001-graml-sysgro/screenA', to restrict ...
    resource : str
        Resource type to search. Default 'image'. Other values: 'screen', 'project', ...
    max_results : int
        Optional client-side cap on the number of image rows returned (the API return...
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
            "value": value,
            "key": key,
            "operator": operator,
            "case_sensitive": case_sensitive,
            "study": study,
            "resource": resource,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IDR_search_images",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IDR_search_images"]
