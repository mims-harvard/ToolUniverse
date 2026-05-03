"""
geo_search_datasets

Search GEO datasets by query terms, organism, study type, or platform. Returns dataset IDs and ba...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def geo_search_datasets(
    query: Optional[str] = None,
    organism: Optional[str] = "",
    study_type: Optional[str] = "",
    platform: Optional[str] = "",
    limit: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search GEO datasets by query terms, organism, study type, or platform. Returns dataset IDs and ba...

    Parameters
    ----------
    query : str
        Search query terms (e.g., 'cancer', 'diabetes', 'microarray')
    organism : str
        Organism name (e.g., 'Homo sapiens', 'Mus musculus')
    study_type : str
        Type of study (e.g., 'Expression profiling by array', 'Expression profiling b...
    platform : str
        Platform used (e.g., 'GPL570', 'GPL96')
    limit : int
        Maximum number of results to return
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
            "query": query,
            "organism": organism,
            "study_type": study_type,
            "platform": platform,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "geo_search_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["geo_search_datasets"]
