"""
MaveDB_search_score_sets

Search MaveDB for variant effect score sets from Multiplexed Assays of Variant Effect (MAVE) expe...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MaveDB_search_score_sets(
    query: str,
    limit: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search MaveDB for variant effect score sets from Multiplexed Assays of Variant Effect (MAVE) expe...

    Parameters
    ----------
    query : str
        Search text - gene name (e.g., 'BRCA1', 'TP53'), protein name, or keyword. Se...
    limit : int
        Maximum number of results to return.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"query": query, "limit": limit}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "MaveDB_search_score_sets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MaveDB_search_score_sets"]
