"""
ORCID_get_works

Get list of publications and works for an ORCID researcher. Returns titles, publication types, da...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ORCID_get_works(
    operation: str,
    orcid: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get list of publications and works for an ORCID researcher. Returns titles, publication types, da...

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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"operation": operation, "orcid": orcid}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ORCID_get_works",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ORCID_get_works"]
