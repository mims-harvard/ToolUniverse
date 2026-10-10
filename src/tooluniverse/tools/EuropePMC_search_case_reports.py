"""
EuropePMC_search_case_reports

Find published clinical case reports about a disease, rare presentation, complication, injury or ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EuropePMC_search_case_reports(
    query: str,
    limit: Optional[int] = 5,
    published_after: Optional[str] = None,
    published_before: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find published clinical case reports about a disease, rare presentation, complication, injury or ...

    Parameters
    ----------
    query : str
        The condition, presentation or treatment in plain words (2-5 words work best)...
    limit : int
        Number of case reports to return (1-25, default 5).
    published_after : str
        Only case reports first published on or after this date: a year (2015) or YYY...
    published_before : str
        Only case reports first published on or before this date: a year (2023) or YY...
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
            "published_after": published_after,
            "published_before": published_before,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EuropePMC_search_case_reports",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EuropePMC_search_case_reports"]
