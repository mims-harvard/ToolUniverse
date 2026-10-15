"""
SCP_search_studies

Keyword search across the Broad Institute Single Cell Portal, which hosts 1000+ single-cell studi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SCP_search_studies(
    query: str,
    limit: Optional[int] = None,
    page: Optional[int] = None,
    description_chars: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Keyword search across the Broad Institute Single Cell Portal, which hosts 1000+ single-cell studi...

    Parameters
    ----------
    query : str
        Search terms, e.g. 'lung', 'glioblastoma', 'COVID-19', 'pancreatic islet'. Ca...
    limit : int
        Maximum studies to return (default 20, max 100).
    page : int
        1-based result page. Use with the total_pages value returned in metadata.
    description_chars : int
        Truncate each description to this many characters (default 500). Set 0 to omi...
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
    _args = {
        k: v
        for k, v in {
            "query": query,
            "limit": limit,
            "page": page,
            "description_chars": description_chars,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SCP_search_studies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SCP_search_studies"]
