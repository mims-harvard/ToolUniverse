"""
ProteomeXchange_search_datasets

Search ProteomeXchange proteomics datasets via the MassIVE PROXI interface. Returns dataset acces...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProteomeXchange_search_datasets(
    query: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search ProteomeXchange proteomics datasets via the MassIVE PROXI interface. Returns dataset acces...

    Parameters
    ----------
    query : str | Any
        Optional search filter (dataset accession or keyword). Examples: 'MSV00009181...
    limit : int | Any
        Maximum results to return (1-50, default 10).
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"query": query, "limit": limit}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ProteomeXchange_search_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ProteomeXchange_search_datasets"]
