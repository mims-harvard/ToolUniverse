"""
ClinicalTrials_search_studies

Search ClinicalTrials.gov for clinical trial studies by condition, intervention, sponsor, or othe...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinicalTrials_search_studies(
    query_cond: Optional[str | Any] = None,
    query_intr: Optional[str | Any] = None,
    query_term: Optional[str | Any] = None,
    filter_status: Optional[str | Any] = None,
    filter_phase: Optional[str | Any] = None,
    filter_study_type: Optional[str | Any] = None,
    page_size: Optional[int] = 10,
    next_page_token: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search ClinicalTrials.gov for clinical trial studies by condition, intervention, sponsor, or othe...

    Parameters
    ----------
    query_cond : str | Any
        Disease or condition to search for (e.g., 'breast cancer', 'type 2 diabetes',...
    query_intr : str | Any
        Intervention or drug to search for (e.g., 'pembrolizumab', 'metformin', 'chem...
    query_term : str | Any
        Free-text search across all study fields. Use for general keyword search.
    filter_status : str | Any
        Filter by recruitment status. Options: 'RECRUITING', 'NOT_YET_RECRUITING', 'A...
    filter_phase : str | Any
        Filter by trial phase. Options: 'EARLY_PHASE1', 'PHASE1', 'PHASE2', 'PHASE3',...
    filter_study_type : str | Any
        Filter by study type: 'INTERVENTIONAL', 'OBSERVATIONAL', 'EXPANDED_ACCESS'.
    page_size : int
        Number of results per page (default 10, max 1000).
    next_page_token : str | Any
        Token for retrieving the next page of results (obtained from previous response).
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
            "name": "ClinicalTrials_search_studies",
            "arguments": {
                "query_cond": query_cond,
                "query_intr": query_intr,
                "query_term": query_term,
                "filter_status": filter_status,
                "filter_phase": filter_phase,
                "filter_study_type": filter_study_type,
                "page_size": page_size,
                "next_page_token": next_page_token,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinicalTrials_search_studies"]
