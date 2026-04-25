"""
OpenFDA_search_drug_ndc

Search the FDA National Drug Code (NDC) Directory via openFDA. The NDC directory identifies drugs...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenFDA_search_drug_ndc(
    search: str,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the FDA National Drug Code (NDC) Directory via openFDA. The NDC directory identifies drugs...

    Parameters
    ----------
    search : str
        Lucene query for NDC products (e.g., 'brand_name:lipitor', 'generic_name:ator...
    limit : int | Any
        Maximum number of results (default 5, max 100)
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
        "search": search,
                "limit": limit
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenFDA_search_drug_ndc",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["OpenFDA_search_drug_ndc"]
