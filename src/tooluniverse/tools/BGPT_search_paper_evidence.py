"""
BGPT_search_paper_evidence

Search scientific papers with BGPT and return structured, full-text-derived study evidence for cr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BGPT_search_paper_evidence(
    query: str,
    num_results: Optional[int] = 10,
    days_back: Optional[int] = None,
    api_key: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search scientific papers with BGPT and return structured, full-text-derived study evidence for cr...

    Parameters
    ----------
    query : str
        Natural-language scientific search query, e.g. 'GLP-1 alcohol craving' or 'se...
    num_results : int
        Number of paper results to return (1-100, default 10).
    days_back : int
        Optional. Restrict results to papers published within the last N days.
    api_key : str
        Optional paid-tier API key, used after the free result allowance is exhausted...
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
            "num_results": num_results,
            "days_back": days_back,
            "api_key": api_key,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BGPT_search_paper_evidence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BGPT_search_paper_evidence"]
