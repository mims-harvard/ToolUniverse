"""
DataONE_search_datasets

Search DataONE (Data Observation Network for Earth) for open scientific datasets. DataONE indexes...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DataONE_search_datasets(
    q: str,
    fl: Optional[str | Any] = None,
    rows: Optional[int | Any] = None,
    start: Optional[int | Any] = None,
    sort: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search DataONE (Data Observation Network for Earth) for open scientific datasets. DataONE indexes...

    Parameters
    ----------
    q : str
        Search query using Solr query syntax. Examples: 'climate change', 'author:Smi...
    fl : str | Any
        Comma-separated list of fields to return. Default: 'id,title,author,dateUploa...
    rows : int | Any
        Number of results to return (default 10, max 1000)
    start : int | Any
        Offset for pagination (default 0)
    sort : str | Any
        Sort order. Examples: 'dateUploaded desc', 'score desc', 'title asc'
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
    _args = {k: v for k, v in {
        "q": q,
                "fl": fl,
                "rows": rows,
                "start": start,
                "sort": sort
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "DataONE_search_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["DataONE_search_datasets"]
