"""
RNAcentral_search

Search aggregated ncRNA records (miRNA, rRNA, lncRNA, etc.) across sources via RNAcentral. Use to...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RNAcentral_search(
    query: str,
    page_size: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search aggregated ncRNA records (miRNA, rRNA, lncRNA, etc.) across sources via RNAcentral. Use to...

    Parameters
    ----------
    query : str
        Keyword, accession, or sequence-based query (per RNAcentral API).
    page_size : int
        Number of records per page (1–100).
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
        for k, v in {"query": query, "page_size": page_size}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RNAcentral_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RNAcentral_search"]
