"""
FAERS_search_serious_reports_by_drug

Search and retrieve detailed reports of serious adverse events for a specific drug. Returns indiv...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FAERS_search_serious_reports_by_drug(
    medicinalproduct: str,
    seriousnessdeath: Optional[str] = None,
    seriousnesshospitalization: Optional[str] = None,
    seriousnesslifethreatening: Optional[str] = None,
    seriousnessdisabling: Optional[str] = None,
    limit: Optional[int] = 10,
    skip: Optional[int] = 0,
    patientsex: Optional[str] = None,
    patientagegroup: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search and retrieve detailed reports of serious adverse events for a specific drug. Returns indiv...

    Parameters
    ----------
    medicinalproduct : str
        Drug name (required).
    seriousnessdeath : str
        Optional: Filter for reports where death was reported. Set to 'Yes' to includ...
    seriousnesshospitalization : str
        Optional: Filter for reports where hospitalization was required. Set to 'Yes'...
    seriousnesslifethreatening : str
        Optional: Filter for reports where the event was life-threatening. Set to 'Ye...
    seriousnessdisabling : str
        Optional: Filter for reports where the event was disabling. Set to 'Yes' to i...
    limit : int
        Maximum number of reports to return. Must be between 1 and 100.
    skip : int
        Number of reports to skip for pagination. Must be non-negative.
    patientsex : str
        Optional: Filter by patient sex. Omit this parameter if you don't want to fil...
    patientagegroup : str
        Optional: Filter by patient age group. Omit this parameter if you don't want ...
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
            "seriousnessdeath": seriousnessdeath,
            "seriousnesshospitalization": seriousnesshospitalization,
            "seriousnesslifethreatening": seriousnesslifethreatening,
            "seriousnessdisabling": seriousnessdisabling,
            "limit": limit,
            "skip": skip,
            "patientsex": patientsex,
            "patientagegroup": patientagegroup,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FAERS_search_serious_reports_by_drug",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FAERS_search_serious_reports_by_drug"]
