"""
OpenFDA_search_drug_events

Search the FDA Adverse Event Reporting System (FAERS) database via openFDA for drug safety report...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenFDA_search_drug_events(
    search: str,
    limit: Optional[int | Any] = None,
    count: Optional[str | Any] = None,
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
        Lucene query for adverse event reports (e.g., 'patient.drug.medicinalproduct:...
    limit : int | Any
        Maximum number of reports to return (default 1, max 100)
    count : str | Any
        Field to count by for frequency analysis (e.g., 'patient.reaction.reactionmed...
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
            "name": "OpenFDA_search_drug_events",
            "arguments": {"search": search, "limit": limit, "count": count},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenFDA_search_drug_events"]
