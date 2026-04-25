"""
AgingCohort_search

Search a curated registry of ~30 major longitudinal cohort studies relevant to aging research worldwide.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AgingCohort_search(
    query: str,
    country: Optional[str] = None,
    design: Optional[str] = None,
    min_sample_size: Optional[int] = None,
    has_variable: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search a curated registry of ~30 major longitudinal cohort studies
    relevant to aging research worldwide.

    Parameters
    ----------
    query : str
        Keyword search across study names, descriptions, variable categories,
        and topics. Examples: 'iron intake longitudinal', 'grip strength aging
        Europe', 'biomarkers elderly China'.
    country : str, optional
        Filter by country or region. Case-insensitive substring match.
    design : str, optional
        Filter by study design: 'longitudinal', 'cross-sectional', or 'both'.
    min_sample_size : int, optional
        Minimum sample size threshold.
    has_variable : str, optional
        Filter for cohorts that include a specific variable category.
        Examples: 'iron', 'grip_strength', 'walking_speed', 'nutrition'.
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
    _args = {
        k: v
        for k, v in {
            "query": query,
            "country": country,
            "design": design,
            "min_sample_size": min_sample_size,
            "has_variable": has_variable,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "AgingCohort_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AgingCohort_search"]
