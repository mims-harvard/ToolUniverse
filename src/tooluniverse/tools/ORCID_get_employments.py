"""
ORCID_get_employments

Get employment and affiliation history for an ORCID researcher. Returns organization names, depar...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ORCID_get_employments(
    operation: str,
    orcid: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get employment and affiliation history for an ORCID researcher. Returns organization names, depar...

    Parameters
    ----------
    operation : str
        Operation type
    orcid : str
        ORCID iD in format XXXX-XXXX-XXXX-XXXX
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

    return get_shared_client().run_one_function(
        {
            "name": "ORCID_get_employments",
            "arguments": {"operation": operation, "orcid": orcid},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ORCID_get_employments"]
