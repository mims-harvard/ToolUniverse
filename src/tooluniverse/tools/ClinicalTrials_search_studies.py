"""
ClinicalTrials_search_studies

Search ClinicalTrials.gov for clinical trial studies by condition, intervention, sponsor, or othe...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinicalTrials_search_studies(
    operation: Optional[str] = "search",
    query_cond: Optional[str] = None,
    query_intr: Optional[str] = None,
    query_term: Optional[str] = None,
    filter_status: Optional[str] = None,
    filter_phase: Optional[str] = None,
    filter_study_type: Optional[str] = None,
    page_size: Optional[int] = 10,
    next_page_token: Optional[str] = None,
    query: Optional[str] = None,
    condition: Optional[str] = None,
    status: Optional[str] = None,
    max_results: Optional[int] = None,
    intervention: Optional[str] = None,
    sponsor: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search ClinicalTrials.gov for clinical trial studies by condition, intervention, sponsor, or othe...

    Parameters
    ----------
    operation : str
        Operation (optional; defaults to 'search' for this tool).
    query_cond : str
        Disease or condition to search for (e.g., 'breast cancer', 'type 2 diabetes',...
    query_intr : str
        Intervention or drug to search for (e.g., 'pembrolizumab', 'metformin', 'chem...
    query_term : str
        Free-text search across all study fields. Use for general keyword search.
    filter_status : str
        Filter by recruitment status. Options: 'RECRUITING', 'NOT_YET_RECRUITING', 'A...
    filter_phase : str
        Filter by trial phase. Options: 'EARLY_PHASE1', 'PHASE1', 'PHASE2', 'PHASE3',...
    filter_study_type : str
        Filter by study type: 'INTERVENTIONAL', 'OBSERVATIONAL', 'EXPANDED_ACCESS'.
    page_size : int
        Number of results per page (default 10, max 1000).
    next_page_token : str
        Token for retrieving the next page of results (obtained from previous response).
    query : str
        General keyword search across all fields. Alias for query_term. E.g., "FLT3 A...
    condition : str
        Disease or condition to search for. Alias for query_cond. E.g., "acute myeloi...
    status : str
        Recruitment status filter. Alias for filter_status. E.g., "RECRUITING", "COMP...
    max_results : int
        Maximum number of results to return. Alias for page_size.
    intervention : str
        Intervention or drug to search for. Alias for query_intr. E.g., "pembrolizuma...
    sponsor : str
        Lead sponsor or collaborator name to search for. E.g., "National Cancer Insti...
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
            "operation": operation,
            "query_cond": query_cond,
            "query_intr": query_intr,
            "query_term": query_term,
            "filter_status": filter_status,
            "filter_phase": filter_phase,
            "filter_study_type": filter_study_type,
            "page_size": page_size,
            "next_page_token": next_page_token,
            "query": query,
            "condition": condition,
            "status": status,
            "max_results": max_results,
            "intervention": intervention,
            "sponsor": sponsor,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ClinicalTrials_search_studies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinicalTrials_search_studies"]
