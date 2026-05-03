"""
civic_search_assertions

Search for assertions in CIViC database. Assertions are higher-level clinical interpretations tha...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def civic_search_assertions(
    limit: Optional[int] = 20,
    therapy: Optional[str] = None,
    therapy_name: Optional[str] = None,
    disease: Optional[str] = None,
    disease_name: Optional[str] = None,
    variant_name: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for assertions in CIViC database. Assertions are higher-level clinical interpretations tha...

    Parameters
    ----------
    limit : int
        Maximum number of assertions to return (default: 20, recommended max: 100)
    therapy : str
        Filter by therapy/drug name (e.g., 'imatinib', 'ponatinib'). Alias: therapy_n...
    therapy_name : str
        Alias for therapy. Filter by therapy/drug name.
    disease : str
        Filter by disease name (e.g., 'leukemia', 'melanoma'). Alias: disease_name.
    disease_name : str
        Alias for disease. Filter by disease name.
    variant_name : str
        Filter by variant name (e.g., 'V600E', 'T315I').
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
            "limit": limit,
            "therapy": therapy,
            "therapy_name": therapy_name,
            "disease": disease,
            "disease_name": disease_name,
            "variant_name": variant_name,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "civic_search_assertions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["civic_search_assertions"]
