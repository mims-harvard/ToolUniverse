"""
ClinicalTrials_search_by_sponsor

Search ClinicalTrials.gov for clinical trials by sponsor or lead organization. Returns trials fun...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinicalTrials_search_by_sponsor(
    sponsor: str,
    query_cond: Optional[str | Any] = None,
    filter_status: Optional[str | Any] = None,
    filter_phase: Optional[str | Any] = None,
    page_size: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search ClinicalTrials.gov for clinical trials by sponsor or lead organization. Returns trials fun...

    Parameters
    ----------
    sponsor : str
        Sponsor or lead organization name (e.g., 'Pfizer', 'National Cancer Institute...
    query_cond : str | Any
        Optional disease/condition filter (e.g., 'cancer', 'cardiovascular disease', ...
    filter_status : str | Any
        Filter by status: 'RECRUITING', 'COMPLETED', 'ACTIVE_NOT_RECRUITING'. Comma-s...
    filter_phase : str | Any
        Filter by phase: 'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4'. Comma-separate multi...
    page_size : int
        Number of results per page (default 10, max 1000).
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

    return get_shared_client().run_one_function(
        {
            "name": "ClinicalTrials_search_by_sponsor",
            "arguments": {
                "sponsor": sponsor,
                "query_cond": query_cond,
                "filter_status": filter_status,
                "filter_phase": filter_phase,
                "page_size": page_size,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinicalTrials_search_by_sponsor"]
