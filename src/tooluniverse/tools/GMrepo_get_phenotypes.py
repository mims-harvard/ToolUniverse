"""
GMrepo_get_phenotypes

List phenotypes and health conditions with gut microbiome data in the GMrepo database. Returns Me...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GMrepo_get_phenotypes(
    query: Optional[str] = "",
    limit: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    List phenotypes and health conditions with gut microbiome data in the GMrepo database. Returns Me...

    Parameters
    ----------
    query : str
        Optional keyword to filter phenotypes. Examples: 'diabetes', 'obesity', 'canc...
    limit : int
        Maximum number of results to return. Default: 20.
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
    _args = {k: v for k, v in {"query": query, "limit": limit}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "GMrepo_get_phenotypes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GMrepo_get_phenotypes"]
