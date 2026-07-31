"""
ORCID_get_fundings

Get the funding/grant records attached to an ORCID researcher's profile. Returns each grant's tit...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ORCID_get_fundings(
    operation: str,
    orcid: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the funding/grant records attached to an ORCID researcher's profile. Returns each grant's tit...

    Parameters
    ----------
    operation : str
        Operation type
    orcid : str
        ORCID iD in format XXXX-XXXX-XXXX-XXXX (e.g., '0000-0001-5109-3700')
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
        for k, v in {"operation": operation, "orcid": orcid}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ORCID_get_fundings",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ORCID_get_fundings"]
