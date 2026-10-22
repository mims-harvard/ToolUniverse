"""
NHANES_download_and_parse

Download and parse NHANES XPT data files from CDC into structured JSON (DataFrame-ready). Bridges...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NHANES_download_and_parse(
    component: str,
    cycle: str,
    dataset_name: Optional[str] = None,
    variables: Optional[list[str]] = None,
    age_min: Optional[float] = None,
    age_max: Optional[float] = None,
    max_rows: Optional[int] = 5000,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Download and parse NHANES XPT data files from CDC into structured JSON (DataFrame-ready). Bridges...

    Parameters
    ----------
    component : str
        NHANES component category. 'Dietary' = Day 1 intake totals (DR1TOT), 'Dietary...
    cycle : str
        NHANES survey cycle (e.g., '2017-2018', '2015-2016', '2013-2014', '2011-2012')
    dataset_name : str
        Exact NHANES dataset filename prefix (without cycle suffix). Required for Lab...
    variables : list[str]
        List of variable names to select (e.g., ['SEQN', 'DR1TIRON', 'DR1TKCAL']). SE...
    age_min : float
        Minimum age filter (inclusive). Filters by RIDAGEYR from Demographics. Auto-m...
    age_max : float
        Maximum age filter (inclusive). Filters by RIDAGEYR from Demographics.
    max_rows : int
        Maximum number of data rows to return (default: 5000). Set lower for faster r...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "component": component,
            "cycle": cycle,
            "dataset_name": dataset_name,
            "variables": variables,
            "age_min": age_min,
            "age_max": age_max,
            "max_rows": max_rows,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NHANES_download_and_parse",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NHANES_download_and_parse"]
