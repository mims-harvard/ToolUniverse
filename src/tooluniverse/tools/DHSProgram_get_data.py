"""
DHSProgram_get_data

Retrieve DHS Program survey results for one indicator, optionally filtered by country (ISO2-like ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DHSProgram_get_data(
    indicator_id: str,
    country_code: Optional[str] = None,
    survey_year_start: Optional[int] = None,
    survey_year_end: Optional[int] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve DHS Program survey results for one indicator, optionally filtered by country (ISO2-like ...

    Parameters
    ----------
    indicator_id : str
        DHS indicator id, e.g. 'FE_FRTR_W_TFR'.
    country_code : str
        Optional DHS country code, e.g. 'EG' (Egypt), 'KE' (Kenya).
    survey_year_start : int
        Optional earliest survey year to include.
    survey_year_end : int
        Optional latest survey year to include.
    limit : int
        Max records to return, 1-100. Default 25.
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
            "indicator_id": indicator_id,
            "country_code": country_code,
            "survey_year_start": survey_year_start,
            "survey_year_end": survey_year_end,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DHSProgram_get_data",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DHSProgram_get_data"]
