"""
SEC_EDGAR_search_filings

Search SEC EDGAR full-text search index for company filings by keyword. Returns filing metadata i...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SEC_EDGAR_search_filings(
    query: str,
    forms: Optional[str] = None,
    startdt: Optional[str] = None,
    enddt: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search SEC EDGAR full-text search index for company filings by keyword. Returns filing metadata i...

    Parameters
    ----------
    query : str
        Search query for SEC filings (e.g., 'Moderna 10-K', 'CRISPR Therapeutics')
    forms : str
        Comma-separated form types to filter (e.g., '10-K', '10-K,8-K', '10-Q,S-1'). ...
    startdt : str
        Start date filter in YYYY-MM-DD format (e.g., '2024-01-01')
    enddt : str
        End date filter in YYYY-MM-DD format (e.g., '2025-12-31')
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
    _args = {k: v for k, v in {
        "query": query,
                "forms": forms,
                "startdt": startdt,
                "enddt": enddt
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SEC_EDGAR_search_filings",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["SEC_EDGAR_search_filings"]
