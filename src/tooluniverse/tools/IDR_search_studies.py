"""
IDR_search_studies

Find which IDR studies (screens and projects) contain images matching a metadata key/value, searc...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IDR_search_studies(
    value: str,
    key: Optional[str] = None,
    operator: Optional[str] = None,
    case_sensitive: Optional[bool] = None,
    study: Optional[str] = None,
    resource: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find which IDR studies (screens and projects) contain images matching a metadata key/value, searc...

    Parameters
    ----------
    value : str
        The metadata value to search for, e.g. 'TP53', 'spindly', 'homo sapiens'. Req...
    key : str
        The metadata attribute to match against, e.g. 'Gene Symbol', 'Phenotype', 'Or...
    operator : str
        Match operator: 'equals' (default) or 'contains'.
    case_sensitive : bool
        Whether the value match is case sensitive. Default false.
    study : str
        Optional study-name filter to restrict to one study.
    resource : str
        Resource type to search. Default 'image'.
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
            "value": value,
            "key": key,
            "operator": operator,
            "case_sensitive": case_sensitive,
            "study": study,
            "resource": resource,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IDR_search_studies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IDR_search_studies"]
