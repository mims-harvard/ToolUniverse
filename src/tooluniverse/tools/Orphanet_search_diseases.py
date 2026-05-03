"""
Orphanet_search_diseases

Search Orphanet for rare diseases by keyword. Orphanet is the reference portal for rare diseases ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Orphanet_search_diseases(
    query: str,
    operation: Optional[str] = None,
    limit: Optional[int] = 20,
    lang: Optional[str] = "en",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search Orphanet for rare diseases by keyword. Orphanet is the reference portal for rare diseases ...

    Parameters
    ----------
    operation : str
        Operation type (fixed: search_diseases)
    query : str
        Search query - disease name or keyword (e.g., 'Marfan', 'muscular dystrophy')
    limit : int
        Maximum number of results to return (default: 20, max: 200). The API may retu...
    lang : str
        Language code (en, fr, de, es, it, pt, pl, nl). Default: en
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
        for k, v in {
            "operation": operation,
            "query": query,
            "limit": limit,
            "lang": lang,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Orphanet_search_diseases",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Orphanet_search_diseases"]
