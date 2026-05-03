"""
arrayexpress_search_experiments

Search ArrayExpress experiments - the original functional genomics database from EMBL-EBI. Search...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def arrayexpress_search_experiments(
    keywords: Optional[str] = None,
    species: Optional[str] = None,
    array: Optional[str] = None,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search ArrayExpress experiments - the original functional genomics database from EMBL-EBI. Search...

    Parameters
    ----------
    keywords : str
        Search keywords (e.g., disease name, tissue type, experimental condition)
    species : str
        Species name (e.g., 'Homo sapiens', 'Mus musculus')
    array : str
        Array platform name
    limit : int
        Maximum number of results (default: 10, max: 100)
    offset : int
        Offset for pagination (default: 0)
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
            "keywords": keywords,
            "species": species,
            "array": array,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "arrayexpress_search_experiments",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["arrayexpress_search_experiments"]
