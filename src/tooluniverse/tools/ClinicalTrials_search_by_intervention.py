"""
ClinicalTrials_search_by_intervention

Search ClinicalTrials.gov for all clinical trials testing a specific drug, biologic, device, or o...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinicalTrials_search_by_intervention(
    intervention: str,
    condition: Optional[str] = None,
    status: Optional[str] = None,
    filter_status: Optional[str] = None,
    filter_phase: Optional[str] = None,
    page_size: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search ClinicalTrials.gov for all clinical trials testing a specific drug, biologic, device, or o...

    Parameters
    ----------
    intervention : str
        Drug, biologic, device, or intervention name (e.g., 'nivolumab', 'CRISPR', 'C...
    condition : str
        Disease or condition to filter trials (e.g., 'HER2 breast cancer', 'NSCLC KRA...
    status : str
        Recruitment status filter: 'RECRUITING', 'COMPLETED', 'ACTIVE_NOT_RECRUITING'...
    filter_status : str
        Filter by recruitment status: 'RECRUITING', 'COMPLETED', 'ACTIVE_NOT_RECRUITI...
    filter_phase : str
        Filter by trial phase: 'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4'. Comma-separate...
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "intervention": intervention,
            "condition": condition,
            "status": status,
            "filter_status": filter_status,
            "filter_phase": filter_phase,
            "page_size": page_size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ClinicalTrials_search_by_intervention",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinicalTrials_search_by_intervention"]
