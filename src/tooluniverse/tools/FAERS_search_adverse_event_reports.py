"""
FAERS_search_adverse_event_reports

Search and retrieve detailed adverse event reports from FAERS. Returns individual case reports wi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FAERS_search_adverse_event_reports(
    medicinalproduct: str,
    limit: Optional[int] = 10,
    skip: Optional[int] = 0,
    patientsex: Optional[str] = None,
    patientagegroup: Optional[str] = None,
    occurcountry: Optional[str] = None,
    serious: Optional[str] = None,
    seriousnessdeath: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search and retrieve detailed adverse event reports from FAERS. Returns individual case reports wi...

    Parameters
    ----------
    medicinalproduct : str
        Drug name (required).
    limit : int
        Maximum number of reports to return. Must be between 1 and 100.
    skip : int
        Number of reports to skip for pagination. Must be non-negative.
    patientsex : str
        Optional: Filter by patient sex. Omit this parameter if you don't want to fil...
    patientagegroup : str
        Optional: Filter by patient age group. Omit this parameter if you don't want ...
    occurcountry : str
        Optional: Filter by country where event occurred (ISO2 code, e.g., 'US', 'GB'...
    serious : str
        Optional: Filter by event seriousness. Omit this parameter if you don't want ...
    seriousnessdeath : str
        Optional: Pass 'Yes' to filter for reports where death was an outcome. Omit t...
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
    _args = {
        k: v
        for k, v in {
            "medicinalproduct": medicinalproduct,
            "limit": limit,
            "skip": skip,
            "patientsex": patientsex,
            "patientagegroup": patientagegroup,
            "occurcountry": occurcountry,
            "serious": serious,
            "seriousnessdeath": seriousnessdeath,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FAERS_search_adverse_event_reports",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FAERS_search_adverse_event_reports"]
