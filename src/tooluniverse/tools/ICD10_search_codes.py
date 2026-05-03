"""
ICD10_search_codes

Search ICD-10-CM (Clinical Modification) codes by disease name or code. ICD-10-CM is the US clini...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ICD10_search_codes(
    query: str,
    limit: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search ICD-10-CM (Clinical Modification) codes by disease name or code. ICD-10-CM is the US clini...

    Parameters
    ----------
    query : str
        Search query (disease name or partial ICD-10 code, e.g., 'diabetes', 'E11', '...
    limit : int
        Maximum number of results to return (default: 20, max: 100)
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
    _args = {k: v for k, v in {"query": query, "limit": limit}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ICD10_search_codes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ICD10_search_codes"]
