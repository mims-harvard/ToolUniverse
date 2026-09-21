"""
AgingCohort_search

Search a curated registry of ~30 major longitudinal cohort studies relevant to aging research wor...
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
    Search a curated registry of ~30 major longitudinal cohort studies relevant to aging research wor...

    Parameters
    ----------
    query : str
        Keyword search across study names, descriptions, variable categories, and top...
    country : str
        Filter by country or region. Examples: 'USA', 'UK', 'China', 'Europe', 'Nethe...
    design : str
        Filter by study design. One of: 'longitudinal', 'cross-sectional', 'both'.
    min_sample_size : int
        Minimum sample size threshold. Only returns cohorts with sample_size >= this ...
    has_variable : str
        Filter for cohorts that include a specific variable category. Substring match...
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
