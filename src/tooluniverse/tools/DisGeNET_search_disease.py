"""
DisGeNET_search_disease

Search DisGeNET for genes associated with a disease. Requires a UMLS CUI, NOT a free-text disease...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DisGeNET_search_disease(
    disease: str,
    operation: Optional[str] = "search_disease",
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search DisGeNET for genes associated with a disease. Requires a UMLS CUI, NOT a free-text disease...

    Parameters
    ----------
    operation : str
        Operation type (fixed: search_disease)
    disease : str
        UMLS CUI for the disease, e.g. 'C0006142' (breast cancer). Free-text disease ...
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"operation": operation, "disease": disease, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DisGeNET_search_disease",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DisGeNET_search_disease"]
