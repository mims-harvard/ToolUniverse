"""
metabolights_search_studies

List MetaboLights study IDs. NOTE: The MetaboLights API does not support keyword filtering — the ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def metabolights_search_studies(
    query: str,
    size: Optional[int] = 20,
    page: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    List MetaboLights study IDs. NOTE: The MetaboLights API does not support keyword filtering — the ...

    Parameters
    ----------
    query : str
        Search query string (e.g., organism name, disease, metabolite name)
    size : int
        Number of results per page (default: 20)
    page : int
        Page number (default: 0)
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
        for k, v in {"query": query, "size": size, "page": page}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "metabolights_search_studies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["metabolights_search_studies"]
