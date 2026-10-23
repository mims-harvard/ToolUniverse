"""
OpenFDA_search_drug_events

Search the FDA Adverse Event Reporting System (FAERS) database via openFDA for drug safety report...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenFDA_search_drug_events(
    search: Optional[str] = None,
    limit: Optional[int] = 1,
    count: Optional[str] = None,
    drug_name: Optional[str] = None,
    reaction: Optional[str] = None,
    adverse_event: Optional[str] = None,
    skip: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the FDA Adverse Event Reporting System (FAERS) database via openFDA for drug safety report...

    Parameters
    ----------
    search : str
        Lucene query for adverse event reports. Use AND/OR with spaces (not +AND+). A...
    limit : int
        Record mode: max 100. Count mode: max 1000 terms.
    count : str
        Field to count by for frequency analysis (e.g., 'patient.reaction.reactionmed...
    drug_name : str
        Drug name to search for adverse events (e.g., 'warfarin', 'metformin'). Brand...
    reaction : str
        MedDRA adverse reaction term (British spelling: 'haemorrhage' not 'hemorrhage...
    adverse_event : str
        Alias for reaction. MedDRA adverse reaction term (British spelling).
    skip : int
        Record mode only. Number of reports to skip; continue with metadata.next_skip...
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
            "search": search,
            "limit": limit,
            "count": count,
            "drug_name": drug_name,
            "reaction": reaction,
            "adverse_event": adverse_event,
            "skip": skip,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenFDA_search_drug_events",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenFDA_search_drug_events"]
