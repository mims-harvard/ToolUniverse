"""
Crossref_get_member

Get a specific Crossref member (publisher) by its numeric member id, with full DOI-coverage analy...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Crossref_get_member(
    member_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a specific Crossref member (publisher) by its numeric member id, with full DOI-coverage analy...

    Parameters
    ----------
    member_id : str
        Numeric Crossref member id (e.g., '78' for Elsevier BV, '340' for PLOS). Find...
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
    _args = {k: v for k, v in {"member_id": member_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Crossref_get_member",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Crossref_get_member"]
