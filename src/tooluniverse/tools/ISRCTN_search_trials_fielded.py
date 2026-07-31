"""
ISRCTN_search_trials_fielded

Field-scoped (fielded) search of the ISRCTN clinical trial registry using its boolean query DSL. ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ISRCTN_search_trials_fielded(
    q: Optional[str] = None,
    query: Optional[str] = None,
    condition: Optional[str] = None,
    phase: Optional[str] = None,
    gender: Optional[str] = None,
    intervention: Optional[str] = None,
    sponsor: Optional[str] = None,
    funder: Optional[str] = None,
    country: Optional[str] = None,
    drug_name: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Field-scoped (fielded) search of the ISRCTN clinical trial registry using its boolean query DSL. ...

    Parameters
    ----------
    q : str
        Raw ISRCTN field-scoped boolean query, used verbatim. Examples: 'condition:di...
    query : str
        Alias for 'q'; a full field-scoped DSL string.
    condition : str
        Condition field helper (compiled to condition:VALUE), e.g. 'diabetes'.
    phase : str
        Phase field helper (compiled to phase:VALUE), e.g. 'Phase III'.
    gender : str
        Gender field helper (compiled to gender:VALUE), e.g. 'Female'.
    intervention : str
        Intervention field helper (compiled to intervention:VALUE).
    sponsor : str
        Sponsor field helper (compiled to sponsor:VALUE).
    funder : str
        Funder field helper (compiled to funder:VALUE).
    country : str
        Recruitment country field helper (compiled to recruitmentCountry:VALUE).
    drug_name : str
        Drug name field helper (compiled to drugName:VALUE).
    limit : int
        Max trials to return (default 10, max 100).
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
            "q": q,
            "query": query,
            "condition": condition,
            "phase": phase,
            "gender": gender,
            "intervention": intervention,
            "sponsor": sponsor,
            "funder": funder,
            "country": country,
            "drug_name": drug_name,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ISRCTN_search_trials_fielded",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ISRCTN_search_trials_fielded"]
