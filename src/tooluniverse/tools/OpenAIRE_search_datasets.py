"""
OpenAIRE_search_datasets

Search OpenAIRE for research datasets from the European open science ecosystem. Covers datasets f...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenAIRE_search_datasets(
    keywords: str,
    funder: Optional[str] = None,
    country: Optional[str] = None,
    size: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search OpenAIRE for research datasets from the European open science ecosystem. Covers datasets f...

    Parameters
    ----------
    keywords : str
        Search keywords for dataset discovery. Searches across titles, descriptions, ...
    funder : str
        Optional funder short name to filter datasets. Examples: 'EC' (European Commi...
    country : str
        Optional ISO 3166-1 alpha-2 country code to filter by. Examples: 'DE' (German...
    size : int
        Number of results to return. Default 10, maximum 100.
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
            "keywords": keywords,
            "funder": funder,
            "country": country,
            "size": size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenAIRE_search_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenAIRE_search_datasets"]
