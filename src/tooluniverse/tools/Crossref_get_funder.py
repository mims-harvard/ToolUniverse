"""
Crossref_get_funder

Get detailed metadata for a specific research funder by its Crossref funder ID. Returns comprehen...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Crossref_get_funder(
    funder_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Optional[dict[str, Any]]:
    """
    Get detailed metadata for a specific research funder by its Crossref funder ID. Returns comprehen...

    Parameters
    ----------
    funder_id : str
        Crossref funder identifier (e.g., '100000001' for NSF, '100000002' for NIH, '...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Optional[dict[str, Any]]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"funder_id": funder_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Crossref_get_funder",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Crossref_get_funder"]
