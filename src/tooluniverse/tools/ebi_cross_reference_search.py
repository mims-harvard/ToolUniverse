"""
ebi_cross_reference_search

Search for cross-references between EBI domains. Find entries in one domain that reference entrie...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ebi_cross_reference_search(
    domain: str,
    query: str,
    size: Optional[int] = 10,
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search for cross-references between EBI domains. Find entries in one domain that reference entrie...

    Parameters
    ----------
    domain : str
        Source EBI domain to search
    query : str
        Search query. Can include cross-reference filters like 'xref_uniprot:P04637'
    size : int
        Number of results to return
    format : str

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
            "domain": domain,
            "query": query,
            "size": size,
            "format": format,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ebi_cross_reference_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ebi_cross_reference_search"]
