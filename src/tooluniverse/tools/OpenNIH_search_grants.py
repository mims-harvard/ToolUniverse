"""
OpenNIH_search_grants

Search NIH project-year rows. WARNING: total_funding is a row sum, and repeated full project numb...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenNIH_search_grants(
    query: Optional[str] = None,
    text_search: Optional[str] = None,
    project_num: Optional[str] = None,
    fiscal_year_start: Optional[int] = None,
    fiscal_year_end: Optional[int] = None,
    activity_code: Optional[str] = None,
    ic: Optional[str] = None,
    institution: Optional[str] = None,
    pi_name: Optional[str] = None,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search NIH project-year rows. WARNING: total_funding is a row sum, and repeated full project numb...

    Parameters
    ----------
    query : str
        Natural-language topic or combined search string.
    text_search : str
        Text to match in grant fields.
    project_num : str
        Full NIH project number.
    fiscal_year_start : int

    fiscal_year_end : int

    activity_code : str
        NIH activity code such as R01 or K23.
    ic : str
        NIH Institute/Center abbreviation, code, or name. Prefer an exact abbreviatio...
    institution : str
        Case-insensitive substring over raw organization names. This can match multip...
    pi_name : str

    limit : int

    offset : int
        Zero-based row offset, capped at 100000. With limit=50 the largest fully retr...
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
            "text_search": text_search,
            "project_num": project_num,
            "fiscal_year_start": fiscal_year_start,
            "fiscal_year_end": fiscal_year_end,
            "activity_code": activity_code,
            "ic": ic,
            "institution": institution,
            "pi_name": pi_name,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenNIH_search_grants",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenNIH_search_grants"]
