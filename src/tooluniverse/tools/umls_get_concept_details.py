"""
umls_get_concept_details

Get detailed information about a UMLS concept by its CUI (Concept Unique Identifier). Returns con...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def umls_get_concept_details(
    cui: str,
    pageNumber: Optional[int] = 1,
    pageSize: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a UMLS concept by its CUI (Concept Unique Identifier). Returns con...

    Parameters
    ----------
    cui : str
        UMLS Concept Unique Identifier (CUI, e.g., 'C0004096')
    pageNumber : int
        Page number for pagination (default: 1)
    pageSize : int
        Number of results per page (default: 25)
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
        for k, v in {"cui": cui, "pageNumber": pageNumber, "pageSize": pageSize}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "umls_get_concept_details",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["umls_get_concept_details"]
