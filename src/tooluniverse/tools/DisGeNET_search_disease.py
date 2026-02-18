"""
DisGeNET_search_disease

Search DisGeNET for genes associated with a disease. Query by disease name or UMLS CUI (e.g., C00...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DisGeNET_search_disease(
    operation: str,
    disease: str,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search DisGeNET for genes associated with a disease. Query by disease name or UMLS CUI (e.g., C00...

    Parameters
    ----------
    operation : str
        Operation type (fixed: search_disease)
    disease : str
        Disease name or UMLS CUI (e.g., C0006142, breast cancer)
    limit : int
        Maximum associations to return (default: 10)
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

    return get_shared_client().run_one_function(
        {
            "name": "DisGeNET_search_disease",
            "arguments": {"operation": operation, "disease": disease, "limit": limit},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DisGeNET_search_disease"]
