"""
NHANES_download_and_parse

Download and parse NHANES XPT data files from CDC into structured JSON (DataFrame-ready).
"""

from typing import Any, Optional, Callable


def NHANES_download_and_parse(
    component: str,
    cycle: str,
    dataset_name: Optional[str] = None,
    variables: Optional[list[str]] = None,
    age_min: Optional[float] = None,
    age_max: Optional[float] = None,
    max_rows: int = 5000,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Download and parse NHANES XPT data files from CDC into structured JSON.

    Parameters
    ----------
    component : str
        NHANES component category (Demographics, Dietary, DietaryDay2,
        Examination, Laboratory, Questionnaire, BodyMeasures)
    cycle : str
        NHANES survey cycle (e.g., '2017-2018', '2015-2016')
    dataset_name : str, optional
        Exact dataset filename prefix. Required for Laboratory.
    variables : list[str], optional
        Variable names to select. SEQN always included.
    age_min : float, optional
        Minimum age filter (inclusive, by RIDAGEYR)
    age_max : float, optional
        Maximum age filter (inclusive, by RIDAGEYR)
    max_rows : int, default 5000
        Maximum data rows to return
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
    from ._shared_client import get_shared_client

    _args: dict[str, Any] = {"component": component, "cycle": cycle}
    if dataset_name is not None:
        _args["dataset_name"] = dataset_name
    if variables is not None:
        _args["variables"] = variables
    if age_min is not None:
        _args["age_min"] = age_min
    if age_max is not None:
        _args["age_max"] = age_max
    if max_rows != 5000:
        _args["max_rows"] = max_rows

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
