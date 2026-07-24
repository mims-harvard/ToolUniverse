"""
CTIS_search_trials_filtered

Structured (filtered) search of the EU Clinical Trials Information System (CTIS) — the European c...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CTIS_search_trials_filtered(
    query: Optional[str] = None,
    medical_condition: Optional[str] = None,
    status: Optional[list[Any] | int | str] = None,
    trial_phase_code: Optional[list[str] | str] = None,
    age_group_code: Optional[list[str] | str] = None,
    gender_code: Optional[list[str] | str] = None,
    therapeutic_area: Optional[list[str] | str] = None,
    has_study_results: Optional[bool] = None,
    sponsor: Optional[str] = None,
    sponsor_type_code: Optional[list[str] | str] = None,
    country: Optional[list[str] | str] = None,
    msc: Optional[list[str] | str] = None,
    trial_region_code: Optional[list[str] | str] = None,
    sort_by: Optional[str] = None,
    limit: Optional[int] = None,
    page: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Structured (filtered) search of the EU Clinical Trials Information System (CTIS) — the European c...

    Parameters
    ----------
    query : str
        Optional free-text term applied as CTIS 'containAll' (e.g. 'cancer', 'pembrol...
    medical_condition : str
        Medical condition / indication filter, e.g. 'breast cancer', 'leukemia'.
    status : list[Any] | int | str
        Trial status code(s), e.g. [3] for ongoing. Accepts a single value or a list.
    trial_phase_code : list[str] | str
        Trial phase code(s) as strings, e.g. ['3'] for Phase III. Accepts a single va...
    age_group_code : list[str] | str
        Age group code(s) as strings, e.g. ['2']. Accepts a single value or a list.
    gender_code : list[str] | str
        Gender code(s) as strings. Accepts a single value or a list.
    therapeutic_area : list[str] | str
        Therapeutic area code(s). Accepts a single value or a list.
    has_study_results : bool
        If true, return only trials that have posted study results.
    sponsor : str
        Sponsor name filter, e.g. 'Pfizer'.
    sponsor_type_code : list[str] | str
        Sponsor type code(s). Accepts a single value or a list.
    country : list[str] | str
        Member State Concerned (MSC) country code(s). Accepts a single value or a lis...
    msc : list[str] | str
        Member State Concerned (MSC) code(s). Accepts a single value or a list.
    trial_region_code : list[str] | str
        Trial region code(s) (e.g. EU/EEA vs partly outside). Accepts a single value ...
    sort_by : str
        Optional CTIS sort key (e.g. by decision date).
    limit : int
        Results per page (default 10, max 100).
    page : int
        Page number (default 1).
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
            "medical_condition": medical_condition,
            "status": status,
            "trial_phase_code": trial_phase_code,
            "age_group_code": age_group_code,
            "gender_code": gender_code,
            "therapeutic_area": therapeutic_area,
            "has_study_results": has_study_results,
            "sponsor": sponsor,
            "sponsor_type_code": sponsor_type_code,
            "country": country,
            "msc": msc,
            "trial_region_code": trial_region_code,
            "sort_by": sort_by,
            "limit": limit,
            "page": page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CTIS_search_trials_filtered",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CTIS_search_trials_filtered"]
